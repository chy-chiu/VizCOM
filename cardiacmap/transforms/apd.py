import concurrent.futures as cf
from types import NoneType

import numpy as np


def GetThresholdIntersections(data, threshold, spacing, intervals=None, mask = None):
    """Function to Find intersections between threshold and data
    Args:
        data (np.ndarray): input data
        threshold (int): threshold value
        spacing (float): minimum x-distance between two intersections
        intervals (array): array of index values to slice 'data'
    """
    print("Minimum Spacing is:", spacing)
    apdArrs = []
    diArrs = []
    
    if intervals is None:
        slices = [data]
    else:
        slices = []
        for i in range(1, len(intervals)):
            start = intervals[i-1]
            end = intervals[i]-1
            slices.append(data[start:end])
    
    for data_slice in slices:
        print(data_slice.shape)
        flat_swapped_arr = np.swapaxes(data_slice.reshape(data_slice.shape[0], -1), 0, 1)
        pixels =  np.arange(flat_swapped_arr.shape[0])
        intersections = []
        apdFlags = []
        print(flat_swapped_arr.shape)
        for p in pixels:
            ints, apd = GetThresholdIntersections1D(flat_swapped_arr[p], threshold, spacing)
            intersections.append(ints)
            apdFlags.append(apd)
        apdArr, diArr = CalculateIntervals(intersections, apdFlags)
        apdArr = np.swapaxes(apdArr, 1, 0).reshape(apdArr.shape[1], data_slice.shape[1], data_slice.shape[2])
        diArr = np.swapaxes(diArr, 1, 0).reshape((diArr.shape[1], data_slice.shape[1], data_slice.shape[2]))
        
        apdArrs.append(apdArr)
        diArrs.append(diArr)
        print(apdArr.shape, diArr.shape)

    return apdArrs, diArrs

def GetThresholdIntersections1D(data, threshold, spacing = 0):
    # get all indices where the data crosses the threshold
    idx0 = np.argwhere( np.diff( np.sign( data - threshold )))[:, 0] # idx before crossing
    idx1 = idx0 + 1 # idx after

    y0 = data[idx0]
    y1 = data[idx1]
    ts, apdFlags = getTimes(threshold, idx0, y0, y1)
    
    # filter out intersections that are less than spacing
    validIdx = np.argwhere(np.diff(ts) >= spacing).flatten()
    
    # np.diff wont return the final index
    # add it back to the valid list
    validIdx = np.append(validIdx, -1)
    
    return ts[validIdx], apdFlags


def getTimes(threshold, x0s, y0s, y1s):
    """Helper function to calculate the exact t values of intersection for a signal
    Args:
        threshold (int): threshold value
        x0s (array): t values BEFORE crossing threshold
        y0s (array): data values BEFORE crossing threshold
        y1s (array): data values AFTER crossing threshold
        resArr (array): indices of crossings
        apdArr (array): apd/di indicator
    """
    slopes = np.subtract(y1s, y0s)
    
    # no intersections found
    if len(slopes) == 0:
        return np.array([0, 1]), False
    
    if slopes[0] > 0:
        apdFirst = True
    elif slopes[0] < 0:
        apdFirst = False
    else:
        return -1
    
    intercepts = y0s - (slopes * x0s)
    ts = (threshold - intercepts) / slopes
    return ts, apdFirst


def CalculateIntervals(intersections, firstIntervalFlag):
    """Function to measure the intervals between intersections and store interval time as apd/di
    Args:
        intersections (array): intersections found by GetThresholdIntersections()
        firstIntervalFlag (array): bool array indicating whether first interval of a signal is apd/di
    """
    apdArr = []
    diArr = []
    longestAPD = 0
    longestDI = 0
    for sig in np.arange(len(intersections)):
        # get this signals intersections
        sigInters = np.array(intersections[sig])
        intervals = np.diff(sigInters)
        # check if the first interval is an apd or di
        apdFirst = firstIntervalFlag[sig]
        
        if apdFirst:
            apds = intervals[::2]
            dis = intervals[1::2] 
        else:
            dis = intervals[::2]
            apds = intervals[1::2]
            
        if len(apds) > longestAPD:
            longestAPD = len(apds)
            
        if len(dis) > longestDI:
            longestDI = len(dis)
            
        apdArr.append(apds)
        diArr.append(dis)

    apdArr = pad(apdArr, longestAPD)
    diArr = pad(diArr, longestDI)
    return apdArr, diArr


# helper function to pad an array with zeros until it is rectangular
def pad(array, targetWidth):
    for i in range(len(array)):
        numZeros = targetWidth - len(array[i])
        zeros = np.zeros(numZeros)
        array[i] = np.concatenate((array[i], zeros))
    return np.asarray(array)
