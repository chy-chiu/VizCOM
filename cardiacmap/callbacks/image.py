import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

from copy import copy

DEFAULT_IMG = np.zeros((128, 128))

DEFAULT_MASK_SHAPE = {
            "editable": True,
            "xref": "x",
            "yref": "y",
            "layer": "above",
            "opacity": 1,
            "line": {"color": "yellow", "width": 4, "dash": "solid"},
            "fillcolor": "rgba(0,0,0,0)",
            "fillrule": "evenodd",
            "type": "path",
            "path": None,
        }

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def image_callbacks(app, signal_cache: Cache):
    # Key image is used only for position exploration and annotation.
    # This should only be called upon changing the active signal
    # Movie mode to come later
    @app.callback(
        Output(
            indexed_component_id("graph-image", MATCH), "figure", allow_duplicate=True
        ),
        Output(
            indexed_component_id("graph-mask", MATCH), "figure", allow_duplicate=True
        ),
        Input(indexed_component_id("refresh-image", MATCH), "data"),
        prevent_initial_call=True,
    )
    def render_image(_refresher):
        sig_id = ctx.triggered_id["index"]
        key_frame = DEFAULT_IMG

        shapes = []

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            
            if active_signal.mask:
                
                mask = copy(DEFAULT_MASK_SHAPE)
                mask['path'] = convert_point_string(active_signal.mask)
                shapes = [mask]
                
            key_frame = active_signal.get_keyframe()

        img_fig = px.imshow(key_frame, binary_string=True)

        mask_fig = px.imshow(key_frame, binary_string=True)

        img_fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="orbit",
        )

        mask_fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="drawclosedpath",
            newshape=dict(line_color="yellow"),
            shapes=shapes,
        )

        # # Add modebar buttons
        # mask_fig.show()

        return img_fig, mask_fig

    def process_point_string(point_string: str):

        # Removing the 'M' at the beginning and 'Z' at the end
        clean_string = point_string[1:-1]

        points = clean_string.split("L")

        point_array = [
            tuple(max(0, min(127, int(float(coord)))) for coord in point.split(","))
            for point in points
        ]

        return point_array

    def convert_point_string(point_array):

        return "M" + "L".join([f"{x},{y}" for x, y in point_array]) + "Z"

    @app.callback(
        # Output(
        #     indexed_component_id("graph-image", MATCH), "figure", allow_duplicate=True
        # ),
        # Output(
        #     indexed_component_id("graph-mask", MATCH), "figure", allow_duplicate=True
        # ),
        Output(
            indexed_component_id("refresh-image", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("graph-mask", MATCH), "relayoutData"),
        State(indexed_component_id("graph-mask", MATCH), "figure"),
        prevent_initial_call=True,
    )
    def update_img_mask(relayout_data, mask_fig):

        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        print(relayout_data)

        if active_signal:

            if relayout_data.get("shapes"):

                active_signal.mask = process_point_string(
                    relayout_data.get("shapes")[-1]['path']
                )

            elif relayout_data.get("shapes[0].path"):

                active_signal.mask = process_point_string(
                    relayout_data.get("shapes[0].path")
                )

            elif relayout_data.get("shapes") == []:

                active_signal.mask = None

            print(active_signal.mask)

            signal_cache.set(sig_id, active_signal)

        return np.random.random()
