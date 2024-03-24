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

DEFAULT_IMG = np.zeros((128, 128))

indexed_component_id = lambda idx, n: {"type": idx, "index": n}

def image_callbacks(app, signal_cache: Cache):
    # Key image is used only for position exploration and annotation.
    # This should only be called upon changing the active signal
    # Movie mode to come later
    @app.callback(
        Output(indexed_component_id("graph-image", MATCH), "figure", allow_duplicate=True),
        Input(indexed_component_id("refresh-image", MATCH), "data"),
        prevent_initial_call=True,
    )
    def update_key_image(_refresher):        
        
        sig_id = ctx.triggered_id["index"]
        
        active_signal: CascadeSignal = signal_cache.get(sig_id)
        
        key_frame = active_signal.get_keyframe() if active_signal is not None else DEFAULT_IMG

        fig = px.imshow(key_frame, binary_string=True)
        fig.update_layout(
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=5, r=5, t=5, b=5),
            dragmode="orbit",
        )

        return fig