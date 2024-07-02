import concurrent.futures as cf
from types import NoneType

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.signal import find_peaks


def GetIntersectionsAPD_DI(data, threshold):
    """Function to Find intersections between threshold and data
    Args:
        data (array): input data
        threshold (int): threshold value
    """
    yLen = len(data)
    xLen = len(data[0])

    # get crossing indices
    idx = np.argwhere(np.diff(np.sign(data - threshold))) # this line is by far the most time consuming
    # TODO: Is there a better way?

    ys = idx[:, 0]
    xs = idx[:, 1]

    validSigs = ys * xLen + xs
    idx0 = idx[:, 2]  # index before
    # split the index values by signal
    split_idx = np.argwhere(np.diff(validSigs) != 0).flatten() + 1
    splits0 = np.split(idx0, split_idx)
    numInvalidSignals = 0  # splits offset

    # get unique signals from "valid" list
    # must do this AFTER splitting
    validSigs = np.unique(validSigs)
    outArr = []
    apdsArr = []
    indices = np.arange(xLen * yLen)
    for index in indices:
        x = int(index % yLen)
        y = int(index / yLen)
        # check if this signal is valid
        if index in validSigs:
            t0Idx = splits0[index - numInvalidSignals]
            t1Idx = t0Idx + 1
            # print(y, x)
            # get t values for apds/dis
            getIndicesAPD_DI(
                threshold, t0Idx, data[y][x][t0Idx], data[y][x][t1Idx], outArr, apdsArr
            )
        else:
            numInvalidSignals += 1

    return outArr, apdsArr


def getIndicesAPD_DI(threshold, x0s, y0s, y1s, resArr, apdArr):
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
    if slopes[0] > 0:
        apdFirst = True
    elif slopes[0] < 0:
        apdFirst = False
    else:
        return -1
    intercepts = y0s - (slopes * x0s)
    indices = (threshold - intercepts) / slopes
    resArr.append(indices)
    apdArr.append(apdFirst)
    return 0


def CalculateAPD_DI(intersections, firstIntervalFlag):
    """Function to measure the intervals between intersections and store interval time as apd/di
    Args:
        intersections (array): intersections found by GetIntersectionsAPD_DI()
        firstIntervalFlag (array): bool array indicating whether first interval of a signal is apd/di
    """
    apdArr = [[] for s in range(len(intersections))]
    apdIdxArr = [[] for s in range(len(intersections))]
    diArr = [[] for s in range(len(intersections))]
    diIdxArr = [[] for s in range(len(intersections))]
    for sig in range(len(intersections)):
        # get this signals intersections
        signalIndices = intersections[sig]
        # check if the first interval is an apd or di
        apdEvens = firstIntervalFlag[sig]
        for i in range(1, len(signalIndices)):
            index0 = signalIndices[i - 1]
            index1 = signalIndices[i]
            duration = index1 - index0

            # append duration and starting index of interval to appropriate array
            if i % 2 == 0:
                if apdEvens:
                    apdArr[sig].append(duration)
                    apdIdxArr[sig].append(index0)
                else:
                    diArr[sig].append(duration)
                    diIdxArr[sig].append(index0)
            else:
                if apdEvens:
                    diArr[sig].append(duration)
                    diIdxArr[sig].append(index0)
                else:
                    apdArr[sig].append(duration)
                    apdIdxArr[sig].append(index0)
    return apdArr, apdIdxArr, diArr, diIdxArr
