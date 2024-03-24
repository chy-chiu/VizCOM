### Simple parser script for .dat format

import argparse
import io
import os
import pickle
import struct
import sys
from copy import deepcopy
from locale import normalize
from typing import Dict, List

import numpy as np

from cardiacmap.transforms import (CalculateAPD_DI, GetIntersectionsAPD_DI,
                                  GetMins, InvertSignal, NormalizeData,
                                  RemoveBaselineDrift, SpatialAverage,
                                  TimeAverage, TrimSignal)


class CascadeSignal:
    """Class for Cascade voltage / calcium signal data. The original data
    is stored in base_data, and any additional transformations is done on
    transformed_data. Transformations are all done by calling the external
    transforms.py library, which provides methods to calculate various
    transforms. Additionally, empty variables are saved for baseline calculation,
    apd / di variables.
    """

    span_T: int
    # TODO: In the event that we do anything other than 128x128 images, this cannot be hardcoded anymore
    span_X: int = 128
    span_Y: int = 128
    base_data: np.ndarray
    transformed_data: np.ndarray

    def __init__(self, signal: np.ndarray) -> None:
        self.base_data = deepcopy(signal)
        self.transformed_data = deepcopy(signal)
        self.span_T = len(signal)

        ## Baseline drift variables
        self.baselineX = []
        self.baselineY = []
        self.show_baseline = False

        ## APD / DI variables
        self.apdThreshold = 0
        self.apdDIThresholdIdxs = []
        self.apdIndicators = []
        self.apds = []
        self.apd_indices = []
        self.dis = []
        self.di_indices = []
        self.show_apd_threshold = False

    def perform_average(
        self,
        type,
        sig,
        rad,
        mask=None,
        mode="Gaussian",
    ):
        if type == "time":
            self.transformed_data = TimeAverage(
                self.transformed_data, sig, rad, mask, mode
            )

        elif type == "spatial":
            self.transformed_data = SpatialAverage(
                self.transformed_data, sig, rad, mask, mode
            )

        return

    def calc_apd_di_threshold(self, threshold):
        data = np.moveaxis(self.transformed_data, 0, -1)
        self.apdDIThresholdIdxs, self.apdIndicators = GetIntersectionsAPD_DI(
            data, threshold
        )
        self.apdThreshold = threshold

    def calc_apd_di(self):
        self.apds, self.apd_indices, self.dis, self.di_indices = CalculateAPD_DI(
            self.apdDIThresholdIdxs, self.apdIndicators
        )

    def reset_apd_di(self):
        self.apdDIThresholdIdxs = self.apdIndicators = []
        self.apds = self.apd_indices = self.dis = self.di_indices = []
        self.apdThreshold = 0

    def invert_data(self):
        self.transformed_data = InvertSignal(self.transformed_data)

    def trim_data(self, startTrim, endTrim):
        self.transformed_data = TrimSignal(self.transformed_data, startTrim, endTrim)

    def reset_data(self):
        self.transformed_data = deepcopy(self.base_data)

    def normalize(self):
        self.transformed_data = NormalizeData(self.transformed_data)

    def calc_baseline(self, method, methodValue):
        print("Calculating baseline", method, methodValue)
        data = self.transformed_data
        t = np.arange(len(data))
        threads = (
            8  # this seems to be optimal thread count, needs more testing to confirm
        )

        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t
        self.baselineX, self.baselineY = GetMins(
            t, dataSwapped, method, methodValue, threads
        )

    def remove_baseline_drift(self):
        data = self.transformed_data
        baselineXs = self.baselineX
        baselineYs = self.baselineY
        t = np.arange(len(data))
        threads = (
            8  # this seems to be optimal thread count, needs more testing to confirm
        )

        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t

        dataMinusBaseline = RemoveBaselineDrift(
            t, dataSwapped, baselineXs, baselineYs, threads
        )

        # flip data axes back and store results
        # NB: np.int16 is double the size of np.uint16
        self.transformed_data = np.moveaxis(dataMinusBaseline, -1, 0)

    def get_baseline(self):
        return self.baselineX, self.baselineY

    def reset_baseline(self):
        self.baselineX = self.baselineY = []

    def get_apd_threshold(self):
        return self.apdDIThresholdIdxs, self.apdThreshold

    def get_apds(self):
        return self.apds, self.apd_indices

    def get_dis(self):
        return self.dis, self.di_indices

    def reset_apd_di(self):
        self.apdDIThresholdIdxs = self.apdIndicators = []
        self.apds = self.apd_indices = []
        self.dis = self.di_indices = []
        self.apdThreshold = 0

    def get_keyframe(self):
        # Take the middle as the key frame for now
        key_frame_idx = self.span_T // 2

        return self.base_data[key_frame_idx]

    def get_curr_signal(self):
        return self.transformed_data


class CascadeDataFile:
    """Container for cascade data voltage signal. It either consists of a single
    signal (voltage), or dual signal (voltage + calcium). All the other relevant
    metadata, such as filename, datetime etc, are all saved as variables here.
    The import / loading functions from .dat (and in the future will support other
    files also) are also contained here.
    """

    filename: str
    datetime: str
    framerate: int
    metadata: str
    span_T: int
    span_X: int
    span_Y: int
    dual_mode: bool
    signals: Dict[int, CascadeSignal]

    def __init__(
        self,
        filename,
        datetime,
        framerate,
        metadata,
        span_T,
        span_X,
        span_Y,
        dual_mode,
        signals,
    ):
        self.filename = filename
        self.datetime = datetime
        self.framerate = framerate
        self.metadata = metadata
        self.span_T = span_T
        self.span_X = span_X
        self.span_Y = span_Y
        self.dual_mode = dual_mode
        self.signals = signals

    @classmethod
    def load_data(cls, filepath, dual_mode=False):
        file_metadata, sigarray = CascadeDataFile.from_dat(filepath)

        signals = {}

        if dual_mode:
            odd_frames, even_frames = [sigarray[::2, :, :], sigarray[1::2, :, :]]
            signals[0] = CascadeSignal(signal=odd_frames)
            signals[1] = CascadeSignal(signal=even_frames)
            file_metadata["span_T"] = file_metadata["span_T"] // 2
        else:
            signals[0] = CascadeSignal(signal=sigarray)

        return cls(
            filename=filepath,
            dual_mode=dual_mode,
            signals=signals,
            **file_metadata,
        )

    def switch_modes(self, dual_mode):
        new_signals = {}

        if dual_mode and not self.dual_mode:
            sigarray = self.signals["signal"].base_data

            odd_frames, even_frames = [sigarray[::2, :, :], sigarray[1::2, :, :]]

            new_signals["odd"] = CascadeSignal(signal=odd_frames)
            new_signals["even"] = CascadeSignal(signal=even_frames)

            self.span_T = self.span_T // 2
            self.dual_mode = True

            self.signals = new_signals

        elif not dual_mode and self.dual_mode:
            odd_frames = self.signals["odd"]
            even_frames = self.signals["even"]

            combined_signal = np.empty(
                (
                    len(odd_frames.base_data) + len(even_frames.base_data),
                    self.span_X,
                    self.span_Y,
                )
            )
            combined_signal[0::2, :, :] = odd_frames.base_data
            combined_signal[1::2, :, :] = even_frames.base_data

            new_signals["signal"] = CascadeSignal(signal=combined_signal)

            self.span_T = self.span_T * 2
            self.dual_mode = False

            self.signals = new_signals


    # TODO: Adding trace instead of the whole thing might be faster? Idk 
    def traces(self):

        signal_traces = {}

        for k, signal in self.signals:
            for i in range(128):
                signal_traces[(k, i)] = signal[:, i, :]

        return signal_traces

    @staticmethod
    def from_dat(filepath: str) -> np.ndarray:
        """Load data from .dat files irrespective of mode

        Args:
            filepath (str): Input file path

        Returns:
            file_metadata: dict of metadata
            imarray: numpy array of size (frame, H, W)
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        f_path = os.path.join(script_dir, f"data/{filepath}")
        file = open(f_path, "rb")

        endian = "<"

        file_metadata = {}

        # First byte of the data is the file version
        file_version = file.read(1).decode()

        if file_version == "d":
            # TODO: Version D is a WIP.This needs to be tested.
            header = file.read(1023)

            # In the original code, it reads 17 + 7 bytes of datetime.
            file_metadata["datetime"] = header.pop(24).decode().rstrip("\x00")

            file.read(8)
            file_metadata["framerate"] = (
                struct.unpack(endian + "I", file.read(4))[0] / 100
            )

            span_T = struct.unpack(endian + "I", file.read(4))[0]
            span_X = struct.unpack(endian + "I", file.read(4))[0]
            span_Y = struct.unpack(endian + "I", file.read(4))[0]

            skip_bytes = 0

            file_metadata["metadata"] = ""

        elif file_version == "f" or file_version == "e":
            # First integer is the byte order
            byte_order = struct.unpack("I", file.read(4))[0]

            if byte_order == 439041101:
                endian = "<"
            else:
                endian = ">"

            # Next three integers are the span
            span_T = struct.unpack(endian + "I", file.read(4))[0]
            span_X = struct.unpack(endian + "I", file.read(4))[0]
            span_Y = struct.unpack(endian + "I", file.read(4))[0]

            # Skip 8 bytes
            file.read(8)
            file_metadata["framerate"] = (
                struct.unpack(endian + "I", file.read(4))[0] / 100
            )
            file_metadata["datetime"] = file.read(24).decode().rstrip("\x00")
            file_metadata["metadata"] = file.read(971).decode().rstrip("\x00")

            skip_bytes = 8

        sigarray = np.frombuffer(file.read(), dtype="uint16")
        skip = skip_bytes // 2

        sigarray = sigarray.reshape(span_T, -1)[:, :-skip].reshape(
            span_T, span_X, span_Y
        )

        file_metadata["span_T"] = span_T
        file_metadata["span_X"] = span_X
        file_metadata["span_Y"] = span_Y

        file.close()

        return file_metadata, sigarray

    def __repr__(self):
        return f"CascadeDataVoltage - {self.filename}"
