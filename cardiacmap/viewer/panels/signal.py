import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
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
    QWidgetAction,
)

from cardiacmap.viewer.colorpalette import ColorPaletteButton
from cardiacmap.viewer.components import (
    ParameterButton,
    ParameterConfirmButton,
    Spinbox,
)

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            QToolButton {
                border: 1px solid #C0C0C0;
                border-radius: 5px;
                background: transparent;
            }
            QToolButton:hover {
                background: #D3D3D3;
            }
            """


class SignalPanel(QWidget):

    def __init__(self, parent, toolbar=True, signal_marker=True, ms_conversion=True):

        super().__init__(parent=parent)

        self.parent = parent

        self.resize(1000, self.height())
        
        self.convertToMS = ms_conversion
        self.allow_signal_marker = signal_marker

        self.plot = pg.PlotWidget()
        self.plot_item = self.plot.getPlotItem()

        # set up pens
        self.sig_pen = pg.mkPen("w")
        self.apd_pen = pg.mkPen("r")
        self.base_pen = pg.mkPen("g")
        self.colors = dict(
            {
                "signal": self.sig_pen.color(),
                "apd": self.apd_pen.color(),
                "baseline": self.base_pen.color(),
                "background": self.plot.backgroundBrush().color(),
            }
        )
        if toolbar: 
             self.init_toolbars()
        self.init_plotting_bar()
        # set up axes
        leftAxis: pg.AxisItem = self.plot_item.getAxis("left")
        bottomAxis: pg.AxisItem = self.plot_item.getAxis("bottom")
        leftAxis.setLabel(text="Normalized Voltage")
        bottomAxis.setLabel(text="Time (ms)")

        # set up data items
        self.signal_data: pg.PlotDataItem = self.plot.plot(
            pen=self.sig_pen, symbol="o", symbolSize=0
        )
        self.signal_data.scatter.setData(tip=self.point_hover_tooltip)

        self.baseline_data: pg.PlotDataItem = self.plot.plot(
            pen=self.base_pen, symbol="o"
        )
        self.baseline_data.scatter.setData(tip=self.point_hover_tooltip, hoverable=True)

        self.apd_data: pg.PlotDataItem = self.plot.plot(pen=self.apd_pen, symbol="o")
        self.apd_data.scatter.setData(tip=self.point_hover_tooltip, hoverable=True)

        # set up signal marker
        self.signal_marker = pg.InfiniteLine(angle=90, movable=True)
        self.signal_marker.sigClicked.connect(self.toggle_signal_follow)
        self.signal_marker_toggle = False
        self.signal_marker.setVisible(signal_marker)
        self.signal_marker.sigPositionChanged.connect(self.parent.update_signal_value)

        self.frame_idx = 0

        self.plot.addItem(self.signal_marker, ignoreBounds=True)

        layout = QVBoxLayout()
        if toolbar:
            layout.addWidget(self.transform_bar)
        layout.addWidget(self.plotting_bar)
        layout.addWidget(self.plot)

        self.setLayout(layout)

        self.plot.scene().sigMouseMoved.connect(self.mouseMoved)

    def init_toolbars(self):

        # TODO: Fix this code below lulz
        self.transform_bar = QToolBar()

        self.transform_bar.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )

        self.reset = QAction(text="Reset", parent=self)
        self.reset.setToolTip("Reset Signal")

        invert = QAction("Invert", self)

        # self.stacking = ParameterButton("Stacking", self.parent.settings.child("Stacking Parameters"))
        time_average = ParameterButton(
            "Time Average", self.parent.settings.child("Time Average")
        )
        spatial_average = ParameterButton(
            "Spatial Average", self.parent.settings.child("Spatial Average")
        )
        trim = ParameterButton("Trim", self.parent.settings.child("Trim Parameters"))

        # Baseline drift button
        self.baseline_drift = ParameterConfirmButton(
            "Remove Baseline Drift", self.parent.settings.child("Baseline Drift")
        )
        # APD Button
        self.apd = ParameterConfirmButton(
            "Calculate APD / DI", self.parent.settings.child("APD Parameters")
        )

        # Display data points
        self.show_points = QCheckBox()
        self.show_points.setChecked(False)
        self.show_points.stateChanged.connect(self.toggle_points)
        self.show_points.stateChanged.connect(self.parent.update_signal_plot)

        self.show_signal_marker = QCheckBox()
        self.show_signal_marker.setChecked(True)
        self.show_signal_marker.stateChanged.connect(self.toggle_signal)
        self.show_signal_marker.stateChanged.connect(self.parent.update_signal_plot)

        # frame to ms conversion
        self.ms_per_frame = Spinbox(1, 500, 2)
        self.ms_per_frame.valueChanged.connect(self.parent.ms_changed)

        # QActions triggers - connect
        self.reset.triggered.connect(
            partial(self.parent.signal_transform, transform="reset")
        )
        invert.triggered.connect(
            partial(self.parent.signal_transform, transform="invert")
        )
        spatial_average.pressed.connect(
            partial(self.parent.signal_transform, transform="spatial_average")
        )
        time_average.pressed.connect(
            partial(self.parent.signal_transform, transform="time_average")
        )
        trim.pressed.connect(partial(self.parent.signal_transform, transform="trim"))

        self.baseline_drift.action.pressed.connect(
            partial(self.parent.calculate_baseline_drift, action="calculate")
        )
        self.baseline_drift.confirm.pressed.connect(
            partial(self.parent.calculate_baseline_drift, action="confirm")
        )
        self.baseline_drift.reset.pressed.connect(
            partial(self.parent.calculate_baseline_drift, action="reset")
        )

        self.apd.action.pressed.connect(
            partial(self.parent.calculate_apd, action="calculate")
        )
        self.apd.confirm.pressed.connect(
            partial(self.parent.calculate_apd, action="confirm")
        )
        self.apd.reset.pressed.connect(
            partial(self.parent.calculate_apd, action="reset")
        )

        self.transform_bar.addAction(self.reset)
        self.transform_bar.addAction(invert)
        self.transform_bar.addWidget(trim)
        self.transform_bar.addWidget(time_average)
        self.transform_bar.addWidget(spatial_average)
        self.transform_bar.addWidget(self.baseline_drift)
        self.transform_bar.addWidget(self.apd)

        self.plotting_bar.addWidget(QLabel("Show Data Points: "))
        self.plotting_bar.addWidget(self.show_points)
        self.plotting_bar.addSeparator()
        self.plotting_bar.addWidget(QLabel("Show Signal Marker:"))
        self.plotting_bar.addWidget(self.show_signal_marker)
        self.plotting_bar.addSeparator()
        self.plotting_bar.addWidget(self.ms_per_frame)
        self.plotting_bar.addWidget(QLabel("ms per frame"))

        # colors
        self.color_button = ColorPaletteButton(self)
        self.plotting_bar.addAction(self.color_button)

        self.transform_bar.setStyleSheet(QTOOLBAR_STYLE)
        
    def init_plotting_bar(self):
        self.plotting_bar = QToolBar()
        
        # Display data points
        self.show_points = QCheckBox()
        self.show_points.setChecked(False)
        self.show_points.stateChanged.connect(self.toggle_points)
        self.show_points.stateChanged.connect(self.parent.update_signal_plot)
        self.plotting_bar.addWidget(QLabel("Show Data Points: "))
        self.plotting_bar.addWidget(self.show_points)
        
        # signal marker
        if self.allow_signal_marker:
            self.show_signal_marker = QCheckBox()
            self.show_signal_marker.setChecked(True)
            self.show_signal_marker.stateChanged.connect(self.toggle_signal)
            self.show_signal_marker.stateChanged.connect(self.parent.update_signal_plot)
            self.plotting_bar.addSeparator()
            self.plotting_bar.addWidget(QLabel("Show Signal Marker:"))
            self.plotting_bar.addWidget(self.show_signal_marker)
            
        # frame to ms conversion
        if self.convertToMS:
            self.ms_per_frame = Spinbox(1, 500, 2)
            self.ms_per_frame.valueChanged.connect(self.parent.ms_changed)
            self.plotting_bar.addSeparator()
            self.plotting_bar.addWidget(self.ms_per_frame)
            self.plotting_bar.addWidget(QLabel("ms per frame"))
            
                
        # colors
        self.color_button = ColorPaletteButton(self)
        self.plotting_bar.addSeparator()
        self.plotting_bar.addAction(self.color_button)
        
        self.plotting_bar.setStyleSheet(QTOOLBAR_STYLE)

    def mouseMoved(self, evt):
        if not self.signal_marker.isVisible():
            return
        pos = evt
        if self.plot.sceneBoundingRect().contains(pos):
            mousePoint = self.plot_item.vb.mapSceneToView(pos)
            signal_y = self.signal_data.getData()[1]
            idx = int(mousePoint.x() / self.parent.ms)
            if idx > 0 and idx < len(signal_y):
                # print(signal_y[idx])
                if self.signal_marker_toggle:
                    self.update_signal_marker(idx)

    def update_signal_marker(self, idx):
        self.frame_idx = idx
        self.signal_marker.setX(idx * self.parent.ms)
        self.parent.update_signal_value(None, idx=idx)

    def update_pens(self):
        for c in self.colors:
            if c == "signal":
                self.sig_pen.setColor(self.colors[c])
            elif c == "baseline":
                self.base_pen.setColor(self.colors[c])
            elif c == "apd":
                self.apd_pen.setColor(self.colors[c])
            elif c == "background":
                self.plot.setBackground(self.colors[c])
        self.parent.update_signal_plot()

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

    def toggle_signal_follow(self):
        self.signal_marker_toggle = not self.signal_marker_toggle

    def toggle_signal(self):
        self.signal_marker.setVisible(self.show_signal_marker.isChecked())
        self.signal_marker_toggle = False

    def point_hover_tooltip(self, x, y, data, xLabel="x: ", yLabel="y: "):
        """Called by signal_panel when hovering over a point"""
        tooltip = xLabel + str(int(x)) + "\n" + yLabel + f"{y:.3f}"
        return tooltip
