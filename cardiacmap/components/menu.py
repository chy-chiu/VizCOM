# Menu components

import dash_bootstrap_components as dbc
from dash import dcc, html
from cardiacmap.components.modal import settings_modal

def navbar(settings):
    if settings is None:

        settings = {}
    return dbc.NavbarSimple(
        children=[
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
            dbc.NavItem(dbc.Button("Settings", id="settings-button")),
            settings_modal(settings)
        ],
        links_left=True,
        brand="CardiacOpticalMapper",
        brand_href="#",
        color="dark",
        dark=True,
        style={"margin-bottom": "20px"},
    )


# TODO: Add more stuff here e.g. framerate, number of frames etc
def metadata_bar():
    return html.Div(
        [
            html.H2(children="Load file to continue...", id="filename-display"),
        ],
        style={
            "display": "flex",
            "align-items": "center",
            "justify-content": "center",
            "margin-top": "20px",
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
                    " Load V-Ca Data (Dual Mode)",
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
