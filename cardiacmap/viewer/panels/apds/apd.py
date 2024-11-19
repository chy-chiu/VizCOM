import numpy as np
import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from cardiacmap.viewer.panels import SignalPanel
from cardiacmap.viewer.panels.apds import ScatterPanel, ScatterPlotView, SpatialPlotView
from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.utils import loading_popup
from cardiacmap.transforms.apd import GetThresholdIntersections, GetThresholdIntersections1D

import time
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


class APDPositionView(QWidget):

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
        self.parent.calculate_apds()
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
        
    def update_spinbox_values(self):
        """Called When Range Changes"""
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        #self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 2, levels[1])

        # set numerical vals to their visual levels
        self.parent.max_val.setValue((levels[1]))
        self.parent.min_val.setValue(levels[0])
        

class APDWindow(QMainWindow):
    def __init__(self, parent):
        QMainWindow.__init__(self)
        self.parent = parent
        self.ms = parent.ms
        self.mask = parent.signal.mask
        self.settings = parent.settings
        
        self.img_data = parent.signal.transformed_data[0] * self.mask
        self.ts = None
        
        self.setWindowTitle("APDs")
        # Create Menus
        self.init_options()
        self.init_plot_bar()

        # Create viewer tabs
        self.image_tab = APDPositionView(
            self, self.img_data
        )  # ----------------------------

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Preview")
        self.image_tabs.setMinimumWidth(300)
        self.image_tabs.setMinimumHeight(350)
        
        self.image_layout = QVBoxLayout()
        self.image_layout.addWidget(self.plotting_bar)
        self.image_layout.addWidget(self.image_tabs)
        self.image_layout.addWidget(self.options_widget)
        self.image_widget = QWidget(layout=self.image_layout)
        
        # Preview Panel
        self.line_count = 0
        self.lines = None
        self.preview_tab = SignalPanel(self, settings=self.settings)
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
        
        self.calculate_apds()

    def update_signal_plot(self):
        self.preview_tab.signal_data.setData(
            x=np.arange(len(self.parent.signal.transformed_data[:, self.x, self.y])) * self.ms, 
            y=self.parent.signal.transformed_data[:, self.x, self.y]
        )
        if self.ts is not None:
            self.preview_tab.apd_data.setData(
                x=self.ts * self.ms,
                y= np.array([self.threshold.value()] * len(self.ts))
            )

    def update_signal_value(self, evt, idx=None):
        return

    def set_image(self, image):
        self.update_signal_plot()
        
    def init_plot_bar(self):
        self.APDvSpace = QPushButton("Spatial APDs")
        self.APDvSpace.clicked.connect(self.plot_apd_spatial)
        self.plotting_bar.addWidget(self.APDvSpace)
        
        self.DIvSpace = QPushButton("Spatial DIs")
        self.DIvSpace.clicked.connect(self.plot_di_spatial)
        self.plotting_bar.addWidget(self.DIvSpace)
        
        self.APDvDI = QPushButton("APD v.s. DI")
        self.APDvDI.clicked.connect(self.plot_apd_di)
        self.plotting_bar.addWidget(self.APDvDI)
        
        self.plot_buttons = [self.APDvSpace, self.DIvSpace, self.APDvDI]
        self.setPlottingButtons(False)
    
    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.apd_toolbar = QToolBar()
        self.interval_toolbar = QToolBar()
        self.calculate_bar = QToolBar()
        self.plotting_bar = QToolBar()
        
        # APD Parameters ========================================================
        self.threshold = Spinbox(
            min=.01,
            max=.99,
            val=self.settings.child("APD Parameters").child("Threshold").value(),
            step=.01,
            min_width=50,
            max_width=50,
        )
        self.threshold.valueChanged.connect(self.calculate_apds)
        
        self.min_frames = Spinbox(
            min= 0,
            max= 500,
            val=3,
            step=1,
            min_width=50,
            max_width=50,
        )
        self.min_frames.valueChanged.connect(self.calculate_apds)
        
        
        self.apd_toolbar.addWidget(QLabel("Threshold: "))
        self.apd_toolbar.addWidget(self.threshold)
        self.apd_toolbar.addWidget(QLabel("Min APD Spacing: "))
        self.apd_toolbar.addWidget(self.min_frames)
        #========================================================================
        
        # Start and End times for intervals =====================================
        max_time = int(len(self.parent.signal.transformed_data) * self.ms)
        self.start_time = Spinbox(
            min=0,
            max=max_time,
            val=0,
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
        
        self.subintervals = Spinbox(
            min=1,
            max=20,
            val=1,
            step=1,
            min_width=50,
            max_width=50,
        )
        self.subintervals.valueChanged.connect(self.update_lines)
        
        self.interval_toolbar.addWidget(QLabel("Start Time: "))
        self.interval_toolbar.addWidget(self.start_time)
        self.interval_toolbar.addWidget(QLabel("End Time: "))
        self.interval_toolbar.addWidget(self.end_time)
        self.interval_toolbar.addWidget(QLabel("Subintervals: "))
        self.interval_toolbar.addWidget(self.subintervals)
        #========================================================================

        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.setPlottingButtons)
        self.confirm.clicked.connect(self.calculate_all_apds)
        self.calculate_bar.addWidget(self.confirm)
        

        self.apd_toolbar.setStyleSheet(QTOOLBAR_STYLE)
        self.interval_toolbar.setStyleSheet(QTOOLBAR_STYLE)
        self.calculate_bar.setStyleSheet(QTOOLBAR_STYLE)
        self.plotting_bar.setStyleSheet(QTOOLBAR_STYLE)
        
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.apd_toolbar)
        layout.addSpacing(5)
        layout.addWidget(self.interval_toolbar)
        layout.addSpacing(5)
        layout.addWidget(self.calculate_bar)

        self.options_widget.setLayout(layout)
        
    def calculate_apds(self):
        threshold = self.threshold.value()
        spacing = self.min_frames.value()
        self.ts, _ = GetThresholdIntersections1D(self.parent.signal.transformed_data[:, self.x, self.y], threshold, spacing)
        self.update_signal_plot()
        
    def calculate_all_apds(self):
        s = time.time()
        threshold = self.threshold.value()
        spacing = self.min_frames.value()
        print("APDs/DIs:", "\nThreshold:", threshold, "\n:", spacing)
        
        self.line_idxs = [int(x.getPos()[0]//self.ms) for x in self.lines]
        self.apds, self.dis = GetThresholdIntersections(self.parent.signal.transformed_data, threshold, spacing, intervals = self.line_idxs)
        e = time.time()
        print("Runtime:", e-s)
        self.data = [self.apds, self.dis]
        self.setPlottingButtons(True)
        
    def plot_apd_spatial(self):
        self.APDvSpaceWindow = APDSubWindow(self, "APD")
        self.APDvSpaceWindow.show()
        
    def plot_di_spatial(self):
        self.DIvSpaceWindow = APDSubWindow(self, "DI")
        self.DIvSpaceWindow.show()
        
    def plot_apd_di(self):
        self.APDvDI = APDSubWindow(self, "APD DI")
        self.APDvDI.show()
    
    def setPlottingButtons(self, b: bool = False):
        for button in self.plot_buttons:
            button.setEnabled(b)
        self.plotting_bar.repaint() # update gui before proceeding
        
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
        line.sigPositionChangeFinished.connect(self.set_apd_range)
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
            
    def set_apd_range(self):
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
      

class APDSubWindow(QMainWindow):
    def __init__(self, parent, typeStr, intervals = 1):
        QMainWindow.__init__(self)
        self.parent = parent
        self.ms = parent.ms
        self.settings = parent.settings
        self.intervals = intervals
        
        self.x1 = self.y1 = self.x2 = self.y2 = 64

        self.image_tabs = QTabWidget()
        self.image_tabs.setMinimumWidth(300)
        self.image_tabs.setMinimumHeight(300)

        match typeStr:
            case "APD":
                self.window_title = "Spatial APDs"
                y_axis_label = "Action Potential Duration (ms)"
                x_axis_label = "Linear Space (px)"
                
                self.data_slices = self.parent.data[0]
                self.view_tab = SpatialPlotView(self)

                self.data_tab = SignalPanel(self, settings=self.settings)
                
            case "DI":
                self.window_title = "Spatial DIs"
                y_axis_label = "Diastolic Interval (ms)"
                x_axis_label = "Linear Space (px)"

                self.data_slices = self.parent.data[1]
                self.view_tab = SpatialPlotView(self)
                
                
                # Create Signal Views
                self.data_tab = SignalPanel(self, settings=self.settings)
                
            case "APD DI":
                self.window_title = "APD v.s. DI"
                y_axis_label = "Action Potential Duration (ms)"
                x_axis_label = "Diastolic Interval (ms)"
                
                self.data_slices = self.parent.data
                self.view_tab = ScatterPlotView(self)
                
                # Create Signal Views
                self.data_tab = ScatterPanel(self)
                
            case _:
                self.close()
                
        self.image_tabs.addTab(self.view_tab, self.window_title)
        self.update_tab_title(0)

        # set up axes
        leftAxis: pg.AxisItem = self.data_tab.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.data_tab.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text=y_axis_label)
        bottomAxis.setLabel(text=x_axis_label)


        self.signal_tabs = QTabWidget()
        self.signal_tabs.addTab(self.data_tab, y_axis_label + " v.s. " + x_axis_label)

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_tabs)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)
        self.setCentralWidget(self.splitter)
        self.setLayout(layout)

    def update_graph(self, coords, idxNum):
        img = self.data_slices[0][idxNum] * self.ms
        data = []
        for coord in coords:
            #print(coord)
            data.append(img[coord[0]][coord[1]])
        self.data_tab.signal_data.setData(data)
        
    def update_plot(self, x, y):
        pass

    def update_signal_plot(self):
        return

    def update_signal_value(self, evt, idx=None):
        return
    
    def update_tab_title(self, interval_idx):
        # called by subplots when the viewing interval changes
        text = self.window_title
        self.image_tabs.setTabText(0, text + " [" + 
                                str(self.parent.line_idxs[interval_idx] * self.ms) + 
                                "-" + 
                                str((self.parent.line_idxs[interval_idx+1]-1) * self.ms) +
                                "]:") 

        

