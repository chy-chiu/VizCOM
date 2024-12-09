import json
from pathlib import Path

import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter
from PySide6.QtWidgets import QProgressDialog
import time

DEFAULT_SETTINGS_PATH = "./settings.json"
DEFAULT_VALUES = {
    # "Stacking Parameters": [
    #     {"name": "Start Time", "type": "int", "value": 0, "limits": (0, 100000)},
    #     {"name": "# of Beats", "type": "int", "value": 10, "limits": (0, 30)},
    #     {
    #         "name": "Alternans",
    #         "type": "bool",
    #         "value": False,
    #     },
    #     {
    #         "name": "End Time",
    #         "type": "int",
    #         "value": -1,
    #         "limits": (-1, 100000),
    #     },
    # ],
    # "FFT Parameters": [
    #     {"name": "Start Time", "type": "int", "value": 0, "limits": (0, 100000)},
    #     {"name": "End Time", "type": "int", "value": -1, "limits": (-1, 100000),},
    # ],
    "Spatial Average": [
        {"name": "Sigma", "type": "int", "value": 8, "limits": (0, 100)},
        {"name": "Radius", "type": "int", "value": 6, "limits": (0, 100)},
        {
            "name": "Mode",
            "type": "list",
            "value": "Gaussian",
            "limits": ["Gaussian", "Uniform"],
        },
    ],
    "Time Average": [
        {"name": "Sigma", "type": "int", "value": 4, "limits": (0, 100)},
        {"name": "Radius", "type": "int", "value": 3, "limits": (0, 100)},
        {
            "name": "Mode",
            "type": "list",
            "value": "Uniform",
            "limits": ["Gaussian", "Uniform"],
        },
    ],
    # "Trim Parameters": [
    #     {"name": "Left", "type": "int", "value": 100, "limits": (0, 100000)},
    #     {"name": "Right", "type": "int", "value": 100, "limits": (0, 100000)},
    # ],
    "Baseline Drift": [
        {
            "name": "Alternans",
            "type": "bool",
            "value": False,
        },
        {"name": "Prominence", "type": "float", "value": 0.1, "limits": (0, 1)},
        {"name": "Period Len", "type": "int", "value": 0, "limits": (0, 1000)},
        {"name": "Threshold", "type": "float", "value": 0, "limits": (0, 1)},
    ],
    "APD Parameters": [
        {"name": "Threshold", "type": "float", "value": 0.5, "limits": (0, 1000)},
    ],
    # "Signal Plot Colors": [
    #     {"name": "signal", "value": [255, 255, 255]}, 
    #     {"name": "apd", "value": [255, 0, 0]},
    #     {"name": "baseline", "value": [0, 255, 0]},
    #     {"name": "points", "value": [0, 0, 255]},
    #     {"name": "background", "value": [0, 0, 0]},
    # ],
}


def get_default_settings():

    params = []
    for k, v in DEFAULT_VALUES.items():
        #print(k, v)
        params.append(Parameter.create(name=k, type="group", children=v))

    params_parent = Parameter.create(
        name="Parameters",
        type="group",
        children=params,
    )

    return params_parent


def load_settings(settings_path=DEFAULT_SETTINGS_PATH):
    settings_path = Path(settings_path)
    try:
        if settings_path.exists():
            with open(settings_path, "r") as f:
                settings = Parameter.create(name="Parameters")

                settings_json = json.loads(f.read())

                # for param in DEFAULT_VALUES.keys():
                #     assert param in settings_json.keys()

                settings.restoreState(settings_json)
        else:
            raise FileNotFoundError("settings.json not found")

    except:
        print("Error Loading Settings. Using hardcoded defaults.")
        settings = get_default_settings()

    return settings


def save_settings(settings: Parameter, file_path=DEFAULT_SETTINGS_PATH):

    with open(file_path, "w") as f:
        f.write(json.dumps(settings.saveState()))


def loading_popup(func):
    """Decorator for progress bar. In order to use, need to add `update_progress`=None in the function signature.
    To update progress, remember to normalize progerss to 1"""

    def wrapper(*args, **kwargs):

        with pg.ProgressDialog("Loading..", 0, 100, wait=0, busyCursor=True) as dlg:

            def update_progress(value):
                dlg.setValue(value * 100)
                if dlg.wasCanceled():
                    raise Exception("Processing canceled by user")

            kwargs["update_progress"] = (
                update_progress  # Pass the callback function to the decorated function
            )

            result = func(*args, **kwargs)  # Call the decorated function

            if dlg.wasCanceled():
                raise Exception("Processing canceled by user")

            return result

    return wrapper
