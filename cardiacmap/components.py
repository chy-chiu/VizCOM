# Components for the Dash app

import dash
import dash_bootstrap_components as dbc

from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

import json


def image_viewport():
    return dbc.Col(
            # TODO: add other menu bar items here
            dcc.Graph(id="graph-image"),
            width={"size": 2, "order": 1},
            # style={"padding-bottom": "100%", "position": "relative"},
            id="col-image"
        )


def signal_viewport():
    return dbc.Col(
        html.Div(
            [
                dcc.Graph(id="graph-signal"),
                dcc.Slider(
                    # TODO: Dynamically change the frames here later
                    0, 5000, step=None, value=100, id="frame-slider", updatemode="drag"
                ),
            ],
        ),
        width={"size": 9, "order": 2},
        id="col-signal"
    )