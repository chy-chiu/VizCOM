import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
from dash.dependencies import ClientsideFunction
from dash_extensions import EventListener
import plotly.express as px
from cardiacmap.data import CascadeDataVoltage
from cardiacmap.callbacks import file_callbacks, signal_callbacks, transform_callbacks, modal_callbacks
import json
import numpy as np
import webbrowser
from threading import Timer
from flask_caching import Cache
from cardiacmap.components import (
    signal_viewer,
    input_modal,
    navbar,
    file_directory,
    transform_modals,
)
import time

DEFAULT_POSITION = 64
DEFAULT_IMG = np.zeros((128, 128))
CACHE_FRAME_LIMIT = 100
DEFAULT_SIGNAL = np.zeros((CACHE_FRAME_LIMIT, 128, 128))
DEFAULT_SIGNAL_SLICE = np.zeros((CACHE_FRAME_LIMIT, 128))
DASH_APP_PORT = 8051

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

# TODO: 
"""
1. Further optimize baseline drift
2. Re-normalize data to 0 etc
3. Further fixes on calcium mode including baseline drift stuff
"""

app.layout = html.Div(
    [
        html.Div(
            [
                dbc.Row(navbar()),
                dbc.Row(file_directory()),
                dbc.Card(signal_viewer(1), className="signal-viewer"),
                html.Div(
                    dbc.Card(signal_viewer(2)),
                    id="calcium-dual-mode-window",
                    hidden=False,
                ),
                # Another div here for APD / DI graphing, and other tertiary graphs
            ],
        ),
        # Event listener for drag events
        EventListener(
            html.Div(
                '{"x": 64, "y": 64}',
                id="hidden-div",
            ),
            events=[event_change, event_mouseup, event_mousedown],
            logging=False,
            id="drag-event-listener",
        ),
        # Modal stuff for transforms
        input_modal(),
        transform_modals(1),
        transform_modals(2),
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

file_callbacks(app, cache)
signal_callbacks(app, cache)
modal_callbacks(app)
transform_callbacks(app, cache)


# Is this necessary???

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
    Output("graph-image-1", "figure", allow_duplicate=True),
    Output("graph-image-2", "figure", allow_duplicate=True),
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


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":

    if not DEBUG:
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)

    cache.clear()
