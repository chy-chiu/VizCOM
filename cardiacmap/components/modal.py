### Components for modal

import dash_bootstrap_components as dbc
from dash import html

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def numerical_input_modal(modal_id, modal_text, n, value):
    return html.Div(
        [
            html.P(modal_text),
            dbc.Input(
                id=indexed_component_id(modal_id, n),
                type="number",
                min=0,
                value=value,
            ),
        ],
    )


def radio_input_modal(modal_id, label, options, n, value):
    return html.Div(
        [
            dbc.Label(label),
            dbc.RadioItems(
                options=options,
                value=value,
                id=indexed_component_id(modal_id, n),
                inline=True,
            ),
        ]
    )


def transform_modals(n):
    spatial_modal = dbc.Modal(
        [
            dbc.ModalHeader("Spatial Averaging"),
            dbc.ModalBody(
                [
                    radio_input_modal(
                        modal_id="spatial-avg-mode",
                        label="Choose Averaging Method:",
                        options=[
                            {"label": "Gaussian", "value": "Gaussian"},
                            {"label": "Uniform", "value": "Uniform"},
                        ],
                        value="Gaussian",
                        n=n,
                    ),
                    numerical_input_modal(
                        modal_id="spatial-avg-sigma", modal_text="Sigma", n=n, value=8
                    ),
                    numerical_input_modal(
                        modal_id="spatial-avg-radius", modal_text="Radius", n=n, value=6
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button(
                    "Confirm", id=indexed_component_id(f"spatial-avg-confirm", n)
                )
            ),
        ],
        id=indexed_component_id(f"spatial-avg-modal", n),
        is_open=False,
    )

    time_modal = dbc.Modal(
        [
            dbc.ModalHeader("Time Averaging"),
            dbc.ModalBody(
                [
                    radio_input_modal(
                        modal_id="time-avg-mode",
                        label="Choose Averaging Method:",
                        options=[
                            {"label": "Gaussian", "value": "Gaussian"},
                            {"label": "Uniform", "value": "Uniform"},
                        ],
                        value="Gaussian",
                        n=n,
                    ),
                    numerical_input_modal(
                        modal_id="time-avg-sigma", modal_text="Sigma", n=n, value=4
                    ),
                    numerical_input_modal(
                        modal_id="time-avg-radius", modal_text="Radius", n=n, value=3
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id=indexed_component_id(f"time-avg-confirm", n))
            ),
        ],
        id=indexed_component_id(f"time-avg-modal", n),
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
                dbc.Button("Confirm", id=indexed_component_id(f"trim-confirm", n))
            ),
        ],
        id=indexed_component_id(f"trim-modal", n),
        is_open=False,
    )

    baseline_modal = dbc.Modal(
        [
            dbc.ModalHeader("Remove Baseline Drift"),
            dbc.ModalBody(
                [
                    radio_input_modal(
                        modal_id="baseline-mode",
                        label="Choose Baseline Method:",
                        options=[
                            {"label": "Period", "value": "Period"},
                            {"label": "Threshold", "value": "Threshold"},
                        ],
                        value="Period",
                        n=n,
                    ),
                    numerical_input_modal(
                        modal_id="baseline-period", modal_text="Period", n=n, value=50
                    ),
                    numerical_input_modal(
                        modal_id="baseline-threshold",
                        modal_text="Threshold",
                        n=n,
                        value=50,
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id=indexed_component_id(f"baseline-confirm", n))
            ),
        ],
        id=indexed_component_id(f"baseline-modal", n),
        is_open=False,
    )

    apd_di_modal = dbc.Modal(
        [
            dbc.ModalHeader("Calculate APD/DI"),
            dbc.ModalBody(
                [
                    numerical_input_modal(
                        modal_id="apd-di-threshold",
                        modal_text="Threshold",
                        n=n,
                        value=0,
                    ),
                ]
            ),
            dbc.ModalFooter(
                dbc.Button("Confirm", id=indexed_component_id(f"apd-di-confirm", n))
            ),
        ],
        id=indexed_component_id(f"apd-di-modal", n),
        is_open=False,
    )

    return html.Div(
        [spatial_modal, time_modal, trim_modal, baseline_modal, apd_di_modal]
    )

def video_modals(n):

    render_modal = dbc.Modal(
        [
            # TODO: Heatmap color, framerate etc.
            dbc.ModalHeader("Rendering Options"),
            dbc.ModalBody(
                [
                    radio_input_modal(
                        modal_id="normalization-mode",
                        label="Choose Normalization:",
                        options=[
                            {"label": "Raw", "value": "Raw"},
                            {"label": "Normalized", "value": "Normalized"},
                        ],
                        value="Raw",
                        n=n,
                    ),
                    radio_input_modal(
                        modal_id="data-source",
                        label="Choose Signal Source:",
                        options=[
                            {"label": "Base Signal", "value": "Base Signal"},
                            {"label": "Transformed Signal", "value": "Transformed Signal"},
                        ],
                        value="Base Signal",
                        n=n,
                    ),
                ]
            )
        ],
        id=indexed_component_id(f"rendering-modal", n),
        is_open=False,
    )

    return html.Div(render_modal)