from cardiacmap.model.voltage_import import VoltageImport


def test_get_extension():
    t = VoltageImport("cardiacmap/data/2012-02-13_Exp000_Rec005_Cam3-Blue.dat")
    assert t.get_filename() == "cardiacmap/data/2012-02-13_Exp000_Rec005_Cam3-Blue.dat"
    assert t.get_extension() == ".dat"


def test_load_signal():
    t = VoltageImport("2012-02-13_Exp000_Rec005_Cam3-Blue.dat")
    sig_data = t.load_signal()
    assert sig_data.transformed_data.shape[0] == sig_data.span_T
    assert sig_data.transformed_data.shape[1] == sig_data.span_X
    assert sig_data.transformed_data.shape[2] == sig_data.span_Y
