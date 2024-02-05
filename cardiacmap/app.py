import dash
import dash_bootstrap_components as dbc

from dash import Dash, dcc, html, Input, Output, State, ctx, callback
import plotly.express as px

from data import cascade_import
from transforms import TimeAverage, SpatialAverage
import json

from components import image_viewport, signal_viewport

app = Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

im_raw = cascade_import("2012-02-13_Exp000_Rec005_Cam3-Blue.dat")
im_edited = im_raw.copy()

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
        html.Div([
            dbc.Modal(
                [
                    dbc.ModalHeader("HEADER", id="modal-header"),
                    dbc.ModalBody(
                        [
                            html.P("Sigma:"),
                            dbc.Input(id='input-sigma', type="number", min = 0, value=0),
                            html.P("Radius:"),
                            dbc.Input(id='input-radius', type="number", min = 0, step = 1, value=0)
                        ]),
                    dbc.ModalFooter(
                        dbc.Button("Perform Averaging", id="perform-avg-button", className="ml-auto")
                    ),
                ],
                id="modal")
        ]),
        html.Button('Reset', id='reset-data-button'),
        html.Div(id='reset-data-pressed'),
        html.Button('Time Averaging', id='time-avg-button'),
        html.Div(id='time-button-pressed'),
        html.Button('Spatial Averaging', id='spatial-avg-button'),
        html.Div(id='spatial-button-pressed'),
        dcc.Store(id='frame-index', storage_type="session"),
        dcc.Store(id='signal-position', storage_type="session"),
    ])


@callback(
    Output("modal", "is_open"),
    Output("modal-header", "children"),
    Output('input-sigma', 'value'),
    Output('input-radius', 'value'),
    Input("time-avg-button", "n_clicks"),
    Input("spatial-avg-button", "n_clicks"),
    Input("perform-avg-button", "n_clicks"),
    Input("modal-header", "children"),
    Input('input-sigma', 'value'),
    Input('input-radius', 'value'),
    State("modal", "is_open")
)
def toggle_modal(n1, n2, n3, avgType, sigIn, radIn, is_open):
    # open modal with spatial
    if 'spatial-avg-button' == ctx.triggered_id:
        return True, "Spatial Averaging", 8, 6
    
    # open modal with time
    elif 'time-avg-button' == ctx.triggered_id:
        return True, "Time Averaging", 4, 3
    
    # close modal and perform averaging
    elif 'perform-avg-button' == ctx.triggered_id:
        return False, avgType, sigIn, radIn
    
    # ignore updates to inputs
    elif 'input-sigma' == ctx.triggered_id or 'input-radius' == ctx.triggered_id:
        return True, avgType, sigIn, radIn
    
    # initial call
    # if you see "header" in modal, something went wrong
    return is_open, "HEADER", 0, 0

@callback(
    Output('reset-data-pressed', 'children', allow_duplicate=True),    
    Output('time-button-pressed', 'children', allow_duplicate=True),
    Output('spatial-button-pressed', 'children', allow_duplicate=True),
    Input('modal-header', "children"),
    Input('input-sigma', 'value'),
    Input('input-radius', 'value'),
    Input("perform-avg-button", "n_clicks"),
    prevent_initial_call=True)
def performAverage(header, sig, rad, n):
    empty = ""
    # if the modal was closed by the 'perform average' button
    if('perform-avg-button' == ctx.triggered_id):
        # if bad inputs (str, negative nums, etc.)
        if(sig is None or sig < 0):
            sig = 0
        if(rad is None or rad < 0):
            rad = 0
        # Time averaging
        if(header.split()[0] == 'Time'):
            msg = performTimeAverage(sig, rad)
            return empty, msg, empty
        # Spatial Averaging
        elif(header.split()[0] == 'Spatial'):
            msg = performSpatialAverage(sig, rad)
            return empty, empty, msg
        else:
            return "Error app.py in performAverage()", header.split()[0], empty
    else:
        return empty, empty, empty;    

def performTimeAverage(sig, rad):
    global im_edited
    im_edited = TimeAverage(im_edited, sig, rad);
    msg = "Time Average completed."
    return msg

def performSpatialAverage(sig, rad):
    global im_edited
    im_edited = SpatialAverage(im_edited, sig, rad);
    msg = "Spatial Averaging Completed."
    return msg

@callback(
        Output('reset-data-pressed', 'children', allow_duplicate=True),
        Output('time-button-pressed', 'children', allow_duplicate=True),
        Output('spatial-button-pressed', 'children', allow_duplicate=True),
        Input('reset-data-button', 'n_clicks'),
        prevent_initial_call=True)
def resetData(n_clicks):
    global im_edited, im_raw
    im_edited = im_raw.copy();
    msg = "Data reset."
    empty = ""
    return msg, empty, empty


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

    fig = px.line(im_edited[10:, x, y])
    fig.add_vline(x=frame_idx)
    fig.update_yaxes(fixedrange=True)
    fig.update_layout(showlegend=False)

    return fig
    

if __name__ == '__main__':
    app.run(debug=True)