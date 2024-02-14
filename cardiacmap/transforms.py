from random import uniform
from types import NoneType
import numpy as np
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
    elif mode=='Uniform':
        avgFunc = useUniform
        
    if(sigma < 0):
        raise ValueError("sigma must be non-negative")
    if(radius < 0):
        raise ValueError("radius must be non-negative")
    
    if isinstance(mask, NoneType):
        return avgFunc(arr, sigma, radius=radius, axes=0)
    else:
        if(np.array(mask).shape != np.array(arr[0]).shape):
            raise IndexError("mask must have same shape as a single frame")
        
        data = avgFunc(arr, sigma, radius=radius, axes=0)

        # set masked points back to original value
        data = np.where(mask == 0, arr, data)
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
