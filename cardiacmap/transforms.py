import numpy as np
from scipy.ndimage import gaussian_filter

### TODO: ? make this a class instead and include to data.py

def TimeAverage(arr, sigma, radius):
    """Function to apply a gaussian filter to a data array along Time Axis
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        
    Returns:
        ndarray: result of averaging along time axis
    """   
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    return gaussian_filter(arr, sigma, radius=radius, axes = 0)

def SpatialAverage(arr, sigma, radius):
    """Function to apply a gaussian filter to a data array along Spatial Axes
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging, kernel width = 2 * radius + 1
        
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
    return gaussian_filter(arr, newSigma, radius=radius, axes = (1, 2))

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
