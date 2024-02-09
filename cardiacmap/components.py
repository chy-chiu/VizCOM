# Components for the Dash app

import dash
import dash_bootstrap_components as dbc

from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

import json

import os

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
        style={"margin-bottom": "20px"},
    )


def file_directory():
    return html.Div(
        [
            html.Div(
                dcc.Dropdown(
                    options=list(os.listdir("./data")),
                    value="",
                    id="file-directory-dropdown",
                    searchable=False,
                    style={"width": "80vw"},
                ),
                style={"display": "inline-block", "margin-right": "10px"},
            ),
            html.Div(
                dbc.Button("Refresh", id="refresh-folder-button"),
                style={"display": "inline-block", "margin-left": "10px"},
            ),
        ],
        style={
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
        },
    )


def image_viewport():
    return dbc.Col(
        # TODO: add other menu bar items here
        dcc.Graph(id="graph-image"),
        width={"size": 2, "order": 1},
        # style={"padding-bottom": "100%", "position": "relative"},
        id="col-image",
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
        id="col-signal",
    )


def input_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader("HEADER", id="modal-header"),
            dbc.ModalBody(
                [
                    html.P("Sigma:"),
                    dbc.Input(id="input-sigma", type="number", min=0, value=0),
                    html.P("Radius:"),
                    dbc.Input(id="input-radius", type="number", min=0, step=1, value=0),
                ]
            ),
            dbc.ModalFooter(dbc.Button("Perform Averaging", id="perform-avg-button")),
        ],
        id="modal",
    )


def buttons_table():
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Button("Reset", id="reset-data-button"),
                    html.Div(id="reset-data-pressed"),
                ],
                width=1,
            ),
            dbc.Col(
                [
                    dbc.Button("Time Averaging", id="time-avg-button"),
                    html.Div(id="time-button-pressed"),
                ],
                width=1,
            ),
            dbc.Col(
                [
                    dbc.Button("Spatial Averaging", id="spatial-avg-button"),
                    html.Div(id="spatial-button-pressed"),
                ],
                width=1,
            ),
            dbc.Col(
                [
                    dbc.Button("Invert Signal", id="invert-signal-button"),
                    html.Div(id="invert-button-pressed"),
                ],
                width=1,
            ),
        ],
        justify="center",
        className="g-0",
    )
