import os
import struct

import numpy as np
import psutil

from cardiacmap.model.signal import CascadeSignal

def read_cascade_data(filepath: str, largeFilePopup) -> np.ndarray:
    """Load raw data from cascade .dat files. Returns a 3D signal array. Can be used in load_cascade_file 
    as the helper method to parse the .dat file or by itself for debug

    Args:
        filepath (str): Input file path
        largeFilePopup (func): callback function to open popup window for larger-than-memory files 

    Returns:
        metadata: dict of metadata
        imarray: numpy array of size (frame, H, W)
    """
    file = open(filepath, "rb")
    filename = os.path.basename(filepath)

    endian = "<"

    metadata = {"filename": filename}

    # First byte of the data is the file version
    file_version = file.read(1).decode()

    # Header parsing
    if file_version == "d":
        # TODO: Version D is a WIP.This needs to be tested.
        header = file.read(1023)

        # In the original code, it reads 17 + 7 bytes of datetime.
        metadata["datetime"] = header.pop(24).decode().rstrip("\x00")

        file.read(8)
        metadata["framerate"] = (
            struct.unpack(endian + "I", file.read(4))[0] / 100
        )

        span_T = struct.unpack(endian + "I", file.read(4))[0]
        span_X = struct.unpack(endian + "I", file.read(4))[0]
        span_Y = struct.unpack(endian + "I", file.read(4))[0]

        skip_bytes = 0

        metadata["metadata"] = ""

    elif file_version == "f" or file_version == "e":
        # First integer is the byte order
        byte_order = struct.unpack("I", file.read(4))[0]

        if byte_order == 439041101:
            endian = "<"
        else:
            endian = ">"

        # Next three integers are the span
        span_T = struct.unpack(endian + "I", file.read(4))[0]
        span_X = struct.unpack(endian + "I", file.read(4))[0]
        span_Y = struct.unpack(endian + "I", file.read(4))[0]

        # Skip 8 bytes
        file.read(8)
        metadata["framerate"] = (
            struct.unpack(endian + "I", file.read(4))[0] / 100
        )
        metadata["datetime"] = file.read(24).decode().rstrip("\x00")
        metadata["file_metadata"] = file.read(971).decode().rstrip("\x00")

        skip_bytes = 8

    # This reads the actual signal data    
    skip = skip_bytes // 2
    
    trimFrames = large_file_check(filepath, largeFilePopup, span_T)
    if trimFrames[1] == 0:
        sigarray = np.frombuffer(file.read(), dtype="uint16")
    else:
        file.read(trimFrames[0] * 2 * span_X * span_Y + trimFrames[0] * skip_bytes) # skip
        sigarray = np.frombuffer(file.read(trimFrames[1] * 2 * span_X * span_Y + trimFrames[1] * skip_bytes), dtype="uint16" ) # read   
        span_T = trimFrames[1] # set new spanT
        
    sigarray = sigarray.reshape(span_T, -1)[:, :-skip].reshape(
        span_T, span_X, span_Y
    )
    
    metadata["span_T"] = span_T
    metadata["span_X"] = span_X
    metadata["span_Y"] = span_Y

    file.close()

    return metadata, sigarray

def load_cascade_file(filepath, largeFilePopup, dual_mode=False):
    """Wrapper to load a raw .dat file to return a single or dual channel signal. 

    Args:
        filepath (str): Path ot file
        largeFilePopup (): _description_
        dual_mode (bool, optional): Whether the input signal is dual mode (Voltage / Calcium). Defaults to False.

    Returns:
        signals: Dictionary of CascadeSignal
    """    
    file_metadata, sigarray = read_cascade_data(filepath, largeFilePopup)

    signals = {}

    if dual_mode:
        odd_frames, even_frames = [sigarray[::2, :, :], sigarray[1::2, :, :]]
        signals[0] = CascadeSignal(signal=odd_frames, metadata=file_metadata, channel="Odd")
        signals[1] = CascadeSignal(signal=even_frames, metadata=file_metadata, channel="Even")
        file_metadata["span_T"] = file_metadata["span_T"] // 2
    else:
        signals[0] = CascadeSignal(signal=sigarray, metadata=file_metadata, channel="Single")

    return signals

def large_file_check(filepath, _callback, fileLen):
    """Helper method to check a Cascade file against available RAM to avoid OOM error
    Args:
        filepath(str): Input file path
    Returns:
        tuple: (skip_frames, read_frames) or (0, 0) if file is small enough to handle
    """
    USAGE_THRESHOLD = .5
    freeMem = psutil.virtual_memory()[1]
    estDataSize = os.path.getsize(filepath) * 4 # estimate conversion to float16 and 2 data sets (raw and transformed)
                                                # THIS IS A VERY ROUGH ESTIMATE PROBABLY NEEDS FURTHER INVESTIGATION
    
    usePercentage = estDataSize / freeMem
    
    # use 50% threshold to leave room for apd, di, fft, etc.
    if usePercentage > USAGE_THRESHOLD:
        maxFrames = int((freeMem * .5)/1040000) # AGAIN, VERY ROUGH ESTIMATE BASED ON 5k FRAMES @ 650MB
            
        start, end = _callback(fileLen, maxFrames) #pauses execution until popup is closed

        skip = start
        size = end - start
        
        return (skip, size)
    return (0, 0)
