from math import floor

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
from cardiacmap.model.data import CascadeSignal
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

class SpatialDragPlot(pg.PlotItem):
    # Position Plot used by APD/DI v.s. Space Plots
    def __init__(self, parent, sCallback, eCallback):
        super().__init__()
        self.sCallback = sCallback
        self.eCallback = eCallback
        self.parent = parent

    def mouseDragEvent(self, event: MouseDragEvent):
        if self.parent.hide_line.isChecked():
            return event.pos()
        
        if event.isStart():
            pos = self.vb.mapSceneToView(event.scenePos())
            self.sCallback(int(pos.x()), int(pos.y()))
            
        elif event.isFinish():
            pos = self.vb.mapSceneToView(event.scenePos())
            self.eCallback(int(pos.x()), int(pos.y()))
            
            # get coordinates that intersect the line
            xDiff = self.parent.x2 - self.parent.x1
            yDiff = self.parent.y2 - self.parent.y1
            maxDiff = max(abs(xDiff), abs(yDiff))
            coords = []
            for i in range(maxDiff):
                x = self.parent.x1 + i * xDiff/maxDiff
                y = self.parent.y1 + i * yDiff/maxDiff
                coords.append((floor(x), floor(y)))
            coords, idxs = np.unique(coords, axis=0, return_index=True)
            coords = coords[np.argsort(idxs)]
            self.parent.spatial_coords = coords
            self.parent.update_graph()
        else:
            pos = self.vb.mapSceneToView(event.scenePos())
            self.eCallback(int(pos.x()), int(pos.y()))
        return event.pos()
    
    def mouseClickEvent(self, event: MouseDragEvent):
        pass

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
        
        self.spatial_coords = None
        
        self.update_data()
        # self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        self.plot = SpatialDragPlot(self, self.line_start, self.line_end)
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

        # Draggable red dots
        self.startPoint = pg.ScatterPlotItem(
            pos=[[32, 32]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )
        self.endPoint = pg.ScatterPlotItem(
            pos=[[64, 64]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )
        
        self.line = pg.PlotCurveItem(x=[32, 64], y=[32, 64])
        self.line_visable = True

        self.image_view.getView().addItem(self.startPoint)
        self.image_view.getView().addItem(self.endPoint)
        self.image_view.getView().addItem(self.line)
        
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
        self.frameIdx.valueChanged.connect(self.update_graph)
        
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
        self.show_diff.stateChanged.connect(self.update_data)

        self.colormap_bar.addWidget(QLabel("   Plot Difference: "))
        self.colormap_bar.addWidget(self.show_diff)
        
        self.hide_line = QCheckBox()
        self.hide_line.setChecked(False)
        self.hide_line.checkStateChanged.connect(self.update_data)

        self.colormap_bar.addWidget(QLabel("   Hide Line: "))
        self.colormap_bar.addWidget(self.hide_line)

    def update_spinbox_values(self):
        """Called When Range Changes"""
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])
        
        # set numerical vals to their visual levels
        self.max_val.setValue((levels[1]))
        if self.show_diff.isChecked():
            self.diff_min.setValue(levels[0])
        else:
            self.zero_val.setValue(levels[0])
        
        
    def update_ui(self):
        # show proper min
        if self.show_diff.isChecked():
            self.diff_min_spinbox.setVisible(True)
            self.min_spinbox.setVisible(False)
        else:
            self.diff_min_spinbox.setVisible(False)
            self.min_spinbox.setVisible(True)
            
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])
    
    def jump_frames(self):
        if self.beatNumber < self.frameIdx.value():
            self.image_view.jumpFrames(1) 
        else:
            self.image_view.jumpFrames(-1)
            
        self.beatNumber = self.frameIdx.value()
        self.update_data()
        
    def line_start(self, x, y):
        y = np.clip(y, 0, IMAGE_SIZE)
        x = np.clip(x, 0, IMAGE_SIZE)
        self.x1 = x
        self.y1 = y
        self.startPoint.setData(pos=[[x, y]])
        #print("Start", self.x1, self.y1)
    
    def line_end(self, x, y):
        y = np.clip(y, 0, IMAGE_SIZE)
        x = np.clip(x, 0, IMAGE_SIZE)
        self.x2 = x
        self.y2 = y
        self.endPoint.setData(pos=[[x, y]])
        self.line.setData(x=[self.x1, self.x2], y=[self.y1, self.y2])
        #print("End", self.x2, self.y2)

    def update_data(self):
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

        self.update_line()
        self.update_ui()
        self.image_view.update()
        
    def update_graph(self):
        if self.spatial_coords is not None and len(self.spatial_coords) >= 1:
            self.parent.update_graph(self.spatial_coords, self.frameIdx.value())
            
    def update_line(self):
        imgVw = self.image_view.getView()
        if self.hide_line.isChecked():
            if self.line_visable:
                # hide line
                imgVw.removeItem(self.line)
                imgVw.removeItem(self.startPoint)
                imgVw.removeItem(self.endPoint)
                self.line_visable = False
        else:
            if not self.line_visable:
                # plot line
                imgVw.addItem(self.line)
                imgVw.addItem(self.startPoint)
                imgVw.addItem(self.endPoint)
                self.line_visable = True