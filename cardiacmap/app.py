
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
from dash.dependencies import ClientsideFunction
from dash_extensions import EventListener
from dash.exceptions import PreventUpdate
import plotly.express as px
from cardiacmap.data import cascade_import, CascadeDataVoltage
from cardiacmap.model.calcium_import import VoltageCalciumImport
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
DUMMY_FILENAME = "put .dat files here"
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
                html.Div(dbc.Row(
                    [
                        image_viewport(2),
                        signal_viewport(2),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                    },
                ), id="calcium-dual-mode-window", hidden=True)
            ],
        ),
        # Modal stuff for transforms
        input_modal(),
        # Dash store components
        # dcc.Store(id="frame-index", storage_type="session"), # TODO: Move this to movie mode later
        # Position of signal
        dcc.Store(id="signal-position", storage_type="session"),
        # Current file when there are multiple files
        dcc.Store(id="active-file-idx", storage_type="session"),
        dcc.Store(id="active-signal-patch", data=None, storage_type="session"),
        # Dummy variable to trigger a refresh
        dcc.Store(id="signal-position-lock", data=False, storage_type="session"),
        dcc.Store(id="signal-position-calcium", storage_type="session"),
        dcc.Store(id="signal-position-lock-calcium", data=False, storage_type="session"),
        dcc.Store(
            id="active-file-idx", storage_type="session"
        ),  # Current file when there are multiple files
        dcc.Store(id="refresh-dummy", storage_type="session"),
        EventListener(
            html.Div(
                '{"x":-1, "y": -1}',
                id="hidden-div",
            ),
            events=[event_change, event_mouseup, event_mousedown],
            logging=False,
            id="drag-event-listener",
        ),
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
    ClientsideFunction(namespace="clientside", function_name="update_signal_clientside"),
    Output("signal-position", "data"),
    Output("graph-signal", "figure"),
    # Output("hidden-div-2", "children"),
    Input("graph-refresher", "n_intervals"),
    State("active-signal-patch", "data"),
)


@callback(
    Output("active-signal-patch", "data"),
    Output("position-refresher", "disabled"),
    # Output("position-refresher", "n_intervals"),
    # Output("position-refresher", "max_intervals"),
    Output("graph-refresher", "disabled"),
    Output("graph-refresher", "n_intervals"),
    Output("graph-refresher", "max_intervals"),
    Input("position-refresher", "n_intervals"),
    Input("drag-event-listener", "n_events"),
    State("drag-event-listener", "event"),
    State("signal-position", "data"),
    prevent_initial_call=True,
)
def update_signal_data(position_refresh, n_events, event, signal_position):
    
    disable_refresher = False

    if event is None:
        signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}
        disable_refresher = True

    else:
        if event["type"] == "drag-mouseup":
            disable_refresher = True

    x = signal_position["x"]
    y = signal_position["y"]

    x_patch = x // PATCH_SIZE
    y_patch = y // PATCH_SIZE

    patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

    curr_signal = cache.get("active-signal-{x}".format(x=patch_idx))

    if curr_signal is None:
        # Empty patch of signal
        curr_signal = np.array([np.zeros((PATCH_SIZE, PATCH_SIZE))]*10)
    else:
        curr_signal = curr_signal[:, :, :]

    curr_signal = curr_signal.transpose(1,2,0)

    return json.dumps(curr_signal.flatten().tolist()), disable_refresher, disable_refresher, 0, 10



@callback(
    Output("active-file-idx", "data"),
    Input("file-directory-dropdown", "value"),
    Input("calcium-mode-badge", "hidden"),
    Input("calcium-mode-even", "active"),
    Input("calcium-mode-odd", "active"),
    Input("calcium-mode-dual", "active"),
    prevent_initial_call=True,
)
def load_file(value):

    if value is not None and cache.get(value) is None:
        active_signal = CascadeDataVoltage.from_dat(value)
        cache.set(value, active_signal)

    return value  # , signal_preview


@callback(
    Output("refresh-dummy", "data"),
    Input("refresh-dummy", "data"),
    Input("active-file-idx", "data"),
)
def cache_active_signal(_, active_file_idx):

    if active_file_idx is not None:
        active_signal: CascadeDataVoltage = cache.get(active_file_idx)
def load_file(value, hidden_calcium_mode, e, o, d):
    global signals_all

    if hidden_calcium_mode and value is not None and value not in signals_all.keys():
        signals_all[value] = CascadeDataVoltage.from_dat(value)
    elif not hidden_calcium_mode and value is not None:
        if e:
            c = VoltageCalciumImport('e', value)
            signals_all[value] = c.get_data()
        if o:
            c = VoltageCalciumImport('o', value)
            signals_all[value] = c.get_data()
        if d:
            c_e = VoltageCalciumImport('e', value)
            signals_all[value] = c_e.get_data()
            c_o = VoltageCalciumImport('o', value)
            signals_all[DUAL_ODD] = c_o.get_data()

    return value


# ================

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


@callback(
    Output("signal-position", "data"),
    Input("graph-image-1", "hoverData"),
    State("signal-position-lock", "data"),
    State("signal-position", "data"),
    prevent_initial_call=True,
)
def update_signal_position(hoverData, signal_lock, signal_position):
    if signal_lock:
        return signal_position
    else:
        if hoverData is not None:
            x = hoverData["points"][0]["x"]
            y = hoverData["points"][0]["y"]
        else:
            # Default to middle for now
            x = DEFAULT_POSITION
            y = DEFAULT_POSITION
        return json.dumps({"x": x, "y": y})


@callback(
    Output("signal-position-lock", "data"),
    Input("graph-image-1", "clickData"),
    State("signal-position-lock", "data"),
    prevent_initial_call=True,
)
def update_signal_lock(_, signal_lock):
    if signal_lock:
        return False
    else:
        active_signal = None

    if active_signal is not None:
        print("caching signal")
        curr_signal = active_signal.get_curr_signal()

        N, x, y = curr_signal.shape

        patches = curr_signal.reshape(
            N, x // PATCH_SIZE, PATCH_SIZE, y // PATCH_SIZE, PATCH_SIZE
        )
        patches = patches.transpose(1, 3, 0, 2, 4).reshape(
            (x // PATCH_SIZE) * (y // PATCH_SIZE), N, PATCH_SIZE, PATCH_SIZE
        )
        print(len(patches))

        print(active_signal.span_T)
        
        x = 119
        y = 14

        print(curr_signal[:, 119, 14])
        x_patch = x // PATCH_SIZE
        y_patch = y // PATCH_SIZE

        patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

        start = time.time()

        success = cache.set_many(
            {"active-signal-{x}".format(x=x): patch for x, patch in enumerate(patches)}
        )
        print(cache.has("active-signal-63"))
        print(time.time() - start)
    return np.random.random()


# This should only be called upon changing the active signal
# Movie mode to come later
@callback(
    Output("graph-image-1", "figure"),
    Input("active-file-idx", "data"),
)
def update_image(signal_idx):
    global signals_all

    if signal_idx is not None:
        active_signal: CascadeDataVoltage = cache.get(signal_idx)
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
    ## To move this
    fig.add_shape(
        type="circle",
        xref="x",
        yref="y",
        xsizemode="pixel",
        ysizemode="pixel",
        xanchor=64,
        yanchor=64,
        x0=60,
        y0=60,
        x1=68,
        y1=68,
        line_color="red",
        fillcolor="red",
        editable=True,
    )

    return fig


# @callback(
#     Output("graph-signal", "figure"),
#     Input("signal-position", "data"),
# )
# def display_signal_data_preview(signal_position, cached_signal):
#     signal_position = json.loads(signal_position)
#     x = signal_position["x"]
#     y = signal_position["y"]
#     fig = px.line(cached_signal[10:, x, y])
#     fig.update_layout(showlegend=False)

#     return fig
@callback(
    Output("graph-signal-1", "figure"),
    Input("signal-position", "data"),
    Input("active-file-idx", "data"),
    Input("refresh-dummy", "data"),
    prevent_initial_call=True,
)
def display_signal_data(signal_position, signal_idx, _):
    if signal_position is not None:
        signal_position = json.loads(signal_position)
        x = signal_position["x"]
        y = signal_position["y"]
    else:
        x = 64
        y = 64

    if signal_idx is not None:
        active_signal = signals_all[signal_idx].get_curr_signal()
    else:
        active_signal = np.ones((128, 128, 128))
        
    global showBaseline
    if showBaseline:
        # baseline is calculated for transposed data
        baselineIndex = (128 * x) + y
        # get the current signal's baseline
        bXs, bYs = signals_all[signal_idx].get_baseline()
        bX = bXs[baselineIndex]
        bY = bYs[baselineIndex]

        fig = px.line(active_signal[:, x, y])
        fig.add_scatter(x=bX, y=bY)
    else:
        fig = px.line(active_signal[:, x, y])
    # fig.add_vline(x=frame_idx)
    fig.update_layout(showlegend=False)

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
@callback(
    Output("calcium-mode-badge", "hidden"),
    Output("calcium-mode-even", "active"),
    Output("calcium-mode-odd", "active"),
    Output("calcium-mode-dual", "active"),
    Output("calcium-mode-reset", "disabled"),
    Input("calcium-mode-even", "n_clicks"),
    Input("calcium-mode-odd", "n_clicks"),
    Input("calcium-mode-dual", "n_clicks"),
    Input("calcium-mode-reset", "n_clicks"),
)
def enable_calcium_mode_badge_and_buttons(e, o, d, r):
    match ctx.triggered_id:
        case "calcium-mode-even":
            return False, True, False, False, False
        case "calcium-mode-odd":
            return False, False, True, False, False
        case "calcium-mode-dual":
            return False, False, False, True, False
        case "calcium-mode-reset":
            return True, False, False, False, True
        case _:
            return True, False, False, False, True


@callback(
    Output("signal-position-calcium", "data"),
    Input("graph-image-2", "hoverData"),
    State("signal-position-lock-calcium", "data"),
    State("signal-position-calcium", "data"),
    prevent_initial_call=True,
)
def update_signal_position(hover_data, signal_lock, signal_position):
    if signal_lock:
        return signal_position
    else:
        if hover_data is not None:
            x = hover_data["points"][0]["x"]
            y = hover_data["points"][0]["y"]
        else:
            # Default to middle for now
            x = DEFAULT_POSITION
            y = DEFAULT_POSITION
        return json.dumps({"x": x, "y": y})


@callback(
    Output("signal-position-lock-calcium", "data"),
    Input("graph-image-2", "clickData"),
    State("signal-position-lock-calcium", "data"),
    prevent_initial_call=True,
)
def update_signal_lock(_, signal_lock):
    if signal_lock:
        return False
    else:
        return True


@callback(
    Output("graph-image-2", "figure"),
    Input("active-file-idx", "data"),
)
def update_image(signal_idx):
    global signals_all

    if signal_idx is not None and DUAL_ODD in signals_all.keys():
        key_frame = signals_all[DUAL_ODD].get_keyframe()
    else:
        key_frame = DEFAULT_IMG

    fig = px.imshow(key_frame, binary_string=True)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=5, r=5, t=5, b=5),
    )

    return fig


@callback(
    Output("graph-signal-2", "figure"),
    Input("signal-position-calcium", "data"),
    Input("active-file-idx", "data"),
    Input("refresh-dummy", "data"),
    prevent_initial_call=True,
)
def display_signal_data(signal_position, signal_idx, _):
    if signal_position is not None:
        signal_position = json.loads(signal_position)
        x = signal_position["x"]
        y = signal_position["y"]
    else:
        x = 64
        y = 64

    if signal_idx is not None and DUAL_ODD in signals_all.keys():
        active_signal = signals_all[DUAL_ODD].get_curr_signal()
    else:
        active_signal = np.ones((128, 128, 128))

    fig = px.line(active_signal[10:, x, y])
    fig.update_layout(showlegend=False)

    return fig


@callback(
    Output("calcium-dual-mode-window", "hidden"),
    Input("calcium-mode-dual", "active"),
    Input("active-file-idx", "data"),
    Input("calcium-mode-reset", "n_clicks")
)
def display_calcium_dual_mode_window(cmd, idx, cmr):
    global signals_all
    if ctx.triggered_id == "calcium-mode-reset":
        if DUAL_ODD in signals_all.keys():
            signals_all[DUAL_ODD].reset_data()
        return True
    elif cmd and idx is not None:
        return False
    else:
        return True

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
    if ("spatial-avg-button" == ctx.triggered_id 
        or "time-avg-button" == ctx.triggered_id 
        or "avg-mode-select" == ctx.triggered_id):
        # Hide: baseline mode select
        if avgVal == 'Gaussian':
            return False, False, True, False, False
        # Hide: baseline mode select, in1
        elif avgVal == 'Uniform':
            return False, False, True, True, False
        # nothing is selected for dropdown, show everything except baseline mode select
        elif avgVal is None:
            return False, False, True, False, False
        
    # when modal is opened with remove baseline drift, or on change of mode
    elif ("baseline-drift-button" == ctx.triggered_id
        or "baseline-mode-select" == ctx.triggered_id):
        # Hide: avg mode select, in1
        if baseVal == 'Threshold':
            return False, True, False, True, False
        # Hide: avg mode select, in2
        elif baseVal == 'Period':
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
    Output("file-directory-dropdown", "options"),
    Input("refresh-folder-button", "n_clicks"),
)
def update_file_directory(_):

    # To convert this to settings.json
    file_list = os.listdir("./data")

    if DUMMY_FILENAME in file_list:
        file_list.pop(file_list.index(DUMMY_FILENAME))

    return file_list


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("modal-header", "children"),
    Input("avg-mode-select", "value"),
    Input("baseline-mode-select", "value"),
    Input("input-one", "value"),
    Input("input-two", "value"),
    Input("confirm-button", "n_clicks"),
    Input("calcium-mode-dual", "active"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performOperation(header, avgMode, baseMode, in1, in2, _, signal_idx):

    if signal_idx is not None:
        active_signal: CascadeDataVoltage = cache.get(signal_idx)
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
            if baseMode == 'Period':
                val = in1
            elif baseMode == 'Threshold':
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
    State("active-file-idx", "data"),
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
    State("active-file-idx", "data"),
    prevent_initial_call=True
)
def performDriftRemoval(n1, n2, signal_idx):
    if ("confirm-baseline-button" == ctx.triggered_id):
        signals_all[signal_idx].remove_baseline_drift()
        signals_all[signal_idx].normalize()
    else:
        signals_all[signal_idx].reset_baseline()
    global showBaseline
    showBaseline = False
    
@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("normalize-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True
)
def performNormalize(_, signal_idx):
    signals_all[signal_idx].normalize()

## FIX THIS AS WELL PLEASE
@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("reset-data-button", "n_clicks"),
    State("active-file-idx", "data"),
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
#     State("active-file-idx", "data"),
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


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":

    if not DEBUG:
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)

    cache.clear()
