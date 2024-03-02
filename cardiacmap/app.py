
import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, State, ctx, callback
import plotly.express as px
from cardiacmap.data import cascade_import, CascadeDataVoltage
from cardiacmap.transforms import TimeAverage, SpatialAverage
import json
import numpy as np
import os
import webbrowser
from threading import Timer
from cardiacmap.components import (
    image_viewport,
    signal_viewport,
    input_modal,
    navbar,
    file_directory,
)

DEFAULT_POSITION = 64
EMPTY_IMG = np.zeros((128, 128))
DASH_APP_PORT = 8051
DUMMY_FILENAME = "put .dat files here"


app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP])

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

showBaseline = False

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
        dcc.Store(id="signal-position", storage_type="session"),
        dcc.Store(id="signal-position-lock", data=False, storage_type="session"),
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
    Input("graph-image", "hoverData"),
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
    Input("graph-image", "clickData"),
    State("signal-position-lock", "data"),
    prevent_initial_call=True,
)    
def update_signal_lock(_, signal_lock):
    if signal_lock:
        return False
    else:
        return True


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

    return fig


# TODO: Make this clean (?)
@callback(
    Output("modal", "is_open"),
    Output("modal-header", "children"),
    Output("input-one-prompt", "children"), Output("input-one", "value"), # input 1: Sigma/Trim Left
    Output("input-two-prompt", "children"), Output("input-two", "value"), # input 2: Radius/Trim Right
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("trim-signal-button", "n_clicks"),
    Input("baseline-drift-button", "n_clicks"),
    Input("confirm-button", "n_clicks"),
    Input("modal-header", "children"),                                    # For passing values to closed modal
    Input("input-one-prompt", "children"),Input("input-one", "value"),    # For passing values to closed modal
    Input("input-two-prompt", "children"), Input("input-two", "value"),   # For passing values to closed modal
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

    file_list = os.listdir('./data')

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
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performOperation(header, avgMode, baseMode, in1, in2, _, signal_idx):

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
            signals_all[signal_idx].perform_average("time", in1, in2, mode=avgMode)
            signals_all[signal_idx].normalize()
            return np.random.random()
        # Spatial Averaging
        elif operation == "Spatial":
            signals_all[signal_idx].perform_average("spatial", in1, in2, mode=avgMode)
            signals_all[signal_idx].normalize()
            return np.random.random()
        # Trim Signal
        elif operation == "Trim":
            signals_all[signal_idx].trim_data(in1, in2)
            signals_all[signal_idx].normalize()
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


@callback(
    Output("refresh-dummy", "data", allow_duplicate=True),
    Input("invert-signal-button", "n_clicks"),
    State("active-file-idx", "data"),
    prevent_initial_call=True,
)
def performInvert(_, signal_idx):

    signals_all[signal_idx].invert_data()
    signals_all[signal_idx].normalize()
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
