### Simple parser script for .dat format

import argparse
import io
import struct
import pickle
import numpy as np

class CascadeData():

    datetime: str
    framerate: int
    metadata: str
    span_T: int
    span_X: int
    span_Y: int
    imarray: np.ndarray

    def __init__(self):
        return
    
    def transform(self, type, **transform_kwargs):
        
        return
    
    @classmethod
    def from_dat(cls):
        return


# TODO: Refactor this into a class method
def cascade_import(filepath: str):
    """Main function to import cascade .DAT files.

    Args:
        filepath (str): path to file to be converted
        format (str): which format to save / return the file in. Can be "binary" or "pickle"
        save (bool, optional): Whether to save the file locally. Defaults to True.
    """    
    """Main function to import cascade .DAT files"""

    with open(filepath, 'rb') as file:
        
        endian = "<"

        # First byte of the data is the file version
        file_version = file.read(1).decode()

        if file_version == "d":
            # TODO: Version D is a WIP. 
            header = file.read(1023)

            # In the original code, it reads 17 + 7 bytes of datetime. 
            datetime = header.pop(24).decode().rstrip('\x00')

            file.read(8)
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100

            span_T = struct.unpack(endian + "I", file.read(4))[0]
            span_X = struct.unpack(endian + "I", file.read(4))[0]
            span_Y = struct.unpack(endian + "I", file.read(4))[0]

            skip_bytes = 0

            metadata = ""
        
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
            framerate = struct.unpack(endian + "I", file.read(4))[0] / 100
            datetime = file.read(24).decode().rstrip('\x00')
            metadata = file.read(971).decode().rstrip('\x00')

            skip_bytes = 8

        bstream = file.read()

    # TODO Sort out chunking here and make it more elegant
            
    len_file = len(bstream)
    raw_image_data = list(struct.unpack('H'*(len_file//2), bstream))

    skip = skip_bytes / 2 # Because each long integer is 2 bytes)
    imarray = []
    for t in range(span_T):

        position = int(t * (span_X * span_Y + skip))

        im_raw = raw_image_data[position: position + span_X * span_Y]

        imarray.append(im_raw)

    imarray = np.array(imarray)

    return np.array([im.reshape(span_X, span_Y) for im in imarray])
