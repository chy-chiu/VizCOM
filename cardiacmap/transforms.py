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
    return gaussian_filter(arr, sigma, radius=radius, axes = (1, 2))
