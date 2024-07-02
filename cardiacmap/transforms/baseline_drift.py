import concurrent.futures as cf
from types import NoneType

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.signal import find_peaks


def RemoveBaselineDrift(t, data, baselineXs, baselineYs, threads):
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

    executor = cf.ThreadPoolExecutor(max_workers=threads)
    for y in range(yLen):
        for x in range(xLen):
            index = y * yLen + x
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
    # interpolate baseline
    interp = np.interp(t, minsX, minsY)
    # subtract interpolation from data
    res = np.subtract(d, interp)
    # store result
    output[outputIndex] = res
    # return success
    return 0
