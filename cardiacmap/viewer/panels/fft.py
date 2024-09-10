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
        #self.image_view.view.enableAutoRange(enable=True)
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
        self.image_view.setImage(self.image_data, autoLevels=False, autoRange=False)

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
        
    def update_image(self):
        colorLimits = (self.parent.min_val.value(), self.parent.max_val.value())
        self.image_view.setImage(self.image_data, levels=colorLimits, autoRange=False)
        
        # scale histogram
        self.image_view.ui.histogram.item.setHistogramRange(colorLimits[0]-2, colorLimits[1])

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
        #self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])

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
        
        self.img_data = [parent.signal.transformed_data[0]]
        self.img_index = 0
        
        self.setWindowTitle("FFT")
        
        # Create Menu
        self.init_options()

        # Create viewer tabs
        self.image_tab = FFTPositionView(
            self, self.img_data[self.img_index]
        )  # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Preview")
        self.image_tabs.setMinimumWidth(380)
        self.image_tabs.setMinimumHeight(500)
        
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.options_widget)
        self.image_layout.addWidget(self.image_tabs)
        self.image_widget = QWidget(layout=self.image_layout)

        # FFT Panel
        self.fft_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False, settings=self.settings)
        # set up axes
        leftAxis: pg.AxisItem = self.fft_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.fft_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Normalized Power")
        bottomAxis.setLabel(text="Frequency", units='Hz')
        
        # Preview Panel
        self.line_count = 0
        self.lines = None
        self.preview_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False, settings=self.settings)
        self.add_line(self.preview_tab)
        self.add_line(self.preview_tab)
        self.update_lines()

        # set up axes        
        leftAxis: pg.AxisItem = self.preview_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.preview_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Normalized Voltage")
        bottomAxis.setLabel(text="Time (ms)")

        # add panels
        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.preview_tab, "Preview")
        self.signal_tabs.addTab(self.fft_tab, "FFT")

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_widget)
        self.splitter.addWidget(self.signal_tabs)
        self.splitter.setSizes((500, 1500))

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.setCentralWidget(self.splitter)

        self.x = 64
        self.y = 64
        self.update_signal_plot()

    def update_signal_plot(self):
        if len(self.data) > 0:    
            self.fft_tab.signal_data.setData(x=self.freqs[self.img_index], y=self.data[self.img_index][:, self.x, self.y])
            peak = self.img_data[self.x, self.y]
            self.fft_tab.apd_data.setData(x=[peak], y=[self.data[self.img_index][self.peakIdx[self.x, self.y], self.x, self.y]])
            
        self.preview_tab.signal_data.setData(
            x=np.arange(len(self.parent.signal.transformed_data[:, self.x, self.y])) * self.parent.ms, 
            y=self.parent.signal.transformed_data[:, self.x, self.y]
        )

    def update_signal_value(self, evt, idx=None):
        return

    def set_image(self, setRange = False):
        self.img_index = int(self.interval_num.value() - 1)
        
        if self.img_index >= len(self.data):
            self.img_index = len(self.data) - 1
            self.interval_num.setValue(self.img_index + 1)
            return
        
        if len(self.data) > 0:
            self.peakIdx = np.argmax(self.data[self.img_index], axis=0)
            self.img_data = self.freqs[self.img_index][self.peakIdx]
            self.image_tab.image_data = self.img_data
            self.image_tabs.setTabText(0, "Peak Frequency (" + 
                                       str(self.line_idxs[self.img_index] * self.ms) + 
                                       "-" + 
                                       str((self.line_idxs[self.img_index+1]-1) * self.ms) +
                                       "):")
            self.image_tab.update_image()
            
        self.update_signal_plot()
            
    def init_image(self, setRange = False):
        self.img_index = int(self.interval_num.value() - 1)
        if self.img_index >= len(self.data):
            self.img_index = len(self.data) - 1
            self.interval_num.setValue(self.img_index + 1)
        
        if len(self.data) > 0:
            self.peakIdx = np.argmax(self.data[self.img_index], axis=0)
            self.img_data = self.freqs[self.img_index][self.peakIdx]
            self.image_tab.image_data = self.img_data
            self.image_tabs.setTabText(0, "Peak Frequency (" + 
                                       str(self.line_idxs[self.img_index] * self.ms) + 
                                       "-" + 
                                       str((self.line_idxs[self.img_index+1]-1) * self.ms) +
                                       "):")
            self.image_tab.update_image()
            
            self.min_val.setValue(np.min(self.img_data))
            self.max_val.setValue(np.max(self.img_data))
    
    def set_data(self, data, freqs):
        self.data = data
        self.freqs = freqs
        
    def update_image(self):
        self.image_tab.update_image()
    
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
        self.start_time.valueChanged.connect(self.update_lines)
        self.end_time = Spinbox(
            min=0,
            max=max_time,
            val=max_time,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.end_time.valueChanged.connect(self.update_lines)

        self.min_val = Spinbox(
            min=-100000,
            max=100000,
            val=0,
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
        
        self.interval_num = Spinbox(
            min=1,
            max=20,
            val=1,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.interval_num.valueChanged.connect(self.set_image)
        
        self.subintervals = Spinbox(
            min=1,
            max=20,
            val=1,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.subintervals.valueChanged.connect(self.update_lines)
        
        self.options.addWidget(QLabel("Start Time: "))
        self.options.addWidget(self.start_time)
        self.options.addWidget(QLabel("End Time: "))
        self.options.addWidget(self.end_time)
        
        self.actions_bar.addWidget(QLabel("Subintervals: "))
        self.actions_bar.addWidget(self.subintervals)

        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.perform_fft)
        self.actions_bar.addWidget(self.confirm)
        
        self.histogram_scale.addWidget(QLabel("Min: "))
        self.histogram_scale.addWidget(self.min_val)
        self.histogram_scale.addWidget(QLabel("Max: "))
        self.histogram_scale.addWidget(self.max_val)
        self.histogram_scale.addWidget(QLabel("Interval #: "))
        self.histogram_scale.addWidget(self.interval_num)
        

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
        
    def update_lines(self):
        duration = self.end_time.value() - self.start_time.value()
        interval = duration // self.subintervals.value()
        timeVals = np.arange(self.subintervals.value() + 1) * interval + self.start_time.value()
        
        # generate proper number of lines for selected number of subintervals
        while self.line_count != len(timeVals):
            if self.line_count < len(timeVals):
                self.add_line(self.preview_tab)
            elif self.line_count > len(timeVals):
                self.remove_line(self.preview_tab)
        
        # set lines to be evenly placed over the selected time interval
        for i in range(self.line_count):
            self.lines[i].setPos((int(timeVals[i]), 0))
            
    def add_line(self, panel: SignalPanel):
        line = pg.InfiniteLine(movable = True)
        line.sigPositionChangeFinished.connect(self.set_fft_range)
        panel.plot.addItem(line)
        
        if self.lines is None:
            self.lines = np.array([line])
        else:
            self.lines = np.append(self.lines, line)
            
        self.line_count += 1
        
    def remove_line(self, panel: SignalPanel):
        if self.line_count > 0:
            self.line_count -= 1
            line = self.lines[-1]
            panel.plot.removeItem(line)
            self.lines = self.lines[:-1]
            
    def set_fft_range(self):
        minLineX = np.min([int(line.getPos()[0]) for line in self.lines])
        if minLineX != self.start_time.value():
            print("change min", self.start_time.value(), 'to', minLineX)
            self.start_time.setValue(minLineX)
            self.update_lines()
            
        maxLineX = np.max([int(line.getPos()[0]) for line in self.lines])
        if maxLineX != self.end_time.value():
            if maxLineX > (self.parent.signal.span_T * self.parent.ms):
                maxLineX = self.end_time.value()
            else:
                maxLineX = (maxLineX - minLineX) // self.subintervals.value() * self.subintervals.value() + minLineX
            print("change max", self.end_time.value(), 'to', maxLineX)
            self.end_time.setValue(maxLineX)
            self.update_lines()
        
    def perform_fft(self):
        ffts = []
        freqs = []
        self.line_idxs = [int(x.getPos()[0]//self.ms) for x in self.lines]
        for i in range(1, len(self.line_idxs)):
            start = self.line_idxs[i-1]
            end = self.line_idxs[i]-1
            print("FFT:", "start:", start, "end:", end)
            
            # do fft
            fft = self.parent.signal.perform_fft(start, end)
            # get sample frequencies with 'self.ms' sample spacing
            freq = np.fft.fftfreq(end - start, self.ms)
            # scale to hertz and cut in half
            freq = freq[:len(freq)//2] * 1000
            
            freqs.append(freq)
            ffts.append(fft)
            
        # startIdx = int(self.start_time.value()//self.ms)
        # endIdx = int(self.end_time.value()//self.ms)
        # fft_frames = self.parent.signal.perform_fft(startIdx, endIdx)
        
        # # get sample frequencies with 'self.ms' sample spacing
        # freqs = np.fft.fftfreq(endIdx - startIdx, self.ms)
        # # scale to hertz and cut in half
        # freqs = freqs[:len(freqs)//2] * 1000
        
        self.set_data(ffts, freqs)
        self.init_image()
        self.update_signal_plot()
        

