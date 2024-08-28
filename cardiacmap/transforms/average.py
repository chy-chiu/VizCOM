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
