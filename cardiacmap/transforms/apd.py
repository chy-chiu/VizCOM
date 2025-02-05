import numpy as np


def GetThresholdIntersections(data, threshold, spacing, intervals=None, mask = None):
    """Function to Find intersections between threshold and data
    Args:
        data (np.ndarray): input data
        threshold (int): threshold value
        spacing (float): minimum x-distance between two intersections
        intervals (array): array of index values to slice 'data'
    """
    #print("Minimum Spacing is:", spacing)
    apdArrs = []
    diArrs = []
    
    if intervals is None:
        slices = [data]
    else:
        slices = []
        for i in range(1, len(intervals)):
            start = intervals[i-1]
            end = intervals[i]-1
            slices.append(data[start:end])
            
    #executor = cf.ThreadPoolExecutor(4)
    
    for data_slice in slices:
        flat_swapped_arr = np.swapaxes(data_slice.reshape(data_slice.shape[0], -1), 0, 1)
        pixels =  np.arange(flat_swapped_arr.shape[0])
        intersections = []
        apdFlags = []
        for p in pixels:
            ints, apd = GetThresholdIntersections1D(flat_swapped_arr[p], threshold, spacing)
            intersections.append(ints)
            apdFlags.append(apd)
        apdArr, diArr = CalculateIntervals(intersections, apdFlags)
        apdArr = np.swapaxes(apdArr, 1, 0).reshape(apdArr.shape[1], data_slice.shape[1], data_slice.shape[2])
        diArr = np.swapaxes(diArr, 1, 0).reshape((diArr.shape[1], data_slice.shape[1], data_slice.shape[2]))
        
        apdArrs.append(apdArr)
        diArrs.append(diArr)

    return apdArrs, diArrs

def GetThresholdIntersections1D(data, threshold, spacing = 0):
    #print(spacing)
    # remove points that lie directly on the line
    threshData = data - threshold
    mask = np.argwhere(threshData == 0)
    threshData[mask] = threshData[mask-1]

    # get indices immediately before data crosses the threshold
    idx0 = np.argwhere(
                np.diff( 
                    np.sign(threshData)
                )
           )[:, 0]


    idx1 = idx0 + 1 # idx after

    y0 = data[idx0]
    y1 = data[idx1]

    ts, apdFlags = getTimes(idx0, y0, y1, threshold, spacing)
    
    return ts, apdFlags


def getTimes(x0s, y0s, y1s, threshold, spacing):
    """Helper function to calculate the exact t values of intersection for a signal
    Args:
        threshold (int): threshold value
        x0s (array): t values BEFORE crossing threshold
        y0s (array): data values BEFORE crossing threshold
        y1s (array): data values AFTER crossing threshold
        threshold (float): apd threshold for calculation
        spacing (int): minimum x-distance between points
    """
    slopes = np.subtract(y1s, y0s)
    # no intersections found
    if len(slopes) == 0:
        return np.array([0, 1]), False

    # if the slope is positive, its an apd
    apdFlags = slopes > 0
    
    # remove the first (leftmost) intersection where two consective APDs/DIs are found
    invalid = np.argwhere(np.diff(apdFlags) == False)
    apdFlags = np.delete(apdFlags, invalid)
    slopes = np.delete(slopes, invalid)
    x0s = np.delete(x0s, invalid)
    y0s = np.delete(y0s, invalid)
    
    # remove where slope is 0
    invalid = np.argwhere(slopes == 0)
    apdFlags = np.delete(apdFlags, invalid)
    slopes = np.delete(slopes, invalid)
    x0s = np.delete(x0s, invalid)
    y0s = np.delete(y0s, invalid)
    
    # calculation intersection times
    intercepts = y0s - (slopes * x0s)
    ts = (threshold - intercepts) / slopes
    
    # delete intersections that are too short
    tooShort = np.argwhere(np.diff(ts) < spacing).reshape(-1) + 1
    ts = np.delete(ts, tooShort)
    newApdFlags = np.delete(apdFlags, tooShort)

    # combine unmatched APD/DIs
    unmatched = np.argwhere(np.diff(newApdFlags) == False)
    ts = np.delete(ts, unmatched)
    
    return ts, apdFlags[0] # tooShort


def CalculateIntervals(intersections, firstIntervalFlag):
    """Function to measure the intervals between intersections and store interval time as apd/di
    Args:
        intersections (array): intersections found by GetThresholdIntersections()
        firstIntervalFlag (array): bool array indicating whether first interval of a signal is apd/di
    """
    apdArr = []
    diArr = []
    longestAPD = 0
    longestDI = 0
    for sig in np.arange(len(intersections)):
        # get this signals intersections
        sigInters = np.array(intersections[sig])
        intervals = np.diff(sigInters)
        # check if the first interval is an apd or di
        apdFirst = firstIntervalFlag[sig]
        
        if apdFirst:
            dis = intervals[1::2]
            apds = intervals[2::2]
        else:
            dis = intervals[::2]
            apds = intervals[1::2]
            
        if len(apds) > longestAPD:
            longestAPD = len(apds)
            
        if len(dis) > longestDI:
            longestDI = len(dis)
            
        apdArr.append(apds)
        diArr.append(dis)

    apdArr = pad(apdArr, longestAPD)
    diArr = pad(diArr, longestDI)
    return apdArr, diArr


# helper function to pad an array with zeros until it is rectangular
def pad(array, targetWidth):
    for i in range(len(array)):
        numZeros = targetWidth - len(array[i])
        zeros = np.zeros(numZeros)
        array[i] = np.concatenate((array[i], zeros))
    return np.asarray(array)
