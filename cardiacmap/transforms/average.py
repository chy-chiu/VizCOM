import concurrent.futures as cf

import numpy as np
import numpy.ma as ma
from scipy.ndimage import gaussian_filter, uniform_filter

import time


def TimeAverage(arr, sigma, radius, mask=None, mode="Uniform"):
    """Function to apply a gaussian filter to a data array along Time Axis
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging
        mask (array): 2d array with same dimensions as arr[0]

    Returns:
        array: result of averaging along time axis
    """
    #s = time.time()
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if radius < 0:
        raise ValueError("radius must be non-negative")
    
    if np.array(mask).shape != np.array(arr[0]).shape:
        raise ValueError("mask must have same shape as a single frame")
    
    # flatten x and y, and swap resulting axes to view data pixelwise
    flat_swapped_arr = np.swapaxes(arr.reshape(arr.shape[0], -1), 0, 1)
    
    # select averaging mode
    if mode == "Gaussian":
        flat_swapped_data = gaussian_filter(flat_swapped_arr, sigma, radius=radius, axes=1)
    elif mode == "Uniform":
        flat_swapped_data = uniform_filter(flat_swapped_arr, size=radius, axes=1)
        
    # swap axes of result back, unflatten x and y
    data = np.reshape(np.swapaxes(flat_swapped_data, 0, 1), (arr.shape))
    
    #e = time.time()
    #print("Time Avg Runtime:", e-s)
    return data

def SpatialAverage(arr, sigma, radius, mask=None, mode="Gaussian"):
    """Function to apply a gaussian filter to a data array along Spatial Axes
    Args:
        arr (array): data, must be 3-dimensional with time on the first axis
        sigma (float): intensity of averaging, higher values -> more blur
        radius (int): radius of averaging
        mask (array): 2d array with same dimensions as arr[0]

    Returns:
        array: result of averaging along spatial axes
    """
    #s = time.time()
    
    if sigma < 0:
        raise ValueError("sigma must be non-negative")
    if radius < 0:
        raise ValueError("radius must be non-negative")

    # convert sigma to sqrt(sigma/2)
    # replicates Java version functionality
    newSigma = np.sqrt(sigma / 2)

    if np.array(mask).shape != np.array(arr[0]).shape:
        raise IndexError("mask must have same shape as a single frame")
    
    # select averaging mode

    if mode == "Gaussian":
        maskedData = gaussian_filter(arr * mask, newSigma, radius=radius, axes=(1, 2))
        maskWeights = gaussian_filter(mask.astype(np.float64), newSigma, radius=radius, axes=(0, 1))
    elif mode == "Uniform":
        maskedData = uniform_filter(arr * mask, size=radius, axes=(1, 2))
        maskWeights = uniform_filter(mask.astype(np.float64), newSigma, size=radius, axes=(0, 1))

    # normalize data by relative mask weights
    data = maskedData / ma.array(maskWeights, mask = maskWeights==0)

    return ma.getdata(data) * mask
