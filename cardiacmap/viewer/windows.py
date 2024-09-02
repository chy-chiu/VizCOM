import os
import sys
from functools import partial
from typing import List, Optional
import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph.console import ConsoleWidget

from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.data import CascadeSignal
from cardiacmap.viewer.panels import (
    FFTPositionView,
    PositionView,
    MetadataPanel,
    ScatterPlotView,
    ScatterPanel,
    SpatialPlotView,
    SignalPanel,
    StackingPositionView,
    AnnotateView,
    IsochromeWindow
)
from cardiacmap.viewer.utils import loading_popup, load_settings, save_settings

from typing import Literal

TITLE_STYLE = """QDockWidget::title
{
font-family: "Roboto Lt";
font-size: 18pt;
background: #DCDCDC;
padding-left: 10px;
padding-top: 4px;
}
"""
INITIAL_POSITION = (64, 64)


class CardiacMap(QMainWindow):
    """Main window for signal analysis"""

    def __init__(self, signal: Optional[CascadeSignal]=None, title: str=""):

        super().__init__()

        self.title = title
        self.resize(1200, 600)
        self.setStyleSheet(TITLE_STYLE)
        self.init_menu()


        # TODO: Fix / Add Console Function
        self.console = ConsoleWidget()
        self.console.setMinimumWidth(500)
        self.console.setMinimumHeight(100)
        size_policy = QtWidgets.QSizePolicy()
        size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        self.console.setSizePolicy(size_policy)
        
        self.signal = signal
        
        self.default_widget = QWidget()
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(QLabel("No files loaded. Load a Cascade Image File with \"File → Load Data\" to continue..."))
        layout.addStretch()
        self.default_widget.setLayout(layout)
        self.default_widget.setStyleSheet(
        "QLabel {font-size:20px; }"
        )

        self.init_viewer()

    def init_menu(self):

        self.menubar = QMenuBar(self)
        self.menubar.setNativeMenuBar(False)
        self.menubar.setStyleSheet("QMenuBar {border-bottom: 1px solid #D3D3D3;}")

        self.file_menu = self.menubar.addMenu("File")
        # self.transforms_menu = self.menubar.addMenu("Transforms")
        self.windows_menu = self.menubar.addMenu("Windows")

        # Settings Menu
        self.settings_menu = self.menubar.addMenu("Settings")

        # File Menu
        self.load_voltage = QAction("Load Voltage Data")
        self.load_voltage.triggered.connect(
            partial(self.load_signal, calcium_mode=False)
        )

        self.load_calcium = QAction("Load Voltage / Calcium Data")
        self.load_calcium.triggered.connect(
            partial(self.load_signal, calcium_mode=True)
        )

        self.save_signal = QAction("Save Signal")

        self.file_menu.addAction(self.load_voltage)
        self.file_menu.addAction(self.load_calcium)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_signal)

        # Windows Menu

        self.stacking = QAction("Stacking")
        self.stacking.triggered.connect(self.create_stacking_window)
        self.apd_window = QAction("APD / DI Plots")
        self.apd_window.triggered.connect(self.plot_apds)
        self.isochrome = QAction("Isochrome / Vector Map")
        self.isochrome.triggered.connect(self.create_isochrome_window)
        self.fft = QAction("FFT", self)
        self.fft.triggered.connect(self.perform_FFT)
        
        self.windows_menu.addAction(self.stacking)
        self.windows_menu.addAction(self.apd_window)
        self.windows_menu.addAction(self.isochrome)
        self.windows_menu.addAction(self.fft)
        


        # # TODO: Transforms Menu
        # self.transforms_menu.addAction("Spatial Average")
        # self.transforms_menu.addAction("Time Average")

        # Help Menu
        self.help = self.menubar.addAction("Help")



        self.setMenuBar(self.menubar)

        return

    def init_viewer(self):

        self.setWindowTitle(self.title + " – CardiacMap" if self.title else "CardiacMap")

        if self.signal:

            self.x, self.y = INITIAL_POSITION
            self.settings = load_settings()

            self.metadata_panel = MetadataPanel(self.signal, self)

            # Create Signal view
            self.signal_panel = SignalPanel(self)

            # Create Image tabs
            self.position_tab = PositionView(self)
            self.position_tab.image_view.setImage(
                self.signal.image_data, autoLevels=True, autoRange=False
            )

            self.annotate_tab = AnnotateView(self)

            self.image_tabs = QTabWidget()
            size_policy = QtWidgets.QSizePolicy()
            size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
            size_policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.Fixed)
            self.image_tabs.setSizePolicy(size_policy)
            self.image_tabs.setMinimumWidth(380)
            self.image_tabs.setMinimumHeight(500)

            self.image_tabs.addTab(self.position_tab, "Position")
            self.image_tabs.addTab(self.annotate_tab, "Annotate")

            # Create docking windows for viewer and signa view.
            self.metadata_dock = QDockWidget()
            self.metadata_dock.setWidget(self.metadata_panel)
            self.metadata_dock.setFloating(False)

            self.signal_dock = QDockWidget("Signal View", self)
            self.image_dock = QDockWidget("Image View", self)

            self.signal_dock.setWidget(self.signal_panel)
            self.image_dock.setWidget(self.image_tabs)

            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
            self.image_dock.resize(400, 1000)

            self.signal.normalize()
            self.ms_changed()  # initialize plot with scaled x values

            self.default_widget.setVisible(False)
            
            self.setCentralWidget(self.metadata_panel)

        else:
            
            self.setCentralWidget(self.default_widget)


    def load_signal(self, calcium_mode=False):

        filepath = QtWidgets.QFileDialog.getOpenFileName()[0]

        if filepath and ".dat" in filepath:

            filename = os.path.split(filepath)[-1]

            signals = load_cascade_file(
                filepath, self.largeFilePopUp, dual_mode=calcium_mode
            )

            if calcium_mode:

                signal_odd = signals[0]
                signal_even = signals[1]

                for signal, suffix in [(signal_odd, "_odd"), (signal_even, "_even")]:
                    self.create_viewer(signal, filename + suffix)
            else:
                signal = signals[0]

                self.create_viewer(signal, filename)

    
    def create_viewer(self, signal: CascadeSignal, title: str):

        """IF there is a signal already, create a new viewer window. Otherwise
        load signal in current window"""

        if self.signal:
            
            viewer = CardiacMap(signal, title)
            viewer.show()
        
        else:
            self.title = title
            self.signal = signal
            self.init_viewer()

    def largeFilePopUp(self, tLen, maxFrames):
        print("Max Possible Frames:", maxFrames)
        self.filePopup = PopupWindow()
        start = self.filePopup.getInt(
            self,
            "File Too Large",
            "Enter Start Frame (0, " + str(tLen) + "):",
            minValue=0,
            maxValue=tLen,
        )[0]

        if start + maxFrames >= tLen:
            maxInput = tLen
        else:
            maxInput = start + maxFrames

        end = self.filePopup.getInt(
            self,
            "File Too Large",
            "Enter End Frame (" + str(start + 1) + ", " + str(maxInput) + "):",
            minValue=start + 1,
            maxValue=tLen,
        )[0]

        return start, end

    def update_signal_value(self, evt, idx=None):

        if self.signal_panel.signal_marker:
            if not idx:
                idx = self.signal_panel.signal_marker.getXPos()
            idx = int(idx / self.ms)
            if idx >= 0 and idx < len(self.signal_panel.signal_data.getData()[0]):

                self.metadata_panel.frame_index.setText(str(idx))
                self.metadata_panel.signal_value.setText(
                    f"{self.signal_panel.signal_data.getData()[1][idx]:.3f}"
                )

    def update_signal_plot(self):
        signal_data = self.signal.transformed_data[:, self.x, self.y]

        xs = self.xVals[0 : len(signal_data)]  # ensure len(xs) == len(signal_data)
        self.signal_panel.signal_data.setData(x=xs, y=signal_data)

        self.metadata_panel.img_position.setText(f"{self.x}, {self.y}")

        self.update_signal_value(None, idx=self.signal_panel.frame_idx)

        if self.signal.show_baseline:
            baseline_idx = self.x * self.signal.span_X + self.y

            bX = self.signal.baselineX[baseline_idx] * self.ms
            bY = self.signal.baselineY[baseline_idx]

            self.signal_panel.baseline_data.setData(bX, bY)
        else:
            self.signal_panel.baseline_data.setData()

        if self.signal.show_apd_threshold:

            sig_idx = self.x * self.signal.span_X + self.y
            indices, thresh = self.signal.get_apd_threshold()

            tX = indices[sig_idx] * self.ms
            tY = [thresh for t in tX]

            self.signal_panel.apd_data.setData(tX, tY)
        else:
            self.signal_panel.apd_data.setData()

    def ms_changed(self):
        self.ms = self.signal_panel.ms_per_frame.value()
        self.xVals = np.arange(0, self.ms * self.signal.span_T, self.ms)
        print("updated ms:", self.ms)
        self.update_signal_plot()

    @loading_popup
    def signal_transform(
        self,
        transform: Literal[
            "spatial_average", "time_average", "trim", "normalize", "reset", "invert"
        ],
    ):
        # Calls a transform function within the signal item
        if transform == "spatial_average":
            sigma = self.settings.child("Spatial Average").child("Sigma").value()
            radius = self.settings.child("Spatial Average").child("Radius").value()
            mode = self.settings.child("Spatial Average").child("Mode").value()
            self.signal.perform_average(
                type="spatial", sig=sigma, rad=radius, mode=mode
            )
            self.signal.normalize()

        elif transform == "time_average":
            sigma = self.settings.child("Time Average").child("Sigma").value()
            radius = self.settings.child("Time Average").child("Radius").value()
            mode = self.settings.child("Time Average").child("Mode").value()
            self.signal.perform_average(type="time", sig=sigma, rad=radius, mode=mode)
            self.signal.normalize()

        elif transform == "trim":
            left = int(self.settings.child("Trim Parameters").child("Left").value() / self.ms)
            right = int(self.settings.child("Trim Parameters").child("Right").value() / self.ms)
            self.signal.trim_data(startTrim=left, endTrim=right)
            self.signal.normalize()

        elif transform == "normalize":
            self.signal.normalize()

        elif transform == "reset":
            self.signal.reset_data()
            self.signal.normalize()

        elif transform == "invert":
            self.signal.invert_data()
            self.signal.normalize()

        self.update_signal_plot()
        self.position_tab.update_data()

    def calculate_baseline_drift(
        self, action: Literal["calculate", "confirm", "reset"]
    ):
        period = int(self.settings.child("Baseline Drift").child("Period Len").value() / self.ms)
        prominence = self.settings.child("Baseline Drift").child("Prominence").value()
        threshold = self.settings.child("Baseline Drift").child("Threshold").value()
        alternans = self.settings.child("Baseline Drift").child("Alternans").value()

        if action == "calculate":
            self.signal.calc_baseline(period, threshold, prominence, alternans)

            self.signal_panel.baseline_drift.enable_confirm_buttons()
            self.signal.show_baseline = True
        else:
            if action == "confirm":
                self.signal.remove_baseline_drift()
                self.signal.normalize()

            self.signal.reset_baseline()
            self.signal.show_baseline = False

            self.signal_panel.baseline_drift.disable_confirm_buttons()
            
        self.update_signal_plot()

    def calculate_apd(self, action: Literal["calculate", "confirm", "reset"]):

        threshold = self.settings.child("APD Parameters").child("Threshold").value()

        if action == "calculate":
            self.signal.calc_apd_di_threshold(threshold)
            
            self.signal_panel.apd.enable_confirm_buttons()

            self.signal.show_apd_threshold = True
        else:
            if action == "confirm":
                self.signal.calc_apd_di()
                #self.signal_panel.spatialPlotApdDi.setVisible(True)
                #self.signal_panel.spatialPlotApdDi.setEnabled(True)
                #self.signal_panel.spatialPlotApdDi.setText("APD/DI Plots")
            else:
                self.signal.reset_apd_di()

            self.signal.show_apd_threshold = False

            self.signal_panel.apd.disable_confirm_buttons()

        self.update_signal_plot()

    def plot_apds(self):
        apd = self.signal.get_spatial_apds() * self.ms
        di = self.signal.get_spatial_dis() * self.ms
        self.apd_spatial_plot = SpatialPlotWindow(
            self, apd, di, self.signal.apdIndicators
        )
        self.apd_spatial_plot.show()

    def create_stacking_window(self):
        start = int(self.settings.child("Stacking Parameters").child("Start Time").value() / self.ms)
        end = int(self.settings.child("Stacking Parameters").child("End Time (Optional)").value() / self.ms)
        beats = int(self.settings.child("Stacking Parameters").child("# of Beats").value())
        alternans = self.settings.child("Stacking Parameters").child("Alternans").value()
        image = self.signal.transformed_data[0]
        # DO STACKING
        print("Stacking", beats, "beats")
        stack = self.signal.perform_stacking(start, end, beats, alternans)
        self.stacking_window = StackingWindow(self, image, stack, self.xVals[0 : len(stack)])
        self.stacking_window.show()

    def create_isochrome_window(self):
        self.isochrome_window = IsochromeWindow(self)
        self.isochrome_window.show()
        
    def perform_FFT(self):
        print("FFT")
        fft_frames = self.signal.perform_fft()
        self.fft_window = FFTWindow(fft_frames)
        self.fft_window.show()

class PopupWindow(QInputDialog):
    def __init__(self):
        QInputDialog.__init__(self)


class SpatialPlotWindow(QMainWindow):
    def __init__(self, parent, apdData=None, diData=None, flags=None):
        QMainWindow.__init__(self)
        self.parent = parent
        self.x1 = self.y1 = self.x2 = self.y2 = 64
        self.data = [apdData, diData]
        self.flags = flags
        apd_mode = 0
        di_mode = 1
        # Create viewer tabs
        self.APD_view_tab = SpatialPlotView(self, apd_mode)
        self.DI_view_tab = SpatialPlotView(self, di_mode)
        self.APD_DI_view_tab = ScatterPlotView(self)

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.APD_view_tab, "Spatial APDs")
        self.image_tabs.addTab(self.DI_view_tab, "Spatial DIs")
        self.image_tabs.addTab(self.APD_DI_view_tab, "APD v.s. DI")
        self.image_tabs.setMinimumWidth(380)
        self.image_tabs.setMinimumHeight(500)

        # Create Signal Views
        self.APD_signal_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False)
        # set up axes
        leftAxis: pg.AxisItem = self.APD_signal_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.APD_signal_tab.plot.getPlotItem().getAxis(
            "bottom"
        )
        leftAxis.setLabel(text="Action Potential Duration (ms)")
        bottomAxis.setLabel(text="Linear Space (px)")
        # self.DI_signal_tab = SignalPanel(self, False)
        self.APD_DI_tab = ScatterPanel(self)

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.APD_signal_tab, "APD v.s. Linear Space")
        # self.signal_tabs.addTab(self.DI_signal_tab, "DI v.s. Linear Space")
        self.signal_tabs.addTab(self.APD_DI_tab, "APD v.s. DI")

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_tabs)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.signal_dock = QDockWidget("Signal View", self)
        self.image_dock = QDockWidget("Image View", self)

        self.signal_dock.setWidget(self.signal_tabs)
        self.image_dock.setWidget(self.image_tabs)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
        self.image_dock.resize(400, 1000)
        self.setLayout(layout)

    def update_graph(self, coords, beatNum):
        img = self.data[0][beatNum + 1]
        data = []
        for coord in coords:
            data.append(img[coord[0]][coord[1]])
        self.APD_signal_tab.signal_data.setData(data)

    def update_signal_value(self, evt, idx=None):
        return


class StackingWindow(QMainWindow):
    def __init__(self, parent, img_data, stack_data, xVals):
        super().__init__()
        self.parent = parent
        self.ms = self.parent.ms
        self.img_data = img_data
        self.data = stack_data
        self.xVals = xVals

        # Create viewer tabs
        self.image_tab = StackingPositionView(
            self, img_data
        )  # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Image")
        self.image_tabs.setMinimumWidth(380)
        self.image_tabs.setMinimumHeight(500)
        
        # Create Signal Views
        self.signal_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False)

        # set up axes
        leftAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Periodic Voltage Average")
        bottomAxis.setLabel(text="Time (ms)")

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.signal_tab, "Stack")

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_tabs)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.signal_dock = QDockWidget("Signal View", self)
        self.image_dock = QDockWidget("Image View", self)

        self.signal_dock.setWidget(self.signal_tabs)
        self.image_dock.setWidget(self.image_tabs)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
        self.image_dock.resize(400, 1000)
        self.setLayout(layout)

        self.x = 64
        self.y = 64
        self.update_signal_plot()

    def update_signal_plot(self):
        self.signal_tab.signal_data.setData(
            x=self.xVals, y=self.data[:, self.y, self.x]
        )

    def update_signal_value(self, evt, idx=None):
        return
    
class FFTWindow(QMainWindow):
    def __init__(self, fftData):
        QMainWindow.__init__(self)
        self.data = fftData
        self.img_data = np.argmax(fftData, axis=0)

        # Create viewer tabs
        self.image_tab = FFTPositionView(self, self.img_data) # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Peak Frequency")
        self.image_tabs.setMinimumWidth(380)
        self.image_tabs.setMinimumHeight(500)

        # Create Signal Views
        self.signal_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False)
        
        # set up axes
        leftAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis('left')
        bottomAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis('bottom')
        leftAxis.setLabel(text= "Spectral Density")
        bottomAxis.setLabel(text= "Frequency (kHz)")

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.signal_tab, "FFT")
        
        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_tabs)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.signal_dock = QDockWidget("Signal View", self)
        self.image_dock = QDockWidget("Image View", self)
        
        self.signal_dock.setWidget(self.signal_tabs)
        self.image_dock.setWidget(self.image_tabs)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
        self.image_dock.resize(400, 1000)
        self.setLayout(layout)
        
        self.x = 64
        self.y = 64
        self.update_signal_plot()
        
    def update_signal_plot(self):
        self.signal_tab.signal_data.setData(self.data[:, self.x, self.y])
        peak = self.img_data[self.x, self.y]
        self.signal_tab.apd_data.setData(x = [peak], y = [self.data[peak, self.x, self.y]])
 
    def update_signal_value(self, evt, idx=None):
        return


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    # signals = load_cascade_file("2011-08-23_Exp000_Rec112_Cam1-Blue.dat", None)

    # signal = signals[0]

    # viewer = CardiacMap(signal)

    # viewer.show()

    main_window = CardiacMap()
    main_window.show()

    sys.exit(app.exec())
