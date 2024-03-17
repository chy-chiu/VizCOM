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

    # # This might not be a good idea. Will fix :(
    # @app.callback(
    #     Output("active-signal-patch", "data"),
    #     Output("position-refresher", "disabled"),
    #     # Output("graph-refresher", "disabled"),
    #     Output("graph-refresher", "n_intervals"),
    #     Output("graph-refresher", "max_intervals"),
    #     Input("position-refresher", "n_intervals"),
    #     Input("drag-event-listener", "n_events"),
    #     State("drag-event-listener", "event"),
    #     State("signal-position", "data"),
    #     prevent_initial_call=True,
    # )
    # def update_signal_data(position_refresh, n_events, event, signal_position):

    #     disable_refresher = False

    #     if event is None:
    #         disable_refresher = True

    #     else:
    #         if event["type"] == "drag-mouseup":
    #             disable_refresher = True

    #     if signal_position is None:
    #         signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}

    #     x = signal_position["x"]
    #     y = signal_position["y"]

    #     x_patch = x // PATCH_SIZE
    #     y_patch = y // PATCH_SIZE

    #     patch_idx = x_patch * (IMG_WIDTH // PATCH_SIZE) + y_patch

    #     patch_dict = {}

    #     for i in range(2):

    #         curr_signal: np.ndarray = cache.get(
    #             "active-signal-{i}-{x}".format(i=i, x=patch_idx)
    #         )

    #         if curr_signal is None:
    #             # Empty patch of signal
    #             curr_signal = np.array([np.zeros((PATCH_SIZE, PATCH_SIZE))] * 2)
    #         else:
    #             if curr_signal.shape[0] > PATCH_MAX_FRAME:
    #                 curr_signal = curr_signal[:PATCH_MAX_FRAME, :, :]

    #         patch_dict["signal_{i}".format(i=i)] = (
    #             curr_signal.transpose(1, 2, 0).flatten().tolist()
    #         )

        ### TODO for Grayson: Add Transform baseline here for patching (?)
            
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
        

        # return (
        #     json.dumps(patch_dict),
        #     disable_refresher,
        #     # disable_refresher,
        #     0,
        #     10,
        # )

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        # Output("position-refresher", "n_intervals"),
        Output("graph-refresher", "disabled", allow_duplicate=True),
        Input("refresh-dummy", "data"),
        Input("active-file", "data"),
        # State("position-refresher", "n_intervals"),
        prevent_initial_call=True,
    )
    def cache_active_signal(_, active_file): # , pos_refresher):

        active_signal = get_active_signal(active_file, cache)

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

                start = time.time()

                cache.set_many(
                    {
                        "active-signal-{ix}-{x}".format(ix=ix, x=x): patch
                        for x, patch in enumerate(patches)
                    }
                )
                print("CACHE TIME: ", time.time() - start)

        return np.random.random(), False # pos_refresher + 1, False

    @app.callback(
        Output("graph-signal-1", "figure", allow_duplicate=True),
        Output("graph-signal-2", "figure", allow_duplicate=True),
        State("signal-position", "data"),
        State("active-file", "data"),
        Input("drag-event-listener", "n_events"),
        Input("refresh-dummy", "data"),
        State("hidden-div", "children"),
        prevent_initial_call=True,
    )
    def update_full_signal(signal_position, active_file, _drag_listener, _refresher, hidden_div):

        print("MEEP")

        print(hidden_div)

        active_signal = get_active_signal(active_file, cache)

        if active_signal:
            curr_signals = active_signal.get_curr_signal()
        else: 
            return BLANK_SIGNAL, BLANK_SIGNAL

        if signal_position is None:
            signal_position = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}

        x = signal_position["x"]
        y = signal_position["y"]

        # NB: This is also where we add the traces
        fig_0 = {"data": [{"y": curr_signals[0][:, x, y], "type": "line"}], "layout": {}}

        if len(curr_signals) == 1:
            return fig_0, fig_0
        else: 
            fig_1 = {"data": [{"y": curr_signals[1][:, x, y], "type": "line"}], "layout": {}}

            return fig_0, fig_1



def modal_callbacks(app: Dash):

    def toggle_modal(n, is_open):
        if n:
            return not is_open
        return is_open

    app.callback(
        Output({"type":"spatial-avg-modal", "index": MATCH}, "is_open"),
        Input({"type":"spatial-avg-button", "index": MATCH}, "n_clicks"),
        State({"type":"spatial-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type":"time-avg-modal", "index": MATCH}, "is_open"),
        Input({"type":"time-avg-button", "index": MATCH}, "n_clicks"),
        State({"type":"time-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type":"trim-modal", "index": MATCH}, "is_open"),
        Input({"type":"trim-signal-button", "index": MATCH}, "n_clicks"),
        State({"type":"trim-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    # def test():
    #     print("asdfasdf")
    #     # (toggle_modal)
    #     return True


# TODO: 
# 1. Fix up trim, baseline average
# 2. Update header + swap between signals 
# 3. Add dot follow
# 
# 

def transform_callbacks(app, cache: Cache):

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output({"type":"spatial-avg-modal", "index": ALL}, "is_open", allow_duplicate=True),
        Input({"type":"spatial-avg-confirm", "index": ALL}, "n_clicks"),
        State({"type":"spatial-avg-sigma", "index": ALL}, "value"),
        State({"type":"spatial-avg-radius", "index": ALL}, "value"),
        State({"type":"spatial-avg-mode", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_spatial_avg(_, sigma, radius, mode, active_file):

        sig_id = ctx.triggered_id['index'] - 1       
    
        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.perform_average("spatial", sigma[sig_id], radius[sig_id], sig_id, mode=mode[sig_id])
            active_signal.normalize(sig_id)
            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random(), [False, False]

    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output({"type":"time-avg-modal", "index": ALL}, "is_open", allow_duplicate=True),
        Input({"type":"time-avg-confirm", "index": ALL}, "n_clicks"),
        State({"type":"time-avg-sigma", "index": ALL}, "value"),
        State({"type":"time-avg-radius", "index": ALL}, "value"),
        State({"type":"time-avg-mode", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_time_avg(_, sigma, radius, mode, active_file):

        sig_id = ctx.triggered_id['index'] - 1       
    
        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.perform_average("time", sigma[sig_id], radius[sig_id], sig_id, mode=mode[sig_id])
            active_signal.normalize(sig_id)
            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random(), [False, False]


    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type":"invert-signal-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_invert(_, active_file):

        sig_id = ctx.triggered_id['index'] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.invert_data(sig_id)
            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random()
    
    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Output({"type":"trim-modal", "index": ALL}, "is_open", allow_duplicate=True),
        Input({"type":"trim-confirm", "index": ALL}, "n_clicks"),
        State({"type":"trim-left", "index": ALL}, "value"),
        State({"type":"trim-right", "index": ALL}, "value"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def trim_data(_, trim_left, trim_right, active_file):

        sig_id = ctx.triggered_id['index'] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.trim_data(sig_id, startTrim=trim_left[sig_id], endTrim=trim_right[sig_id])

            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random(), [False, False]
    
    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type":"normalize-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def normalize_data(_, active_file):

        sig_id = ctx.triggered_id['index'] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random()
    
    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input({"type":"reset-data-button", "index": ALL}, "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def reset_data(_, active_file):

        sig_id = ctx.triggered_id['index'] - 1

        active_signal = get_active_signal(active_file, cache)

        if active_signal:

            active_signal.reset_data(sig_id)
            active_signal.normalize(sig_id)

            cache.set(json.loads(active_file)["filename"], active_signal)
            
        return np.random.random()


    # @app.callback(
    #     Output("refresh-dummy", "data", allow_duplicate=True),
    #     Input("modal-header", "children"),
    #     Input("avg-mode-select", "value"),
    #     Input("baseline-mode-select", "value"),
    #     Input("input-one", "value"),
    #     Input("input-two", "value"),
    #     Input("confirm-button", "n_clicks"),
    #     Input("calcium-mode-dual", "active"),
    #     State("active-file", "data"),
    #     prevent_initial_call=True,
    # )
    # def perform_operation(header, avg_mode, base_mode, in1, in2, _, __, active_file):

    #     active_file = json.loads(active_file)

    #     if active_file["filename"]:
    #         active_signal: CascadeDataVoltage = cache.get(active_file["filename"])
    #     else:
    #         return np.random.random()

    #     # if the modal was closed by the 'perform average' button
    #     if "confirm-button" == ctx.triggered_id:
    #         # if bad inputs
    #         # should we give a warning?
    #         if in1 is None or in1 < 0:
    #             in1 = 0
    #         if in2 is None or in2 < 0:
    #             in2 = 0

    #         # TODO: FIX THIS PART YO
    #         operation = header.split()[0]
    #         # Time averaging
    #         if operation == "Time":
    #             signals_all[signal_idx].perform_average("time", in1, in2, mode=mode)
    #             if cmd and DUAL_ODD in signals_all.keys():
    #                 signals_all[DUAL_ODD].perform_average("time", in1, in2, mode=mode)
    #             return np.random.random()
    #         # Spatial Averaging
    #         elif operation == "Spatial":
    #             signals_all[signal_idx].perform_average("spatial", in1, in2, mode=mode)
    #             if cmd and DUAL_ODD in signals_all.keys():
    #                 signals_all[DUAL_ODD].perform_average("spatial", in1, in2, mode=mode)
    #             return np.random.random()
    #         # Trim Signal
    #         elif operation == "Trim":
    #             signals_all[signal_idx].trim_data(in1, in2)
    #             if cmd and DUAL_ODD in signals_all.keys():
    #                 signals_all[DUAL_ODD].trim_data(in1, in2)
    #             return np.random.random()
    #         # Remove Baseline Drift (Just get the baseline, it will not be removed until user approval)
    #         elif operation == "Remove":
    #             if baseMode == "Period":
    #                 val = in1
    #             elif baseMode == "Threshold":
    #                 val = in2
    #             else:
    #                 raise Exception("baseline mode must be Period or Threshold")

    #             signals_all[signal_idx].calc_baseline(baseMode, val)
    #             global showBaseline
    #             showBaseline = True
    #         return np.random.random()



    @callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input("confirm-baseline-button", "n_clicks"),
        Input("cancel-baseline-button", "n_clicks"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def perform_drift_removal(n1, n2, signal_idx):
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
