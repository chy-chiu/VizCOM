from pathlib import Path
from cardiacmap.data import CascadeDataVoltage


# TODO: Extend this class as more filetypes are supported
class VoltageImport:
    """
         Handles the decision of which import function to use. Uses the file extension
         of the passed-in filename to determine which ImportCommand to use.
    """

    def __init__(self, filename):
        self._filename = filename
        self._ext = Path(self._filename).suffix

    def get_extension(self):
        return self._ext

    def get_filename(self):
        return self._filename

    def load_signal(self):
        match self._ext:
            case ".dat":
                return CascadeDataVoltage.from_dat(self._filename)
            case _:
                raise ValueError("Extension not recognized")
