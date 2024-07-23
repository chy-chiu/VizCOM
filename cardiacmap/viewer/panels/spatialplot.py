import os
from random import Random
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
import matplotlib.pyplot as plt

from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget, QComboBox, QCheckBox)

from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.signal import CascadeSignal
from cardiacmap.viewer.panels.settings import ParameterWidget
from typing import Literal

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

class SpatialPlotView(QWidget):

    def __init__(self, parent, mode):

        super().__init__(parent=parent)

        self.parent=parent
        self.mode = mode
        
        self.init_image_view()
        self.init_player_bar()
        

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.player_bar)
        layout.addWidget(self.colormap_bar)
        self.setLayout(layout)
        
        self.update_data()
        # self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        self.plot = DraggablePlot(self.update_position)
        self.image_view = pg.ImageView(view=self.plot)
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-2, IMAGE_SIZE + 2), yRange=(-2, IMAGE_SIZE + 2)
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        #self.image_view.ui.histogram.hide()
        self.image_view.ui.histogram.item.sigLevelChangeFinished.connect(self.update_spinbox_values)
        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable Red Dot
        # Add posiiton marker
        self.position_marker = pg.ScatterPlotItem(
            pos=[[0, 0]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )

        self.image_view.getView().addItem(self.position_marker)
        
        return self.image_view

    def init_player_bar(self):
        self.player_bar = QToolBar()
        self.colormap_bar = QToolBar()

        self.frameIdx = QtWidgets.QSpinBox()
        self.frameIdx.setFixedWidth(60)
        self.frameIdx.setMaximum(len(self.parent.data[self.mode][0]) - 1)
        self.frameIdx.setValue(0)
        self.frameIdx.setSingleStep(1)
        self.frameIdx.setStyleSheet(SPINBOX_STYLE)
        self.frameIdx.valueChanged.connect(self.jump_frames)
        
        self.diff_min = QtWidgets.QSpinBox()
        self.diff_min.setFixedWidth(60)
        self.diff_min.setMinimum(-100000)
        self.diff_min.setMaximum(100000)
        self.diff_min.setValue(np.min(np.diff(self.parent.data[self.mode])))
        self.diff_min.setStyleSheet(SPINBOX_STYLE)
        self.diff_min.valueChanged.connect(self.update_data)
        
        self.zero_val = QtWidgets.QSpinBox()
        self.zero_val.setFixedWidth(60)
        self.zero_val.setMinimum(-100000)
        self.zero_val.setMaximum(100000)
        self.zero_val.setValue(0)
        self.zero_val.setStyleSheet(SPINBOX_STYLE)
        self.zero_val.valueChanged.connect(self.update_data)
        
        self.max_val = QtWidgets.QSpinBox()
        self.max_val.setFixedWidth(60)
        self.max_val.setMinimum(-100000)
        self.max_val.setMaximum(100000)
        self.max_val.setValue(np.max(self.parent.data[self.mode]))
        self.max_val.setStyleSheet(SPINBOX_STYLE)
        self.max_val.valueChanged.connect(self.update_data)
        
        self.beatNumber = self.frameIdx.value()
        
        self.player_bar.addWidget(QLabel("   Beat #: "))
        self.player_bar.addWidget(self.frameIdx)
        
        self.player_bar.addWidget(QLabel("   Minimum: "))
        self.diff_min_spinbox = self.player_bar.addWidget(self.diff_min)
        self.min_spinbox = self.player_bar.addWidget(self.zero_val)
        
        self.player_bar.addWidget(QLabel("   Maximum: "))
        self.player_bar.addWidget(self.max_val)

        self.show_diff = QCheckBox()
        self.show_diff.setChecked(False)
        self.show_diff.checkStateChanged.connect(self.update_data)

        self.colormap_bar.addWidget(QLabel("   Plot Difference: "))
        self.colormap_bar.addWidget(self.show_diff)

    def update_spinbox_values(self):
        levels = self.image_view.ui.histogram.item.getLevels()
        
        self.max_val.setValue((levels[1]))
        if self.show_diff.isChecked():
            self.diff_min.setValue(levels[0])
        else:
            self.zero_val.setValue(levels[0])
        
        
    def update_ui(self):
        if self.show_diff.isChecked():
            self.diff_min_spinbox.setVisible(True)
            self.min_spinbox.setVisible(False)
            print(self.diff_min.value(), self.max_val.value())
            #self.image_view.ui.histogram.item.setHistogramRange(self.diff_min.value(), self.max_val.value())
        else:
            self.diff_min_spinbox.setVisible(False)
            self.min_spinbox.setVisible(True)
            print(self.zero_val.value(), self.max_val.value())
            #self.image_view.ui.histogram.item.setHistogramRange(self.zero_val.value(), self.max_val.value())
    
    def jump_frames(self):
        if self.beatNumber < self.frameIdx.value():
            self.image_view.jumpFrames(1) 
        else:
            self.image_view.jumpFrames(-1)
            
        self.beatNumber = self.frameIdx.value()
        self.update_data()
        
    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)
        self.parent.x = x
        self.parent.y = y
        self.parent.update_graph()

    def update_data(self):
        self.update_ui()
        
        if self.show_diff.isChecked():
            color_range = (self.diff_min.value(), self.max_val.value())
            self.frameIdx.setMaximum(len(self.parent.data[self.mode][0]) - 2)
            self.image_view.setImage(
                    np.diff(self.parent.data[self.mode][self.frameIdx.value()]), levels=color_range, autoRange=False
            )
        else:
            color_range = (self.zero_val.value(), self.max_val.value())
            self.frameIdx.setMaximum(len(self.parent.data[self.mode][0]) - 1)
            self.image_view.setImage(
                    self.parent.data[self.mode][self.frameIdx.value()], levels=color_range, autoRange=False
            )
        
        # print(self.frameIdx.value())
        # print(self.parent.data[self.mode].shape)
        
        self.image_view.update()