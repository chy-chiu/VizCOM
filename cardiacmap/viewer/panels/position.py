from genericpath import samefile
import os
import sys
from functools import partial
from typing import Literal

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGradient
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

from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.data import CascadeSignal
from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.panels.settings import ParameterWidget

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
INITIAL_POSITION = (64, 64)
POSITION_MARKER_SIZE = 5
VIEWPORT_MARGIN = 2


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


class PositionView(QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent

        self.init_image_view()
        self.init_player_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.player_bar)
        layout.addWidget(self.colormap_bar)
        self.setLayout(layout)
        
        self.init_colormap()

        self.update_data()

        # self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        view = DraggablePlot(self.update_position)
        self.image_view = pg.ImageView(view=view)
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        #self.image_view.ui.histogram.hide()

        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable posiiton marker
        self.position_marker = pg.ScatterPlotItem(
            pos=[INITIAL_POSITION],
            size=POSITION_MARKER_SIZE,
            pen=pg.mkPen("r"),
            brush=pg.mkBrush("r"),
        )

        self.image_view.getView().addItem(self.position_marker)

        self.image_view.sigTimeChanged.connect(
            self.parent.signal_panel.update_signal_marker
        )

        return self.image_view

    def init_player_bar(self):
        self.player_bar = QToolBar()
        self.colormap_bar = QToolBar()

        play_button = QAction("⏯", self)
        forward_button = QAction("⏭", self)
        back_button = QAction("⏮", self)

        self.skiprate = Spinbox(
            min=1, max=10000, val=10, min_width=60, max_width=60, step=10
        )

        play_button.triggered.connect(self.image_view.togglePause)
        forward_button.triggered.connect(partial(self.jump_frames, forward=True))
        back_button.triggered.connect(partial(self.jump_frames, forward=False))

        # Need to update it for the first time first
        self.framerate = Spinbox(
            min=1, max=10000, val=50, min_width=60, max_width=60, step=10
        )
        self.update_framerate()
        self.framerate.valueChanged.connect(self.update_framerate)

        self.player_bar.addAction(play_button)
        self.player_bar.addAction(back_button)
        self.player_bar.addAction(forward_button)
        self.player_bar.addWidget(QLabel("   FPS: "))
        self.player_bar.addWidget(self.framerate)
        self.player_bar.addWidget(QLabel("   Skip Frames: "))
        self.player_bar.addWidget(self.skiprate)

        self.normalize = QComboBox()
        self.normalize.addItems(["Base", "Transformed"])
        self.normalize.currentTextChanged.connect(self.update_data)

        self.colormap = QComboBox()
        self.colormap.addItems(["nipy_spectral", "gray", "hsv", "viridis", "plasma"])
        self.colormap.currentTextChanged.connect(self.update_data)

        self.show_marker = QCheckBox()
        self.show_marker.setChecked(True)
        self.show_marker.stateChanged.connect(self.toggle_marker)

        self.colormap_bar.addWidget(QLabel("Data: "))
        self.colormap_bar.addWidget(self.normalize)
        self.colormap_bar.addWidget(QLabel("   Colormap: "))
        self.colormap_bar.addWidget(self.colormap)
        self.colormap_bar.addWidget(QLabel("   Marker: "))
        self.colormap_bar.addWidget(self.show_marker)

    def update_framerate(self):
        framerate = self.framerate.value()
        self.image_view.playRate = framerate

    def jump_frames(self, forward=True):
        skip_frames = int(self.skiprate.value() * self.parent.ms)
        (
            self.image_view.jumpFrames(skip_frames)
            if forward
            else self.image_view.jumpFrames(-skip_frames)
        )

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.parent.x = x
        self.parent.y = y
        self.parent.update_signal_plot()
        
    def init_colormap(self):
        cmap_name = self.colormap.currentText() or "nipy_spectral"
        self.cmap = pg.colormap.get(cmap_name, source="matplotlib")
        
    def update_colormap(self):
        print("colormap update")

    def update_data(self):
        mode = self.normalize.currentText() or "Base"
        
        if mode == "Base":
            self.image_view.setImage(
                self.parent.signal.image_data, autoLevels=False, autoRange=False
            )
        elif mode == "Transformed":
            self.image_view.setImage(
                self.parent.signal.transformed_data, autoLevels=False, autoRange=False
            )
            
        self.image_view.setColorMap(self.cmap)

        if hasattr(self.parent, "annotate_tab"):

            self.parent.annotate_tab.img_view.setImage(self.image_view.image)
            self.parent.annotate_tab.img_view.setColorMap(self.cmap)

    def update_marker(self, x, y):
        self.position_marker.setData(pos=[[x, y]])

    def toggle_marker(self):
        (
            self.position_marker.setVisible(True)
            if self.show_marker.isChecked()
            else self.position_marker.setVisible(False)
        )
