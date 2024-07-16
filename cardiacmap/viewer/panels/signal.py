from ast import Param
import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
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
        self.signal_data: pg.PlotDataItem = self.plot.plot()
        self.baseline_data: pg.PlotDataItem = self.plot.plot(pen=pg.mkPen('g'))
        self.apd_data: pg.PlotDataItem = self.plot.plot(pen=pg.mkPen('r'))

        layout = QVBoxLayout()
        if toolbar: layout.addWidget(self.button_bar)
        layout.addWidget(self.plot)
        
        self.setLayout(layout)

    def init_transform_toolbar(self):
        self.button_bar = QToolBar()
        
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

        self.button_bar.addAction(reset)
        self.button_bar.addAction(invert)
        self.button_bar.addWidget(trim)
        self.button_bar.addWidget(time_average)
        self.button_bar.addWidget(spatial_average)
        self.button_bar.addWidget(self.baseline_drift)
        self.button_bar.addWidget(self.apd)
        self.button_bar.addAction(self.spatialPlotApdDi)
        self.button_bar.addWidget(self.stacking)

        self.button_bar.setStyleSheet("QToolButton:!hover {color:black;}")
