import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback
import plotly.express as px

from cardiacmap.data import cascade_import, CascadeDataVoltage
from cardiacmap.transforms import TimeAverage, SpatialAverage
import json

import numpy as np

from cardiacmap.components import (
    image_viewport,
    signal_viewport,
    input_modal,
    buttons_table,
    navbar,
    file_directory,
)

DEFAULT_POSITION = 64
EMPTY_IMG = np.zeros((128, 128))
DASH_APP_PORT = 8051
DUMMY_FILENAME = "put .dat files here"

import os

import webbrowser
from threading import Timer

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

# server = app.server
# CACHE_CONFIG = {
#     "DEBUG": True,
#     "CACHE_TYPE": "SimpleCache",
#     "CACHE_DEFAULT_TIMEOUT": 7200,
# }

"""This dict stores ALL the signals that has been uploaded. 
Currently it is stored as a unsafe, global variable. 
To explore using caching e.g. flask-cache to make it more stable / safe?
Or that might not be necessary since this app is meant to be a one
and done deal."""
signals_all = {}

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
        ## Modal stuff for transforms
        input_modal(),
        buttons_table(),
        
        # Dash store components
        # dcc.Store(id="frame-index", storage_type="session"), # TODO: Move this to movie mode later
        dcc.Store(id="signal-position", storage_type="session"),
        dcc.Store(
            id="active-file-idx", storage_type="session"
        ),  # Current file when there are multiple files
        dcc.Store(id="refresh-dummy", storage_type="session"),
    ]
)


@callback(
    Output("active-file-idx", "data"),
    Input("file-directory-dropdown", "value"),
    prevent_initial_call=True,
)
def load_file(value):

    global signals_all

    if value is not None and value not in signals_all.keys():
        signals_all[value] = CascadeDataVoltage.from_dat(value)

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
    Input("graph-image", "clickData"),
    prevent_initial_call=True,
)
def update_signal_position(clickData):
    if clickData is not None:
        x = clickData["points"][0]["x"]
        y = clickData["points"][0]["y"]
    else:
        # Default to middle for now
        x = DEFAULT_POSITION
        y = DEFAULT_POSITION
    return json.dumps({"x": x, "y": y})


# This should only be called upon changing the signal
# Movie mode to come later
@callback(
    Output("graph-image", "figure"),
    Input("active-file-idx", "data"),
)
def update_image(signal_idx):

    global signals_all

    if signal_idx is not None:
        key_frame = signals_all[signal_idx].get_keyframe()
    else:
        key_frame = EMPTY_IMG

    fig = px.imshow(key_frame, binary_string=True)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=5, r=5, t=5, b=5),
    )

    return fig


@callback(
    Output("graph-signal", "figure"),
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

    fig = px.line(active_signal[10:, x, y])
    # fig.add_vline(x=frame_idx)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(showlegend=False)

    return fig


# TODO: Make this clean (?)
@callback(
    Output("modal", "is_open"),
    Output("modal-header", "children"),
    Output("input-one", "value"),
    Output("input-one-prompt", "children"),
    Output("input-two", "value"),
    Output("input-two-prompt", "children"),
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("trim-signal-button", "n_clicks"),
    Input("confirm-button", "n_clicks"),
    Input("modal-header", "children"),
    Input("input-one", "value"),
    Input("input-one-prompt", "children"),
    Input("input-two", "value"),
    Input("input-two-prompt", "children"),
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
        return True, "Trim Signal", "Trim Left:", 10, "Trim Right:", 10

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
    Output("file-directory-dropdown", "options"),
    Input("refresh-folder-button", "n_clicks"),
)
def update_file_directory(_):

    file_list = os.listdir('./data')

    if DUMMY_FILENAME in file_list:
        file_list.pop(file_list.index(DUMMY_FILENAME))

    return file_list

@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("modal-header", "children"),
    Input("input-one", "value"),
    Input("input-two", "value"),
    Input("confirm-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performOperation(header, in1, in2, _, signal_idx):

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
            signals_all[signal_idx].perform_average("time", in1, in2)
            return np.random.random()
        # Spatial Averaging
        elif operation == "Spatial":
            signals_all[signal_idx].perform_average("spatial", in1, in2)
            return np.random.random()
        # Trim Signal
        elif operation == "Trim":
            signals_all[signal_idx].trim_data(in1, in2)
            return np.random.random()
    else:
        return np.random.random()


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("invert-signal-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performInvert(_, signal_idx):

    signals_all[signal_idx].invert_data()

    return np.random.random()


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("reset-data-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def reset_data(_, signal_idx):

    signals_all[signal_idx].reset_data()

    return np.random.random()


# ===========================


def open_browser():
    webbrowser.open_new("http://localhost:{}".format(DASH_APP_PORT))


DEBUG = True

if __name__ == "__main__":
    
    if not DEBUG: 
        Timer(1, open_browser).start()

    app.run(debug=DEBUG, port=DASH_APP_PORT)
