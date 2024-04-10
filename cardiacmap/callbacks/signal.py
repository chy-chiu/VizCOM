import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

from cardiacmap.callbacks.image import get_position_shape, DEFAULT_IMG

IMG_WIDTH = 128
DEFAULT_SIG_POSITION = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}
BLANK_SIGNAL = {"data": [{"y": np.zeros(10), "type": "line"}], "layout": {}}

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def signal_callbacks(app, signal_cache: Cache):
    @app.callback(
        Output(
            indexed_component_id("graph-signal", MATCH), "figure", allow_duplicate=True
        ),
        Output(
            indexed_component_id("graph-image", MATCH), "figure", allow_duplicate=True
        ),
        Output(
            indexed_component_id("signal-position", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("drag-event-listener", MATCH), "event"),
        Input(indexed_component_id("drag-event-listener", MATCH), "n_events"),
        Input(indexed_component_id("refresh-signal", MATCH), "data"),
        prevent_initial_call=True,
    )
    def update_signal(event, _drag_listener, _refresher):
        # start = time.time()

        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        signal_position = (
            json.loads(event["srcElement.innerText"]) if event else DEFAULT_SIG_POSITION
        )

        pos_shapes = []

        key_frame = DEFAULT_IMG


        if active_signal:
            curr_signal = active_signal.transformed_data

            x = signal_position["x"]
            y = signal_position["y"]

            signal_fig = {
                "data": [{"y": curr_signal[:, x, y], "type": "line"}],
                "layout": {},
            }

            if active_signal.show_baseline:
                baseline_idx = x * active_signal.span_X + y

                bX = active_signal.baselineX[baseline_idx]
                bY = active_signal.baselineY[baseline_idx]

                signal_fig["data"].append(
                    {"x": bX, "y": bY, "type": "line"},
                )

            if active_signal.show_apd_threshold:
                sig_idx = x * active_signal.span_X + y
                indices, thresh = active_signal.get_apd_threshold()

                tX = indices[sig_idx]
                tY = [thresh for t in tX]

                signal_fig["data"].append(
                    {
                        "x": tX,
                        "y": tY,
                        "type": "scatter",
                        "mode": "markers+lines",
                        "marker": {"symbol": "circle"},
                    }
                )

            # print(time.time() - start)

            key_frame = active_signal.get_keyframe()

            pos_shapes = [get_position_shape(signal_position)]

            
        else:
            signal_fig = BLANK_SIGNAL
        
        img_fig = px.imshow(key_frame, binary_string=True)
        img_fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="orbit",
            shapes=pos_shapes,
        )

        return signal_fig, img_fig, signal_position
