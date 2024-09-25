import os
import struct
import numpy as np
import skimage

from cardiacmap.model.data import CascadeSignal


# TODO: To test and make robust
def read_scimedia_data(filepath: str, update_progress=None):

    file = open(filepath, "rb")

    file.read(256)

    xPixels = struct.unpack("<" + "h" * 1, file.read(2))[0]
    yPixels = struct.unpack("<" + "h" * 1, file.read(2))[0]
    xSkipPix = struct.unpack("<" + "h" * 1, file.read(2))[0]
    ySkipPix = struct.unpack("<" + "h" * 1, file.read(2))[0]
    xActPix = struct.unpack("<" + "h" * 1, file.read(2))[0]
    yActPix = struct.unpack("<" + "h" * 1, file.read(2))[0]
    nFrames = struct.unpack("<" + "h" * 1, file.read(2))[0]

    print(nFrames)

    file = open(filepath, "rb")

    file.read(972)

    bg_img = struct.unpack(
        "<" + "h" * xPixels * yPixels, file.read(xPixels * yPixels * 2)
    )
    bg_img = np.array(bg_img).reshape(xPixels, yPixels)

    if update_progress:
        update_progress(0.8)

    dt = np.dtype("int16")
    dt = dt.newbyteorder("<")

    sig_array = np.frombuffer(
        file.read(xPixels * yPixels * nFrames * 2), dtype=dt
    ).reshape(xPixels, yPixels, nFrames)
    pooled_array = skimage.measure.block_reduce(sig_array, (2, 2, 1), np.sum)

    print(pooled_array.shape)

    file.close()

    metadata = dict(
        span_T=nFrames,
        span_X=128,
        span_Y=128,
        framerate=500,
        filename=os.path.basename(filepath),
    )

    return metadata, pooled_array.transpose(2, 0, 1)


def load_scimedia_data(filepath: str, largeFilePopup, update_progress=None):

    file_metadata, sigarray = read_scimedia_data(
        filepath, update_progress=update_progress
    )

    signals = {}

    signals[0] = CascadeSignal(
        signal=sigarray, metadata=file_metadata, channel="Single"
    )

    return signals
