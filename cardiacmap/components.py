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
            html.I(
                className="bi-sm bi-tools h5",
                style={"color": "white", "margin-left": "4vw", "margin-top": "1vh"},
            ),
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Trim",
                                className="bi bi-crop",
                                id="trim-signal-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            ),
                            html.Div(id="trim-button-pressed"),
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Invert",
                                className="bi bi-caret-down",
                                id="invert-signal-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            ),
                            html.Div(id="invert-button-pressed"),
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Reset",
                                className="bi-bootstrap-reboot",
                                id="reset-data-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            ),
                            html.Div(id="reset-data-pressed"),
                        ]
                    ),
                    html.Div(
                        dbc.DropdownMenu(
                            [
                                dbc.DropdownMenuItem(
                                    "Even",
                                    style={"font-size": "14px"},
                                    id="calcium-mode-even",
                                ),
                                dbc.DropdownMenuItem(
                                    "Odd",
                                    style={"font-size": "14px"},
                                    id="calcium-mode-odd",
                                ),
                                dbc.DropdownMenuItem(
                                    "Dual",
                                    style={"font-size": "14px"},
                                    id="calcium-mode-dual",
                                ),
                                dbc.DropdownMenuItem(
                                    "Reset",
                                    style={"font-size": "14px"},
                                    id="calcium-mode-reset",
                                    disabled=True,
                                ),
                            ],
                            label="Calcium Mode",
                            direction="end",
                            id="calcium-mode-menu",
                            color="light",
                            size="sm",
                        ),
                        style={
                            "margin-left": "1vw",
                            "margin-top": "1vh",
                            "margin-right": "1vw",
                        },
                    ),
                ],
                in_navbar=True,
                nav=True,
                style={"margin-right": "2vw"},
            ),
            html.I(
                className="bi-sm bi-activity h4",
                style={"color": "white", "margin-top": "1vh"},
            ),
            dbc.DropdownMenu(
                children=[
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Normalize",
                                className="bi bi-bar-chart",
                                id="normalize-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Time Average",
                                className="bi bi-bar-chart",
                                id="time-avg-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Spatial Average",
                                className="bi bi-bar-chart",
                                id="spatial-avg-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Remove Baseline Drift",
                                className="bi bi-bar-chart",
                                id="baseline-drift-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Confirm Baseline",
                                className="bi bi-bar-chart",
                                id="confirm-baseline-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                    dbc.DropdownMenuItem(
                        [
                            dbc.Button(
                                "  Cancel Baseline",
                                className="bi bi-bar-chart",
                                id="cancel-baseline-button",
                                color="light",
                                style={"width": "100%", "font-size": "14px"},
                            )
                        ]
                    ),
                ],
                in_navbar=True,
                nav=True,
            ),
            html.Div(
                dbc.Badge("calcium mode", color="info", className="me-1", pill=True),
                hidden=True,
                id="calcium-mode-badge",
                style={
                    "margin-top": "1vh",
                    "margin-right": "1vw",
                    "margin-left": "1vw",
                },
            ),
        ],
        links_left=True,
        brand="CardiacOpticalMapper",
        brand_href="#",
        color="dark",
        dark=True,
        style={"margin-bottom": "20px"},
    )


def file_directory():
    return html.Div(
        [
            html.Div(
                dcc.Dropdown(
                    options=[],
                    value="",
                    id="file-directory-dropdown",
                    searchable=False,
                    style={"width": "60vw"},
                ),
                style={"display": "inline-block", "margin-right": "10px"},
            ),
            html.Div(
                dbc.Button(
                    " Load Voltage Data",
                    id="load-voltage-button",
                    className="bi bi-cloud-upload",
                    color="light",
                ),
                style={"display": "inline-block", "margin-left": "10px"},
            ),
            html.Div(
                dbc.Button(
                    " Load Calcium Data",
                    id="load-calcium-button",
                    className="bi bi-cloud-upload-fill",
                    color="light",
                ),
                style={"display": "inline-block", "margin-left": "10px"},
            ),
            html.Div(
                dbc.Button(
                    " Refresh Folder", 
                    id="refresh-folder-button",
                    className="bi bi-arrow-clockwise",
                    color="light",
                ),
                style={"display": "inline-block", "margin-left": "10px"},
            ),
        ],
        style={
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
        },
    )


def image_viewport(n):
    return dbc.Col(
        # TODO: add other menu bar items here
        dcc.Graph(id=f"graph-image-{n}"),
        width={"size": 2, "order": 1},
        # style={"padding-bottom": "100%", "position": "relative"},
        id=f"col-image-{n}",
    )


def signal_viewport(n):
    return dbc.Col(
        dcc.Graph(id=f"graph-signal-{n}"),
        # html.Div(
        #     [
        #         # dcc.Slider(
        #         #     # TODO: Dynamically change the frames here later
        #         #     0, 5000, step=None, value=100, id="frame-slider", updatemode="drag"
        #         # ),
        #     ],
        # ),
        width={"size": 9, "order": 2},
        id=f"col-signal-{n}",
    )


def input_modal():
    return dbc.Modal(
        [
            dbc.ModalHeader("HEADER", id="modal-header"),
            dbc.ModalBody(
                [
                    html.Div(
                        # dcc.Dropdown(['Gaussian', 'Uniform'], 'Gaussian', id="avg-mode-dropdown"),
                        [
                            html.Div(
                                [
                                    dbc.Label("Choose Averaging Method:"),
                                    dbc.RadioItems(
                                        options=[
                                            {"label": "Gaussian", "value": "Gaussian"},
                                            {"label": "Uniform", "value": "Uniform"},
                                        ],
                                        value="Gaussian",
                                        id="avg-mode-select",
                                        inline=True,
                                    ),
                                ],
                                id="avg-mode-parent",
                            ),
                            html.Div(
                                [
                                    dbc.Label("Choose Baseline Method:"),
                                    dbc.RadioItems(
                                        options=[
                                            {"label": "Period", "value": "Period"},
                                            {
                                                "label": "Threshold",
                                                "value": "Threshold",
                                                "disabled": False,
                                            },
                                        ],
                                        value="Period",
                                        id="baseline-mode-select",
                                        inline=True,
                                    ),
                                ],
                                id="baseline-mode-parent",
                            ),
                        ],
                        id="mode-select-parent",
                    ),
                    html.Div(
                        [
                            html.P("In 1:", id="input-one-prompt"),
                            dbc.Input(id="input-one", type="number", min=0, value=0),
                        ],
                        id="input-one-parent",
                    ),
                    html.Div(
                        [
                            html.P("In 2:", id="input-two-prompt"),
                            dbc.Input(id="input-two", type="number", min=0, value=0),
                        ],
                        id="input-two-parent",
                    ),
                ]
            ),
            dbc.ModalFooter(dbc.Button("Confirm", id="confirm-button")),
        ],
        id="modal",
    )
