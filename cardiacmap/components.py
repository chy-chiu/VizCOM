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
                    dbc.DropdownMenuItem([]),
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


def button_bar(n):
    return dbc.Row(
        [
            dbc.Button(
                [html.I(className="bi bi-crop"), "  Trim"],
                id={"type": "trim-signal-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-caret-down"), "  Invert"],
                id={"type": "invert-signal-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi-bootstrap-reboot"), "  Reset"],
                id={"type": "reset-data-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Normalize"],
                id={"type": "normalize-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Time Average"],
                id={"type": "time-avg-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Spatial Average"],
                id={"type": "spatial-avg-button", "index": n},
                color="light",
                class_name="button-viewer",
            ),
        ],
        id="button-bar-{n}".format(n=n),
        style={
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
        },
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


def signal_viewer(n):

    return dbc.Row(
        [
            image_viewport(n),
            signal_viewport(n),
        ],
        style={
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
        },
        id="signal-viewer-{n}".format(n=n),
    )


def image_viewport(n):
    return dbc.Col(
        # TODO: add other menu bar items here
        dcc.Graph(id=f"graph-image-{n}", ),
        width={"size": 2, "order": 1},
        # style={"padding-bottom": "100%", "position": "relative"},
        id=f"col-image-{n}",
    )


def signal_viewport(n):
    return dbc.Col(
        [button_bar(n), dcc.Graph(id=f"graph-signal-{n}")],
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


# spatial_modal
# time_modal
# trim_modal
# baseline_modal


### Components for modal

def numerical_input_modal(modal_id, modal_text, n, value):

    return html.Div(
        [
            html.P(modal_text),
            dbc.Input(
                id={"type": modal_id, "index": n},
                type="number",
                min=0,
                value=value,
            ),
        ],
    )

def average_method_div(n, avg_type: str):

    return html.Div(
        [
            dbc.Label("Choose Averaging Method:"),
            dbc.RadioItems(
                options=[
                    {"label": "Gaussian", "value": "Gaussian"},
                    {"label": "Uniform", "value": "Uniform"},
                ],
                value="Gaussian",
                id={"type": f"{avg_type}-avg-mode", "index": n},
                inline=True,
            ),
        ],
    )


def transform_modals(n):

    spatial_modal = dbc.Modal(
        [
            dbc.ModalHeader("Spatial Averaging"),
            dbc.ModalBody(
                [
                    average_method_div(n, "spatial"),
                    numerical_input_modal(
                        modal_id="spatial-avg-sigma", modal_text="Sigma", n=n, value=8
                    ),
                    numerical_input_modal(
                        modal_id="spatial-avg-radius", modal_text="Radius", n=n, value=6
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id={"type": f"spatial-avg-confirm", "index": n})
            ),
        ],
        id={"type": f"spatial-avg-modal", "index": n},
        is_open=False,
    )

    time_modal = dbc.Modal(
        [
            dbc.ModalHeader("Time Averaging"),
            dbc.ModalBody(
                [
                    average_method_div(n, "time"),
                    numerical_input_modal(
                        modal_id="time-avg-sigma", modal_text="Sigma", n=n, value=4
                    ),
                    numerical_input_modal(
                        modal_id="time-avg-radius", modal_text="Radius", n=n, value=3
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id={"type": f"time-avg-confirm", "index": n})
            ),
        ],
        id={"type": f"time-avg-modal", "index": n},
        is_open=False,
    )

    trim_modal = dbc.Modal(
        [
            dbc.ModalHeader("Trim Signal"),
            dbc.ModalBody(
                [
                    numerical_input_modal(
                        modal_id="trim-left", modal_text="Trim Left", n=n, value=100
                    ),
                    numerical_input_modal(
                        modal_id="trim-right", modal_text="Trim Right", n=n, value=100
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id={"type": f"trim-confirm", "index": n})
            ),
        ],
        id={"type": f"trim-modal", "index": n},
        is_open=False,
    )

    return html.Div([spatial_modal, time_modal, trim_modal])


# spatial_modal = dbc.Modal()


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
