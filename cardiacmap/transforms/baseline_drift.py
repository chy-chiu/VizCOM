import concurrent.futures as cf

import numpy as np
from scipy.signal import find_peaks


def RemoveBaselineDrift(t, data, baselineXs, baselineYs, threads, update_progress=None):
    """Function to remove baseline drift from data
    Args:
        t (array): list of t values from 0 to len(data)
        data (array): data to process
        baselineXs (array): 2-d arr of the baseline X values for every signal
        baselineYs (array): 2-d arr of the the baseline Y values for every signal
        threads (int): the number of threads to use for removing baseline
    """
    yLen = len(data)
    xLen = len(data[0])
    tLen = len(data[0][0])
    resData = [0 for j in range(xLen * yLen)]

    if update_progress:
        total = xLen * yLen
        print(total)

    executor = cf.ThreadPoolExecutor(max_workers=threads)
    for y in range(yLen):
        for x in range(xLen):
            index = y * yLen + x

            if update_progress:
                update_progress(index / total)

            d = data[y][x]
            xs = baselineXs[index]
            ys = baselineYs[index]
            executor.submit(baselineDriftThread, t, d, resData, index, xs, ys)

    executor.shutdown(wait=True)
    # reshape results array, then convert to int from float
    return np.array(resData).reshape(yLen, xLen, tLen)


def baselineDriftThread(t, d, output, outputIndex, minsX, minsY):
    """Function to remove baseline drift a signal
    Args:
        t (array): list of t values from 0 to len(data)
        d (array): data (one signal) to process
        output (array): the output array
        outputIndex (array): the index to store the resulting data within output
        minsX (array): the baseline x values for d
        minsY (array): the baseline y values for d
    """
    if len(minsX) == 0 or len(minsY) == 0:
        print("No Mins Found @ index", outputIndex)
        # keep data
        output[outputIndex] = d
        return 1
    
    # interpolate baseline
    interp = np.interp(t, minsX, minsY)

    # subtract interpolation from data
    res = np.subtract(d, interp)

    # set any negative values to 0
    res[res < 0] = 0

    # store result
    output[outputIndex] = res
    return 0


def GetMins(t, data, prominence, periodLen, threshold, alternans, threads):
    """Function for calculating the baseline of the data for each xy pair
    Args:
        t (array): list of t values from 0 to len(data)
        data (array): data to process
        periodLen (int): baseline period length
        threshold (float): baseline  max threshold
        threads (int): the number of threads to use
    """
    # set up output
    yLen = len(data)
    xLen = len(data[0])
    baselineX = [0 for j in range(yLen * xLen)]
    baselineY = baselineX.copy()

    # set up params
    dst = 0.75 * periodLen
    if dst < 1:
        dst = 1
    if prominence == 0:
        prominence = 0.1
    params = dict(
        {
            "alternans": alternans,
            "threshold": threshold,
            "distance": dst,
            "prominence": prominence,
        }
    )

    # run a thread for each signal
    executor = cf.ThreadPoolExecutor(max_workers=threads)
    for y in range(yLen):
        for x in range(xLen):
            index = y * yLen + x
            d = data[y][x]
            executor.submit(getMinsThread, t, d, baselineX, baselineY, index, params)
    executor.shutdown(wait=True)

    return baselineX, baselineY


def getMinsThread(t, d, xOut, yOut, outIndex, params):
    """Function called by GetMins for a single signal
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
    minsIndex = find_peaks(
        -d, distance=params["distance"], prominence=params["prominence"]
    )[0]

    # check threshold
    if 0 < params["threshold"] < 1:
        # find indices where minima is > threshold
        minsY = d[minsIndex]
        badMinsIndex = np.argwhere(minsY > params["threshold"])

        # if all mins are invalid
        if len(badMinsIndex) == len(minsIndex):
            # ignore threshold
            print(
                "ERR: No minima found below threshold:",
                params["threshold"],
                ". Param Ignored.",
            )
        else:
            # otherwise, get rid of bad indicies
            minsIndex = np.delete(minsIndex, badMinsIndex)

    # check alternans
    if params["alternans"]:
        xVals = t[minsIndex]
        first8Mins = xVals[0:8]
        beatLengths = np.diff(first8Mins)
        oddBeatAvg = np.mean(beatLengths[0:8:2])
        evenBeatAvg = np.mean(beatLengths[1:9:2])

        # get rid of odd/even beat mins (keep the longer beats)
        if evenBeatAvg < oddBeatAvg:
            minsIndex = minsIndex[::2]
        else:
            minsIndex = minsIndex[1::2]

    # set output
    xOut[outIndex] = t[minsIndex]
    yOut[outIndex] = d[minsIndex]
