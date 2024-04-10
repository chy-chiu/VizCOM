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

import cv2

DEFAULT_IMG = np.zeros((128, 128))

BASE_MASK_SHAPE = {
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

BASE_POSITION_SHAPE = {"type": "circle", "fillcolor": "red", "line_color": "red"}
POSITION_TRACKER_RADIUS = 1

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def get_position_shape(signal_position):
    x = signal_position["x"]
    y = signal_position["y"]

    mask = copy(BASE_POSITION_SHAPE)

    mask["x0"] = x - POSITION_TRACKER_RADIUS
    mask["x1"] = x + POSITION_TRACKER_RADIUS
    mask["y0"] = y - POSITION_TRACKER_RADIUS
    mask["y1"] = y + POSITION_TRACKER_RADIUS

    return mask


def image_callbacks(app: Dash, signal_cache: Cache):

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
        State(
            indexed_component_id("signal-position", MATCH),
            "data",
        ),
        prevent_initial_call=True,
    )
    def render_image(_refresher, signal_position):
        sig_id = ctx.triggered_id["index"]
        key_frame = DEFAULT_IMG

        pos_shapes = []
        mask_shapes = []

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:

            if signal_position:
                pos_shapes = [get_position_shape(signal_position)]

            if active_signal.mask:

                mask = copy(BASE_MASK_SHAPE)
                mask["path"] = convert_point_string(active_signal.mask)
                mask_shapes = [mask]

            key_frame = active_signal.get_keyframe()

        img_fig = px.imshow(key_frame, binary_string=True)

        mask_fig = px.imshow(key_frame, binary_string=True)

        img_fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="orbit",
            shapes=pos_shapes,
        )

        mask_fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="drawclosedpath",
            newshape=dict(line_color="yellow"),
            shapes=mask_shapes,
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

        if active_signal:

            if relayout_data.get("shapes"):

                active_signal.mask = process_point_string(
                    relayout_data.get("shapes")[-1]["path"]
                )

            elif relayout_data.get("shapes[0].path"):

                active_signal.mask = process_point_string(
                    relayout_data.get("shapes[0].path")
                )

            elif relayout_data.get("shapes") == []:

                active_signal.mask = None

            signal_cache.set(sig_id, active_signal)

        return np.random.random()

    @app.callback(
        Output(
            indexed_component_id("refresh-image", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("confirm-mask-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def confirm_mask(n_clicks):

        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            if active_signal.mask:

                mask_line = np.array(active_signal.mask, dtype=np.int32)

                blank_img = np.zeros((128, 128), dtype=np.int32)

                mask_arr = cv2.fillPoly(blank_img, pts=[mask_line], color=1)

                active_signal.mask_arr = mask_arr

                active_signal.transformed_data *= np.uint16(mask_arr)

        signal_cache.set(sig_id, active_signal)

        return np.random.random()

    @app.callback(
        Output(
            indexed_component_id("refresh-image", MATCH), "data", allow_duplicate=True
        ),
        Input(indexed_component_id("reset-mask-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_mask(n_clicks):

        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        if active_signal:
            active_signal.mask = []
            active_signal.mask_arr = None

        signal_cache.set(sig_id, active_signal)

        return np.random.random()
