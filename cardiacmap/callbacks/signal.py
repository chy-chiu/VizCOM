
import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import (ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc,
                  html)
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

IMG_WIDTH = 128
DEFAULT_SIG_POSITION = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}
BLANK_SIGNAL = {"data": [{"y": np.zeros(10), "type": "line"}], "layout": {}}

indexed_component_id = lambda idx, n: {"type": idx, "index": n}

def signal_callbacks(app, signal_cache: Cache):
    @app.callback(
        Output(indexed_component_id("graph-signal", MATCH), "figure", allow_duplicate=True),
        Output(indexed_component_id("signal-position", MATCH), "data", allow_duplicate=True),
        Input(indexed_component_id("drag-event-listener", MATCH), "event"),
        Input(indexed_component_id("drag-event-listener", MATCH), "n_events"),
        Input(indexed_component_id("refresh-signal", MATCH), "data"),
        prevent_initial_call=True,
    )
    def update_signal(event, _drag_listener, _refresher):

        start = time.time()
        
        sig_id = ctx.triggered_id["index"]
        
        active_signal: CascadeSignal = signal_cache.get(sig_id)

        signal_position = (
            json.loads(event["srcElement.innerText"]) if event else DEFAULT_SIG_POSITION
        )

        if active_signal:
            curr_signal = active_signal.transformed_data

            x = signal_position["x"]
            y = signal_position["y"]

            fig = {
                "data": [{"y": curr_signal[:, x, y], "type": "line"}],
                "layout": {},
            }

            if active_signal.show_baseline:
                baseline_idx = x * active_signal.span_X + y

                bX = active_signal.baselineX[baseline_idx]
                bY = active_signal.baselineY[baseline_idx]

                fig["data"].append(
                    {"x": bX, "y": bY, "type": "line"},
                )

            if active_signal.show_apd_threshold:
                sig_idx = x * active_signal.span_X + y
                indices, thresh = active_signal.get_apd_threshold()

                print(len(indices))

                tX = indices[sig_idx]
                tY = [thresh for t in tX]

                fig["data"].append(
                    {
                        "x": tX,
                        "y": tY,
                        "type": "scatter",
                        "mode": "markers+lines",
                        "marker": {"symbol": "circle"},
                    }
                )

            print(time.time() - start)
            
        else:
            fig = BLANK_SIGNAL

        return fig, signal_position

