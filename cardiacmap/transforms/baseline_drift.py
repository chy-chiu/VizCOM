import concurrent.futures as cf

import numpy as np
from scipy.signal import find_peaks


def RemoveBaselineDrift(data, mask, threads, params, peaks=False, update_progress=None):
    """Function to remove baseline drift from data
    Args:
        data (array): data to process
        mask (array): mask of pixels to ignore
        threads (int): the number of threads to use for removing baseline
        params (dict): find_peaks params
        peaks (bool): find peaks (and normalize) or valleys (and subtract)
    """
    yLen = len(data)
    xLen = len(data[0])
    tLen = len(data[0][0])
    t = np.arange(tLen)
    resData = [0 for j in range(xLen * yLen)]

    if update_progress:
        total = xLen * yLen

    if peaks:
        print("Normalize Amplitude")
        func = NormalizeAmplitude1D
    else:
        print("Remove Baseline")
        func = RemoveBaseline1D

    executor = cf.ThreadPoolExecutor(max_workers=threads)
    index = 0
    for y in range(yLen):
        for x in range(xLen):
            if mask[y, x] != 0:
                if update_progress:
                    update_progress(index / total)
                d = data[y][x]
                executor.submit(func, t, d, params, resData, index)
            else:
                resData[index] = data[y][x]
            index += 1

    executor.shutdown(wait=True)
    # reshape results array, then convert to int from float
    return np.array(resData).reshape(yLen, xLen, tLen)

def NormalizeAmplitude1D(t, data, params, output, outIdx):
    peaks = FindPeaks(t, data, params)
    if len(peaks) == 0:
        print("No Mins Found @ index", outIdx)
        # keep data
        output[outIdx] = data
        return None
    # interpolate baseline
    interp = np.interp(t, peaks, data[peaks])
    # normalize peaks
    res = data / interp
    # set any value > 1 to 1 
    # (flatten peaks that weren't caught to avoid error)
    res[res > 1] = 1
    # store result
    output[outIdx] = res
    

def RemoveBaseline1D(t, data, params, output, outIdx):
    """Function to remove baseline drift a signal
    Args:
        t (array): list of t values from 0 to len(data)
        d (array): data (one signal) to process
        output (array): the output array
        outputIndex (array): the index to store the resulting data within output
        minsX (array): the baseline x values for d
        minsY (array): the baseline y values for d
    """
    peaks = FindPeaks(t, -data, params)
    if len(peaks) == 0:
        print("No Mins Found @ index", outIdx)
        # keep data
        output[outIdx] = data
        return None
    # interpolate baseline
    interp = np.interp(t, peaks, data[peaks])
    # subtract interpolation from data
    res = np.subtract(data, interp)
    # set any negative values to 0
    # (flatten valleys that weren't caught to avoid error)
    res[res < 0] = 0
    # store result
    output[outIdx] = res


def FindPeaks(t, d, params):
    """
    Args:
        t (array): list of t values from 0 to len(data)
        d (array): data (one signal) to process
        xOut (array): the output for the baseline X values
        yOut (array): the output for the baseline Y values
        outIndex (int): where in the output arrays to store results
        params (dict): params for peak finding
            alternans (bool): use alternans
            distance (int): minimum distance between baseline points (75% of the period length)
            prominence (float): minimum peak prominance to be considered for the baseline
            threshold (float): maximal value to be considered for the baseline
    """
    # find peaks
    peakIdx = find_peaks(
        d, distance=params["distance"], prominence=params["prominence"]
    )[0]

    # check threshold
    if 0 < params["threshold"] < 1:
        # find indices where minima is > threshold
        peakY = d[peakIdx]
        invalidIdx = np.argwhere(peakY > params["threshold"])

        # if all mins are invalid
        if len(invalidIdx) == len(peakIdx):
            # ignore threshold
            print(
                "ERR: No minima found below threshold:",
                params["threshold"],
                ". Param Ignored.",
            )
        else:
            # otherwise, get rid of bad indicies
            peakIdx = np.delete(peakIdx, invalidIdx)

    # check alternans
    if params["alternans"]:
        xVals = t[peakIdx]
        first8Mins = xVals[0:8]
        beatLengths = np.diff(first8Mins)
        oddBeatAvg = np.mean(beatLengths[0:8:2])
        evenBeatAvg = np.mean(beatLengths[1:9:2])

        # get rid of odd/even beat mins (keep the longer beats)
        if evenBeatAvg < oddBeatAvg:
            peakIdx = peakIdx[::2]
        else:
            peakIdx = peakIdx[1::2]
    return t[peakIdx]


# def GetMins(t, data, mask, prominence, periodLen, threshold, alternans, threads):
#     """Function for calculating the baseline of the data for each xy pair
#     Args:
#         t (array): list of t values from 0 to len(data)
#         data (array): data to process
#         periodLen (int): baseline period length
#         threshold (float): baseline  max threshold
#         threads (int): the number of threads to use
#     """
#     # set up output
#     yLen = len(data)
#     xLen = len(data[0])
#     baselineX = [0 for j in range(yLen * xLen)]
#     baselineY = baselineX.copy()

#     # set up params
#     dst = periodLen
#     if dst < 1:
#         dst = 1
#     if prominence == 0:
#         prominence = 0.00001
#     params = dict(
#         {
#             "alternans": alternans,
#             "threshold": threshold,
#             "distance": dst,
#             "prominence": prominence,
#         }
#     )

#     # run a thread for each signal
#     executor = cf.ThreadPoolExecutor(max_workers=threads)
#     for y in range(yLen):
#         for x in range(xLen):
#             index = y * yLen + x
#             if mask[y][x] != 0:
#                 d = data[y][x]
#                 executor.submit(getMinsThread, t, d, baselineX, baselineY, index, params)
#             else:
#                 baselineX[index] = np.array([np.argmin(data[y][x])])
#                 baselineY[index] = np.array([np.min(data[y][x])])
#     executor.shutdown(wait=True)

#     return baselineX, baselineY


# def getMinsThread(t, d, xOut, yOut, outIndex, params):
#     """Function called by GetMins for a single signal
#     Args:
#         t (array): list of t values from 0 to len(data)
#         d (array): data (one signal) to process
#         xOut (array): the output for the baseline X values
#         yOut (array): the output for the baseline Y values
#         outIndex (int): where in the output arrays to store results
#         params (dict): params for peak finding
#             alternans (bool): use alternans
#             distance (int): minimum distance between baseline points (75% of the period length)
#             prominence (float): minimum peak prominance to be considered for the baseline
#             threshold (float): maximal value to be considered for the baseline
#     """
#     # find peaks
#     minsIndex = find_peaks(
#         -d, distance=params["distance"], prominence=params["prominence"]
#     )[0]

#     # check threshold
#     if 0 < params["threshold"] < 1:
#         # find indices where minima is > threshold
#         minsY = d[minsIndex]
#         badMinsIndex = np.argwhere(minsY > params["threshold"])

#         # if all mins are invalid
#         if len(badMinsIndex) == len(minsIndex):
#             # ignore threshold
#             print(
#                 "ERR: No minima found below threshold:",
#                 params["threshold"],
#                 ". Param Ignored.",
#             )
#         else:
#             # otherwise, get rid of bad indicies
#             minsIndex = np.delete(minsIndex, badMinsIndex)

#     # check alternans
#     if params["alternans"]:
#         xVals = t[minsIndex]
#         first8Mins = xVals[0:8]
#         beatLengths = np.diff(first8Mins)
#         oddBeatAvg = np.mean(beatLengths[0:8:2])
#         evenBeatAvg = np.mean(beatLengths[1:9:2])

#         # get rid of odd/even beat mins (keep the longer beats)
#         if evenBeatAvg < oddBeatAvg:
#             minsIndex = minsIndex[::2]
#         else:
#             minsIndex = minsIndex[1::2]

#     # set output
#     xOut[outIndex] = t[minsIndex]
#     yOut[outIndex] = d[minsIndex]

