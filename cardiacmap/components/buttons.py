import dash_bootstrap_components as dbc
from dash import html

indexed_component_id = lambda idx, n: {"type": idx, "index": n}


def button_bar(n):
    return dbc.Row(
        [
            dbc.Button(
                [html.I(className="bi bi-crop"), "  Trim"],
                id=indexed_component_id("trim-signal-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-caret-down"), "  Invert"],
                id=indexed_component_id("invert-signal-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi-bootstrap-reboot"), "  Reset"],
                id=indexed_component_id("reset-data-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Normalize"],
                id=indexed_component_id("normalize-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Time Average"],
                id=indexed_component_id("time-avg-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.Button(
                [html.I(className="bi bi-bar-chart"), "  Spatial Average"],
                id=indexed_component_id("spatial-avg-button", n),
                color="light",
                class_name="button-viewer",
            ),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        [
                            html.I(className="bi bi-bar-chart"),
                            "  Remove Baseline Drift",
                        ],
                        id=indexed_component_id("remove-drift-button", n),
                        color="light",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-check")],
                        id=indexed_component_id("confirm-baseline-button", n),
                        className="btn btn-success",
                        color="light",
                        disabled=True,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-x")],
                        id=indexed_component_id("reject-baseline-button", n),
                        className="btn btn-danger",
                        color="light",
                        disabled=True,
                    ),
                ],
                class_name="button-viewer",
            ),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        [
                            html.I(className="bi bi-bar-chart"),
                            "  Calculate APDs/DIs",
                        ],
                        id=indexed_component_id("calc-apd-di-button", n),
                        color="light",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-check")],
                        id=indexed_component_id("confirm-apd-di-button", n),
                        className="btn btn-success",
                        color="light",
                        disabled=True,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-x")],
                        id=indexed_component_id("reject-apd-di-button", n),
                        className="btn btn-danger",
                        color="light",
                        disabled=True,
                    ),
                ],
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
