import dash
import dash_bootstrap_components as dbc

from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

from data import cascade_import
from transforms import TimeAverage, SpatialAverage
import json

from components import image_viewport, signal_viewport

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

im_raw = cascade_import("2012-02-13_Exp000_Rec005_Cam3-Blue.dat")

navbar = dbc.NavbarSimple(
    children=[
        dbc.DropdownMenu(
            children=[
                dbc.DropdownMenuItem("Upload", header=True),
                dbc.DropdownMenuItem("Upload", href="#"),
                dbc.DropdownMenuItem("Upload", href="#"),
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


app.layout = html.Div(
    [
        html.Div(
            [
                dbc.Row(navbar),
                dbc.Row(
                    [
                        image_viewport(),
                        signal_viewport(),
                    ]
                ),
            ]
        ),
        dcc.Upload(
            id="upload-data",
            children=html.Div(["Drag and Drop or ", html.A("Select Files")]),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            multiple=False,
        ),
        html.Button("Time Averaging", id="time-avg"),
        html.Button("Spatial Averaging", id="spatial-avg"),
        html.Div(id="time-button"),
        html.Div(id="spatial-button"),
        dcc.Store(id="frame-index", storage_type="session"),
        dcc.Store(id="signal-position", storage_type="session"),
    ]
)


@callback(
    Output("time-button", "children"),
    Input("time-avg", "n_clicks"),
    prevent_initial_call=True,
)
def performTimeAverage(n_clicks):
    global im_raw
    im_raw = TimeAverage(im_raw, 8, 5)
    msg = "Time Average completed."
    return html.Div(msg)


@callback(
    Output("spatial-button", "children"),
    Input("spatial-avg", "n_clicks"),
    prevent_initial_call=True,
)
def performSpatialAverage(n_clicks):
    global im_raw
    im_raw = SpatialAverage(im_raw, 8, 5)
    msg = "Spatial Averaging Completed."
    return html.Div(msg)


@callback(
    Output("frame-index", "data"),
    Input("frame-slider", "value"),
)
def update_frame_idx(frame_idx):
    return frame_idx


@callback(
    Output("frame-slider", "value"),
    Input("graph-signal", "clickData"),
    prevent_initial_call=True,
)
def update_frame_slider_idx(clickData):
    if clickData is not None:
        frame_idx = clickData["points"][0]["pointIndex"]
    return frame_idx


@callback(Output("signal-position", "data"), Input("graph-image", "clickData"))
def update_signal_position(clickData):
    if clickData is not None:
        x = clickData["points"][0]["x"]
        y = clickData["points"][0]["y"]
    else:
        x = 64
        y = 64
    return json.dumps({"x": x, "y": y})


@callback(Output("graph-image", "figure"), Input("frame-index", "data"))
def update_figure(frame_idx):
    fig = px.imshow(im_raw[frame_idx], binary_string=True)
    fig.update_layout(
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=5, r=5, t=5, b=5),   
    )

    return fig


@callback(
    Output("graph-signal", "figure"),
    Input("signal-position", "data"),
    Input("frame-index", "data"),
)
def display_click_data(signal_position, frame_idx):
    signal_position = json.loads(signal_position)
    x = signal_position["x"]
    y = signal_position["y"]

    fig = px.line(im_raw[10:, x, y])
    fig.add_vline(x=frame_idx)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(showlegend=False)

    return fig


if __name__ == "__main__":
    app.run(debug=True)
