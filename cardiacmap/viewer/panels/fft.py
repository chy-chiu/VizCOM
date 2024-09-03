import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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
from scipy.signal import find_peaks
from cardiacmap.viewer.panels import SignalPanel
from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.utils import loading_popup

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

SPINBOX_STYLE = """QSpinBox
            {
                border: 1px solid;
            }

            QSpinBox::up-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                top: -5px;
                right: 0px;
            }

            QSpinBox::down-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                bottom: -5px;
                right: 0px;
            }"""

IMAGE_SIZE = 128


class DraggablePlot(pg.PlotItem):

    # Draggable PlotItem that takes in a callback function.
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def mouseClickEvent(self, event: MouseDragEvent):
        pos = self.vb.mapSceneToView(event.scenePos())

        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def mouseDragEvent(self, event: MouseDragEvent):

        pos = self.vb.mapSceneToView(event.scenePos())

        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def hoverEvent(self, event: HoverEvent):
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(Qt.MouseButton.LeftButton)


class FFTPositionView(QWidget):

    def __init__(self, parent, image_data):

        super().__init__(parent=parent)

        self.parent = parent
        self.image_data = image_data

        self.init_image_view()
        self.init_player_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        self.setLayout(layout)

        # self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        view = DraggablePlot(self.update_position)
        self.image_view = pg.ImageView(view=view)
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-2, IMAGE_SIZE + 2), yRange=(-2, IMAGE_SIZE + 2)
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        # self.image_view.ui.histogram.hide()
        self.image_view.ui.histogram.item.sigLevelChangeFinished.connect(
            self.update_spinbox_values
        )

        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # draw image
        self.image_view.setImage(self.image_data, autoLevels=True, autoRange=False)

        # Draggable Red Dot
        # Add posiiton marker
        self.position_marker = pg.ScatterPlotItem(
            pos=[[64, 64]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )

        self.image_view.getView().addItem(self.position_marker)

        return self.image_view

    def init_player_bar(self):
        self.show_marker = QCheckBox()
        self.show_marker.setChecked(True)
        self.show_marker.stateChanged.connect(self.toggle_marker)
        
    def update_image(self, img):
        colorLimits = (self.parent.min_val.value(), self.parent.max_val.value())
        self.image_data = img
        self.image_view.setImage(self.image_data, levels=colorLimits, autoRange=False)
        
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.parent.x = x
        self.parent.y = y
        self.parent.update_signal_plot()

    def update_marker(self, x, y):
        self.position_marker.setData(pos=[[x, y]])

    def toggle_marker(self):
        (
            self.position_marker.setVisible(True)
            if self.show_marker.isChecked()
            else self.position_marker.setVisible(False)
        )
        
    def update_spinbox_values(self):
        """Called When Range Changes"""
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])

        # set numerical vals to their visual levels
        self.parent.max_val.setValue((levels[1]))
        self.parent.min_val.setValue(levels[0])
        

class FFTWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self)
        self.data = []
        self.parent = parent
        self.ms = parent.ms
        self.settings = parent.settings
        self.img_data = parent.signal.transformed_data[0]
        
        self.setWindowTitle("FFT")
        
        # Create Menu
        self.init_options()

        # Create viewer tabs
        self.image_tab = FFTPositionView(
            self, self.img_data
        )  # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Peak Frequency")
        self.image_tabs.setMinimumWidth(380)
        self.image_tabs.setMinimumHeight(500)
        
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.options_widget)
        self.image_layout.addWidget(self.image_tabs)
        self.image_widget = QWidget(layout=self.image_layout)

        # Create Signal Views
        self.signal_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False, settings=self.settings)
        
        # set up axes
        leftAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Spectral Density")
        bottomAxis.setLabel(text="Frequency (kHz)")

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.signal_tab, "FFT")

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_widget)
        self.splitter.addWidget(self.signal_tabs)
        self.splitter.setSizes((500, 1500))

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        # self.signal_dock = QDockWidget("Signal View", self)
        # self.image_dock = QDockWidget("Image View", self)

        # self.signal_dock.setWidget(self.signal_tabs)
        # self.image_dock.setWidget(self.image_tabs)

        # self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
        # self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)
        # self.image_dock.resize(400, 1000)
        # self.setLayout(layout)
        self.setCentralWidget(self.splitter)

        self.x = 64
        self.y = 64
        self.update_signal_plot()

    def update_signal_plot(self):
        if len(self.data) > 0:    
            self.signal_tab.signal_data.setData(self.data[:, self.x, self.y])
            peak = self.img_data[self.x, self.y]
            self.signal_tab.apd_data.setData(x=[peak], y=[self.data[peak, self.x, self.y]])

    def update_signal_value(self, evt, idx=None):
        return

    def update_image(self):
        if len(self.data) > 0:
            self.img_data = np.argmax(self.data, axis=0)
            self.image_tab.update_image(self.img_data)
    
    def set_data(self, data):
        self.data = data
    
    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options = QToolBar()
        self.actions_bar = QToolBar()
        self.histogram_scale = QToolBar()

        max_time = int(len(self.parent.signal.transformed_data) * self.ms)
        self.start_time = Spinbox(
            min=0,
            max=max_time,
            val=self.settings.child("FFT Parameters").child("Start Time").value(),
            step=1,
            min_width=60,
            max_width=60,
        )
        self.end_time = Spinbox(
            min=0,
            max=max_time,
            val=max_time,
            step=1,
            min_width=60,
            max_width=60,
        )


        self.min_val = Spinbox(
            min=-100000,
            max=100000,
            val=-1,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.min_val.valueChanged.connect(self.update_image)

        self.max_val = Spinbox(
            min=-100000,
            max=100000,
            val=1,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.max_val.valueChanged.connect(self.update_image)
        
        self.options.addWidget(QLabel("Start Time: "))
        self.options.addWidget(self.start_time)
        self.options.addWidget(QLabel("End Time: "))
        self.options.addWidget(self.end_time)

        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.perform_stacking)
        self.actions_bar.addWidget(self.confirm)
        
        self.histogram_scale.addWidget(QLabel("Min: "))
        self.histogram_scale.addWidget(self.min_val)
        self.histogram_scale.addWidget(QLabel("Max: "))
        self.histogram_scale.addWidget(self.max_val)
        

        self.options.setStyleSheet(QTOOLBAR_STYLE)
        self.actions_bar.setStyleSheet(QTOOLBAR_STYLE)
        self.histogram_scale.setStyleSheet(QTOOLBAR_STYLE)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)
        layout.addSpacing(5)
        layout.addWidget(self.histogram_scale)

        self.options_widget.setLayout(layout)
        
    def perform_stacking(self):
        fft_frames = self.parent.signal.perform_fft()
        self.set_data(fft_frames)
        self.min_val.setValue(np.min(np.argmax(fft_frames, axis=0)))
        self.max_val.setValue(np.max(np.argmax(fft_frames, axis=0)))
        self.update_image()
        self.update_signal_plot()
        

