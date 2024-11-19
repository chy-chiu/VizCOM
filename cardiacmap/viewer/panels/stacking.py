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


class StackingPositionView(QWidget):

    def __init__(self, parent, image_data):

        super().__init__(parent=parent)

        self.parent = parent
        self.image_data = image_data

        self.init_image_view()
        self.init_player_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.px_bar)
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
        #self.image_view.ui.histogram.hide()

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
        
        self.px_bar = QToolBar()
        self.x_box = Spinbox(
            min=0, max=127, val=64, min_width=50, max_width=50, step=1
        )
        self.y_box = Spinbox(
            min=0, max=127, val=64, min_width=50, max_width=50, step=1
        )
            
        self.x_box.valueChanged.connect(self.update_position_boxes)
        self.y_box.valueChanged.connect(self.update_position_boxes)
        
        self.px_bar.addWidget(QLabel("   X: "))
        self.px_bar.addWidget(self.x_box)
        self.px_bar.addWidget(QLabel("   Y: "))
        self.px_bar.addWidget(self.y_box)

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.parent.x = x
        self.parent.y = y
        self.parent.update_signal_plot()
        self.update_position_boxes(val=None)
            
    def update_position_boxes(self, val=None):
        #print("Update Boxes val", val)
        if val is not None:
            # set position to box values
            x = int(self.x_box.value())
            y = int(self.y_box.value())
            self.update_marker(x, y)
            self.parent.x = x
            self.parent.y = y
            self.parent.update_signal_plot()
        else:
            # set box values to position
            self.x_box.blockSignals(True) # block signals to avoid
            self.y_box.blockSignals(True) # circular callback
            self.x_box.setValue(self.parent.x)
            self.y_box.setValue(self.parent.y)
            self.x_box.blockSignals(False)
            self.y_box.blockSignals(False)

    def update_marker(self, x, y):
        self.position_marker.setData(pos=[[x, y]])

    def toggle_marker(self):
        (
            self.position_marker.setVisible(True)
            if self.show_marker.isChecked()
            else self.position_marker.setVisible(False)
        )


class StackingWindow(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.settings = parent.settings
        self.ms = parent.ms
        self.mask = parent.signal.mask
        self.setWindowTitle("Stacking")
        
        self.x = 64
        self.y = 64

        #        image, stack,

        # Create Menu
        self.init_options()

        # Create viewer tabs
        self.image_tab = StackingPositionView(
            self, self.parent.signal.transformed_data[0] * self.mask
        )  # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Image")

        # TODO: To refactor this later
        self.image_tabs.setMinimumWidth(300)
        self.image_tabs.setMinimumHeight(200)
        
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.options_widget)
        self.image_layout.addWidget(self.image_tabs)

        self.image_widget = QWidget(layout=self.image_layout)

        # Create Signal Views
        self.stack_tab = SignalPanel(self, settings=self.settings)
        
        # Preview Panel
        self.line_count = 0
        self.lines = None
        self.preview_tab = SignalPanel(self, settings=self.settings)
        self.add_line(self.preview_tab)
        self.add_line(self.preview_tab)

        # set up axes
        leftAxis: pg.AxisItem = self.stack_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.stack_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Periodic Voltage Average")
        bottomAxis.setLabel(text="Time (ms)")

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.preview_tab, "Preview")
        self.signal_tabs.addTab(self.stack_tab, "Stack")

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

        self.stack = None
        self.resize(self.parent.init_width, self.parent.init_height)
        self.update_signal_plot()

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options1 = QToolBar()
        self.options2 = QToolBar()
        self.options3 = QToolBar()
        self.actions_bar = QToolBar()

        self.beats = Spinbox(
            min=1,
            max=100,
            val=self.settings.child("Stacking Parameters").child("# of Beats").value(),
            step=1,
            min_width=50,
            max_width=50,
        )
        self.beats.sigValueChanged.connect(self.update_signal_plot)

        max_time = int(len(self.parent.signal.transformed_data) * self.ms)
        self.start_time = Spinbox(
            min=0,
            max=max_time,
            val=self.settings.child("Stacking Parameters").child("Start Time").value(),
            step=1,
            min_width=50,
            max_width=50,
        )
        self.start_time.sigValueChanged.connect(self.update_signal_plot)
        
        self.end_time = Spinbox(
            min=0,
            max=max_time,
            val=max_time,
            step=1,
            min_width=50,
            max_width=50,
        )
        self.end_time.sigValueChanged.connect(self.update_signal_plot)
        
        self.min_width = Spinbox(
            min=self.ms,
            max=len(self.parent.signal.transformed_data),
            val=self.ms,
            step=1,
            min_width=50,
            max_width=50,
        )
        self.min_width.sigValueChanged.connect(self.update_signal_plot)
        
        self.offset = Spinbox(
            min=0,
            max=1,
            val=.1,
            step=.05,
            min_width=50,
            max_width=50,
        )
        
        self.offset.sigValueChanged.connect(self.update_signal_plot)
        
        self.sensitivity = Spinbox(
            min=.01,
            max=1,
            val=.7,
            step=.05,
            min_width=50,
            max_width=50,
        )
        self.sensitivity.sigValueChanged.connect(self.update_signal_plot)

        self.alternans = QCheckBox()
        self.alternans.setChecked(
            self.settings.child("Stacking Parameters").child("Alternans").value()
        )
        self.alternans.checkStateChanged.connect(self.update_signal_plot)

        self.options1.addWidget(QLabel(" Start Time:"))
        self.options1.addWidget(self.start_time)
        self.options1.addWidget(QLabel(" End Time:"))
        self.options1.addWidget(self.end_time)

        self.options2.addWidget(QLabel(" # of Beats:"))
        self.options2.addWidget(self.beats)
        self.options2.addWidget(QLabel(" Alternans:"))
        self.options2.addWidget(self.alternans)
        
        self.options3.addWidget(QLabel(" Min Slice Width:"))
        self.options3.addWidget(self.min_width)
        self.options3.addWidget(QLabel(" Offset:"))
        self.options3.addWidget(self.offset)
        self.options3.addWidget(QLabel(" Sensitivity:"))
        self.options3.addWidget(self.sensitivity)

        self.options1.setStyleSheet(QTOOLBAR_STYLE)
        self.options2.setStyleSheet(QTOOLBAR_STYLE)
        self.options3.setStyleSheet(QTOOLBAR_STYLE)
        self.actions_bar.setStyleSheet(QTOOLBAR_STYLE)


        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.perform_stacking)
        self.actions_bar.addWidget(self.confirm)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options1)
        layout.addSpacing(5)
        layout.addWidget(self.options2)
        layout.addSpacing(5)
        layout.addWidget(self.options3)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.options_widget.setLayout(layout)

    @loading_popup
    def perform_stacking(self, update_progress=None):
        start = int(self.start_time.value() // self.ms)
        end = int(self.end_time.value() // self.ms)
        beats = int(self.beats.value())
        offset = self.offset.value()
        distance = int(self.min_width.value() // self.ms)
        alternans = self.alternans.isChecked()
        mask = self.mask

        self.stack = self.parent.signal.perform_stacking(start, end, beats, distance, offset, alternans, mask, update_progress)
        self.xVals = self.parent.xVals[0 : len(self.stack)]
        self.update_signal_plot()

    def update_signal_plot(self):
        if self.stack is not None:
            self.stack_tab.signal_data.setData(
                x=self.xVals, y=self.stack[:, self.x, self.y] # stacking results are transposed
            )
            
        start = int(self.start_time.value()//self.ms)
        end = int(self.end_time.value()//self.ms)

        self.preview = self.parent.signal.transformed_data[start:end, self.y, self.x]
        self.preview_tab.signal_data.setData(x=np.arange(len(self.preview))* int(self.ms), y=self.preview)
        self.update_lines()

    def update_signal_value(self, evt, idx=None):
        return
    
    def update_lines(self):
        # generate proper number of lines for selected number of beats
        while self.line_count != int(self.beats.value() + 1):
            if self.line_count < int(self.beats.value() + 1):
                self.add_line(self.preview_tab)
            elif self.line_count > int(self.beats.value() + 1):
                self.remove_line(self.preview_tab)

        derivative = NormalizeData(np.gradient(self.preview))
        prominence = 1 - self.sensitivity.value()
        
        if int(self.min_width.value()) != 0:
            peaks = find_peaks(derivative, distance=(self.min_width.value() + 1)//int(self.ms), prominence=prominence)[0]
        else:
            peaks = find_peaks(derivative, prominence=prominence)[0]
        if peaks is None:
            return
        offset = self.offset.value()
        if self.alternans.isChecked():
            peaks = peaks[::2]  # take only even peaks
            offset // 2
        periodLen = np.mean(np.diff(peaks))
        peaks -= int(periodLen * offset)
        
        # trim peaks
        while len(peaks) > 0 and peaks[0] <= 0:
            peaks = peaks[1:]
        peaks = peaks[:self.line_count]
        
        # set lines to stacking indices
        for i in range(self.line_count):
            if len(peaks) > i:
                self.lines[i].setPos((int(peaks[i] * self.ms), 0))
            else:
                self.lines[i].setPos((int(peaks[0] * self.ms), 0))
            
    def add_line(self, panel: SignalPanel):
        line = pg.InfiniteLine(movable = False)
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
            
def NormalizeData(data):
    data = data - data.min(axis=0)
    return data / data.max(axis=0)
