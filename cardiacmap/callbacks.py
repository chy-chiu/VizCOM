from dash import Dash, dcc, html, Input, Output, State, ctx, callback, ALL, MATCH
import os
import json
from cardiacmap.data import CascadeDataVoltage
import numpy as np
from flask_caching import Cache
import time

DUMMY_FILENAME = "put .dat files here"
PATCH_MAX_FRAME = 5000
IMG_WIDTH = 128
PATCH_SIZE = 8


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

        if file_idx is None:
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

            curr_signal: np.ndarray = cache.get(
                "active-signal-{i}-{x}".format(i=i, x=patch_idx)
            )

            if curr_signal is None:
                # Empty patch of signal
                curr_signal = np.array([np.zeros((PATCH_SIZE, PATCH_SIZE))] * 2)
            else:
                if curr_signal.shape[0] > PATCH_MAX_FRAME:
                    curr_signal = curr_signal[:PATCH_MAX_FRAME, :, :]

            patch_dict["signal_{i}".format(i=i)] = (
                curr_signal.transpose(1, 2, 0).flatten().tolist()
            )

        ### TODO for Grayson: Add Transform baseline here for patching (?)

        return (
            json.dumps(patch_dict),
            disable_refresher,
            disable_refresher,
            0,
            10,
        )

    # To fix this part (!)
    @app.callback(
        Output("refresh-dummy", "data", allow_duplicate=True),
        Input("refresh-dummy", "data"),
        State("active-file", "data"),
        prevent_initial_call=True,
    )
    def cache_active_signal(_, active_file):

        active_file = json.loads(active_file)
        active_signal = None

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

                start = time.time()

                success = cache.set_many(
                    {
                        "active-signal-{ix}-{x}".format(ix=ix, x=x): patch
                        for x, patch in enumerate(patches)
                    }
                )
                print("CACHE TIME: ", time.time() - start)

        return np.random.random()

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
