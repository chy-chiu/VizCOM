import concurrent.futures as cf
from types import NoneType

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.signal import find_peaks


def InvertSignal(arr):
    """Function to invert array values
    Args:
        arr (array): data
    Returns:
        newArr: -data
    """

    newArr = np.multiply(arr, -1)
    return newArr


def TrimSignal(arr, trimStart, trimEnd):
    """Function to trim array
    Args:
        arr (array): data
        trimStart: int, number of frames to delete from start
        trimEnd: int, number of frames to delete from end
    Returns:
        newArr: results, size = arrLength - trimStart - trimEnd
    """
    arrLen = len(arr)

    start = np.arange(trimStart)
    end = np.arange(arrLen - trimEnd - 1, arrLen)
    trimIndices = np.concatenate((start, end))
    newArr = np.delete(arr, trimIndices, axis=0)
    return newArr


def useUniform(arr, sig, radius=1, axes=-1):
    """Function to convert gaussian_filter inputs for a uniform_filter
       Doing it this way avoids 4 if statements in Spatial/TimeAverage()
    Args:
        arr (array): data
        sig (int): gaussian_filter takes this input, uniform does not, THIS PARAM IS IGNORED IN THIS FUNCTION
        radius(int): radius of averaging, kernel width = 2*radius+1
        axes (int, tuple): axes of averaging
    """
    return uniform_filter(arr, size=2 * radius + 1, axes=axes)


def GetMins(t, data, method, methodValue, threads, alternans):
    """Function for calculating the baseline of the data for each xy pair
    Args:
        t (array): list of t values from 0 to len(data)
        data (array): data to process
        method (string): the method (threshold or period) to use to get mins
        methodValue (int): threshold value OR period width, depending on method
        threads (int): the number of threads to use for threshold method (ignored if method = 'period')
    """
    yLen = len(data)
    xLen = len(data[0])
    tLen = len(data[0][0])

    baselineX = [0 for j in range(yLen * xLen)]
    baselineY = baselineX.copy()

    if method == "Threshold":
        executor = cf.ThreadPoolExecutor(max_workers=threads)
        for y in range(yLen):
            for x in range(xLen):
                index = y * yLen + x
                d = data[y][x]
                executor.submit(
                    getMinsByThresholdThread,
                    methodValue,
                    t,
                    d,
                    baselineX,
                    baselineY,
                    index,
                )
        executor.shutdown(wait=True)

    elif method == "Period":
        if tLen % methodValue == 0:
            offset = [methodValue * i for i in range(int(tLen / methodValue))]
        else:
            offset = [
                methodValue * i for i in range(int(tLen / methodValue) + 1)
            ]  # numpy doesnt support jagged arrs, must do the last segment seperately
        pIdx = np.arange(methodValue, tLen, methodValue)
        for y in range(yLen):
            for x in range(xLen):
                index = y * yLen + x
                d = data[y][x]
                getMinsByPeriod(
                    t, d, baselineX, baselineY, index, offset, pIdx, alternans
                )

    else:
        raise ValueError("getMins method must be Threshold or Period. Was:", method)

    # baselineX = np.array(baselineX)
    # baselineY = np.array(baselineY)

    return baselineX, baselineY


def getMinsByThresholdThread(threshold, t, d, xOut, yOut, outIndex):
    """Function called by getMins when method = 'threshold'
    Args:
        threshold (int): the threshold to make mins invalid
        t (array): list of t values from 0 to len(data)
        d (array): data (one signal) to process
        xOut (array): the output for the baseline X values
        yOut (array): the output for the baseline Y values
        outIndex (int): where in the output arrays to store results
    """
    # find negative peaks (mins), only detect with index distance >=50
    minsIndex = find_peaks(-d, distance=50)[0]
    minsY = d[minsIndex]
    # find indices where minima is > threshold
    badMinsIndex = np.argwhere(minsY > threshold)

    # all mins are invalid
    # use beginning and end of signal as baseline
    if len(badMinsIndex) == len(minsIndex):
        minsIndex = [0, len(d) - 1]
        # set output
        xOut[outIndex] = t[minsIndex]
        yOut[outIndex] = d[minsIndex]

        # return warning
        return 1
    # get rid of bad indicies
    minsIndex = np.delete(minsIndex, badMinsIndex)

    # set output
    xOut[outIndex] = t[minsIndex]
    yOut[outIndex] = d[minsIndex]

    # return success
    return 0


def getMinsByPeriod(t, d, xOut, yOut, outIndex, offset, periodIdx, alternans):
    """Function called by getMins when method = 'period'
    Args:
        t (array): list of t values from 0 to len(data)
        d (array): data (one signal) to process
        xOut (array): the output for the baseline X values
        yOut (array): the output for the baseline Y values
        outIndex (int): where in the output arrays to store results
        offset (array): the offset to be applied when converting periodic indicies to signal indicies
        periodIdx (array): indices where split should occur
    """
    # split data into periods
    periods = np.array_split(d, periodIdx)

    # last period is usually not a full period
    # pop it so periods has homogenous shape
    lastPeriod = periods.pop(-1)

    # get argmin of each period and add it to the index list
    # note: if a period has multiple mins, argmin returns the first found index
    minsIndex = np.argmin(periods, axis=1)

    # if its not the last 10 indices of the period
    if np.argmin(lastPeriod) < len(lastPeriod) - 10:
        # add in last period min back in
        minsIndex = np.append(minsIndex, np.argmin(lastPeriod))
    else:
        # otherwise, duplicate the previous min
        # MUST DO THIS so minsIndex has correct length
        minsIndex = np.append(minsIndex, minsIndex[-1] - len(periods[-1]))

    # for each period index, convert to index in d
    minsIndex = np.add(minsIndex, offset)

    # check alternans
    if alternans:
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

    # return success
    return 0


def NormalizeData(data):
    data = data - data.min(axis=0)

    return data / data.max(axis=0)


def fft(signal, sampling_rate):
    """
    Returns the dominant frequency of each pixel across all the frames
    @:arg:
    signal: np array with image data
    :return: 2D np array containing the dominant frequency value for each pixel
    """
    fft_frames = np.fft.fft(signal, axis=0)
    fft_abs = np.abs(fft_frames)  # Magnitude of the frequency
    fft_abs[..., 0] = 0  # Remove zero frequency component
    dominant_frequencies = np.argmax(fft_abs, axis=0)
    dominant_frequencies = dominant_frequencies * sampling_rate / signal.shape[0]

    return dominant_frequencies
