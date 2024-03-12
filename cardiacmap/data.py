### Simple parser script for .dat format

import argparse
import io
from locale import normalize
import struct
import pickle
import numpy as np
import os
import sys

from typing import List

from cardiacmap.transforms import TimeAverage, SpatialAverage, InvertSignal, TrimSignal, GetMins, RemoveBaselineDrift, NormalizeData

class CascadeDataVoltage:

    filename: str
    datetime: str
    framerate: int
    metadata: str
    span_T: int
    span_X: int
    span_Y: int
    base_data: np.ndarray

    # TODO: To implement history later. For now will include only base and transformed. 
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
    ):
        self.filename = filename
        self.datetime = datetime
        self.framerate = framerate
        self.metadata = metadata
        self.span_T = span_T
        self.span_X = span_X
        self.span_Y = span_Y
        self.base_data = voltage_data
        self.transformed_data = voltage_data
        self.baselineX = []
        self.baselineY = []
        
        # self.transform_history = [voltage_data]
        # self.curr_index = 0

    def __repr__(self):
        return f"CascadeDataVoltage - {self.filename}"

    def perform_average(self, type, sig, rad, mask=None, mode='Gaussian'):
        if type == "time":
            self.transformed_data = TimeAverage(self.transformed_data, sig, rad, mask, mode)
        elif type == "spatial":
            self.transformed_data = SpatialAverage(self.transformed_data, sig, rad, mask, mode)
        return
    
    def calc_baseline(self, method, methodValue):
        data = self.transformed_data
        t = np.arange(len(data))
        threads = 8 # this seems to be optimal thread count, needs more testing to confirm
        
        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1) # y, x, t
        self.baselineX, self.baselineY = GetMins(t, dataSwapped, method, methodValue, threads)
        
    def remove_baseline_drift(self):
        data = self.transformed_data
        baselineXs = self.baselineX
        baselineYs = self.baselineY
        t = np.arange(len(data))
        threads = 8 # this seems to be optimal thread count, needs more testing to confirm
        
        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1) # y, x, t
        
        dataMinusBaseline = RemoveBaselineDrift(t, dataSwapped, baselineXs, baselineYs, threads)
        
        # flip data axes back and store results
        self.transformed_data = np.moveaxis(dataMinusBaseline, -1, 0)
    
    def invert_data(self):
        self.transformed_data = InvertSignal(self.transformed_data)
    
    def trim_data(self, startTrim, endTrim):
        self.transformed_data = TrimSignal(self.transformed_data, startTrim, endTrim)

    def reset_data(self):
        self.transformed_data = self.base_data

    def normalize(self):
        self.transformed_data = NormalizeData(self.transformed_data)
    
    def get_curr_signal(self):
        return self.transformed_data
        # return self.transform_history[self.curr_index]

    def get_baseline(self):
        return self.baselineX, self.baselineY
    
    def reset_baseline(self):
        self.baselineX = self.baselineY = []
    
    def get_keyframe(self):
        # Take the middle as the key frame for now
        key_frame_idx = self.span_T // 2
        return self.base_data[key_frame_idx]

    # TODO: Refactor this chunk and optimize it
    @classmethod
    def from_dat(cls, filepath):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        f_path = os.path.join(script_dir, f'data/{filepath}')
        file = open(f_path, "rb")

        endian = "<"

        # First byte of the data is the file version
        file_version = file.read(1).decode()

        if file_version == "d":
            # TODO: Version D is a WIP.This needs to be tested.
            header = file.read(1023)

            # In the original code, it reads 17 + 7 bytes of datetime.
            datetime = header.pop(24).decode().rstrip("\x00")

            file.read(8)
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100

            span_T = struct.unpack(endian + "I", file.read(4))[0]
            span_X = struct.unpack(endian + "I", file.read(4))[0]
            span_Y = struct.unpack(endian + "I", file.read(4))[0]

            skip_bytes = 0

            metadata = ""

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
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100
            datetime = file.read(24).decode().rstrip("\x00")
            metadata = file.read(971).decode().rstrip("\x00")

            skip_bytes = 8

        
        imarray = np.frombuffer(file.read(), dtype='uint16')
        skip = skip_bytes // 2

        imarray = imarray.reshape(span_T, -1)[:, :-skip].reshape(span_T, span_X, span_Y)

        file.close()

        return cls(
            filename=filepath,
            datetime=datetime,
            framerate=framerate,
            metadata=metadata,
            span_T=span_T,
            span_X=span_X,
            span_Y=span_Y,
            voltage_data=imarray,
        )


# TODO: Refactor this into a class method
def cascade_import(filepath: str):
    """Main function to import cascade .DAT files.

    Args:
        filepath (str): path to file to be converted
        format (str): which format to save / return the file in. Can be "binary" or "pickle"
        save (bool, optional): Whether to save the file locally. Defaults to True.
    """
    """Main function to import cascade .DAT files"""

    with open(filepath, "rb") as file:

        endian = "<"

        # First byte of the data is the file version
        file_version = file.read(1).decode()

        if file_version == "d":
            # TODO: Version D is a WIP.This needs to be tested.
            header = file.read(1023)

            # In the original code, it reads 17 + 7 bytes of datetime.
            datetime = header.pop(24).decode().rstrip("\x00")

            file.read(8)
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100

            span_T = struct.unpack(endian + "I", file.read(4))[0]
            span_X = struct.unpack(endian + "I", file.read(4))[0]
            span_Y = struct.unpack(endian + "I", file.read(4))[0]

            skip_bytes = 0

            metadata = ""

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
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100
            datetime = file.read(24).decode().rstrip("\x00")
            metadata = file.read(971).decode().rstrip("\x00")

            skip_bytes = 8

        bstream = file.read()

    # TODO Sort out chunking here and make it more elegant

    len_file = len(bstream)
    raw_image_data = list(struct.unpack("H" * (len_file // 2), bstream))

    skip = skip_bytes / 2  # Because each long integer is 2 bytes)
    imarray = []
    for t in range(span_T):

        position = int(t * (span_X * span_Y + skip))

        im_raw = raw_image_data[position : position + span_X * span_Y]

        imarray.append(im_raw)

    imarray = np.array(imarray)

    return np.array([im.reshape(span_X, span_Y) for im in imarray])
