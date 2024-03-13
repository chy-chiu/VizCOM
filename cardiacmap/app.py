import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
from dash.dependencies import ClientsideFunction
from dash_extensions import EventListener
import plotly.express as px
from cardiacmap.data import CascadeDataVoltage
from cardiacmap.callbacks import file_callbacks, PATCH_MAX_FRAME
import json
import numpy as np
import os
import webbrowser
from threading import Timer
from flask_caching import Cache
from cardiacmap.components import (
    image_viewport,
    signal_viewport,
    input_modal,
    navbar,
    file_directory,
)
import time

DEFAULT_POSITION = 64
DEFAULT_IMG = np.zeros((128, 128))
CACHE_FRAME_LIMIT = 100
DEFAULT_SIGNAL = np.zeros((CACHE_FRAME_LIMIT, 128, 128))
DEFAULT_SIGNAL_SLICE = np.zeros((CACHE_FRAME_LIMIT, 128))
DASH_APP_PORT = 8051
IMG_WIDTH = 128
PATCH_SIZE = 8

event_change = {"event": "drag-change", "props": ["type", "srcElement.innerText"]}
event_mousedown = {"event": "drag-mousedown", "props": ["type", "srcElement.innerText"]}
event_mouseup = {"event": "drag-mouseup", "props": ["type", "srcElement.innerText"]}

# This needs to be removed
DUAL_ODD = "dual_odd"  # key to store odd frames in dual mode

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

server = app.server
CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "./cache",
    "CACHE_DEFAULT_TIMEOUT": 28800,
    "CACHE_THRESHOLD": 0,
}

cache = Cache(server, config=CACHE_CONFIG)

showBaseline = False

app.layout = html.Div(
    [
        html.Div(
            [
                dbc.Row(navbar()),
                dbc.Row(file_directory()),
                dbc.Row(
                    [
                        image_viewport(1),
                        signal_viewport(1),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                    },
                ),
                html.Div(
                    dbc.Row(
                        [
                            image_viewport(2),
                            signal_viewport(2),
                        ],
                        style={
                            "display": "flex",
                            "align-items": "center",
                            "justify-content": "center",
                        },
                    ),
                    id="calcium-dual-mode-window",
                    hidden=False,
                ),
            ],
        ),
        # Event listener for drag events
        EventListener(
            html.Div(
                '{"x":-1, "y": -1}',
                id="hidden-div",
            ),
            events=[event_change, event_mouseup, event_mousedown],
            logging=False,
            id="drag-event-listener",
        ),
        # Modal stuff for transforms
        input_modal(),
        ###### Dash store components
        # dcc.Store(id="frame-index", storage_type="session"), # TODO: Move this to movie mode later
        # Position of signal
        dcc.Store(id="signal-position", storage_type="session"),
        # Active signal patch
        dcc.Store(id="active-signal-patch", data=None, storage_type="session"),
        # Store for info for current file metadata. Includes filename, frames
        dcc.Store(id="active-file", data='{"filename": "", "frames": 0, "dual": false}', storage_type="session"),
        # Dummy variable to trigger a refresh
        dcc.Store(id="refresh-dummy", storage_type="session"),
        dcc.Interval(
            id="graph-refresher",
            interval=25,
            n_intervals=0,
            max_intervals=50,
            disabled=True,
        ),
        dcc.Interval(
            id="position-refresher",
            interval=500,
            n_intervals=0,
            # max_intervals=40,
            disabled=True,
        ),
        html.Div(
            "",
            id="hidden-div-2",
        ),
    ]  # + signal_preview_stores # Client-side storage for preview of signal
)


# This input is not directly used but triggers the clientside callback execution on load.
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="setup_drag_listener"),
    Output("hidden-div", "children"),
    Input("refresh-dummy", "data"),
)

app.clientside_callback(
    ClientsideFunction(
        namespace="clientside", function_name="update_signal_clientside"
    ),
    Output("signal-position", "data"),
    Output("graph-signal-1", "figure"),
    Output("graph-signal-2", "figure"),
    # Output("hidden-div-2", "children"),
    Input("graph-refresher", "n_intervals"),
    State("active-signal-patch", "data"),
    State("active-file", "data"),
)

file_callbacks(app, cache)


# To fix this part (!)
@app.callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("refresh-dummy", "data"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def cache_active_signal(_, active_file):

    active_file = json.loads(active_file)
    active_signal=None

    if active_file["filename"]:

        active_signal: CascadeDataVoltage = cache.get(active_file["filename"])
    
    if active_signal: 

        curr_signals = active_signal.get_curr_signal()

        for ix, curr_signal in enumerate(curr_signals):

            N, x, y = curr_signal.shape

            patches = curr_signal.reshape(
                N, x // PATCH_SIZE, PATCH_SIZE, y // PATCH_SIZE, PATCH_SIZE
            )
            patches = patches.transpose(1, 3, 0, 2, 4).reshape(
                (x // PATCH_SIZE) * (y // PATCH_SIZE), N, PATCH_SIZE, PATCH_SIZE
            )

            # print(active_signal.span_T)

            # x = 118
            # y = 101

            # print(curr_signal[:, 118, 101])
            # x_patch = x // PATCH_SIZE
            # y_patch = y // PATCH_SIZE

            # patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

            start = time.time()

            success = cache.set_many(
                {"active-signal-{ix}-{x}".format(ix=ix, x=x): patch for x, patch in enumerate(patches)}
            )
            print("CACHE TIME: ", time.time() - start)
    return np.random.random()


@app.callback(
    Output("active-signal-patch", "data"),
    Output("position-refresher", "disabled"),
    Output("graph-refresher", "disabled"),
    Output("graph-refresher", "n_intervals"),
    Output("graph-refresher", "max_intervals"),
    Input("position-refresher", "n_intervals"),
    Input("drag-event-listener", "n_events"),
    State("drag-event-listener", "event"),
    State("signal-position", "data"),
    prevent_initial_call=True,
)
def update_signal_patch(position_refresh, n_events, event, signal_position):

    disable_refresher = False

    if event is None:
        disable_refresher = True

    else:
        if event["type"] == "drag-mouseup":
            disable_refresher = True

    if signal_position is None:
        signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}
        
    x = signal_position["x"]
    y = signal_position["y"]

    x_patch = x // PATCH_SIZE
    y_patch = y // PATCH_SIZE

    patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

    patch_dict = {}

    for i in range(2):

        curr_signal = cache.get("active-signal-{i}-{x}".format(i=i, x=patch_idx))

        if curr_signal is None:
            # Empty patch of signal
            curr_signal = np.array([np.zeros((PATCH_SIZE, PATCH_SIZE))] * 2)
        else:
            if curr_signal.shape[0] > PATCH_MAX_FRAME:
                curr_signal = curr_signal[:PATCH_MAX_FRAME, :, :]
            

        patch_dict["signal_{i}".format(i=i)] = curr_signal.transpose(1, 2, 0).flatten().tolist()

    ### TODO for Grayson: Add Transform baseline here for patching (?)

    
    return (
        json.dumps(patch_dict),
        disable_refresher,
        disable_refresher,
        0,
        10,
    )


# Is this necessary???
@app.callback(
    Output("refresh-dummy", "data"),
    Input("refresh-dummy", "data"),
    Input("active-file", "data"),
)
def cache_active_signal(_, active_file):

    active_file = json.loads(active_file)

    if active_file["filename"]:

        active_signal: CascadeDataVoltage = cache.get(active_file["filename"])

        cache.set(active_file["filename"], active_signal)

    return np.random.random()


# To delete
# @callback(
#     Output("signal-position", "data"),
#     Input("graph-image-1", "hoverData"),
#     State("signal-position-lock", "data"),
#     State("signal-position", "data"),
#     prevent_initial_call=True,
# )
# def update_signal_position(hoverData, signal_lock, signal_position):
#     if signal_lock:
#         return signal_position
#     else:
#         if hoverData is not None:
#             x = hoverData["points"][0]["x"]
#             y = hoverData["points"][0]["y"]
#         else:
#             # Default to middle for now
#             x = DEFAULT_POSITION
#             y = DEFAULT_POSITION
#         return json.dumps({"x": x, "y": y})


# Key image is used only for position exploration and annotation.
# This should only be called upon changing the active signal
# Movie mode to come later
@app.callback(
    Output("graph-image-1", "figure"),
    Output("graph-image-2", "figure"),
    Input("active-file", "data"),
    prevent_initial_call=True,
)
def update_key_image(active_file):

    active_file = json.loads(active_file)


    if active_file["filename"]:
        active_signal: CascadeDataVoltage = cache.get(active_file["filename"])
    else:
        active_signal = None

    if active_signal is not None:
        key_frame = active_signal.get_keyframe()
    else:
        key_frame = DEFAULT_IMG

    fig = px.imshow(key_frame, binary_string=True)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=5, r=5, t=5, b=5),
        dragmode="orbit",
    )

    # Support for dual mode
    fig_dual = fig
    if active_signal and active_signal.dual_mode:
        key_frame_dual = active_signal.get_keyframe(series=1)
        fig_dual = px.imshow(key_frame_dual, binary_string=True)
        fig_dual.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="orbit",
        )

    return fig, fig_dual

    # ## To move this
    # fig.add_shape(
    #     type="circle",
    #     xref="x",
    #     yref="y",
    #     xsizemode="pixel",
    #     ysizemode="pixel",
    #     xanchor=64,
    #     yanchor=64,
    #     x0=60,
    #     y0=60,
    #     x1=68,
    #     y1=68,
    #     line_color="red",
    #     fillcolor="red",
    #     editable=True,
    # )


# @callback(
#     Output("graph-signal-1", "figure"),
#     Input("signal-position", "data"),
#     Input("active-file", "data"),
#     Input("refresh-dummy", "data"),
#     prevent_initial_call=True,
# )
# def display_signal_data(signal_position, signal_idx, _):
#     if signal_position is not None:
#         signal_position = json.loads(signal_position)
#         x = signal_position["x"]
#         y = signal_position["y"]
#     else:
#         x = 64
#         y = 64

#     if signal_idx is not None:
#         active_signal = signals_all[signal_idx].get_curr_signal()
#     else:
#         active_signal = np.ones((128, 128, 128))

#     global showBaseline
#     if showBaseline:
#         # baseline is calculated for transposed data
#         baselineIndex = (128 * x) + y
#         # get the current signal's baseline
#         bXs, bYs = signals_all[signal_idx].get_baseline()
#         bX = bXs[baselineIndex]
#         bY = bYs[baselineIndex]

#         fig = px.line(active_signal[:, x, y])
#         fig.add_scatter(x=bX, y=bY)
#     else:
#         fig = px.line(active_signal[:, x, y])
#     # fig.add_vline(x=frame_idx)
#     fig.update_layout(showlegend=False)


#     active_signal = cache.get(signal_idx)

#     if active_signal is not None:

#         curr_signal = active_signal.get_curr_signal()

#     else:
#         curr_signal = DEFAULT_SIGNAL

#     fig = px.line(curr_signal[10:, x, y])
#     # fig.add_vline(x=frame_idx)
#     fig.update_layout(showlegend=False)

#     return fig


# ----------------------------For Calcium Modes---------------------------------
# @callback(
#     Output("calcium-mode-badge", "hidden"),
#     Output("calcium-dual-mode-window", "hidden"),
#     Output("calcium-mode-dual", "active"),
#     Output("calcium-mode-reset", "disabled"),
#     Input("calcium-mode-dual", "n_clicks"),
#     Input("calcium-mode-reset", "n_clicks"),
# )
# def enable_calcium_mode_badge_and_buttons(_, __):

#     match ctx.triggered_id:
#         case "calcium-mode-dual":
#             return False, False, True, True
#         case "calcium-mode-reset":
#             return True, True, False, False
#         case _:
#             return False, False, True, False


# @callback(
#     Output("calcium-dual-mode-window", "hidden"),
#     Input("calcium-mode-dual", "active"),
#     Input("active-file", "data"),
#     Input("calcium-mode-reset", "n_clicks"),
# )
# def display_calcium_dual_mode_window(cmd, idx, cmr):
#     global signals_all
#     if ctx.triggered_id == "calcium-mode-reset":
#         if DUAL_ODD in signals_all.keys():
#             signals_all[DUAL_ODD].reset_data()
#         return True
#     elif cmd and idx is not None:
#         return False
#     else:
#         return True

# ---------------------------------------END CALCIUM DUAL MODE------------------------------#


# TODO: Make this clean (?)
@callback(
    Output("modal", "is_open"),
    Output("modal-header", "children"),
    Output("input-one-prompt", "children"),
    Output("input-one", "value"),  # input 1: Sigma/Trim Left
    Output("input-two-prompt", "children"),
    Output("input-two", "value"),  # input 2: Radius/Trim Right
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("trim-signal-button", "n_clicks"),
    Input("baseline-drift-button", "n_clicks"),
    Input("confirm-button", "n_clicks"),
    Input("modal-header", "children"),  # For passing values to closed modal
    Input("input-one-prompt", "children"),
    Input("input-one", "value"),  # For passing values to closed modal
    Input("input-two-prompt", "children"),
    Input("input-two", "value"),  # For passing values to closed modal
    State("modal", "is_open"),
)
def toggle_modal(n1, n2, n3, n4, n5, operation, in1P, in1, in2P, in2, is_open):
    # open modal with spatial
    if "spatial-avg-button" == ctx.triggered_id:
        return True, "Spatial Averaging", "Sigma:", 8, "Radius:", 6

    # open modal with time
    elif "time-avg-button" == ctx.triggered_id:
        return True, "Time Averaging", "Sigma:", 4, "Radius:", 3

    # open modal with trim
    elif "trim-signal-button" == ctx.triggered_id:
        return True, "Trim Signal", "Trim Left:", 100, "Trim Right:", 100

    # open modal with 'remove baseline drift'
    elif "baseline-drift-button" == ctx.triggered_id:
        return True, "Remove Baseline Drift", "Period:", 0, "Threshold:", 0

    # close modal and perform selected operation
    elif "confirm-button" == ctx.triggered_id:
        return False, operation, in1P, in1, in2P, in2

    # ignore updates to inputs
    elif "input-one" == ctx.triggered_id or "input-two" == ctx.triggered_id:
        return True, operation, in1P, in1, in2P, in2

    # initial call
    # if you see "header" in modal, something went wrong
    return is_open, "HEADER", "In1:", 0, "In2:", 0


@callback(
    Output("mode-select-parent", "hidden"),
    Output("avg-mode-parent", "hidden"),
    Output("baseline-mode-parent", "hidden"),
    Output("input-one-parent", "hidden"),
    Output("input-two-parent", "hidden"),
    Input("avg-mode-select", "value"),
    Input("baseline-mode-select", "value"),
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("trim-signal-button", "n_clicks"),
    Input("baseline-drift-button", "n_clicks"),
)
def hide_modal_components(avgVal, baseVal, n1, n2, n3, n4):
    # Return Elements correspond to hiding:
    # Dropdown Menu, in1 (sigma/trim_left), in2(radius/trim_right)

    # when modal is opened with spatial or time, or on change of mode
    if (
        "spatial-avg-button" == ctx.triggered_id
        or "time-avg-button" == ctx.triggered_id
        or "avg-mode-select" == ctx.triggered_id
    ):
        # Hide: baseline mode select
        if avgVal == "Gaussian":
            return False, False, True, False, False
        # Hide: baseline mode select, in1
        elif avgVal == "Uniform":
            return False, False, True, True, False
        # nothing is selected for dropdown, show everything except baseline mode select
        elif avgVal is None:
            return False, False, True, False, False

    # when modal is opened with remove baseline drift, or on change of mode
    elif (
        "baseline-drift-button" == ctx.triggered_id
        or "baseline-mode-select" == ctx.triggered_id
    ):
        # Hide: avg mode select, in1
        if baseVal == "Threshold":
            return False, True, False, True, False
        # Hide: avg mode select, in2
        elif baseVal == "Period":
            return False, True, False, False, True
        # nothing is selected for dropdown, show everything except avg mode select
        elif baseVal is None:
            return False, True, False, False, False

    # when modal is opened with trim
    elif "trim-signal-button" == ctx.triggered_id:
        # show in1 (Trim Left), in2 (Trim Right)
        return True, True, True, False, False

    # Show everything
    else:
        return False, False, False, False, False


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("modal-header", "children"),
    Input("avg-mode-select", "value"),
    Input("baseline-mode-select", "value"),
    Input("input-one", "value"),
    Input("input-two", "value"),
    Input("confirm-button", "n_clicks"),
    Input("calcium-mode-dual", "active"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def perform_operation(header, avg_mode, base_mode, in1, in2, _, __, active_file):

    active_file = json.loads(active_file)

    if active_file["filename"]:
        active_signal: CascadeDataVoltage = cache.get(active_file["filename"])
    else:
        return np.random.random()

    # if the modal was closed by the 'perform average' button
    if "confirm-button" == ctx.triggered_id:
        # if bad inputs
        # should we give a warning?
        if in1 is None or in1 < 0:
            in1 = 0
        if in2 is None or in2 < 0:
            in2 = 0

        # TODO: FIX THIS PART YO
        operation = header.split()[0]
        # Time averaging
        if operation == "Time":
            signals_all[signal_idx].perform_average("time", in1, in2, mode=mode)
            if cmd and DUAL_ODD in signals_all.keys():
                signals_all[DUAL_ODD].perform_average("time", in1, in2, mode=mode)
            return np.random.random()
        # Spatial Averaging
        elif operation == "Spatial":
            signals_all[signal_idx].perform_average("spatial", in1, in2, mode=mode)
            if cmd and DUAL_ODD in signals_all.keys():
                signals_all[DUAL_ODD].perform_average("spatial", in1, in2, mode=mode)
            return np.random.random()
        # Trim Signal
        elif operation == "Trim":
            signals_all[signal_idx].trim_data(in1, in2)
            if cmd and DUAL_ODD in signals_all.keys():
                signals_all[DUAL_ODD].trim_data(in1, in2)
            return np.random.random()
        # Remove Baseline Drift (Just get the baseline, it will not be removed until user approval)
        elif operation == "Remove":
            if baseMode == "Period":
                val = in1
            elif baseMode == "Threshold":
                val = in2
            else:
                raise Exception("baseline mode must be Period or Threshold")

            signals_all[signal_idx].calc_baseline(baseMode, val)
            global showBaseline
            showBaseline = True
        return np.random.random()


## FIX THIS SHIT
@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("invert-signal-button", "n_clicks"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def performInvert(_, signal_idx):

    active_signal: CascadeDataVoltage = cache.get(signal_idx)

    active_signal.invert_data()
    active_signal.normalize()

    cache.set(signal_idx, active_signal)


def perform_invert(_, signal_idx):
    signals_all[signal_idx].invert_data()
    if DUAL_ODD in signals_all.keys():
        signals_all[DUAL_ODD].invert_data()

    return np.random.random()


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("confirm-baseline-button", "n_clicks"),
    Input("cancel-baseline-button", "n_clicks"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def performDriftRemoval(n1, n2, signal_idx):
    if "confirm-baseline-button" == ctx.triggered_id:
        signals_all[signal_idx].remove_baseline_drift()
        signals_all[signal_idx].normalize()
    else:
        signals_all[signal_idx].reset_baseline()
    global showBaseline
    showBaseline = False


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("normalize-button", "n_clicks"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def performNormalize(_, signal_idx):
    signals_all[signal_idx].normalize()


## FIX THIS AS WELL PLEASE
@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("reset-data-button", "n_clicks"),
    State("active-file", "data"),
    prevent_initial_call=True,
)
def reset_data(_, signal_idx):

    active_signal: CascadeDataVoltage = cache.get(signal_idx)

    active_signal.reset_data()

    cache.set(signal_idx, active_signal)

    return np.random.random()

    signals_all[signal_idx].reset_data()
    if DUAL_ODD in signals_all.keys():
        signals_all[DUAL_ODD].reset_data()
    return np.random.random()


# @app.callback(
#     Output({'type': "cache-signal-preview", 'index': ALL}, 'data'),
#     Input("refresh-dummy", "data"),
#     State("active-file", "data"),
#     prevent_initial_call=True,
# )
# def load_data(_, signal_idx):
#     active_signal: CascadeDataVoltage = cache.get(signal_idx)
#     if active_signal is not None:
#         curr_signal = active_signal.get_curr_signal()[CACHE_FRAME_LIMIT, :, :]
#     else:
#         curr_signal = DEFAULT_SIGNAL

#     print(curr_signal[:, 0, :].shape)

#     return curr_signal.transpose((1, 0, 2)).tolist()


# @callback(
#         Output(),

# )
# def update_signal_preview():
#     return


# ===========================


# ================ This might be useful later still fml

# @callback(
#     Output("frame-index", "data"),
#     Input("frame-slider", "value"),
# )
# def update_frame_idx(frame_idx):
#     return frame_idx


# @callback(
#     Output("frame-slider", "value"),
#     Input("graph-signal", "clickData"),
#     prevent_initial_call=True,
# )
# def update_frame_slider_idx(clickData):
#     if clickData is not None:
#         frame_idx = clickData["points"][0]["pointIndex"]
#     return frame_idx


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":

    if not DEBUG:
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)

    cache.clear()
