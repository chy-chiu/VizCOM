from copy import deepcopy
from typing import Dict, List, Tuple, Literal
from scipy.signal import find_peaks

import cv2
import numpy as np
import itertools as it

from cardiacmap.transforms import (
    CalculateAPD_DI,
    GetIntersectionsAPD_DI,
    GetMins,
    InvertSignal,
    NormalizeData,
    RemoveBaselineDrift,
    SpatialAverage,
    TimeAverage,
    TrimSignal,
)


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

    def __init__(
        self,
        signal: np.ndarray,
        metadata: Dict[str, str],
        channel: Literal["Single", "Odd", "Even"],
    ):

        self.metadata = metadata
        self.channel = channel

        signal = signal.transpose(0, 2, 1)

        # This is the single source of truth that will be referred to again
        self.base_data = deepcopy(signal)

        # Variable to hold the data signal for transformations
        self.transformed_data = deepcopy(signal)

        # This is the base image data
        self.image_data = (signal - signal.min()) / signal.max()

        # This is the length of the data
        self.span_T = len(signal)
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
        self.mask = []
        self.mask_arr = None

    def perform_average(
        self,
        type: Literal["time", "spatial"],
        sig,
        rad,
        mode: Literal["Gaussian", "Uniform"]="Gaussian",
    ):
        if type == "time":
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
        self.inverted = not self.inverted

    def trim_data(self, startTrim, endTrim):
        self.trimmed = [self.trimmed[0] + startTrim, self.trimmed[1] + endTrim]
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
    
    def get_spatial_apds(self):
        most_beats = len(max(self.apds, key=len))
        spatialAPDs = self.pad(self.apds, most_beats)
        spatialAPDs = spatialAPDs.reshape((self.span_Y, self.span_X, most_beats))
        return np.moveaxis(spatialAPDs, -1, 0)

    def get_dis(self):
        return self.dis, self.di_indices
    
    def get_spatial_dis(self):
        most_beats = len(max(self.dis, key=len))
        spatialDIs = self.pad(self.dis, most_beats)
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

        if self.mask_arr is not None:

            key_frame = key_frame * self.mask_arr

        return key_frame

    def apply_mask(self, mask_arr):
        self.mask_arr = mask_arr
        print(mask_arr.shape)
        print(self.transformed_data.shape)
        print(self.image_data.shape)
        self.transformed_data = self.transformed_data * np.expand_dims(self.mask_arr, 0)
        self.image_data = self.image_data * self.mask_arr

    def get_curr_signal(self):
        return self.transformed_data
    
    # helper function to pad an array with zeros until it is rectangular
    def pad(self, array, targetWidth):
        for i in range(len(array)):
            numZeros = targetWidth - len(array[i])
            zeros = np.zeros(numZeros)
            array[i] = np.concatenate((array[i], zeros))
        return np.asarray(array)
    
    def performStacking(self, endingFrame, numPeriods, startingFrame):
        if self.inverted:
            data = -self.base_data
        else:
            data = self.base_data
        derivative = np.gradient(self.transformed_data, axis = 0)
        
        # trim data
        if endingFrame > len(derivative) or endingFrame <= startingFrame:
            endingFrame = len(derivative)

        data = data[startingFrame + self.trimmed[0]:startingFrame + self.trimmed[0] + endingFrame]
        derivative = derivative[startingFrame:startingFrame + endingFrame]
        
        #frequency map
        freqs = np.fft.rfftfreq(len(data))
        
        # speeds computation
        derivative = np.moveaxis(derivative, 0, -1)
        data = np.moveaxis(data, 0, -1)

        minima = [[[] for j in range(len(data[0]))] for i in range(len(data))]
        results = [[] for j in range(len(data[0]) * len(data))]
        longestRes = 0
        # stack each pixel
        for y in range (len(data)):
            for x in range(len(data[0])):
                d = data[y][x]
                #print(len(d))
                dYdX = derivative[y][x]
                result, minIdx = self.stack(d, dYdX, freqs, numPeriods)
                
                if len(result) > longestRes:
                    longestRes = len(result)
                # display progress
                if ((y * 128 + x )% 1000 == 0):
                    print("Stacking:", int(100 * (y * 128 + x)/(128*128)), "%")
                results[y * self.span_Y + x] = result
        
        results = self.pad(results, longestRes)
        results = results.reshape((128, 128, longestRes))
        results = np.moveaxis(results, -1, 0)
        return NormalizeData(results)
    
    def stack(self, data, derivative, freqs, n):
        #FFT for period length
        fft = np.abs(np.fft.rfft(data))
        fft[0:5:]=0
        periodLen = 1/freqs[np.argmax(fft)]
        
        # Find derivative peaks and offset
        peaks = find_peaks(derivative, distance = int(periodLen * .8))[0]
        peaks -= int(periodLen * .1)
        while len(peaks) > 0 and peaks[0] <= 0:
            peaks = peaks[1:]

        peaks = peaks[0:n+1]
        # slice data
        data = NormalizeData(data)
        slices = np.split(data, peaks)
        
        if len(slices) < 3:
            return [0], [0]
        
        slices.pop(0)
        slices.pop()
    
        #print(len(slices))
        # average all the slices (pad with 0s)
        stacked = [0] + list(map(paddedAvg, it.zip_longest(*slices)))
 
        return stacked,  peaks
    
def paddedAvg(x):
    x = [0 if i is None else i for i in x]
    return sum(x, 0) / len(x)
