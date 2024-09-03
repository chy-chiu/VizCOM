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


class StackingWindow(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.settings = parent.settings
        self.ms = self.parent.ms
        self.setWindowTitle("Stacking")

        #        image, stack,

        # Create Menu
        self.init_options()

        # Create viewer tabs
        self.image_tab = StackingPositionView(
            self, self.parent.signal.transformed_data[0]
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
        self.signal_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False, settings=self.settings)

        # set up axes
        leftAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.signal_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Periodic Voltage Average")
        bottomAxis.setLabel(text="Time (ms)")

        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.signal_tab, "Stack")

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
        self.setCentralWidget(self.splitter)

        self.x = 64
        self.y = 64

        self.stack = None
        self.resize(self.parent.init_width, self.parent.init_height)
        # self.update_signal_plot()

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options = QToolBar()
        self.actions_bar = QToolBar()

        self.beats = Spinbox(
            min=1,
            max=100,
            val=self.settings.child("Stacking Parameters").child("# of Beats").value(),
            step=1,
            min_width=50,
            max_width=50,
        )

        max_time = int(len(self.parent.signal.transformed_data) * self.ms)
        self.start_time = Spinbox(
            min=0,
            max=max_time,
            val=self.settings.child("Stacking Parameters").child("Start Time").value(),
            step=1,
            min_width=60,
            max_width=60,
        )
        self.end_time = Spinbox(
            min=0,
            max=max_time,
            val=self.settings.child("Stacking Parameters")
            .child("End Time (Optional)")
            .value(),
            step=1,
            min_width=60,
            max_width=60,
        )

        self.alternans = QCheckBox()
        self.alternans.setChecked(
            self.settings.child("Stacking Parameters").child("Alternans").value()
        )

        self.options.addWidget(QLabel("Start Time: "))
        self.options.addWidget(self.start_time)
        self.options.addWidget(QLabel("End Time: "))
        self.options.addWidget(self.end_time)

        self.actions_bar.addWidget(QLabel("# Beats: "))
        self.actions_bar.addWidget(self.beats)
        self.actions_bar.addWidget(QLabel("Alternans: "))
        self.actions_bar.addWidget(self.alternans)

        self.options.setStyleSheet(QTOOLBAR_STYLE)
        self.actions_bar.setStyleSheet(QTOOLBAR_STYLE)


        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.perform_stacking)
        self.actions_bar.addWidget(self.confirm)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.options_widget.setLayout(layout)

    @loading_popup
    def perform_stacking(self, update_progress=None):
        start = int(self.start_time.value())
        end = int(self.end_time.value()
        )
        beats = int(self.beats.value())
        alternans = self.alternans.isChecked()

        self.stack = self.parent.signal.perform_stacking(start, end, beats, alternans, update_progress)
        self.xVals = self.parent.xVals[0 : len(self.stack)]
        self.update_signal_plot()

    def update_signal_plot(self):
        if self.stack is not None:
            self.signal_tab.signal_data.setData(
                x=self.xVals, y=self.stack[:, self.y, self.x]
            )

    def update_signal_value(self, evt, idx=None):
        return
