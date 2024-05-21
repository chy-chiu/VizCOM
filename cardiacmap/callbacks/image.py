import json
import os
import time
from types import NoneType
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

# helper function to pad an array with zeros until it is rectangular
def pad(array, targetWidth):
    for i in range(len(array)):
        numZeros = targetWidth - len(array[i])
        zeros = np.zeros(numZeros)
        array[i] = np.concatenate((array[i], zeros))
    return np.asarray(array)

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


    @app.callback(
        Output(
            indexed_component_id("graph-apd-spatial", MATCH), "figure", allow_duplicate=True
        ),
        Input(indexed_component_id("image-tabs", MATCH), "active_tab"),
        Input(indexed_component_id("spatial-apd-index", MATCH), "value"),
        Input(indexed_component_id("spatial-apd-select", MATCH), "value"),
        State(indexed_component_id("min-bound-apd", MATCH), "value"),
        State(indexed_component_id("min-bound-apd-diff", MATCH), "value"),
        State(indexed_component_id("max-bound-apd", MATCH), "value"),
        prevent_initial_call=True,
    )
    def apd_spatial_plot(at, spatialAPDIdx, displayType, minBound, minBoundDiff, maxBound):
        if at == "apd-spatial-tab":

            sig_id = ctx.triggered_id["index"]
            spatial_apd_id = 1000                            # using signal cache here, sig_id+1000 to avoid key conflicts
            spatial_apd_diff_id = 2000
            
            spatialAPDs = None

            active_spatial_apds = signal_cache.get(sig_id + spatial_apd_id)
            if active_spatial_apds is not None and len(active_spatial_apds) > 0:
                spatialAPDs = active_spatial_apds
            else:
                active_signal: CascadeSignal = signal_cache.get(sig_id)
            
                if active_signal:   
                    # calculate spatial apd plot
                    active_apds = active_signal.apds
                    
                    # check if apds have been calculated
                    if len(active_apds) == 0:
                        print("No APDs Calculated")
                        return px.imshow(DEFAULT_IMG, binary_string=True, title="No APDs Calculated")
                    
                    # get largest apd list (each pixel has its own)
                    max_apd_size = len(max(active_apds, key=len))

                    # extend every pixel with zeros until each pixel has len of max_apd_size (rectangular)
                    spatialAPDs = pad(active_apds, max_apd_size)
                    
                    # reshape and save
                    spatialAPDs = spatialAPDs.reshape((128, 128, max_apd_size))
                    spatialAPDs = np.moveaxis(spatialAPDs, -1, 0)
                    
                    spatialAPDDiffs = np.diff(spatialAPDs, axis=0)

                    signal_cache.set(sig_id + spatial_apd_id, spatialAPDs)
                    signal_cache.set(sig_id + spatial_apd_diff_id, spatialAPDDiffs)

            if spatialAPDs is None:
                print("No Active Signal")
                return px.imshow(DEFAULT_IMG, binary_string=True, title="No Active Signal")

            # ensure index is within limits
            if spatialAPDIdx >= len(spatialAPDs):
                spatialAPDIdx = len(spatialAPDs) - 1
                if displayType == "Difference":
                    spatialAPDIdx -= 1
           
            minBoundToUse = 0
            
            # get the frame to display
            # select either minBound or minBoundDiff for use
            # get the data range
            if displayType == "Value":
                frame = (spatialAPDs[spatialAPDIdx])

                minBoundToUse = minBound
                
                minDataVal = spatialAPDs.min()
                maxDataVal = spatialAPDs.max()

            elif displayType == "Difference":
                spatialAPDDiffs = signal_cache.get(sig_id + spatial_apd_diff_id)
                
                frame = (spatialAPDDiffs[spatialAPDIdx])

                minBoundToUse = minBoundDiff
                
                minDataVal = spatialAPDDiffs.min()
                maxDataVal = spatialAPDDiffs.max()
                
            if minBound is None or maxBound is None:
                # if bounds are not provided, autoscale to min and max
                fig = px.imshow(frame, zmin=minDataVal, zmax=maxDataVal, color_continuous_scale='gray')
            else:
                # remove outliers
                indices_under_range = frame < minBoundToUse
                indices_over_range = frame > maxBound
                frame[indices_under_range] = frame[indices_over_range] = 0
                
                # make frame data into an image
                fig = px.imshow(frame, zmin=minBoundToUse, zmax=maxBound, color_continuous_scale='gray')
            
            
            fig.update_layout(
                showlegend=True,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                margin=dict(l=5, r=5, t=5, b=5),
                dragmode="drawline",
            )
                
            return fig    
        return px.imshow(DEFAULT_IMG, binary_string=True)
    
    @app.callback(
        Output(indexed_component_id("spatial-apd-index", MATCH), "value", allow_duplicate=True),
        Input(indexed_component_id("spatial-apd-index", MATCH), "value"),
        Input(indexed_component_id("prev-apd-button", MATCH), "n_clicks"),
        Input(indexed_component_id("next-apd-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def update_apd_spatial_plot_index(inputVal, prev, next):
        button_clicked = ctx.triggered_id["type"]
        print(button_clicked)
        if(button_clicked == "prev-apd-button" and inputVal >= 1):
            return inputVal - 1
        if(button_clicked == "next-apd-button"):
            return inputVal + 1
        else:
            return inputVal
        
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
