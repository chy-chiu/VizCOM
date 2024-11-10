import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QRgba64
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
    QSlider,
)

from cardiacmap.viewer.colorpalette import ColorPaletteButton
from cardiacmap.viewer.components import (
    ParameterButton,
    ParameterConfirmButton,
    Spinbox,
)
from cardiacmap.transforms.baseline_drift import FindPeaks

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

class SignalPlot(pg.PlotWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

    def mouseDoubleClickEvent(self, e):
        self.getPlotItem().enableAutoRange()

class SignalPanel(QWidget):

    def __init__(self, parent, main_signal = False, settings = None):

        super().__init__(parent=parent)

        self.parent = parent
        
        self.settings = settings

        self.resize(1000, self.height())
        
        self.mainSignal = main_signal

        self.plot = SignalPlot(self)
        self.plot_item = self.plot.getPlotItem()

        sig_c = self.settings.child("Signal Plot Colors").child("signal").value()
        apd_c = self.settings.child("Signal Plot Colors").child("apd").value()
        base_c = self.settings.child("Signal Plot Colors").child("baseline").value()
        pts_c = self.settings.child("Signal Plot Colors").child("points").value()
        bg_c = self.settings.child("Signal Plot Colors").child("background").value()
        
        self.colors = dict(
            {
                "signal": QColor(sig_c[0], sig_c[1], sig_c[2], a=255),
                "apd": QColor(apd_c[0], apd_c[1], apd_c[2], a=255),
                "baseline": QColor(base_c[0], base_c[1], base_c[2], a=255),
                "points": QColor(pts_c[0], pts_c[1], pts_c[2], a=255),
                "background": QColor(bg_c[0], bg_c[1], bg_c[2], a=255),
            }
        )
        # set up colors
        self.sig_pen = pg.mkPen(self.colors['signal'])
        self.apd_pen = pg.mkPen(self.colors['apd'])
        self.base_pen = pg.mkPen(self.colors['baseline'])
        self.pt_brush = pg.mkBrush(self.colors['points'])
        self.plot.setBackground(self.colors['background'])
        
        if self.mainSignal: 
             self.init_toolbars()
        self.init_plotting_bar()
        # TODO: To make this settable later
        font=QtGui.QFont()
        font.setPixelSize(16)
        # set up axes
        leftAxis: pg.AxisItem = self.plot_item.getAxis("left")
        bottomAxis: pg.AxisItem = self.plot_item.getAxis("bottom")
        leftAxis.setLabel(text="Normalized Voltage")
        bottomAxis.setLabel(text="Time (ms)")
        leftAxis.setTickFont(font)
        bottomAxis.setTickFont(font)
        leftAxis.label.setFont(font)
        bottomAxis.label.setFont(font)

        # set up data items
        self.signal_data: pg.PlotDataItem = self.plot.plot(
            pen=self.sig_pen, symbol="o", symbolSize=0
        )
        self.signal_data.scatter.setData(brush=self.pt_brush, tip=self.point_hover_tooltip)
        self.signal_data.setSymbolBrush(self.pt_brush)

        self.baseline_data: pg.PlotDataItem = self.plot.plot(
            pen=self.base_pen, symbol="o"
        )
        self.baseline_data.scatter.setData(brush=self.pt_brush, tip=self.point_hover_tooltip, hoverable=True)
        self.baseline_data.setSymbolBrush(self.pt_brush)
        
        self.apd_data: pg.PlotDataItem = self.plot.plot(pen=self.apd_pen, symbol="o")
        self.apd_data.scatter.setData(brush=self.pt_brush, tip=self.point_hover_tooltip, hoverable=True)
        self.apd_data.setSymbolBrush(self.pt_brush)

        self.start_range_marker = pg.InfiniteLine(angle=90, movable=True)
        self.end_range_marker = pg.InfiniteLine(angle=90, movable=True)
        
        self.start_range_marker.setPen(pg.mkPen("g"))
        self.end_range_marker.setPen(pg.mkPen("g"))

        
        # set up signal marker
        self.signal_marker = pg.InfiniteLine(angle=90, movable=True)
        self.signal_marker.sigClicked.connect(self.toggle_signal_follow)
        self.signal_marker_toggle = False
        self.signal_marker.setVisible(main_signal)
        self.signal_marker.sigPositionChanged.connect(self.parent.update_signal_value)

        self.frame_idx = 0

        self.plot.addItem(self.signal_marker, ignoreBounds=True)
        self.plot.addItem(self.start_range_marker, ignoreBounds=True)
        self.plot.addItem(self.end_range_marker, ignoreBounds=True)


        layout = QVBoxLayout()
        if self.mainSignal:
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

        self.undo = QAction(text="Undo", parent=self)
        self.undo.setToolTip("Undo Last Action")

        invert = QAction("Invert", self)

        # self.stacking = ParameterButton("Stacking", self.parent.settings.child("Stacking Parameters"))
        time_average = ParameterButton(
            "Time Average", self.settings.child("Time Average")
        )
        spatial_average = ParameterButton(
            "Spatial Average", self.settings.child("Spatial Average")
        )
        trim = ParameterButton("Trim", self.settings.child("Trim Parameters"))

        # Baseline drift button
        self.baseline_drift = ParameterConfirmButton(
            "Remove Baseline Drift", self.settings.child("Baseline Drift")
        )
        self.normalize_peaks = ParameterConfirmButton(
            "Normalize Peaks", self.settings.child("Baseline Drift")
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
        self.undo.triggered.connect(
            partial(self.parent.signal_transform, transform="undo")
        )

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
        
        self.normalize_peaks.action.pressed.connect(
            partial(self.parent.normalize_peaks, action="calculate")
        )
        self.normalize_peaks.confirm.pressed.connect(
            partial(self.parent.normalize_peaks, action="confirm")
        )
        self.normalize_peaks.reset.pressed.connect(
            partial(self.parent.normalize_peaks, action="reset")
        )

        self.transform_bar.addAction(self.reset)
        self.transform_bar.addAction(self.undo)
        self.transform_bar.addAction(invert)
        self.transform_bar.addWidget(trim)
        self.transform_bar.addWidget(time_average)
        self.transform_bar.addWidget(spatial_average)
        self.transform_bar.addWidget(self.baseline_drift)
        self.transform_bar.addWidget(self.normalize_peaks)

        # colors
        self.color_button = ColorPaletteButton(self)

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
        
        # Add sliders for start and end
        self.start_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_slider = QSlider(Qt.Orientation.Horizontal)

        if self.mainSignal:
            # signal marker
            self.show_signal_marker = QCheckBox()
            self.show_signal_marker.setChecked(True)
            self.show_signal_marker.stateChanged.connect(self.toggle_signal)
            self.show_signal_marker.stateChanged.connect(self.parent.update_signal_plot)

            self.show_range_marker = QCheckBox()
            self.show_range_marker.setChecked(True)
            self.show_range_marker.stateChanged.connect(self.toggle_range)
            self.show_range_marker.stateChanged.connect(self.parent.update_signal_plot)
            
            self.plotting_bar.addSeparator()
            self.plotting_bar.addWidget(QLabel("Signal Marker:"))
            self.plotting_bar.addWidget(self.show_signal_marker)
            self.plotting_bar.addWidget(QLabel("Range Marker:"))
            self.plotting_bar.addWidget(self.show_range_marker)


            # frame to ms conversion
            self.ms_per_frame = Spinbox(1, 500, 2)
            self.ms_per_frame.valueChanged.connect(self.parent.ms_changed)
            self.plotting_bar.addSeparator()
            self.plotting_bar.addWidget(self.ms_per_frame)
            self.plotting_bar.addWidget(QLabel("ms per frame"))
            
            self.start_slider.setRange(0, len(self.parent.signal.transformed_data))
            self.end_slider.setRange(0, len(self.parent.signal.transformed_data))

            # Set initial values
            self.start_slider.setValue(0)
            self.end_slider.setValue(len(self.parent.signal.transformed_data))

            # Add labels for start and end sliders
            self.start_frame_label = QLabel("Start Frame: 0")
            self.plotting_bar.addWidget(self.start_frame_label)
            self.plotting_bar.addWidget(self.start_slider)
            self.end_frame_label = QLabel(f"End Frame: {self.end_slider.value()}")
            self.plotting_bar.addWidget(self.end_frame_label)
            self.plotting_bar.addWidget(self.end_slider)
        
            # Connect sliders to update function
            self.start_slider.valueChanged.connect(self.update_slice_range)
            self.end_slider.valueChanged.connect(self.update_slice_range)

        # colors
        self.color_button = ColorPaletteButton(self)
        self.plotting_bar.addSeparator()
        self.plotting_bar.addAction(self.color_button)

        self.plotting_bar.setStyleSheet(QTOOLBAR_STYLE)    

    def update_slice_range(self):
        self.start_frame = self.start_slider.value()
        self.end_frame = self.end_slider.value()
        
        # Ensure start is always less than or equal to end
        if self.start_frame > self.end_frame:
            self.end_slider.setValue(self.start_frame)
            self.start_frame = self.end_frame

        self.start_frame_label.setText(f"Start Frame: {int(self.start_frame * self.parent.ms)}")
        self.end_frame_label.setText(f"End Frame: {int(self.end_frame * self.parent.ms)}")

        self.start_range_marker.setX(int(self.start_frame * self.parent.ms))
        self.end_range_marker.setX(int(self.end_frame * self.parent.ms))


        
    def signal_transform(self, transform, update_progress=None, start=None, end=None):
        # ... (existing code remains the same)

        if transform == "spatial_average":
            sigma = self.settings.child("Spatial Average").child("Sigma").value()
            radius = self.settings.child("Spatial Average").child("Radius").value()
            mode = self.settings.child("Spatial Average").child("Mode").value()
            self.signal.perform_average(
                type="spatial",
                sig=sigma,
                rad=radius,
                mode=mode,
                update_progress=update_progress,
                start=start,
                end=end,
            )
            self.signal.normalize(start=start, end=end)

        # ... (rest of the method remains the same)

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
        self.frame_idx = int(idx)
        self.signal_marker.setX(int(idx * self.parent.ms))
        self.parent.update_signal_value(None, idx=idx)

    def update_pens(self):
        for c in self.colors:
            if c == "signal":
                self.sig_pen.setColor(self.colors[c])
            elif c == "baseline":
                self.base_pen.setColor(self.colors[c])
            elif c == "apd":
                self.apd_pen.setColor(self.colors[c])
            elif c == "points":
                self.pt_brush.setColor(self.colors[c])
                self.signal_data.setSymbolBrush(self.pt_brush)
                self.apd_data.setSymbolBrush(self.pt_brush)
                self.baseline_data.setSymbolBrush(self.pt_brush)
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

    def toggle_range(self):
        self.start_range_marker.setVisible(self.show_range_marker.isChecked())
        self.end_range_marker.setVisible(self.show_range_marker.isChecked())
        
    def show_baseline(self, b = -1, params = None):
        if b == -1:
            # refresh baseline
            params = self.baseline_params
            b = self.baseline_mode
        else:
            # new baseline
            self.baseline_params = params
            self.baseline_mode = b
            
        if b == 0:
            # no preview
            self.baseline_data.setData()
        elif b == 1:
            # preview peaks
            d = self.signal_data.getData()[1]
            t = np.arange(len(d))
            baseline = FindPeaks(t, d, params)
            self.baseline_data.setData(baseline * int(self.ms_per_frame.value()), d[baseline])
        elif b == 2:
            # preview baseline
            d = self.signal_data.getData()[1]
            t = np.arange(len(d))
            baseline = FindPeaks(t, -d, params)
            self.baseline_data.setData(baseline * int(self.ms_per_frame.value()), d[baseline])
        else:
            return 
        
        
    def point_hover_tooltip(self, x, y, data, xLabel="x: ", yLabel="y: "):
        """Called by signal_panel when hovering over a point"""
        tooltip = xLabel + f"{x:.3f}" + "\n" + yLabel + f"{y:.3f}"
        return tooltip
