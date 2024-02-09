from operator import call
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
        # html.Button("Reset", id="reset-data-button"),
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
        x = 64
        y = 64
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
        key_frame = np.zeros((128, 128))

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

    signal_position = json.loads(signal_position)
    x = signal_position["x"]
    y = signal_position["y"]

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
    Output("input-sigma", "value"),
    Output("input-radius", "value"),
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("perform-avg-button", "n_clicks"),
    Input("modal-header", "children"),
    Input("input-sigma", "value"),
    Input("input-radius", "value"),
    State("modal", "is_open"),
)
def toggle_modal(n1, n2, n3, avgType, sigIn, radIn, is_open):
    # open modal with spatial
    if "spatial-avg-button" == ctx.triggered_id:
        return True, "Spatial Averaging", 8, 6

    # open modal with time
    elif "time-avg-button" == ctx.triggered_id:
        return True, "Time Averaging", 4, 3

    # close modal and perform averaging
    elif "perform-avg-button" == ctx.triggered_id:
        return False, avgType, sigIn, radIn

    # ignore updates to inputs
    elif "input-sigma" == ctx.triggered_id or "input-radius" == ctx.triggered_id:
        return True, avgType, sigIn, radIn

    # initial call
    # if you see "header" in modal, something went wrong
    return is_open, "HEADER", 0, 0

@callback(
    Output("file-directory-dropdown", "options"),
    Input("refresh-folder-button", "n_clicks"),
    prevent_initial_call=True,
)
def update_file_directory(_):

    return os.listdir('./data')

@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("modal-header", "children"),
    Input("input-sigma", "value"),
    Input("input-radius", "value"),
    Input("perform-avg-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performAverage(header, sig, rad, _, signal_idx):

    # if the modal was closed by the 'perform average' button
    if "perform-avg-button" == ctx.triggered_id:
        # if bad inputs (str, negative nums, etc.)
        if sig is None or sig < 0:
            sig = 0
        if rad is None or rad < 0:
            rad = 0
        # Time averaging
        if header.split()[0] == "Time":
            signals_all[signal_idx].perform_average("time", sig, rad)
            return np.random.random()
        # Spatial Averaging
        elif header.split()[0] == "Spatial":
            signals_all[signal_idx].perform_average("spatial", sig, rad)
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
    webbrowser.open_new("http://localhost:{}".format(8051))


if __name__ == "__main__":
    # Timer(1, open_browser).start()
    app.run(debug=True, port=8051)
