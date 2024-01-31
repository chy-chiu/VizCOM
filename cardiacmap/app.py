from dash import Dash, dcc, html, Input, Output, callback
import plotly.express as px

from data import cascade_import
from transforms import TimeAverage, SpatialAverage
import json

app = Dash(__name__)

im_raw = cascade_import("2012-02-13_Exp000_Rec005_Cam3-Blue.dat")

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
    html.Button('Time Averaging', id='time-avg'),
    html.Button('Spatial Averaging', id='spatial-avg'),
    html.Div(id='buttons'),
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

    fig = px.line(im_raw[10:, x, y])
    fig.add_vline(x=frame_idx)
    
    return fig
    

if __name__ == '__main__':
    app.run(debug=True)