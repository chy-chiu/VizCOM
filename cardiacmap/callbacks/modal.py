from dash import MATCH, Dash, Input, Output, State


def modal_callbacks(app: Dash):
    def toggle_modal(n, is_open):
        if n:
            return not is_open
        return is_open

    app.callback(
        Output({"type": "spatial-avg-modal", "index": MATCH}, "is_open"),
        Input({"type": "spatial-avg-button", "index": MATCH}, "n_clicks"),
        State({"type": "spatial-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "time-avg-modal", "index": MATCH}, "is_open"),
        Input({"type": "time-avg-button", "index": MATCH}, "n_clicks"),
        State({"type": "time-avg-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "trim-modal", "index": MATCH}, "is_open"),
        Input({"type": "trim-signal-button", "index": MATCH}, "n_clicks"),
        State({"type": "trim-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "baseline-modal", "index": MATCH}, "is_open"),
        Input({"type": "remove-drift-button", "index": MATCH}, "n_clicks"),
        State({"type": "baseline-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)

    app.callback(
        Output({"type": "apd-di-modal", "index": MATCH}, "is_open"),
        Input({"type": "calc-apd-di-button", "index": MATCH}, "n_clicks"),
        State({"type": "apd-di-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)
    
    app.callback(
        Output({"type": "spatial-apd-settings-modal", "index": MATCH}, "is_open"),
        Input({"type": "spatial-apd-settings-button", "index": MATCH}, "n_clicks"),
        State({"type": "spatial-apd-settings-modal", "index": MATCH}, "is_open"),
        prevent_initial_call=True,
    )(toggle_modal)
