from cardiacmap.model.voltage_import import VoltageImport


class VoltageCalciumImport(VoltageImport):
    """Loads either the odd or the even frames from the given file into the
    current view, and if requested will load a second view
    to look at both the odd and even frames in separate windows.
    """

    def __init__(self, mode, filename):
        super().__init__(filename)
        self._mode = mode

    def get_even_mode_data(self):
        cascade_obj = super().load_signal()
        signal = cascade_obj.get_curr_signal()
        cascade_obj.transformed_data = signal[::2, :, :]
        return cascade_obj

    def get_odd_mode_data(self):
        cascade_obj = super().load_signal()
        signal = cascade_obj.get_curr_signal()
        cascade_obj.transformed_data = signal[1::2, :, :]
        return cascade_obj

    def get_data(self):
        match self._mode:
            case 'e':
                return self.get_even_mode_data()
            case 'o':
                return self.get_odd_mode_data()
            case _:
                raise ValueError(f"Invalid value for mode:{self._mode}")
