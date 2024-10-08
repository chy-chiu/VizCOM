import numpy as np


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


def NormalizeData(data: np.ndarray):
    d = (data - data.min(axis=0))
    return  d / d.max(axis=0)

def FFT(signal):
    """
    perform a fast fourier transform on a video signal
    @:arg:
    signal: np array with image data
    :return: 2D np array containing the dominant frequency value for each pixel
    """
    fft = np.fft.fft(signal, axis=0)
    fft_frames = fft.real ** 2 + fft.imag ** 2
    fft_frames = np.abs(fft_frames)
    fft_frames[0, ...] = 0  # Remove zero frequency component
    fft_frames = fft_frames[0:int(len(fft_frames)/2), ...] # cut in half
    
    return NormalizeData(fft_frames)
