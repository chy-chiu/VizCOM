import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal

DEFAULT_IMG = np.zeros((128, 128))

indexed_component_id = lambda idx, n: {"type": idx, "index": n}

# helper function to pad an array with zeros until it is rectangular
def pad(array, targetWidth):
    for i in range(len(array)):
        numZeros = targetWidth - len(array[i])
        zeros = np.zeros(numZeros)
        array[i] = np.concatenate((array[i], zeros))
    return np.asarray(array)

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
    def update_key_image(_refresher):
        sig_id = ctx.triggered_id["index"]

        active_signal: CascadeSignal = signal_cache.get(sig_id)

        key_frame = (
            active_signal.get_keyframe() if active_signal is not None else DEFAULT_IMG
        )

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
            newshape=dict(line_color="yellow")
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
        State(indexed_component_id("max-bound-apd", MATCH), "value"),
        prevent_initial_call=True,
    )
    def apd_spatial_plot(at, spatialAPDIdx, displayType, minBound, maxBound):
        if at == "apd-spatial-tab":

            sig_id = ctx.triggered_id["index"]
            spatial_apd_id = 1000                            # using signal cache here, sig_id+1000 to avoid key conflicts

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

                    signal_cache.set(sig_id + spatial_apd_id, spatialAPDs)

            if spatialAPDs is None:
                print("No Active Signal")
                return px.imshow(DEFAULT_IMG, binary_string=True, title="No Active Signal")

            # ensure index is within limits
            if spatialAPDIdx >= len(spatialAPDs):
                spatialAPDIdx = len(spatialAPDs) - 1
                if displayType == "Difference":
                    spatialAPDIdx -= 1
                
                
            # show/calculate the frame to display
            if displayType == "Value":
                frame = (spatialAPDs[spatialAPDIdx])
            elif displayType == "Difference":
                # doing the subtraction at runtime
                # saves storage space, but may cause lag
                frame0 = (spatialAPDs[spatialAPDIdx])
                frame1 = (spatialAPDs[spatialAPDIdx + 1])
                frame = frame1 - frame0
                
            # remove outliers
            indices_under_range = frame < minBound
            indices_over_range = frame > maxBound
            frame[indices_under_range] = frame[indices_over_range] = 0
                
            # make frame data into an image
            fig = px.imshow(frame, zmin=minBound, zmax=maxBound, binary_string=True)

            fig.update_layout(
                showlegend=False,
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                margin=dict(l=5, r=5, t=5, b=5),
                dragmode="orbit",
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
    
    # @app.callback(
    #     Output(
    #         indexed_component_id("graph-image", MATCH), "figure", allow_duplicate=True
    #     ),
    #     Output(
    #         indexed_component_id("graph-mask", MATCH), "figure", allow_duplicate=True
    #     ),
    #     Input(indexed_component_id("graph-mask", MATCH), "relayoutData"),
    #     State(indexed_component_id("graph-image", MATCH), "figure"),
    #     State(indexed_component_id("graph-mask", MATCH), "figure"),
    #     prevent_initial_call=True,
    # )
    # def update_img_mask(relayout_data, img_fig, mask_fig):

    #     print(json.dumps(relayout_data, indent=2))

    #     return img_fig, mask_fig
