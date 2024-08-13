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
