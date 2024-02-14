from types import NoneType
import numpy as np
from scipy.ndimage import gaussian_filter

### TODO: ? make this a class instead and include to data.py

def TimeAverage(arr, sigma, radius, mask=None):
    """Function to apply a gaussian filter to a data array along Time Axis
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        mask (array): 2d array with same dimensions as arr[0] (128 x 128)
        
    Returns:
        ndarray: result of averaging along time axis
    """   
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    
    if isinstance(mask, NoneType):
        return gaussian_filter(arr, sigma, radius=radius, axes=0)
    else:
        if(np.array(mask).shape != np.array(arr[0]).shape):
            raise IndexError("mask must have same shape as a single frame")
        
        data = gaussian_filter(arr, sigma, radius=radius, axes=0)

        # set masked points back to original value (TODO: is this needed?)
        data = np.where(mask == 0, arr, data)
        return data.astype('int')

def SpatialAverage(arr, sigma, radius, mask=None):
    """Function to apply a gaussian filter to a data array along Spatial Axes
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        mask (array): 2d array with same dimensions as arr[0] (128 x 128)
        
    Returns:
        ndarray: result of averaging along spatial axes
    """   
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    
    # convert sigma to sqrt(sigma/2)
    # replicates Java version functionality
    newSigma = np.sqrt(sigma/2)
    if isinstance(mask, NoneType):
        return gaussian_filter(arr, newSigma, radius=radius, axes=(1,2))
    else:
        if(np.array(mask).shape != np.array(arr[0]).shape):
            raise IndexError("mask must have same shape as a single frame")
        
        maskedData = gaussian_filter(arr * mask, newSigma, radius=radius, axes=(1, 2))
        maskWeights = gaussian_filter(mask, newSigma, radius=radius) # axes = (0, 1)

        # normalize data by relative mask weights
        data = maskedData / maskWeights

        # set masked points back to original value (TODO: is this needed?)
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
