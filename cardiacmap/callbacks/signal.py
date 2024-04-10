import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
import pandas as pd
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

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

            # print(time.time() - start)

        else:
            fig = BLANK_SIGNAL

        return fig, signal_position
    
    @app.callback(
        Output(
            indexed_component_id("graph-plot", MATCH), "figure", allow_duplicate=True
        ),
        Input(indexed_component_id("image-tabs", MATCH), "active_tab"),
        Input(indexed_component_id("signal-position", MATCH), "data"),
        prevent_initial_call=True,
    )
    def apd_di_scatterplot(at, sig_pos):
        # print(px.data.iris())
        if at == "apd-di-tab":
            sig_id = ctx.triggered_id["index"]

            active_signal: CascadeSignal = signal_cache.get(sig_id)
            
            if active_signal:
                x = sig_pos["x"]
                y = sig_pos["y"]
                sig_idx = x * active_signal.span_X + y
                
                # check if apds have been calculated
                if len(active_signal.apds) <= sig_idx or len(active_signal.dis) <= sig_idx:
                    return BLANK_SIGNAL
                
                active_apds = active_signal.apds[sig_idx]
                active_dis = active_signal.dis[sig_idx]
                lenAPD = len(active_apds)
                lenDI = len(active_dis)
                
                # make sure signal is valid
                if lenAPD <= 0 or lenDI <= 0:
                    return BLANK_SIGNAL
                
                # make sure apd and di arrays are the same length
                if lenAPD > lenDI:
                    active_apds.pop(-1)
                elif lenAPD < lenDI:
                    active_dis.pop(0)
                    
                #print(len(active_apds), len(active_dis))
                
                figDict = {"APDs": active_apds, "DIs": active_dis}
                df = pd.DataFrame(figDict)
                
                fig = px.scatter(df, x="APDs", y="DIs")
                fig.update_yaxes(range = [0, max(active_dis) + 5])
                fig.update_xaxes(range = [0, max(active_apds) + 5])
                fig.update_layout(margin=dict(l=5, r=5, t=5, b=5))
                
                return fig
            
        return BLANK_SIGNAL