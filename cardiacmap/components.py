# Components for the Dash app

import dash
import dash_bootstrap_components as dbc

from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

import json

def navbar():
    return dbc.NavbarSimple(
        children=[
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem("Test", header=True),
                    dbc.DropdownMenuItem("Test", href="#"),
                    dbc.DropdownMenuItem("Test", href="#"),
                ],
                nav=True,
                in_navbar=True,
                label="More",
            ),
        ],
        brand="CardiacOpticalMapper",
        brand_href="#",
        color="primary",
        dark=True,
    )

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
        dcc.Graph(id="graph-signal"),      
        # html.Div(
        #     [
        #         # dcc.Slider(
        #         #     # TODO: Dynamically change the frames here later
        #         #     0, 5000, step=None, value=100, id="frame-slider", updatemode="drag"
        #         # ),
        #     ],
        # ),
        width={"size": 9, "order": 2},
        id="col-signal"
    )
