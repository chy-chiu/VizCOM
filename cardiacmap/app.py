import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
from dash.dependencies import ClientsideFunction
from dash_extensions import EventListener
from dash.exceptions import PreventUpdate
import plotly.express as px
from cardiacmap.data import cascade_import, CascadeDataVoltage
from cardiacmap.transforms import TimeAverage, SpatialAverage
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
PATCH_SIZE = 16

event = {"event": "change", "props": ["srcElement.innerText"]}

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

server = app.server
CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "./cache",
    "CACHE_DEFAULT_TIMEOUT": 28800,
}

cache = Cache(server, config=CACHE_CONFIG)

app.layout = html.Div(
    [
        html.Div(
            [
                dbc.Row(navbar()),
                dbc.Row(file_directory()),
                dbc.Row(
                    [
                        image_viewport(),
                        signal_viewport(),
                    ],
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                    },
                ),
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
        # Dummy variable to trigger a refresh
        dcc.Store(id="refresh-dummy", storage_type="session"),
        EventListener(
            html.Div(
                "",
                id="hidden-div",
            ),
            events=[event],
            logging=True,
            id="drag-event-listener",
        ),
    ]  # + signal_preview_stores # Client-side storage for preview of signal
)


# This input is not directly used but triggers the clientside callback execution on load.
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="setup_drag_listener"),
    Output("hidden-div", "children"),
    Input("refresh-dummy", "data"),
)


@callback(
    Output("active-file-idx", "data"),
    Input("file-directory-dropdown", "value"),
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
    else:
        active_signal = None

    if active_signal is not None:
        print("caching signal")
        curr_signal = active_signal.get_curr_signal()

        N, x, y = curr_signal.shape

        patches = curr_signal.reshape(N, x//PATCH_SIZE, PATCH_SIZE, y//PATCH_SIZE, PATCH_SIZE)
        patches = patches.transpose(1, 3, 0, 2, 4).reshape((x // PATCH_SIZE) * (y // PATCH_SIZE), N , PATCH_SIZE, PATCH_SIZE)
        print(len(patches))

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
    Output("graph-image", "figure"),
    Input("active-file-idx", "data"),
)
def update_image(signal_idx):

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
#     Input("cache-signal-preview", "data"),
# )
# def display_signal_data_preview(signal_position, cached_signal):
#     signal_position = json.loads(signal_position)
#     x = signal_position["x"]
#     y = signal_position["y"]
#     fig = px.line(cached_signal[10:, x, y])
#     fig.update_layout(showlegend=False)

#     return fig

# Drag event listener - Clientside callback
# app.clientside_callback(
#         """
#         function(n_events, event) {
#             return event['srcElement.innerText'];
#         }
#         """,
#         Output('signal-position', 'data'),
#         Input('drag-event-listener', 'n_events'),
#         State('drag-event-listener', 'event')
#     )


# # This will need to be converted to a clientside callback
# @callback(
#     Output("graph-signal", "figure"),
#     Input("signal-position", "data"),
#     Input("active-file-idx", "data"),
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

#     active_signal = cache.get(signal_idx)

#     if active_signal is not None:

#         curr_signal = active_signal.get_curr_signal()

#     else:
#         curr_signal = DEFAULT_SIGNAL

#     fig = px.line(curr_signal[10:, x, y])
#     # fig.add_vline(x=frame_idx)
#     fig.update_layout(showlegend=False)

#     return fig


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
    Input("confirm-button", "n_clicks"),
    Input("modal-header", "children"),  # For passing values to closed modal
    Input("input-one-prompt", "children"),
    Input("input-one", "value"),  # For passing values to closed modal
    Input("input-two-prompt", "children"),
    Input("input-two", "value"),  # For passing values to closed modal
    State("modal", "is_open"),
)
def toggle_modal(n1, n2, n3, n4, operation, in1P, in1, in2P, in2, is_open):
    # open modal with spatial
    if "spatial-avg-button" == ctx.triggered_id:
        return True, "Spatial Averaging", "Sigma:", 8, "Radius:", 6

    # open modal with time
    elif "time-avg-button" == ctx.triggered_id:
        return True, "Time Averaging", "Sigma:", 4, "Radius:", 3

    # open modal with trim
    elif "trim-signal-button" == ctx.triggered_id:
        return True, "Trim Signal", "Trim Left:", 100, "Trim Right:", 100

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
    Output("input-one-parent", "hidden"),
    Output("input-two-parent", "hidden"),
    Input("avg-mode-select", "value"),
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("trim-signal-button", "n_clicks"),
)
def hide_modal_components(ddVal, n1, n2, n3):
    # Return Elements correspond to hiding:
    # Dropdown Menu, in1 (sigma/trim_left), in2(radius/trim_right)

    # when modal is opened with spatial or time, or on change of mode
    if (
        "spatial-avg-button" == ctx.triggered_id
        or "time-avg-button" == ctx.triggered_id
        or "avg-mode-select" == ctx.triggered_id
    ):
        # show dropdown, in1 (sigma), in2 (radius)
        if ddVal == "Gaussian":
            return False, False, False
        # show dropdown, in2 (radius)
        elif ddVal == "Uniform":
            return False, True, False
        # nothing is selected for dropdown, show everything
        elif ddVal is None:
            return False, False, False

    # when modal is opened with trim
    elif "trim-signal-button" == ctx.triggered_id:
        # show in1 (Trim Left), in2 (Trim Right)
        return True, False, False

    # Show everything
    else:
        return False, False, False


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
    Input("input-one", "value"),
    Input("input-two", "value"),
    Input("confirm-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performOperation(header, mode, in1, in2, _, signal_idx):

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
            active_signal.perform_average("time", in1, in2, mode=mode)

        # Spatial Averaging
        elif operation == "Spatial":
            active_signal.perform_average("time", in1, in2, mode=mode)

        # Trim Signal
        elif operation == "Trim":
            active_signal.perform_average("time", in1, in2, mode=mode)

    # After any transformations to the signal, we will need to save the active signal to the cache again
    cache.set(signal_idx, active_signal)

    return np.random.random()


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("invert-signal-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performInvert(_, signal_idx):

    active_signal: CascadeDataVoltage = cache.get(signal_idx)

    active_signal.invert_data()

    cache.set(signal_idx, active_signal)

    return np.random.random()


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


@callback(
    Output("signal-position", "data"),
    Output("graph-signal", "figure"),
    Input("active-file-idx", "data"),
    Input("refresh-dummy", "data"),
    Input("drag-event-listener", "n_events"),
    State("drag-event-listener", "event"),
    prevent_initial_call=True,
)
def update_signal_data(signal_idx, _, n_events, event):

    if event is None:
        signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}
    else:
        signal_position = json.loads(event["srcElement.innerText"])


    x = signal_position["x"]
    y = signal_position["y"]

    x_patch = x // PATCH_SIZE
    x_offset = x % PATCH_SIZE
    y_patch = y // PATCH_SIZE
    y_offset = y % PATCH_SIZE

    patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

    start = time.time()

    curr_signal = cache.get("active-signal-{x}".format(x=patch_idx))
    print("fetch", time.time() - start)

    if curr_signal is None:
        curr_signal = np.zeros(1000)
    else:
        curr_signal = curr_signal[:, x_offset, y_offset]

    start = time.time()
    fig = px.line(curr_signal)
    # fig.add_vline(x=frame_idx)
    fig.update_layout(showlegend=False)
    print("update graph", time.time() - start)

    return json.dumps(signal_position), fig


# ===========================


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":

    if not DEBUG:
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)

    cache.clear()
