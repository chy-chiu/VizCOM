from copy import deepcopy
from typing import Dict, List, Literal, Tuple

import numpy as np

from cardiacmap.transforms import (
    FFT,
    InvertSignal,
    NormalizeData,
    RemoveBaselineDrift,
    SpatialAverage,
    Stacking,
    TimeAverage,
    TrimSignal,
)


class CardiacSignal:
    """Class for voltage / calcium signal data from cardiac optical mapping. The data
    source could be from `cascade` or `scimedia`. . The original data
    is stored in base_data, and any additional transformations is done on
    transformed_data. Transformations are all done by calling the external
    transforms.py library, which provides methods to calculate various
    transforms. Additionally, empty variables are saved for baseline calculation,
    apd / di variables.
    """

    span_T: int
    span_X: int
    span_Y: int
    base_data: np.ndarray
    transformed_data: np.ndarray
    position: np.ndarray
    mask: np.ndarray
    spatial_apds = []

    def __init__(
        self,
        signal: np.ndarray,
        metadata: Dict[str, str],
        channel: Literal["Single", "Odd", "Even"],
        source: Literal["cascade", "scimedia"] = "cascade",
    ):

        self.metadata = metadata
        self.channel = channel
        self.signal_name = (
            metadata.get("filename", "").split(".")[0]
            if channel == "Single"
            else metadata.get("filename", "").split(".")[0] + "_" + channel
        )

        # This is transposed to account go y-x instead of x-y
        signal = signal.transpose(0, 2, 1)

        # This is the single source of truth that will be referred to again
        self.base_data = deepcopy(signal).astype(np.float32)

        # Variable to hold the data signal for transformations. We use np.float32 to conserve memory
        self.transformed_data = deepcopy(signal).astype(np.float32)

        # Extra copy to save the previous transform in case user wants to undo an action
        self.previous_transform = deepcopy(signal).astype(np.float32)

        # This is the base image data
        self.image_data = (signal - signal.min()) / signal.max()

        # This is the length of the data
        self.span_T = len(signal)
        self.span_Y = len(signal[0])
        self.span_X = len(signal[0][0])

        self.trimmed = [0, 0]

        # Inverted Flag, used when accessing base_data
        self.inverted = False

        ## Baseline drift variables
        self.baselineX = []
        self.baselineY = []
        self.show_baseline = False

        ## APD / DI variables
        self.apdThreshold = 0
        self.apdDIThresholdIdxs = []  # TODO: Can this be cleared after confirmation?
        self.apdIndicators = []
        self.apds = []
        self.apd_indices = []
        self.dis = []
        self.di_indices = []
        self.show_apd_threshold = False
        self.spatial_apds = []

        # Mask to isolate relevant bits of the signal only
        self.mask = np.ones((self.span_Y, self.span_X))

    def perform_average(
        self,
        type: Literal["time", "spatial"],
        sig,
        rad,
        mode: Literal["Gaussian", "Uniform"] = "Gaussian",
        update_progress=None,
        start=None,
        end=None,
    ):
        start = start or 0
        end = end or len(self.transformed_data) - 1

        if update_progress:
            update_progress(0.2)

        self.previous_transform = deepcopy(self.transformed_data)

        if type == "time":
            self.transformed_data[start:end] = TimeAverage(
                self.transformed_data[start:end], sig, rad, self.mask, mode
            )
        elif type == "spatial":
            self.transformed_data[start:end] = SpatialAverage(
                self.transformed_data[start:end], sig, rad, self.mask, mode
            )

    def invert_data(self):
        self.transformed_data = InvertSignal(self.transformed_data)
        self.inverted = not self.inverted

    def trim_data(self, startTrim, endTrim):
        self.trimmed = [self.trimmed[0] + startTrim, self.trimmed[1] + endTrim]
        self.previous_transform = deepcopy(self.transformed_data)
        self.transformed_data = self.transformed_data[startTrim:-endTrim, :, :]

    def reset_data(self):
        self.transformed_data = deepcopy(self.base_data)

    def undo(self):
        self.transformed_data = self.previous_transform

    def reset_image(self):
        self.image_data = (self.base_data - self.base_data.min()) / self.base_data.max()

    def normalize(self, start=None, end=None):
        start = start or 0
        end = end or len(self.transformed_data)
        n = NormalizeData(self.transformed_data[start:end, :, :])
        self.transformed_data[start:end, :, :] = n

    ############## Baseline drift related methods
    # def calc_baseline(
    #     self,
    #     periodLen,
    #     threshold,
    #     prominence,
    #     alternans,
    #     start=None,
    #     end=None,
    # ):
    #     start = start or 0
    #     end = end or len(self.transformed_data) - 1

    #     print("Calculating baseline:", periodLen, threshold, prominence, alternans)
    #     data = self.transformed_data[start:end]
    #     mask = self.mask
    #     t = np.arange(len(data))
    #     threads = 4

    #     # flip data axes so we can look at it signal-wise instead of frame-wise
    #     dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t
    #     self.baselineX, self.baselineY = GetMins(
    #         t, dataSwapped, mask, prominence, periodLen, threshold, alternans, threads
    #     )

    def remove_baseline(
        self, params, peaks=False , start=None, end=None, update_progress=None
    ):
        start = start or 0
        end = end or len(self.transformed_data) - 1

        mask = self.mask
        self.previous_transform = deepcopy(self.transformed_data)
        data = self.transformed_data[start:end]
        mask = self.mask
        threads = 4


        # flip data axes so we can look at it signal-wise instead of frame-wise
        dataSwapped = np.moveaxis(data, 0, -1)  # y, x, t

        results = RemoveBaselineDrift(
            dataSwapped,
            mask,
            threads,
            params, 
            peaks,
            update_progress=update_progress,
        )

        # flip data axes back and store results
        data = np.moveaxis(results, -1, 0)
        self.transformed_data[start:end] = data

    def get_baseline(self):
        return self.baselineX, self.baselineY

    def reset_baseline(self):
        self.baselineX = self.baselineY = []

    ############### APD / DI related methods
    # def calc_apd_di_threshold(self, threshold):
    #     data = np.moveaxis(self.transformed_data, 0, -1)
    #     self.apdDIThresholdIdxs, self.apdIndicators = GetIntersectionsAPD_DI(
    #         data, threshold, self.mask
    #     )
    #     self.apdThreshold = threshold

    # def calc_apd_di(self):
    #     self.apds, self.apd_indices, self.dis, self.di_indices = CalculateAPD_DI(
    #         self.apdDIThresholdIdxs, self.apdIndicators
    #     )

    def reset_apd_di(self):
        self.apdDIThresholdIdxs = self.apdIndicators = []
        self.apds = self.apd_indices = self.dis = self.di_indices = []
        self.apdThreshold = 0

    def get_apd_threshold(self):
        return self.apdDIThresholdIdxs, self.apdThreshold

    def get_apds(self):
        return self.apds, self.apd_indices

    def get_spatial_apds(self):
        most_beats = len(max(self.apds, key=len))
        spatialAPDs = pad(self.apds, most_beats)
        spatialAPDs = spatialAPDs.reshape((self.span_Y, self.span_X, most_beats))
        return np.moveaxis(spatialAPDs, -1, 0)

    def get_dis(self):
        return self.dis, self.di_indices

    def get_spatial_dis(self):
        most_beats = len(max(self.dis, key=len))
        spatialDIs = pad(self.dis, most_beats)
        spatialDIs = spatialDIs.reshape((self.span_Y, self.span_X, most_beats))
        return np.moveaxis(spatialDIs, -1, 0)

    def reset_apd_di(self):
        self.apdDIThresholdIdxs = self.apdIndicators = []
        self.apds = self.apd_indices = []
        self.dis = self.di_indices = []
        self.apdThreshold = 0

    def get_keyframe(self):
        # Take the middle as the key frame for now
        key_frame_idx = self.span_T // 2

        key_frame = self.base_data[key_frame_idx]

        if self.mask is not None:

            key_frame = key_frame * self.mask

        return key_frame

    def apply_mask(self, mask_arr):
        self.mask = mask_arr
        print("Mask Applied")
        # print(self.transformed_data.shape)
        # print(self.image_data.shape)
        # self.transformed_data = self.transformed_data * np.expand_dims(self.mask, 0)
        # self.image_data = self.image_data * self.mask

    def get_curr_signal(self):
        return self.transformed_data

    def perform_stacking(
        self,
        startingFrame,
        endingFrame,
        numPeriods,
        distance,
        offset,
        alternans=False,
        mask=None,
        update_progress=None,
    ):
        # prep data
        if self.inverted:
            data = -self.base_data
        else:
            data = self.base_data
        derivative = np.gradient(self.transformed_data, axis=0)

        # plt.plot(derivative[:, 64, 64])
        # plt.show()
        # trim data
        if endingFrame > len(derivative) or endingFrame <= startingFrame:
            endingFrame = len(derivative)

        data = data[
            startingFrame
            + self.trimmed[0] : startingFrame
            + self.trimmed[0]
            + endingFrame
        ]
        derivative = derivative[startingFrame : startingFrame + endingFrame]

        # perform stacking
        results, longestRes = Stacking(
            data,
            derivative,
            numPeriods,
            distance,
            offset,
            alternans,
            mask,
            update_progress,
        )

        # reshape for display
        results = pad(results, longestRes)
        results = results.reshape((self.span_Y, self.span_X, longestRes))
        results = np.moveaxis(results, -1, 0)
        return NormalizeData(results)

    def perform_fft(self, start, end):
        return FFT(self.transformed_data[start:end])


# helper function to pad an array with zeros until it is rectangular
def pad(array, targetWidth):
    for i in range(len(array)):
        numZeros = targetWidth - len(array[i])
        zeros = np.zeros(numZeros)
        array[i] = np.concatenate((array[i], zeros))
    return np.asarray(array)
