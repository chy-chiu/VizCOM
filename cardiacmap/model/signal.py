import argparse
import io
import os
import pickle
import struct
import sys
from copy import deepcopy
from locale import normalize
from typing import Dict, List, Tuple

import cv2
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
    position: np.ndarray
    mask: List[Tuple[int, int]]
    mask_arr: np.ndarray
    spatial_apds = []

    def __init__(self, signal: np.ndarray) -> None:
        self.base_data = deepcopy(signal)
        self.transformed_data = deepcopy(signal)
        self.image_data = (signal - signal.min()) / signal.max()
        self.span_T = len(signal)

        ## Baseline drift variables
        self.baselineX = []
        self.baselineY = []
        self.show_baseline = False

        ## APD / DI variables
        self.apdThreshold = 0
        self.apdDIThresholdIdxs = []    # TODO: Can this be cleared after confirmation?
        self.apdIndicators = []
        self.apds = []
        self.apd_indices = []
        self.dis = []
        self.di_indices = []
        self.mask = []
        self.mask_arr = None
        self.show_apd_threshold = False
        self.spatial_apds = []

    def perform_average(
        self,
        type,
        sig,
        rad,
        mode="Gaussian",
    ):
        if type == "time":
            print(self.transformed_data.shape)
            self.transformed_data = TimeAverage(
                self.transformed_data, sig, rad, self.mask_arr, mode
            )

        elif type == "spatial":
            self.transformed_data = SpatialAverage(
                self.transformed_data, sig, rad, self.mask_arr, mode
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

    def reset_image(self):
        self.image_data = (self.base_data - self.base_data.min()) / self.base_data.max()

    def normalize(self):
        self.transformed_data = NormalizeData(self.transformed_data)

    def calc_baseline(self, method, methodValue, alternans):
        print("Calculating baseline", method, methodValue, alternans)
        data = self.transformed_data
        t = np.arange(len(data))
        threads = (
            8  # this seems to be optimal thread count, needs more testing to confirm
        )

        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t
        self.baselineX, self.baselineY = GetMins(
            t, dataSwapped, method, methodValue, threads, alternans
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

        key_frame = self.base_data[key_frame_idx]

        if self.mask_arr is not None:

            key_frame = key_frame * self.mask_arr

        return key_frame
    
    def apply_mask(self, mask_arr):
        self.mask_arr = mask_arr
        self.transformed_data = self.transformed_data * self.mask_arr
        self.image_data = self.image_data * self.mask_arr

    def get_curr_signal(self):
        return self.transformed_data

