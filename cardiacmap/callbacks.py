from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
import os
import json
from cardiacmap.data import CascadeDataVoltage
import numpy as np
from flask_caching import Cache
import time
from typing import Union

DUMMY_FILENAME = "put .dat files here"
PATCH_MAX_FRAME = 5000
IMG_WIDTH = 128
PATCH_SIZE = 8

BLANK_SIGNAL = {"data": [{"y": np.zeros(10), "type": "line"}], "layout": {}}


def get_active_signal(active_file, cache) -> Union[CascadeDataVoltage, None]:

    active_file = json.loads(active_file)

    if active_file["filename"]:
        active_signal: CascadeDataVoltage = cache.get(active_file["filename"])
        return active_signal
    else:
        return None


def file_callbacks(app, cache: Cache):

    # Load data from specific directory
    @app.callback(
        Output("file-directory-dropdown", "options"),
        Input("refresh-folder-button", "n_clicks"),
    )
    def update_file_directory(_):

        # To convert this to settings.json
        file_list = os.listdir("./data")

        if DUMMY_FILENAME in file_list:
            file_list.pop(file_list.index(DUMMY_FILENAME))

        return file_list

    # Load file
    @app.callback(
        Output("active-file", "data"),
        Output("calcium-dual-mode-window", "hidden"),
        Output("calcium-mode-badge", "hidden"),
        Input("load-voltage-button", "n_clicks"),
        Input("load-calcium-button", "n_clicks"),
        State("file-directory-dropdown", "value"),
    )
    def load_file(_, __, file_idx):

        dual_mode = False

        if ctx.triggered_id == "load-calcium-button":
            dual_mode = True

        if file_idx is None or file_idx.split(".")[-1] != "dat":

            return json.dumps({"filename": "", "frames": 0, "dual": False}), True, True

        active_signal: CascadeDataVoltage = cache.get(file_idx)

        if active_signal is None:
            active_signal = CascadeDataVoltage.load_data(
                filepath=file_idx, calcium_mode=dual_mode
            )

            cache.set(file_idx, active_signal)

        elif active_signal.dual_mode != dual_mode:

            active_signal.switch_modes(dual_mode)

            cache.set(file_idx, active_signal)

        frames = (
            active_signal.span_T
            if active_signal.span_T <= PATCH_MAX_FRAME
            else PATCH_MAX_FRAME
        )

        file_metadata = json.dumps(
            {"filename": file_idx, "frames": frames, "dual": active_signal.dual_mode}
        )

        return file_metadata, not dual_mode, not dual_mode


def signal_callbacks(app, cache: Cache):

    @app.callback(
        Output("graph-signal-1", "figure", allow_duplicate=True),
        Output("graph-signal-2", "figure", allow_duplicate=True),
        Output("signal-position", "data"),
        State("active-file", "data"),
        Input("drag-event-listener", "n_events"),
        State("drag-event-listener", "event"),
        Input("refresh-dummy", "data"),
        prevent_initial_call=True,
    )
    def update_full_signal(active_file, _drag_listener, event, _refresher):

        active_signal = get_active_signal(active_file, cache)

        if event and active_signal:

            curr_signals = active_signal.get_curr_signal()

            signal_position = json.loads(event["srcElement.innerText"])

        else:
            return (
                BLANK_SIGNAL,
                BLANK_SIGNAL,
                {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2},
            )

        if signal_position is None:
            signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}

        x = signal_position["x"]
        y = signal_position["y"]

        # NB: This is also where we add the traces
        fig_0 = {
            "data": [{"y": curr_signals[0][:, x, y], "type": "line"}],
            "layout": {},
        }

        if active_signal.show_baseline:
            baseline_idx = x * active_signal.span_X + y

            bX = active_signal.baselineX[baseline_idx]
            bY = active_signal.baselineY[baseline_idx]

            fig_0 = {
                "data": [
                    {"y": curr_signals[0][:, x, y], "type": "line"},
                    {"x": bX, "y": bY, "type": "line"},
                ],
                "layout": {},
            }

        else:

            fig_0 = {
                "data": [{"y": curr_signals[0][:, x, y], "type": "line"}],
                "layout": {},
            }

        if len(curr_signals) == 1:
            return fig_0, fig_0, signal_position
        else:
            fig_1 = {
                "data": [{"y": curr_signals[1][:, x, y], "type": "line"}],
                "layout": {},
            }

            return fig_0, fig_1, signal_position


def modal_callbacks(app: Dash):

    def toggle_modal(n, is_open):
        if n:
            return not is_open
        return is_open

    app.callback(
        Output({"type": "spatial-avg-modal", "index": MATCH}, "is_open"),
        Input({"type": "spatial-avg-button", "index": MATCH}, "n_clicks"),
        State({"type": "spatial-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "time-avg-modal", "index": MATCH}, "is_open"),
        Input({"type": "time-avg-button", "index": MATCH}, "n_clicks"),
        State({"type": "time-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "trim-modal", "index": MATCH}, "is_open"),
        Input({"type": "trim-signal-button", "index": MATCH}, "n_clicks"),
        State({"type": "trim-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "baseline-modal", "index": MATCH}, "is_open"),
        Input({"type": "remove-drift-button", "index": MATCH}, "n_clicks"),
        State({"type": "baseline-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)


# TODO:
# 2. Update header + swap between signals

def transform_callbacks(app, cache: Cache):

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output(
            {"type": "spatial-avg-modal", "index": ALL}, "is_open", allow_duplicate=True
        ),
        Input({"type": "spatial-avg-confirm", "index": ALL}, "n_clicks"),
        State({"type": "spatial-avg-sigma", "index": ALL}, "value"),
        State({"type": "spatial-avg-radius", "index": ALL}, "value"),
        State({"type": "spatial-avg-mode", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_spatial_avg(_, sigma, radius, mode, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.perform_average(
                "spatial", sigma[sig_id], radius[sig_id], sig_id, mode=mode[sig_id]
            )
            active_signal.normalize(sig_id)
            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random(), [False, False]

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output(
            {"type": "time-avg-modal", "index": ALL}, "is_open", allow_duplicate=True
        ),
        Input({"type": "time-avg-confirm", "index": ALL}, "n_clicks"),
        State({"type": "time-avg-sigma", "index": ALL}, "value"),
        State({"type": "time-avg-radius", "index": ALL}, "value"),
        State({"type": "time-avg-mode", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_time_avg(_, sigma, radius, mode, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.perform_average(
                "time", sigma[sig_id], radius[sig_id], sig_id, mode=mode[sig_id]
            )
            active_signal.normalize(sig_id)
            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random(), [False, False]

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type": "invert-signal-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_invert(_, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.invert_data(sig_id)
            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random()

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output({"type": "trim-modal", "index": ALL}, "is_open", allow_duplicate=True),
        Input({"type": "trim-confirm", "index": ALL}, "n_clicks"),
        State({"type": "trim-left", "index": ALL}, "value"),
        State({"type": "trim-right", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def trim_data(_, trim_left, trim_right, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.trim_data(
                sig_id, startTrim=trim_left[sig_id], endTrim=trim_right[sig_id]
            )

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random(), [False, False]

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type": "normalize-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def normalize_data(_, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random()

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output(
            {"type": "baseline-modal", "index": ALL}, "is_open", allow_duplicate=True
        ),
        Output(
            {"type": "confirm-baseline-button", "index": ALL}, "disabled", allow_duplicate=True
        ),
        Output(
            {"type": "reject-baseline-button", "index": ALL}, "disabled", allow_duplicate=True
        ),
        Output(
            {"type": "confirm-baseline-button", "index": ALL}, "color", allow_duplicate=True
        ),
        Output(
            {"type": "reject-baseline-button", "index": ALL}, "color", allow_duplicate=True
        ),
        Input({"type": "baseline-confirm", "index": ALL}, "n_clicks"),
        State({"type": "baseline-period", "index": ALL}, "value"),
        State({"type": "baseline-threshold", "index": ALL}, "value"),
        State({"type": "baseline-mode", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def remove_baseline_drift(_, period, threshold, mode, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            if mode[sig_id] == "Period":
                print(mode, period)
                active_signal.calc_baseline(sig_id, mode[sig_id], period[sig_id])
            elif mode == "Threshold":
                active_signal.calc_baseline(sig_id, mode[sig_id], threshold[sig_id])

            active_signal.show_baseline = True

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random(), [False, False], [False, False], [False, False], ["success", "success"], ["danger", "danger"]

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output(
            {"type": "confirm-baseline-button", "index": ALL}, "disabled", allow_duplicate=True
        ),
        Output(
            {"type": "reject-baseline-button", "index": ALL}, "disabled", allow_duplicate=True
        ),
        Output(
            {"type": "confirm-baseline-button", "index": ALL}, "color", allow_duplicate=True
        ),
        Output(
            {"type": "reject-baseline-button", "index": ALL}, "color", allow_duplicate=True
        ),    
        Input({"type": "confirm-baseline-button", "index": ALL}, "n_clicks"),
        Input({"type": "reject-baseline-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def confirm_baseline_drift(_confirm, _reject, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:
            if ctx.triggered_id['type'] == "confirm-baseline-button":
                active_signal.remove_baseline_drift(sig_id)
            
            active_signal.reset_baseline()
            active_signal.show_baseline = False

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random(), [True, True], [True, True], ["light", "light"], ["light", "light"]


    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type": "reset-data-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def reset_data(_, active_file):

        sig_id = ctx.triggered_id["index"] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.reset_data(sig_id)
            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)

        return np.random.random()
    