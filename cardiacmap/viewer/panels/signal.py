import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction)

from cardiacmap.viewer.components import ParameterButton

class SignalPanel(QWidget):

    def __init__(self, parent, toolbar = True):

        super().__init__(parent=parent)

        self.parent = parent

        self.resize(1000, self.height())

        if toolbar: self.init_transform_toolbar()

        self.plot = pg.PlotWidget()
        self.signal_data: pg.PlotDataItem = self.plot.plot(symbol='o', symbolSize=0)
        self.signal_data.scatter.setData(tip=self.point_hover_tooltip)
        
        self.baseline_data: pg.PlotDataItem = self.plot.plot(pen=pg.mkPen('g'), symbol='o')
        self.apd_data: pg.PlotDataItem = self.plot.plot(pen=pg.mkPen('r'), symbol='o')

        layout = QVBoxLayout()
        if toolbar: 
            layout.addWidget(self.transform_bar)
            layout.addWidget(self.plotting_bar)
        layout.addWidget(self.plot)
        
        self.setLayout(layout)

    def init_transform_toolbar(self):
        self.transform_bar = QToolBar()
        self.plotting_bar = QToolBar()
        
        reset = QAction("Reset", self)
        invert = QAction("Invert", self)

        self.stacking = ParameterButton("Stacking", self.parent.stacking_params) 
        time_average = ParameterButton("Time Average", self.parent.time_params)
        spatial_average = ParameterButton("Spatial Average", self.parent.spatial_params)
        trim = ParameterButton("Trim", self.parent.trim_params)
        
        
        self.confirm_baseline_drift = QAction("Confirm")
        self.confirm_baseline_drift.setDisabled(True)
        self.reset_baseline_drift = QAction("Reset")
        self.reset_baseline_drift.setDisabled(True)
        self.baseline_drift = ParameterButton("Calculate Baseline Drift", self.parent.baseline_params, actions=[self.confirm_baseline_drift, self.reset_baseline_drift])
        
        self.confirm_apd = QAction("Confirm")
        self.confirm_apd.setDisabled(True)
        self.reset_apd = QAction("Reset")
        self.reset_apd.setDisabled(True)
        self.apd = ParameterButton("Calculate APD / DI", self.parent.apd_params, actions=[self.confirm_apd, self.reset_apd])
        
        self.spatialPlotApdDi = QAction("Spatial Plot", self)
        self.spatialPlotApdDi.setDisabled(True)
        self.spatialPlotApdDi.setVisible(False)
        
        self.show_points = QCheckBox()
        self.show_points.setChecked(False)
        self.show_points.stateChanged.connect(self.toggle_points)
        self.show_points.stateChanged.connect(self.parent.update_signal_plot)
         
        reset.triggered.connect(partial(self.parent.signal_transform, transform="reset"))
        invert.triggered.connect(partial(self.parent.signal_transform, transform="invert"))
        spatial_average.pressed.connect(partial(self.parent.signal_transform, transform="spatial_average"))
        time_average.pressed.connect(partial(self.parent.signal_transform, transform="time_average"))
        trim.pressed.connect(partial(self.parent.signal_transform, transform="trim"))
        
        self.spatialPlotApdDi.triggered.connect(self.parent.plot_apd_spatial)
        self.stacking.pressed.connect(self.parent.perform_stacking)

        self.baseline_drift.pressed.connect(partial(self.parent.calculate_baseline_drift, action="calculate"))
        self.confirm_baseline_drift.triggered.connect(partial(self.parent.calculate_baseline_drift, action="confirm"))
        self.reset_baseline_drift.triggered.connect(partial(self.parent.calculate_baseline_drift, action="reset"))

        self.apd.pressed.connect(partial(self.parent.calculate_apd, action="calculate"))
        self.confirm_apd.triggered.connect(partial(self.parent.calculate_apd, action="confirm"))
        self.reset_apd.triggered.connect(partial(self.parent.calculate_apd, action="reset"))

        self.transform_bar.addAction(reset)
        self.transform_bar.addAction(invert)
        self.transform_bar.addWidget(trim)
        self.transform_bar.addWidget(time_average)
        self.transform_bar.addWidget(spatial_average)
        self.transform_bar.addWidget(self.baseline_drift)
        self.transform_bar.addWidget(self.apd)
        self.plotting_bar.addWidget(self.stacking)
        self.plotting_bar.addAction(self.spatialPlotApdDi)
        self.plotting_bar.addWidget(QLabel("    Show Data Points: "))
        self.plotting_bar.addWidget(self.show_points)

        self.transform_bar.setStyleSheet("QToolButton:!hover {color:black;}")
        self.plotting_bar.setStyleSheet("QToolButton:!hover {color:black;}")
        
    def toggle_points(self):
        """Toggles size of signal_data.scatter points"""
        if self.show_points.isChecked():           
            # show
            self.signal_data.setSymbolSize(10)
            # make signal hoverable
            self.signal_data.scatter.setData(hoverable=True)
        else:          
            # hide
            self.signal_data.setSymbolSize(0)
            # make signal unhoverable
            self.signal_data.scatter.setData(hoverable=False)

    def point_hover_tooltip(self, x, y, data):
        """Called by signal_data.scatter when hovering over a point"""
        tooltip = "x: " + str(x) + "\ny:" + str(y)
        #print(tooltip)
        return tooltip
            
