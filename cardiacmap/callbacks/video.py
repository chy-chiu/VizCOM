import json
import os
import time
from typing import Tuple, Union

import numpy as np
import plotly.express as px
from dash import ALL, MATCH, Dash, Input, Output, State, callback, ctx, dcc, html
from flask_caching import Cache

from cardiacmap.data import CascadeDataFile, CascadeSignal
import numpy as np
import matplotlib.pyplot as plt
import numpy as np
import cv2

from pathlib import Path
import dash_player as dp

import ffmpeg


indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def normalize(data):
    return ((data - np.amin(data)) / (np.amax(data) - np.amin(data)) * 256).astype(
        np.uint8
    )


def normalize_flat(data):
    return (
        (data - np.amin(data, axis=0))
        / (np.amax(data, axis=0) - np.amin(data, axis=0))
        * 256
    ).astype(np.uint8)

def _render_video(data, output_filename):

    # Initialize ffmpeg input stream

    process = (
        ffmpeg.input('pipe:', format='rawvideo', pix_fmt='bgr24', s='128x128', r=230)
        .output(output_filename, vcodec='libx264', pix_fmt='yuv420p')
        .overwrite_output()
        .run_async(pipe_stdin=True)
    )

    for frame in data:

        color_mapped_frame = cv2.applyColorMap(frame, cv2.COLORMAP_RAINBOW)
        process.stdin.write(color_mapped_frame.astype(np.uint8).tobytes())

    process.stdin.close()

    process.wait()

    print(f"Video saved as {output_filename}")

def video_callbacks(app: Dash, signal_cache: Cache):

    @app.callback(
        Output(indexed_component_id("video-dropdown-button", MATCH), "options"),
        Input(indexed_component_id("render-video-button", MATCH), "n_clicks"),
        prevent_initial_call=True,
    )
    def render_video(_):
        sig_id = ctx.triggered_id["index"]
        signal: CascadeSignal = signal_cache.get(sig_id)

        if signal:

            print("Rendering videos..")
            Path("./.videos").mkdir(parents=True, exist_ok=True)
            # Config 1
            data = normalize(signal.base_data)
            _render_video(data, "./.videos/video_1.mp4")

            # Config 2
            data = normalize_flat(signal.base_data)
            _render_video(data, "./.videos/video_2.mp4")

            # Config 3
            data = normalize(signal.transformed_data)
            _render_video(data, "./.videos/video_3.mp4")

            # Config 4
            data = normalize_flat(signal.transformed_data)
            _render_video(data, "./.videos/video_4.mp4")

            
        return os.listdir("./.videos")

    @app.callback(
        Output(indexed_component_id("video-player", MATCH), "src"),
        Input(indexed_component_id("video-dropdown-button", MATCH), "value"),
        prevent_initial_call=True,
    )
    def load_video(filename):

        if filename:
            return os.path.join("/.videos/", filename)

        else:
            return ""
