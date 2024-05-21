import json
import time
import webbrowser
from threading import Timer

import dash_bootstrap_components as dbc
import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from dash.dependencies import ClientsideFunction
from flask_caching import Cache
import flask
import os

# from cardiacmap.data import CascadeDataVoltage
from cardiacmap.callbacks import (
    file_callbacks,
    image_callbacks,
    modal_callbacks,
    signal_callbacks,
    transform_callbacks,
    video_callbacks
)
from cardiacmap.components import file_directory, metadata_bar, navbar, signal_viewer

DEFAULT_POSITION = 64
CACHE_FRAME_LIMIT = 100
DEFAULT_SIGNAL = np.zeros((CACHE_FRAME_LIMIT, 128, 128))
DEFAULT_SIGNAL_SLICE = np.zeros((CACHE_FRAME_LIMIT, 128))
DASH_APP_PORT = 8051

indexed_component_id = lambda idx, n: {"type": idx, "index": n}

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

# Dual cache configuration.
# File cache caches signals to the local file system, for when we want to hot swap between different files.
FILE_CACHE_CONFIG = {
    "CACHE_TYPE": "FileSystemCache",
    "CACHE_DIR": "./cache",
    "CACHE_DEFAULT_TIMEOUT": 28800,
    "CACHE_THRESHOLD": 0,
}
file_cache = Cache(app.server, config=FILE_CACHE_CONFIG)

# Signal cache uses a SimpleCache, which is essentially a global Python dictionary which stores all files in memory.
SIGNAL_CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 28800,
    "CACHE_THRESHOLD": 0,
}
signal_cache = Cache(app.server, config=SIGNAL_CACHE_CONFIG)


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
                dbc.Row(metadata_bar()),
                dbc.Card(signal_viewer(0), className="signal-viewer"),
                html.Div(
                    dbc.Card(signal_viewer(1), className="signal-viewer"),
                    id="calcium-dual-mode-window",
                    hidden=True,
                ),
                # Another div here for APD / DI graphing, and other tertiary graphs
            ],
        ),
        # ###### Dash store components
        # # Store for info for current file metadata. Includes filename, frames - Probably redundant
        # dcc.Store(
        #     id="active-file",
        #     data='{"filename": "", "frames": 0, "dual": false}',
        #     storage_type="session",
        # ),
        # # Also probably redundant
        # dcc.Store(id="calcium-mode", data="single"),
    ]
)

@app.server.route('/.videos/<path:path>')
def serve_static(path):
    root_dir = os.getcwd()
    return flask.send_from_directory(os.path.join(root_dir, '.videos'), path)

# This input is not directly used but triggers the clientside callback execution on load.
app.clientside_callback(
    ClientsideFunction(namespace="clientside", function_name="setup_drag_listener"),
    Output(indexed_component_id("hidden-div", MATCH), "children"),
    Input(indexed_component_id("refresh-signal", MATCH), "data"),
    State(indexed_component_id("graph-image", MATCH), "id"),
    State(indexed_component_id("hidden-div", MATCH), "id"),
)

file_callbacks(app, file_cache, signal_cache)
image_callbacks(app, signal_cache)
signal_callbacks(app, signal_cache)
modal_callbacks(app)
transform_callbacks(app, signal_cache)
video_callbacks(app, signal_cache)


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":
    if not DEBUG:
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)

    file_cache.clear()
    signal_cache.clear()

    input("\nApplication terminated.\nIf there are any error messages above, please copy and paste the error message above to the team for debugging.\nPress Enter to Continue...")
