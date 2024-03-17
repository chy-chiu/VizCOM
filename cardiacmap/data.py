### Simple parser script for .dat format

import argparse
import io
from locale import normalize
import struct
import pickle
import numpy as np
import os
import sys
from copy import deepcopy

from typing import List

from cardiacmap.transforms import (
    TimeAverage,
    SpatialAverage,
    InvertSignal,
    TrimSignal,
    GetMins,
    RemoveBaselineDrift,
    NormalizeData,
)


class CascadeDataVoltage:

    filename: str
    datetime: str
    framerate: int
    metadata: str
    span_T: int
    span_X: int
    span_Y: int
    base_data: List[np.ndarray]  # This list can be either one or two signal arrays
    transformed_data: List[np.ndarray]
    dual_mode: bool

    # TODO: Make signal independent of window / signal selected
    # transform_history: List[np.ndarray]
    # curr_index: int

    def __init__(
        self,
        filename,
        datetime,
        framerate,
        metadata,
        span_T,
        span_X,
        span_Y,
        voltage_data,
        dual_mode,
    ):
        self.filename = filename
        self.datetime = datetime
        self.framerate = framerate
        self.metadata = metadata
        self.span_T = span_T
        self.span_X = span_X
        self.span_Y = span_Y
        self.base_data = deepcopy(voltage_data)
        self.dual_mode = dual_mode
        self.transformed_data = voltage_data
        self.baselineX = []
        self.baselineY = []
        self.show_baseline = False

        # self.transform_history = [voltage_data]
        # self.curr_index = 0

    @classmethod
    def load_data(cls, filepath, calcium_mode=False):

        file_metadata, sigarray = CascadeDataVoltage.from_dat(filepath)

        if calcium_mode:
            voltage_data = [sigarray[::2, :, :], sigarray[1::2, :, :]]
            file_metadata["span_T"] = file_metadata["span_T"] // 2
        else:
            voltage_data = [sigarray]

        return cls(
            filename=filepath,
            voltage_data=voltage_data,
            dual_mode=calcium_mode,
            **file_metadata,
        )

    def switch_modes(self, dual_mode):
        if dual_mode:
            self.transformed_data = [
                self.transformed_data[0][::2, :, :],
                self.transformed_data[0][1::2, :, :],
            ]
            self.base_data = [
                self.base_data[0][::2, :, :],
                self.base_data[0][1::2, :, :],
            ]
            self.span_T = self.span_T // 2
            self.dual_mode = True
        else:
            new_transformed_data = np.empty(
                (
                    len(self.transformed_data[0]) + len(self.transformed_data[1]),
                    self.span_X,
                    self.span_Y,
                )
            )
            new_transformed_data[0::2, :, :], new_transformed_data[1::2, :, :] = (
                self.transformed_data
            )
            self.transformed_data = [new_transformed_data]

            new_base_data = np.empty(
                (
                    len(self.base_data[0]) + len(self.base_data[1]),
                    self.span_X,
                    self.span_Y,
                )
            )
            new_base_data[0::2, :, :], new_base_data[1::2, :, :] = self.base_data
            self.base_data = [new_base_data]

            self.span_T = self.span_T * 2
            self.dual_mode = False

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

    def perform_average(
        self,
        type,
        sig,
        rad,
        sig_id,
        mask=None,
        mode="Gaussian",
    ):
        
        if type == "time":
            self.transformed_data[sig_id] = TimeAverage(
                self.transformed_data[sig_id], sig, rad, mask, mode
            )

        elif type == "spatial":
            self.transformed_data[sig_id] = SpatialAverage(
                self.transformed_data[sig_id], sig, rad, mask, mode
            )

        return

    # TO FIX in a bit

    def invert_data(self, sig_id):
        self.transformed_data[sig_id] = InvertSignal(self.transformed_data[sig_id])

    def trim_data(self, sig_id, startTrim, endTrim):

        self.transformed_data[sig_id] = TrimSignal(
            self.transformed_data[sig_id], startTrim, endTrim
        )

    def reset_data(self, sig_id):
        self.transformed_data[sig_id] = self.base_data[sig_id]

    def normalize(self, sig_id):
        self.transformed_data[sig_id] = NormalizeData(self.transformed_data[sig_id])

    def calc_baseline(self, sig_id, method, methodValue):

        print("Calculating baseline", method, methodValue)
        data = self.transformed_data[sig_id]
        t = np.arange(len(data))
        threads = (
            8  # this seems to be optimal thread count, needs more testing to confirm
        )

        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t
        self.baselineX, self.baselineY = GetMins(
            t, dataSwapped, method, methodValue, threads
        )

    def remove_baseline_drift(self, sig_id):
        data = self.transformed_data[sig_id]
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
        self.transformed_data[sig_id] = np.moveaxis(dataMinusBaseline, -1, 0)

    def get_baseline(self):
        return self.baselineX, self.baselineY

    def reset_baseline(self):
        self.baselineX = self.baselineY = []

    def get_keyframe(self, series=0):
        # Take the middle as the key frame for now
        key_frame_idx = self.span_T // 2

        return self.base_data[series][key_frame_idx]

    def get_curr_signal(self):
        return self.transformed_data
        # return self.transform_history[self.curr_index]
