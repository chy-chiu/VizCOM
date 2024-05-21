import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

DUMMY_FILENAME = "put .dat files here"


def file_callbacks(app, file_cache: Cache, signal_cache: Cache):

    @app.callback(
        Output("settings-store", "data"), 
        Output("data-folder-settings-modal", "value"),
        Input("settings-confirm", "n_clicks"),
        State("data-folder-settings-modal", "value")
    )
    def confirm_settings(_nclicks, data_path):
        print(data_path)

        settings_str = json.dumps({"path": data_path})
        with open('./settings.json', 'w') as f:
            f.write(settings_str)

        return settings_str, data_path

    # Load data from specific directory
    @app.callback(
        Output("file-directory-dropdown", "options"),
        Input("refresh-folder-button", "n_clicks"),
        State("settings-store", "data"), 
    )
    def update_file_directory(_refresh_folder, settings):
        settings = json.loads(settings)
        file_list = os.listdir(settings["path"])

        if DUMMY_FILENAME in file_list:
            file_list.pop(file_list.index(DUMMY_FILENAME))

        return file_list

    @app.callback(
        Output("filename-display", "children"),
        Output("calcium-mode-badge", "hidden"),
        Output("calcium-dual-mode-window", "hidden"),
        Output({"type": "refresh-image", "index": ALL}, "data"),
        Output({"type": "refresh-signal", "index": ALL}, "data"),
        Input("load-voltage-button", "n_clicks"),
        Input("load-calcium-button", "n_clicks"),
        State("file-directory-dropdown", "value"),
        State("settings-store", "data"), 
    )
    def load_file(_load_voltage, _load_calcium, filename: str, settings):
        """This function loads a file from either system or file cache. It also updates the signal cache.

        Args:
            file_idx (str): file name
        """
        settings = json.loads(settings)

        dual_mode = False

        if ctx.triggered_id == "load-calcium-button":
            dual_mode = True

        if filename is None or filename.split(".")[-1] != "dat":
            # Clear signal cache if file is not valid
            signal_cache.clear()

            return (
                "Load file to continue...",
                True,
                True,
                (np.random.random(), np.random.random()),
                (np.random.random(), np.random.random()),
            )

        active_file: CascadeDataFile = file_cache.get(filename)

        # If current file is not in the cache, load data
        if active_file is None:
            active_file = CascadeDataFile.load_data(
                filepath=filename, dual_mode=dual_mode, root_dir=settings["path"]
            )

            file_cache.set(filename, active_file)
        # If current file is in the cache, but the mode is not correct, switch mode
        elif active_file.dual_mode != dual_mode:
            active_file.switch_modes(dual_mode)

            file_cache.set(filename, active_file)

        # Cache signal cache with the current file
        signal_cache.set_many(active_file.signals)

        return (
            filename,
            not dual_mode,
            not dual_mode,
            (np.random.random(), np.random.random()),
            (np.random.random(), np.random.random()),
        )

    # @app.callback(
    #     Output("calcium-mode", "data"),
    #     Output("calcium-dual-mode-window", "hidden"),
    #     Input("calcium-mode-badge", "hidden"),
    #     Input("calcium-mode-dropdown", "value"),
    # )
    # def update_calcium_mode(calcium_mode_inactive, calcium_mode_dropdown):
    #     # There are four potential states.
    #     # - Single channel
    #     # - Dual channel - two windows
    #     # - Dual channel - Odd frames
    #     # - Dual channel - Even frames

    #     if calcium_mode_inactive:
    #         return "single", True
    #     elif calcium_mode_dropdown:
    #         if calcium_mode_dropdown == "dual":
    #             dual_window_hidden = False
    #         else:
    #             dual_window_hidden = True

    #         return calcium_mode_dropdown, dual_window_hidden
    #     else:
    #         return "dual", False
