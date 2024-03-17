import concurrent.futures as cf
from types import NoneType
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter, uniform_filter

### TODO: ? make this a class instead and include to data.py

def TimeAverage(arr, sigma, radius, mask=None, mode='Gaussian'):
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
    if mode=='Gaussian':
        avgFunc = gaussian_filter
        # ~25% faster to swap axes for gaussian time avg than to not
        axis = 2
        arr = np.array(arr).swapaxes(0, -1)
    elif mode=='Uniform':
        avgFunc = useUniform
        axis = 0
        
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    
    if isinstance(mask, NoneType):
        if(axis != 0):
            return avgFunc(arr, sigma, radius=radius, axes=axis).swapaxes(-1, 0)
        return avgFunc(arr, sigma, radius=radius, axes=axis)
    else:
        if(np.array(mask).shape != np.array(arr[0]).shape):
            raise IndexError("mask must have same shape as a single frame")
        
        data = avgFunc(arr, sigma, radius=radius, axes=axis)
        # set masked points back to original value
        data = np.where(mask == 0, arr, data)
        
        if(axis != 0):
            data = data.swapaxes(-1, 0)
            
        return data.astype('int')

def SpatialAverage(arr, sigma, radius, mask=None, mode='Gaussian'):
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
    if mode=='Gaussian':
        avgFunc = gaussian_filter
    elif mode=='Uniform':
        avgFunc = useUniform
        
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    
    # convert sigma to sqrt(sigma/2)
    # replicates Java version functionality
    newSigma = np.sqrt(sigma/2)
    if isinstance(mask, NoneType):
        return avgFunc(arr, newSigma, radius=radius, axes=(1,2))
    else:
        if(np.array(mask).shape != np.array(arr[0]).shape):
            raise IndexError("mask must have same shape as a single frame")
        
        maskedData = avgFunc(arr * mask, newSigma, radius=radius, axes=(1, 2))
        maskWeights = avgFunc(mask, newSigma, radius=radius, axes=(0, 1))

        # normalize data by relative mask weights
        data = maskedData / maskWeights

        # set masked points back to original value
        data = np.where(mask == 0, arr, data)
        return data.astype('int')

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
    end = np.arange(arrLen-trimEnd-1, arrLen)
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
    return uniform_filter(arr, size=2*radius+1, axes=axes)

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
    
    if(method == 'Threshold'):
        executor = cf.ThreadPoolExecutor(max_workers=threads)
        for y in range(yLen):
            for x in range(xLen):
                index = y * yLen + x
                d = data[y][x]
                executor.submit(getMinsByThresholdThread, methodValue, t, d, baselineX, baselineY, index)
        executor.shutdown(wait=True)
        
    elif(method == 'Period'):
        if tLen%methodValue == 0:
            offset = [methodValue * i for i in range(int(tLen/methodValue))]
        else:
            offset = [methodValue * i for i in range(int(tLen/methodValue) + 1)]
        pIdx = np.arange(methodValue, tLen, methodValue)
        for y in range(yLen):
            for x in range(xLen):
                index = y * yLen + x
                d = data[y][x]
                getMinsByPeriod(t, d, baselineX, baselineY, index, offset, pIdx)
        
    else:
        raise ValueError("getMins method must be Threshold or Period. Was:", method)


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
    if(len(badMinsIndex) == len(minsIndex)):
        minsIndex = [0, len(d)-1]
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

    # add in last period min back in
    minsIndex = np.append(minsIndex, np.argmin(lastPeriod))
    
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
            executor.submit(baselineDriftThread, t, d, resData, index,  xs, ys)
  
    executor.shutdown(wait=True)
    # reshape results array, then convert to int from float
    return np.array(resData).reshape(yLen, xLen, tLen).astype(int)

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

def NormalizeData(data):
    data = np.moveaxis(data, 0, -1)
    # constants to normalize data to
    RES_MIN = 10000
    RES_RANGE = 20000
    
    # get mins and maxes
    dataMaxes = np.amax(data, axis=2)
    dataMins = np.amin(data, axis=2)
    
    # subtract mins from both data and maxes
    norm = dataMaxes - dataMins
    dataMins = np.expand_dims(dataMins, 2)
    dataMinusMins = np.subtract(data, dataMins)
    
    # normalize [0 - 1]
    res = dataMinusMins / norm[:, :, np.newaxis]
    
    # output data array will be in range [RES_MIN, RES_MIN + RES_RANGE]
    res *= RES_RANGE
    res += RES_MIN
    
    res = np.moveaxis(res, -1, 0)
    return res.astype(int)