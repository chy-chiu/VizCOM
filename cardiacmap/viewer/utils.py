import pyqtgraph as pq
from pyqtgraph.parametertree import Parameter
from pathlib import Path
import json


DEFAULT_SETTINGS_PATH = "./settings.json"
DEFAULT_VALUES = {
    "Stacking Parameters": [
        {"name": "Start Frame", "type": "int", "value": 0, "limits": (0, 100000)},
        {"name": "# of Beats", "type": "int", "value": 10, "limits": (0, 30)},
        {
            "name": "Alternans",
            "type": "bool",
            "value": False,
        },
        {
            "name": "End Frame (Optional)",
            "type": "int",
            "value": 1000,
            "limits": (0, 1000),
        },
    ],
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
            "value": "Gaussian",
            "limits": ["Gaussian", "Uniform"],
        },
    ],
    "Trim Parameters": [
        {"name": "Left", "type": "int", "value": 100, "limits": (0, 100000)},
        {"name": "Right", "type": "int", "value": 100, "limits": (0, 100000)},
    ],
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
}


def get_default_settings():

    params = []
    for k, v in DEFAULT_VALUES.items():
        params.append(
            Parameter.create(name=k, type="group", children=v)
        )

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

                for param in DEFAULT_VALUES.keys():
                    assert param in settings_json.keys()

                settings.restoreState(settings_json)
        else:
            raise FileNotFoundError("settings.json not found")

    except:
        settings = get_default_settings()

    return settings


def save_settings(settings: Parameter):

    with open(DEFAULT_SETTINGS_PATH, "w") as f:
        f.write(json.dumps(settings.saveState()))


def loading_popup(func):
    def wrapper(*args, **kwargs):
        with pq.ProgressDialog("Processing..", 0, 100, wait=50, busyCursor=True) as dlg:
            # do stuff
            func(*args, **kwargs)
            if dlg.wasCanceled():
                raise Exception("Processing canceled by user")

    return wrapper
