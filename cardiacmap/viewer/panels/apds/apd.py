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

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.parent.x = x
        self.parent.y = y
        self.parent.calculate_apds()

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
        self.preview_tab = SignalPanel(self, toolbar=False, signal_marker=False, ms_conversion=False, settings=self.settings)
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
        self.options = QToolBar()
        self.calculate_bar = QToolBar()
        self.plotting_bar = QToolBar()
        
        self.threshold = Spinbox(
            min=.01,
            max=.99,
            val=self.settings.child("APD Parameters").child("Threshold").value(),
            step=.01,
            min_width=50,
            max_width=50,
        )
        self.threshold.valueChanged.connect(self.calculate_apds)
        
        self.min_dist = Spinbox(
            min= 1,
            max= 500,
            val=1,
            step=1,
            min_width=50,
            max_width=50,
        )
        self.min_dist.valueChanged.connect(self.calculate_apds)
        
        self.options.addWidget(QLabel("Threshold: "))
        self.options.addWidget(self.threshold)
        # self.options.addWidget(QLabel("Min APD/DI Length: "))
        # self.options.addWidget(self.min_dist)

        self.confirm = QPushButton("Calculate")
        self.confirm.clicked.connect(self.setPlottingButtons)
        self.confirm.clicked.connect(self.calculate_all_apds)
        self.calculate_bar.addWidget(self.confirm)
        

        self.options.setStyleSheet(QTOOLBAR_STYLE)
        self.calculate_bar.setStyleSheet(QTOOLBAR_STYLE)
        self.plotting_bar.setStyleSheet(QTOOLBAR_STYLE)
        
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options)
        layout.addSpacing(5)
        layout.addWidget(self.calculate_bar)

        self.options_widget.setLayout(layout)
        
    def calculate_apds(self):
        threshold = self.threshold.value()
        self.ts, _ = GetThresholdIntersections1D(self.parent.signal.transformed_data[:, self.x, self.y], threshold)
        self.update_signal_plot()
        
    def calculate_all_apds(self):
        s = time.time()
        threshold = self.threshold.value()
        print("APDs/DIs:", threshold)
        self.apds, self.dis = GetThresholdIntersections(self.parent.signal.transformed_data, threshold)
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
      

class APDSubWindow(QMainWindow):
    def __init__(self, parent, typeStr, intervals = 1):
        QMainWindow.__init__(self)
        self.parent = parent
        self.settings = parent.settings
        self.intervals = intervals
        
        self.x1 = self.y1 = self.x2 = self.y2 = 64

        match typeStr:
            case "APD":
                window_title = "Spatial APDs"
                y_axis_label = "Action Potential Duration (ms)"
                x_axis_label = "Linear Space (px)"
                
                self.data = self.parent.data[0]
                self.view_tab = SpatialPlotView(self)

                self.data_tab = SignalPanel(
                    self,
                    toolbar=False,
                    signal_marker=False,
                    ms_conversion=False,
                    settings=self.settings,
                )
                
            case "DI":
                window_title = "Spatial DIs"
                y_axis_label = "Diastolic Interval (ms)"
                x_axis_label = "Linear Space (px)"

                self.data = self.parent.data[1]
                self.view_tab = SpatialPlotView(self)
                
                
                # Create Signal Views
                self.data_tab = SignalPanel(
                    self,
                    toolbar=False,
                    signal_marker=False,
                    ms_conversion=False,
                    settings=self.settings,
                )
                
            case "APD DI":
                window_title = "APD v.s. DI"
                y_axis_label = "Action Potential Duration (ms)"
                x_axis_label = "Diastolic Interval (ms)"
                
                self.data = self.parent.data
                self.view_tab = ScatterPlotView(self)
                
                # Create Signal Views
                self.data_tab = ScatterPanel(self)
                
            case _:
                self.close()

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.view_tab, window_title)
        self.image_tabs.setMinimumWidth(200)
        self.image_tabs.setMinimumHeight(200)

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
        img = self.data[idxNum]
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

        

