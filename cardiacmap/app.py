from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

from data import cascade_import
from transforms import TimeAverage, SpatialAverage
import json
import copy

app = Dash(__name__)

im_raw = cascade_import("2012-02-13_Exp000_Rec005_Cam3-Blue.dat")
im_edited = im_raw.copy()

app.layout = html.Div([
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    dcc.Graph(id='graph-image'),
    html.Button('Reset', id='reset-data-button'),
    html.Div(id='reset-data-pressed'),
    html.Button('Time Averaging', id='time-avg-button'),
    html.Div(id='time-button-pressed'),
    html.Button('Spatial Averaging', id='spatial-avg-button'),
    html.Div(id='spatial-button-pressed'),
    dcc.Graph(id='graph-signal'),
    dcc.Slider(
        0,
        5000,
        step=None,
        value=100,
        id='frame-slider',
        updatemode='drag'
    ),
    dcc.Store(id='frame-index', storage_type="session"),
    dcc.Store(id='signal-position', storage_type="session")
])

@callback(
        Output('time-button-pressed', 'children', allow_duplicate=True),
        Input('time-avg-button', 'n_clicks'),
        prevent_initial_call=True)
def performTimeAverage(n_clicks):
    global im_edited
    im_edited = TimeAverage(im_edited, 4, 3);
    msg = "Time Average completed."
    return msg

@callback(
        Output('spatial-button-pressed', 'children', allow_duplicate=True),
        Input('spatial-avg-button', 'n_clicks'),
        prevent_initial_call=True)
def performSpatialAverage(n_clicks):
    global im_edited
    im_edited = SpatialAverage(im_edited, 8, 6);
    msg = "Spatial Averaging Completed."
    return msg

@callback(
        Output('reset-data-pressed', 'children'),
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
    Output('frame-index', 'data'),
    Input('frame-slider', 'value'),
    )
def update_frame_idx(frame_idx):
    return frame_idx

@callback(
    Output('frame-slider', 'value'),
    Input('graph-signal', 'clickData'),
    prevent_initial_call=True
)
def update_frame_slider_idx(clickData):
    if clickData is not None: 
        frame_idx = clickData['points'][0]['pointIndex']
    return frame_idx

@callback(
    Output('signal-position', 'data'),
    Input('graph-image', 'clickData'))
def update_signal_position(clickData):
    if clickData is not None: 
        x = clickData['points'][0]['x']
        y = clickData['points'][0]['y']
    else:
        x = 64
        y = 64
    return json.dumps({"x": x, "y": y})


@callback( Output('graph-image', 'figure'),
          Input('frame-index', 'data'))
def update_figure(frame_idx):

    fig = px.imshow(im_raw[frame_idx], binary_string=True)

    return fig

@callback(
    Output('graph-signal', 'figure'),
    Input('signal-position', 'data'),
    Input('frame-index', 'data'))
def display_click_data(signal_position, frame_idx):
    signal_position = json.loads(signal_position)
    x = signal_position['x']
    y = signal_position['y']

    fig = px.line(im_edited[10:, x, y])
    fig.add_vline(x=frame_idx)
    
    return fig
    

if __name__ == '__main__':
    app.run(debug=True)