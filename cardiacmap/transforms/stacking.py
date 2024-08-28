import itertools as it

import numpy as np
from scipy.signal import find_peaks


def Stacking(data, derivative, numPeriods, alternans):
    # speeds computation
    derivative = np.moveaxis(derivative, 0, -1)
    data = np.moveaxis(data, 0, -1)

    results = [[] for j in range(len(data[0]) * len(data))]
    longestRes = 0
    # stack each pixel
    for y in range(len(data)):
        for x in range(len(data[0])):
            d = data[y][x]
            # print(len(d))
            dYdX = derivative[y][x]
            result = stack(d, dYdX, numPeriods, alternans)

            if len(result) > longestRes:
                longestRes = len(result)
            # display progress
            if (y * 128 + x) % 1000 == 0:
                print("Stacking:", int(100 * (y * 128 + x) / (128 * 128)), "%")
            results[y * len(data) + x] = result

    return results, longestRes


def stack(data, derivative, n, alternans):
    # Find derivative peaks and offset
    peaks = find_peaks(NormalizeData(derivative), prominence=0.3)[0]
    if alternans:
        peaks = peaks[::2]  # take only even peaks
        offset = 0.05
    else:
        offset = 0.1

    periodLen = np.mean(np.diff(peaks))
    peaks -= int(periodLen * offset)

    # trim peaks
    while len(peaks) > 0 and peaks[0] <= 0:
        peaks = peaks[1:]
    peaks = peaks[0 : n + 1]

    # slice data
    data = NormalizeData(data)
    slices = np.split(data, peaks)

    if len(slices) < 3:
        return [0], [0]

    # get rid of outer slices
    slices.pop(0)
    slices.pop()

    # print(len(slices))
    # average all the slices (pad with 0s)
    stacked = [0] + list(map(paddedAvg, it.zip_longest(*slices)))

    return stacked


def paddedAvg(x):
    x = [0 if i is None else i for i in x]
    return sum(x, 0) / len(x)


def NormalizeData(data):
    data = data - data.min(axis=0)
    return data / data.max(axis=0)
