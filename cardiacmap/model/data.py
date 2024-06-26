import argparse
import io
import os
import pickle
import struct
import sys
import psutil
from copy import deepcopy
from locale import normalize
from typing import Dict, List, Tuple

import cv2
import numpy as np

from cardiacmap.transforms import (CalculateAPD_DI, GetIntersectionsAPD_DI,
                                   GetMins, InvertSignal, NormalizeData,
                                   RemoveBaselineDrift, SpatialAverage,
                                   TimeAverage, TrimSignal)

from cardiacmap.model.signal import CascadeSignal

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
    def load_data(cls, filepath, largeFilePopup, dual_mode=False):
        file_metadata, sigarray = CascadeDataFile.from_dat(filepath, largeFilePopup)

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
            sigarray = self.signals[0].base_data

            odd_frames, even_frames = [sigarray[::2, :, :], sigarray[1::2, :, :]]

            new_signals[0] = CascadeSignal(signal=odd_frames)
            new_signals[1] = CascadeSignal(signal=even_frames)

            self.span_T = self.span_T // 2
            self.dual_mode = True

            self.signals = new_signals

        elif not dual_mode and self.dual_mode:
            odd_frames = self.signals[0]
            even_frames = self.signals[1]

            combined_signal = np.empty(
                (
                    len(odd_frames.base_data) + len(even_frames.base_data),
                    self.span_X,
                    self.span_Y,
                )
            )
            combined_signal[0::2, :, :] = odd_frames.base_data
            combined_signal[1::2, :, :] = even_frames.base_data

            new_signals[0] = CascadeSignal(signal=combined_signal)

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
    def large_file_check(filepath, _callback):
        """Check filepath against available RAM
        Args:
            filepath(str): Input file path
        Returns:
            tuple: (skip_frames, read_frames) or (0, 0) if file is small enough to handle
        """
        USAGE_THRESHOLD = .5
        freeMem = psutil.virtual_memory()[1]
        estDataSize = os.path.getsize(filepath) * 4 # estimate conversion to float16 and 2 data sets (raw and transformed)
                                                    # THIS IS A VERY ROUGH ESTIMATE PROBABLY NEEDS FURTHER INVESTIGATION
        
        usePercentage = estDataSize / freeMem
        
        # use 50% threshold to leave room for apd, di, fft, etc.
        if usePercentage > USAGE_THRESHOLD:
            maxFrames = int((freeMem * .5)/1040000) # AGAIN, VERY ROUGH ESTIMATE BASED ON 5k FRAMES @ 650MB
            
            start, end = _callback(maxFrames) #pauses execution until popup is closed

            skip = start
            size = end - start
            
            return (skip, size)
        return (0, 0)

    @staticmethod
    def from_dat(filepath: str, largeFilePopup) -> np.ndarray:
        """Load data from .dat files irrespective of mode

        Args:
            filepath (str): Input file path
            largeFilePopup (func): callback function to open popup window for larger-than-memory files 

        Returns:
            file_metadata: dict of metadata
            imarray: numpy array of size (frame, H, W)
        """
        file = open(filepath, "rb")

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
            
        skip = skip_bytes // 2
        
        trimFrames = CascadeDataFile.large_file_check(filepath, largeFilePopup)
        if trimFrames[1] == 0:
            sigarray = np.frombuffer(file.read(), dtype="float16")
        else:
            file.read(trimFrames[0] * 2 * span_X * span_Y + trimFrames[0] * skip_bytes) # skip
            sigarray = np.frombuffer(file.read(trimFrames[1] * 2 * span_X * span_Y + trimFrames[1] * skip_bytes), dtype="float16" ) # read   
            span_T = trimFrames[1] # set new spanT
            
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
