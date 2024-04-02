import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def transform_callbacks(app, signal_cache: Cache):
    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("spatial-avg-modal", MATCH),
            "is_open",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("spatial-avg-confirm", MATCH), "n_clicks"),
        State(indexed_component_id("spatial-avg-sigma", MATCH), "value"),
        State(indexed_component_id("spatial-avg-radius", MATCH), "value"),
        State(indexed_component_id("spatial-avg-mode", MATCH), "value"),
        prevent_initial_call=True,
    )
    def perform_spatial_avg(_, sigma, radius, mode):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.perform_average("spatial", sigma, radius, mode=mode)
            active_signal.normalize()
            signal_cache.set(sig_id, active_signal)

        return np.random.random(), False

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("time-avg-modal", MATCH),
            "is_open",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("time-avg-confirm", MATCH), "n_clicks"),
        State(indexed_component_id("time-avg-sigma", MATCH), "value"),
        State(indexed_component_id("time-avg-radius", MATCH), "value"),
        State(indexed_component_id("time-avg-mode", MATCH), "value"),
        prevent_initial_call=True,
    )
    def perform_time_avg(_, sigma, radius, mode):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.perform_average("time", sigma, radius, mode=mode)
            active_signal.normalize()
            signal_cache.set(sig_id, active_signal)

        return np.random.random(), False

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("invert-signal-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def perform_invert(_):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.invert_data()
            active_signal.normalize()

            signal_cache.set(sig_id, active_signal)

        return np.random.random()

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("trim-modal", MATCH), "is_open", allow_duplicate=True
        ),
        Input(indexed_component_id("trim-confirm", MATCH), "n_clicks"),
        State(indexed_component_id("trim-left", MATCH), "value"),
        State(indexed_component_id("trim-right", MATCH), "value"),
        prevent_initial_call=True,
    )
    def trim_data(_, trim_left, trim_right):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.trim_data(startTrim=trim_left, endTrim=trim_right)

            signal_cache.set(sig_id, active_signal)

        return np.random.random(), False

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("normalize-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def normalize_data(_):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.normalize()

            signal_cache.set(sig_id, active_signal)

        return np.random.random()

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("baseline-modal", MATCH),
            "is_open",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("confirm-baseline-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-baseline-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("confirm-baseline-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-baseline-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("baseline-confirm", MATCH), "n_clicks"),
        State(indexed_component_id("baseline-period", MATCH), "value"),
        State(indexed_component_id("baseline-threshold", MATCH), "value"),
        State(indexed_component_id("baseline-mode", MATCH), "value"),
        prevent_initial_call=True,
    )
    def remove_baseline_drift(_, period, threshold, mode):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            if mode == "Period":
                active_signal.calc_baseline(mode, period)
            elif mode == "Threshold":
                active_signal.calc_baseline(mode, threshold)

            active_signal.show_baseline = True

            signal_cache.set(sig_id, active_signal)

        return (
            np.random.random(),
            False,
            False,
            False,
            "success",
            "danger",
        )

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("confirm-baseline-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-baseline-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("confirm-baseline-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-baseline-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("confirm-baseline-button", MATCH), "n_clicks"),
        Input(indexed_component_id("reject-baseline-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def confirm_baseline_drift(_confirm, _reject):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            # print(type(active_signal.transformed_data.dtype))

            if ctx.triggered_id["type"] == "confirm-baseline-button":
                active_signal.remove_baseline_drift()
                active_signal.normalize()

            active_signal.reset_baseline()
            active_signal.show_baseline = False

            # print(type(active_signal.transformed_data.dtype))

            signal_cache.set(sig_id, active_signal)

        return (np.random.random(), True, True, "light", "light")

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("apd-di-modal", MATCH), "is_open", allow_duplicate=True
        ),
        Output(
            indexed_component_id("confirm-apd-di-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-apd-di-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("confirm-apd-di-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-apd-di-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("apd-di-confirm", MATCH), "n_clicks"),
        State(indexed_component_id("apd-di-threshold", MATCH), "value"),
        prevent_initial_call=True,
    )
    def calculate_apd_di(_, threshold):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.calc_apd_di_threshold(threshold)

            active_signal.show_apd_threshold = True

            signal_cache.set(sig_id, active_signal)
        return (
            np.random.random(),
            False,
            False,
            False,
            "success",
            "danger",
        )

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Output(
            indexed_component_id("confirm-apd-di-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-apd-di-button", MATCH),
            "disabled",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("confirm-apd-di-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Output(
            indexed_component_id("reject-apd-di-button", MATCH),
            "color",
            allow_duplicate=True,
        ),
        Input(indexed_component_id("confirm-apd-di-button", MATCH), "n_clicks"),
        Input(indexed_component_id("reject-apd-di-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def confirm_apd_di(_confirm, _reject):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            if ctx.triggered_id["type"] == "confirm-apd-di-button":
                active_signal.calc_apd_di()

            active_signal.show_apd_threshold = False

            signal_cache.set(sig_id, active_signal)

        return (np.random.random(), True, True, "light", "light")

    @app.callback(
        Output(
            indexed_component_id("refresh-signal", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("reset-data-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_data(_):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.reset_data()
            active_signal.normalize()

            signal_cache.set(sig_id, active_signal)

        return np.random.random()
