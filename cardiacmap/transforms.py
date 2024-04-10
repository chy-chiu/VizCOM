import concurrent.futures as cf
from types import NoneType

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter
from scipy.signal import find_peaks


def TimeAverage(arr, sigma, radius, mask=None, mode="Gaussian"):
    """Function to apply a gaussian filter to a data array along Time Axis
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        mask (array): 2d array with same dimensions as arr[0] (128 x 128)

    Returns:
        ndarray: result of averaging along time axis
    """
    # select averaging mode
    if mode == "Gaussian":
        avgFunc = gaussian_filter
        # ~25% faster to swap axes for gaussian time avg than to not
        axis = 2
        arr = np.array(arr).swapaxes(0, -1)
    elif mode == "Uniform":
        avgFunc = useUniform
        axis = 0

    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if radius < 0:
        raise ValueError("radius must be non-negative")

    if isinstance(mask, NoneType):
        if axis != 0:
            return avgFunc(arr, sigma, radius=radius, axes=axis).swapaxes(-1, 0)
        return avgFunc(arr, sigma, radius=radius, axes=axis)
    else:
        print(arr.shape)

        # if np.array(mask).shape != np.array(arr[0]).shape:
        #     raise IndexError("mask must have same shape as a single frame")

        data = avgFunc(arr, sigma, radius=radius, axes=axis)
        # set masked points back to original value
        data = np.where(np.expand_dims(mask, axis) == 1, arr, data)

        if axis != 0:
            data = data.swapaxes(-1, 0)

        return data.astype("int")


def SpatialAverage(arr, sigma, radius, mask=None, mode="Gaussian"):
    """Function to apply a gaussian filter to a data array along Spatial Axes
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        mask (array): 2d array with same dimensions as arr[0] (128 x 128)

    Returns:
        ndarray: result of averaging along spatial axes
    """
    # select averaging mode
    if mode == "Gaussian":
        avgFunc = gaussian_filter
    elif mode == "Uniform":
        avgFunc = useUniform

    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if radius < 0:
        raise ValueError("radius must be non-negative")

    # convert sigma to sqrt(sigma/2)
    # replicates Java version functionality
    newSigma = np.sqrt(sigma / 2)
    if isinstance(mask, NoneType):
        return avgFunc(arr, newSigma, radius=radius, axes=(1, 2))
    else:
        if np.array(mask).shape != np.array(arr[0]).shape:
            raise IndexError("mask must have same shape as a single frame")

        maskedData = avgFunc(arr * mask, newSigma, radius=radius, axes=(1, 2))
        maskWeights = avgFunc(mask, newSigma, radius=radius, axes=(0, 1))

        # normalize data by relative mask weights
        data = maskedData / maskWeights

        # set masked points back to original value
        data = np.where(mask == 0, arr, data)
        return data.astype("int")


def InvertSignal(arr):
    """Function to invert array values
    Args:
        arr (array): data
    Returns:
        newArr: results, each data point is equal to: -(value) -1
                                                    i.e. np.invert([6, 0]) -> [-7, -1]
    """

    newArr = np.invert(arr)
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


def GetMins(t, data, method, methodValue, threads):
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
            offset = [methodValue * i for i in range(int(tLen / methodValue) + 1)] # numpy doesnt support jagged arrs, must do the last segment seperately
        pIdx = np.arange(methodValue, tLen, methodValue)
        for y in range(yLen):
            for x in range(xLen):
                index = y * yLen + x
                d = data[y][x]
                getMinsByPeriod(t, d, baselineX, baselineY, index, offset, pIdx)

    else:
        raise ValueError("getMins method must be Threshold or Period. Was:", method)

    baselineX = np.array(baselineX)
    baselineY = np.array(baselineY)

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


def getMinsByPeriod(t, d, xOut, yOut, outIndex, offset, periodIdx):
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
    if(np.argmin(lastPeriod) < len(lastPeriod) - 10):
        # add in last period min back in
        minsIndex = np.append(minsIndex, np.argmin(lastPeriod))
    else:
        # otherwise, duplicate the previous min
        # MUST DO THIS so minsIndex has correct length
        minsIndex = np.append(minsIndex, minsIndex[-1] - len(periods[-1]))

    # for each period index, convert to index in d
    minsIndex = np.add(minsIndex, offset)

    # set output
    xOut[outIndex] = t[minsIndex]
    yOut[outIndex] = d[minsIndex]

    # return success
    return 0


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


def NormalizeData(data):
    # data = np.moveaxis(data, 0, -1)
    # constants to normalize data to
    # RES_MIN = 0
    # RES_RANGE = 10000

    # get mins and maxes
    # dataMaxes = np.amax(data, axis=2)
    dataMins = np.min(data, axis=0)

    print(dataMins)

    # # subtract mins from both data and maxes
    # norm = dataMaxes - dataMins

    # dataMins = np.expand_dims(dataMins, 2)
    # dataMinusMins = np.subtract(data, dataMins)

    data -= np.expand_dims(dataMins, 0)

    # # normalize [0 - 1]
    # res = dataMinusMins / norm[:, :, np.newaxis]

    # # output data array will be in range [RES_MIN, RES_MIN + RES_RANGE]
    # res *= RES_RANGE
    # res += RES_MIN

    # res = np.moveaxis(res, -1, 0)

    print(data.dtype)
    print(data[0, 0, :])

    return data

    return res


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
