# Components for the Dash app

import json
import os

import dash
import dash_bootstrap_components as dbc
import plotly.express as px
from dash import Dash, Input, Output, callback, dcc, html
from dash_extensions import EventListener

from cardiacmap.components.buttons import button_bar
from cardiacmap.components.modal import transform_modals

event_change = {"event": "drag-change", "props": ["type", "srcElement.innerText"]}
event_mousedown = {"event": "drag-mousedown", "props": ["type", "srcElement.innerText"]}
event_mouseup = {"event": "drag-mouseup", "props": ["type", "srcElement.innerText"]}

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def image_viewport(n):
    return dbc.Col(
        # TODO: add other menu bar items here
        dcc.Graph(
            id=indexed_component_id("graph-image", n),
        ),
        width={"size": 2, "order": 1},
        # style={"padding-bottom": "100%", "position": "relative"},
        id=indexed_component_id("col-image", n),
    )


def signal_viewport(n):
    return dbc.Col(
        [button_bar(n), dcc.Graph(id=indexed_component_id("graph-signal", n))],
        # html.Div(
        #     [
        #         # dcc.Slider(
        #         #     # TODO: Dynamically change the frames here later
        #         #     0, 5000, step=None, value=100, id="frame-slider", updatemode="drag"
        #         # ),
        #     ],
        # ),
        width={"size": 9, "order": 2},
        id=indexed_component_id("col-signal", n),
    )


def signal_viewer(n):
    return [
        dbc.Row(
            [
                image_viewport(n),
                signal_viewport(n),
            ],
            style={
                "display": "flex",
                "align-items": "center",
                "justify-content": "center",
            },
            id=indexed_component_id("signal-viewer", n),
        ),
        transform_modals(n),
        # Event listener for drag events
        EventListener(
            html.Div(
                '{"x": 64, "y": 64}',
                id=indexed_component_id("hidden-div", n),
                hidden=True,  # False if debug
            ),
            events=[event_change, event_mouseup, event_mousedown],
            logging=False,
            id=indexed_component_id("drag-event-listener", n),
        ),
        # Position of signal
        dcc.Store(
            id=indexed_component_id("signal-position", n), storage_type="session"
        ),
        # Dummy variables to trigger a refresh in the image and signal viewports respectively
        dcc.Store(id=indexed_component_id("refresh-signal", n), storage_type="session"),
        dcc.Store(id=indexed_component_id("refresh-image", n), storage_type="session"),
    ]
