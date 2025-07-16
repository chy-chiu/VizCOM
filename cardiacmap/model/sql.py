import os

import numpy as np

from cardiacmap.model.data import CardiacSignal
from cardiacmap.viewer.components import large_file_check
from typing import Dict


def read_sql_data(filepath: str, largeFilePopup) -> np.ndarray:
    """Load raw data from SQLite .sql files. Returns a 3D signal array.
    Args:
        filepath (str): Input file path
        largeFilePopup (func): callback function to open popup window for larger-than-memory files

    Returns:
        metadata: dict of metadata
        imarray: numpy array of size (frame, H, W)
    """
    file = open(filepath, "rb")
    filename = os.path.basename(filepath)

    metadata = {"filename": filename}
    sigarray = None # data array

    span_T = None # number of frames, read from header
    span_X = 128
    span_Y = 128

    # trimFrames is a tuple
    # trimFrames[0] contains the number of frames to skip at the beginning of the file
    # trimFrames[1] contains the number of frames to read
    trimFrames = large_file_check(filepath, largeFilePopup, span_T)

    if trimFrames[1] == 0:
        # read the entire file
        pass
    else:
        # skip, then read
        pass



    metadata["span_T"] = span_T
    metadata["span_X"] = span_X
    metadata["span_Y"] = span_Y

    file.close()
    return metadata, sigarray


def load_sql_file(filepath, largeFilePopup, dual_mode=False) -> Dict[int, CardiacSignal]:
    """Wrapper to load a .sql file to return a single or dual channel signal.

    Args:
        filepath (str): Path ot file
        largeFilePopup (): _description_
        dual_mode (bool, optional): Whether the input signal is dual mode (Voltage / Calcium). Defaults to False.

    Returns:
        signals: Dictionary of CascadeSignal
    """
    signals = {}

    file_metadata, sigarray = read_sql_data(filepath, largeFilePopup)
    if sigarray is not None:

        if dual_mode:
            odd_frames, even_frames = [sigarray[::2, :, :], sigarray[1::2, :, :]]
            signals[0] = CardiacSignal(
                signal=odd_frames, metadata=file_metadata, channel="Odd"
            )
            signals[1] = CardiacSignal(
                signal=even_frames, metadata=file_metadata, channel="Even"
            )
            file_metadata["span_T"] = file_metadata["span_T"] // 2
        else:
            signals[0] = CardiacSignal(
                signal=sigarray, metadata=file_metadata, channel="Single"
            )

    return signals