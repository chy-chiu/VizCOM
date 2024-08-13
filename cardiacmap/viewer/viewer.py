import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget)

from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.data import CascadeSignal
from cardiacmap.viewer.panels import PositionView, MetadataPanel, SpatialPlotView, SignalPanel, StackingPositionView, AnnotateView

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


class ImageSignalViewer(QMainWindow):

    def __init__(self, signal: CascadeSignal):

        super().__init__()

        self.resize(1200, 600)

        self.signal = signal
        self.x = 0
        self.y = 0
        
        self.setStyleSheet(TITLE_STYLE)
        # Create settings param
        # TODO: Refactor parameter creation to settings or something
        stacking_params = [
            {"name": "Start Frame", "type": "int", "value": 0, "limits": (0, 100000)},
            {"name": "# of Beats", "type": "int", "value": 10, "limits": (0, 30)},
            {"name": "Alternans", "type": "bool", "value": False,},
            {"name": "End Frame (Optional)", "type": "int", "value": signal.span_T, "limits": (0, signal.span_T)},
        ]
        spatial_params = [
            {"name": "Sigma", "type": "int", "value": 8, "limits": (0, 100)},
            {"name": "Radius", "type": "int", "value": 6, "limits": (0, 100)},
            {"name": "Mode", "type": "list", "value": "Gaussian", "limits": ["Gaussian", "Uniform"]},
        ]

        time_params = [
            {"name": "Sigma", "type": "int", "value": 4, "limits": (0, 100)},
            {"name": "Radius", "type": "int", "value": 3, "limits": (0, 100)},
            {"name": "Mode", "type": "list", "value": "Gaussian", "limits": ["Gaussian", "Uniform"]},
        ]

        trim_params = [
            {"name": "Left", "type": "int", "value": 100, "limits": (0, 100000)},
            {"name": "Right", "type": "int", "value": 100, "limits": (0, 100000)},
        ]

        drift_params = [
            {"name": "Method", "type": "list", "value": "Period", "limits": ["Period"]},
            {"name": "Alternans (Period)", "type": "bool", "value": False,},
            {"name": "Period", "type": "int", "value": 50, "limits": (0, 1000)},
            {"name": "Threshold", "type": "float", "value": 0.5, "limits": (0, 1000)},
        ]

        apd_params = [
            {"name": "Threshold", "type": "float", "value": 0.5, "limits": (0, 1000)},
        ]

        self.stacking_params = Parameter.create(name="Stacking Parameters", type="group", children=stacking_params)
        self.trim_params = Parameter.create(name="Trim Parameters", type="group", children=trim_params)
        self.spatial_params = Parameter.create(name="Spatial Average", type="group", children=spatial_params)
        self.time_params = Parameter.create(name="Time Average", type="group", children=time_params)
        self.baseline_params = Parameter.create(name="Baseline Drift", type="group", children=drift_params)
        self.apd_params = Parameter.create(name="Baseline Drift", type="group", children=apd_params)
        self.params_parent = Parameter.create(name="Parameters", type="group", children=[self.spatial_params, self.time_params, self.trim_params, self.baseline_params])

        self.metadata_panel = MetadataPanel(signal, self)

        # Create Signal View
        self.signal_panel = SignalPanel(self)

        # Create viewer tabs
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


        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_panel)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.signal_dock = QDockWidget("Signal View", self)
        self.image_dock = QDockWidget("Image View", self)
        self.metadata_dock = QDockWidget()
        
        self.signal_dock.setWidget(self.signal_panel)
        self.image_dock.setWidget(self.image_tabs)
        self.metadata_dock.setWidget(self.metadata_panel)
        self.metadata_dock.setFloating(False)

        self.setCentralWidget(self.metadata_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
        self.image_dock.resize(400, 1000)
        self.setLayout(layout)

        self.signal.normalize()
        self.update_signal_plot()

    def update_signal_value(self, evt, idx=None):

        if self.signal_panel.signal_marker:
            if not idx:
                idx = int(self.signal_panel.signal_marker.getXPos())
            self.metadata_panel.frame_index.setText(str(idx))
            self.metadata_panel.signal_value.setText(f"{self.signal_panel.signal_data.getData()[1][idx]:.3f}")

    def update_signal_plot(self):

        signal_data = self.signal.transformed_data[:, self.x, self.y]
        self.signal_panel.signal_data.setData(signal_data)
        self.metadata_panel.img_position.setText(f"{self.x}, {self.y}")

        self.update_signal_value(None, idx=self.signal_panel.frame_idx)

        if self.signal.show_baseline:
            baseline_idx = self.x * self.signal.span_X + self.y

            bX = self.signal.baselineX[baseline_idx]
            bY = self.signal.baselineY[baseline_idx]

            self.signal_panel.baseline_data.setData(bX, bY)
        else:
            self.signal_panel.baseline_data.setData()

        if self.signal.show_apd_threshold:
            
            sig_idx = self.x * self.signal.span_X + self.y
            indices, thresh = self.signal.get_apd_threshold()

            tX = indices[sig_idx]
            tY = [thresh for t in tX]

            self.signal_panel.apd_data.setData(tX, tY)
        else:
            self.signal_panel.apd_data.setData()


    def signal_transform(self, transform: Literal["spatial_average", "time_average", "trim", "normalize", "reset", "invert"]):
        # Calls a transform function within the signal item

        if transform == "spatial_average":
            sigma = self.spatial_params.child('Sigma').value()
            radius = self.spatial_params.child('Radius').value()
            mode = self.spatial_params.child('Mode').value()
            self.signal.perform_average(type="spatial", sig=sigma, rad=radius, mode=mode)
            self.signal.normalize()

        elif transform == "time_average":
            sigma = self.time_params.child('Sigma').value()
            radius = self.time_params.child('Radius').value()
            mode = self.time_params.child('Mode').value()
            self.signal.perform_average(type="time", sig=sigma, rad=radius, mode=mode)
            self.signal.normalize()

        elif transform == "trim":
            left = self.trim_params.child('Left').value()
            right = self.trim_params.child('Right').value()
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

    def calculate_baseline_drift(self, action: Literal["calculate", "confirm", "reset"]):

        method = self.baseline_params.child("Method").value()
        period = self.baseline_params.child("Period").value()
        threshold = self.baseline_params.child("Threshold").value()
        alternans = self.baseline_params.child("Alternans (Period)").value()

        if action == "calculate":
            if method == "Period":
                self.signal.calc_baseline(method, period, alternans)
            elif method == "Threshold":
                self.signal.calc_baseline(method, threshold)

            self.signal_panel.confirm_baseline_drift.setEnabled(True)
            self.signal_panel.reset_baseline_drift.setEnabled(True)
            
            self.signal.show_baseline = True
        else:
            if action == "confirm":
                self.signal.remove_baseline_drift()
                self.signal.normalize()


            self.signal.reset_baseline()
            self.signal.show_baseline = False

            self.signal_panel.confirm_baseline_drift.setEnabled(False)
            self.signal_panel.reset_baseline_drift.setEnabled(False)
            
        self.update_signal_plot()

    def calculate_apd(self, action: Literal["calculate", "confirm", "reset"]):

        threshold = self.apd_params.child("Threshold").value()
        
        if action == "calculate":
            self.signal.calc_apd_di_threshold(threshold)

            self.signal_panel.confirm_apd.setEnabled(True)
            self.signal_panel.reset_apd.setEnabled(True)
            
            self.signal.show_apd_threshold = True
        else:
            if action == "confirm":
                self.signal.calc_apd_di()
                self.signal_panel.spatialPlotApdDi.setVisible(True)
                self.signal_panel.spatialPlotApdDi.setEnabled(True)
            else:
                self.signal.reset_apd_di()
                
            self.signal.show_apd_threshold = False

            self.signal_panel.confirm_apd.setEnabled(False)
            self.signal_panel.reset_apd.setEnabled(False)
            
        self.update_signal_plot()
        
    def plot_apd_spatial(self):
        apd = self.signal.get_spatial_apds()
        di = self.signal.get_spatial_dis()
        #print(np.array(self.signal.dis).shape)
        self.apd_spatial_plot = SpatialPlotWindow(self, apd, di)
        self.apd_spatial_plot.show()
        
    def perform_stacking(self):
        start = int(self.stacking_params.child("Start Frame").value())
        end = int(self.stacking_params.child("End Frame (Optional)").value())
        beats = int(self.stacking_params.child("# of Beats").value())
        alternans = self.stacking_params.child("Alternans").value()

        image = self.signal.transformed_data[0]
        # DO STACKING
        print("Stacking", beats, "beats")
        stack = self.signal.perform_stacking(start, end, beats, alternans)
        self.stacking_window = StackingWindow(image, stack)
        self.stacking_window.show()

class CardiacMapWindow(QMainWindow):
    # This is the main window that allows you to open a new widget etc.
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CardiacMap v0.0.5")
        self.setGeometry(100, 100, 1080, 720)

        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False)
        self.setMenuBar(self.menu_bar)

        self.file_menu = self.menu_bar.addMenu("File")
        self.load_voltage_action = QAction("Load Voltage Data", self)
        self.load_voltage_action.triggered.connect(
            partial(self.create_viewer, calcium_mode=False)
        )
        self.load_calcium_action = QAction("Load Voltage / Calcium Data", self)
        self.load_calcium_action.triggered.connect(
            partial(self.create_viewer, calcium_mode=True)
        )

        self.file_menu.addAction(self.load_voltage_action)
        self.file_menu.addAction(self.load_calcium_action)

        self.docks = []

    def largeFilePopUp(self, tLen, maxFrames):
        print("Max Possible Frames:", maxFrames)
        self.filePopup = PopupWindow()
        start = self.filePopup.getInt(
            self, 
            "File Too Large", 
            "Enter Start Frame (0, " + str(tLen) + "):",
            minValue=0, 
            maxValue=tLen
        )[0]
        
        if start + maxFrames >= tLen:
            maxInput = tLen
        else:
            maxInput = start + maxFrames
            
        end = self.filePopup.getInt(
            self,
            "File Too Large",
            "Enter End Frame (" + str(start+1) + ", " + str(maxInput) + "):",
            minValue=start + 1,
            maxValue=tLen,
        )[0]

        return start, end

    def create_viewer(self, signal=None, calcium_mode=False):

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
                    viewer = ImageSignalViewer(signal)

                    dock = QDockWidget(filename + suffix, self)

                    dock.setWidget(viewer)
                    # dock.setFixedSize(IMAGE_SIZE * 3.05, IMAGE_SIZE * 1.1)
                    self.addDockWidget(Qt.RightDockWidgetArea, dock)
                    self.docks.append(dock)

            else:
                signal = signals[0]

                viewer = ImageSignalViewer(signal)

                dock = QDockWidget(filename, self)

                dock.setWidget(viewer)
                # dock.setFixedSize(IMAGE_SIZE * 3.05, IMAGE_SIZE * 1.1)
                self.addDockWidget(Qt.RightDockWidgetArea, dock)
                self.docks.append(dock)

class PopupWindow(QInputDialog):
    def __init__(self):
        QInputDialog.__init__(self)

class SpatialPlotWindow(QMainWindow):
    def __init__(self, parent, apdData = None, diData = None):
        QMainWindow.__init__(self)
        self.parent = parent
        self.x1 = self.y1 = self.x2 = self.y2 = 0
        self.data = [apdData, diData]
        apd_mode = 0
        di_mode = 1
        # Create viewer tabs
        self.APD_tab = SpatialPlotView(self, apd_mode)
        self.DI_tab = SpatialPlotView(self, di_mode)

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.APD_tab, "APD Plot")
        self.image_tabs.addTab(self.DI_tab, "DI Plot")

        # Create Signal Views
        self.APD_signal_tab = SignalPanel(self, toolbar=False, signal_marker=False)
        #self.DI_signal_tab = SignalPanel(self, False)

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.APD_signal_tab, "APD v.s. Linear Space")
        #self.signal_tabs.addTab(self.DI_signal_tab, "DI v.s. Linear Space")
        
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
        img = self.data[0][beatNum+1]
        data = []
        for coord in coords:
            data.append(img[coord[0]][coord[1]])
        self.APD_signal_tab.signal_data.setData(data)  

    def update_signal_value(self, evt, idx=None):
        return
 
class StackingWindow(QMainWindow):
    def __init__(self, img_data, stack_data):
        QMainWindow.__init__(self)
        self.img_data = img_data
        self.data = stack_data

        # Create viewer tabs
        self.image_tab = StackingPositionView(self, img_data) # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Image")

        # Create Signal Views
        self.signal_tab = SignalPanel(self, toolbar=False, signal_marker=False)

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
        
        self.x = 0
        self.y = 0
        self.update_signal_plot()
        
    def update_signal_plot(self):
        self.signal_tab.signal_data.setData(self.data[:, self.y, self.x])
 
    def update_signal_value(self, evt, idx=None):
        return


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    signals = load_cascade_file("2011-08-23_Exp000_Rec112_Cam1-Blue.dat", None)
        
    signal = signals[0]

    viewer = ImageSignalViewer(signal)

    viewer.show()

    # main_window = CardiacMapWindow()
    # main_window.show()

    sys.exit(app.exec())
