
import numpy as np
import numpy.ma as ma
import pyqtgraph as pg
from pyqtgraph import ErrorBarItem
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
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

from cardiacmap.viewer.components import Spinbox

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


class ScatterDragPlot(pg.PlotItem):
    # Position Plot used by APD/DI Scatter Plot.
    def __init__(self, parent, callback):
        super().__init__()
        self.callback = callback
        self.parent = parent

    def mouseDragEvent(self, event: MouseDragEvent):
        pos = self.vb.mapSceneToView(event.scenePos())
        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def mouseClickEvent(self, event: MouseDragEvent):
        pos = self.vb.mapSceneToView(event.scenePos())
        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def hoverEvent(self, event: HoverEvent):
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(Qt.MouseButton.LeftButton)


class ScatterPanel(QWidget):
    # scatter plot widget
    # displays APD vs DI
    def __init__(self, parent):
        super().__init__(parent=parent)

        self.parent = parent
        self.settings = parent.settings
        self.ms = parent.ms
        self.apd_data = parent.data_slices[0]
        self.di_data = parent.data_slices[1]
        #self.flags = parent.flags

        self.init_plot()

        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def init_plot(self):
        pts_c1 = self.settings.child("Signal Plot Colors").child("points").value()
        pts_c2 = self.settings.child("Signal Plot Colors").child("apd").value()
        pts_brush1 = pg.mkBrush(QColor(pts_c1[0], pts_c1[1], pts_c1[2], a=255))
        pts_brush2 = pg.mkBrush(QColor(pts_c2[0], pts_c2[1], pts_c2[2], a=255))
        
        # Set up Image View
        self.plot = pg.PlotWidget()
        self.plot.setRange(xRange=(-2,np.max(self.di_data[0])), yRange=(-2,np.max(self.apd_data[0])))
        self.plot_item: pg.PlotDataItem = self.plot.plot(
            pen=None, symbol="o", symbolSize=6,
        )
        self.plot_item.scatter.setData(hoverable=True, tip=self.point_hover_tooltip)
        self.plot_item.setSymbolBrush(pts_brush1)
        
        self.plot_item2: pg.PlotDataItem = self.plot.plot(
            pen=None, symbol="o", symbolSize=6,
        )
        self.plot_item2.scatter.setData(hoverable=True, tip=self.point_hover_tooltip)
        self.plot_item2.setSymbolBrush(pts_brush2)
        
        self.mean_item: pg.PlotDataItem = self.plot.plot(
            pen=None, symbol="x", symbolSize=10,
        )
        self.mean_item.scatter.setData(hoverable=True, tip=self.point_hover_tooltip)
        self.mean_item.setSymbolBrush(pg.mkBrush('g'))
        
        self.mean_item2: pg.PlotDataItem = self.plot.plot(
            pen=None, symbol="x", symbolSize=10,
        )
        self.mean_item2.scatter.setData(hoverable=True, tip=self.point_hover_tooltip)
        self.mean_item2.setSymbolBrush(pg.mkBrush('g'))
        
        self.error_bar = None
        self.error_bar2 = None

        # set up axes
        leftAxis: pg.AxisItem = self.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Action Potential Duration (ms)")
        bottomAxis.setLabel(text="Diastolic Interval (ms)")

        self.update_plot(0, 0, 0, False, False)

    def update_plot(self, interval, x, y, show_err, alternans):
        #print(interval, x, y)
        interval = int(interval)
        x = int(x)
        y = int(y)
        apdData = self.apd_data[interval][..., y, x] * self.ms
        diData = self.di_data[interval][..., y, x] * self.ms
        
        if alternans:
            apdData2 = apdData[1::2]
            diData2 = diData[1::2]
            apdData = apdData[0::2]
            diData = diData[0::2]
            
            mApd2 = ma.masked_array(apdData2, mask = apdData2 == 0)
            mDi2 = ma.masked_array(diData2, mask = diData2 == 0)
            
            avgAPD2 = np.mean(mApd2)
            avgDI2 = np.mean(mDi2)
            
            stdAPD2 = np.std(mApd2)
            stdDI2 = np.std(mDi2)
            
            avg_pt2 = [(avgDI2, avgAPD2)]
            self.mean_item2.setData(np.array(avg_pt2))
            
        mApd = ma.masked_array(apdData, mask = apdData == 0)
        mDi = ma.masked_array(diData, mask = diData == 0)
        
        avgAPD = np.mean(mApd)
        avgDI = np.mean(mDi)
        
        stdAPD = np.std(mApd)
        stdDI = np.std(mDi)
        
        avg_pt = [(avgDI, avgAPD)]
        self.mean_item.setData(np.array(avg_pt))
        
        # if there is already an error bar, remove it before adding another one
        if self.error_bar is not None:
            self.plot.removeItem(self.error_bar)
            self.error_bar = None
        if self.error_bar2 is not None:
            self.plot.removeItem(self.error_bar2)
            self.error_bar2 = None
        if show_err:
            self.mean_item.show()
            self.error_bar = ErrorBarItem(x=avgDI, y=avgAPD, height=stdAPD, width=stdDI, beam = 2, pen = pg.mkPen('b'))
            self.plot.addItem(self.error_bar)
            if alternans:
                self.mean_item2.show()
                self.error_bar2 = ErrorBarItem(x=avgDI2, y=avgAPD2, height=stdAPD2, width=stdDI2, beam = 2, pen = pg.mkPen('y'))
                self.plot.addItem(self.error_bar2)
            else:
                self.mean_item2.hide()
        else:
            self.mean_item.hide()
            self.mean_item2.hide()

        xyData = tuple(zip(diData, apdData))
        # remove zero values
        xyData = [pt for pt in xyData if pt != (0.0, 0.0)]
        self.plot_item.setData(np.array(xyData))
        
        if alternans:
            xyData2 = tuple(zip(diData2, apdData2))
            # remove zero values
            xyData2 = [pt for pt in xyData2 if pt != (0.0, 0.0)]
            self.plot_item2.setData(np.array(xyData2))
        else:
            self.plot_item2.setData(np.array([]))

    def point_hover_tooltip(self, x, y, data):
        """Called by plot_item.scatter when hovering over a point"""
        tooltip = (
            "APD: " + f"{y:.3f}" + "\nDI: " + f"{x:.3f}"
        )  # + "\nBeat #: " + str(b)
        return tooltip


class ScatterPlotView(QWidget):
    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent

        self.init_image_view()
        self.init_toolbar()
        self.swap_button = QPushButton("Swap APD/DI (current interval only)")
        self.swap_button.clicked.connect(self.swap_apd_di)

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.px_bar)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.swap_button)
        self.setLayout(layout)

        self.set_image()

    def init_image_view(self):
        # Set up Image View
        self.plot = ScatterDragPlot(self, self.update_marker)
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
        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable red dot
        self.marker = pg.ScatterPlotItem(
            pos=[[64, 64]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )
        self.image_view.getView().addItem(self.marker)
        self.x = self.y = 64

        return self.image_view

    def init_toolbar(self):
        self.toolbar = QToolBar()
        self.intervalIdx = QtWidgets.QSpinBox()
        self.intervalIdx.setFixedWidth(60)
        self.intervalIdx.setMaximum(len(self.parent.data_slices[0]))
        #print("Number of Slices", len(self.parent.data_slices[0]))
        self.intervalIdx.setMinimum(1)
        self.intervalIdx.setValue(1)
        self.intervalIdx.setSingleStep(1)
        self.intervalIdx.setStyleSheet(SPINBOX_STYLE)
        self.intervalIdx.valueChanged.connect(self.update_scatter)
        self.intervalIdx.valueChanged.connect(self.set_image)
        
        self.show_err = QCheckBox()
        self.show_err.checkStateChanged.connect(self.update_scatter)
        
        self.alternans = QCheckBox()
        self.alternans.checkStateChanged.connect(self.update_scatter)
        
        self.toolbar.addWidget(QLabel("Interval #:"))
        self.toolbar.addWidget(self.intervalIdx)
        self.toolbar.addWidget(QLabel(" Show Mean/Std:"))
        self.toolbar.addWidget(self.show_err)
        self.toolbar.addWidget(QLabel(" Alternans:"))
        self.toolbar.addWidget(self.alternans)
        
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

    def set_image(self):
        self.image_view.setImage(
            self.parent.parent.img_data,
            autoRange=False,
            autoLevels=False,
        )
        self.image_view.update()
        self.parent.update_tab_title(self.intervalIdx.value()-1)

    def update_marker(self, x, y):
        self.y = np.clip(y, 0, IMAGE_SIZE - 1)
        self.x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.marker.setData(pos=[[x, y]])
        self.update_scatter()
        self.update_position_boxes(val=None)
            
    def update_position_boxes(self, val=None):
        #print("Update Boxes val", val)
        if val is not None:
            # set position to box values
            x = int(self.x_box.value())
            y = int(self.y_box.value())
            self.marker.setData(pos=[[x, y]])
            self.update_scatter()
        else:
            # set box values to position
            self.x_box.blockSignals(True) # block signals to avoid
            self.y_box.blockSignals(True) # circular callback
            self.x_box.setValue(self.x)
            self.y_box.setValue(self.y)
            self.x_box.blockSignals(False)
            self.y_box.blockSignals(False)
    
    def update_scatter(self):
        # call update_plot in ScatterPanel
        self.parent.data_tab.update_plot(self.intervalIdx.value()-1, self.x, self.y, self.show_err.isChecked(), self.alternans.isChecked())
        self.parent.parent.image_tab.update_position(self.x, self.y) # link scatter coord to APDWindow coord

    def swap_apd_di(self):
        interval =  self.intervalIdx.value()-1
        apdArr = self.parent.parent.data[0][interval]
        self.parent.parent.data[0][interval] = self.parent.parent.data[1][interval] # set apdArr to diArr
        self.parent.parent.data[1][interval] = apdArr # set diArr to apdArr
        self.update_scatter()
