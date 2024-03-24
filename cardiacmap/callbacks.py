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

DUMMY_FILENAME = "put .dat files here"
DEFAULT_IMG = np.zeros((128, 128))
PATCH_MAX_FRAME = 5000
IMG_WIDTH = 128
PATCH_SIZE = 8

BLANK_SIGNAL = {"data": [{"y": np.zeros(10), "type": "line"}], "layout": {}}
DEFAULT_SIG_POSITION = {"x": IMG_WIDTH // 2, "y": IMG_WIDTH // 2}


def get_active_signal(
    calcium_mode: str, signal_cache: Cache
) -> Union[
    Tuple[CascadeSignal, CascadeSignal], Tuple[CascadeSignal, None], Tuple[None, None]
]:
    if calcium_mode == "single":
        active_signal = signal_cache.get("signal")
        return active_signal, None
    elif calcium_mode == "dual":
        odd_frames_signal = signal_cache.get("odd")
        even_frames_signal = signal_cache.get("even")
        return odd_frames_signal, even_frames_signal
    elif calcium_mode == "odd":
        odd_frames_signal = signal_cache.get("odd")
        return odd_frames_signal, None
    elif calcium_mode == "even":
        even_frames_signal = signal_cache.get("even")
        return even_frames_signal, None
    else:
        return None, None

