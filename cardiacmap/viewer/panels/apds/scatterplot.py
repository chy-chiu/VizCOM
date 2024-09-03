import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
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
        self.apd_data = parent.data[0]
        self.di_data = parent.data[1]
        self.flags = parent.flags

        self.init_plot()

        layout = QVBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def init_plot(self):
        # Set up Image View
        self.plot = pg.PlotWidget()
        self.plot_item: pg.PlotDataItem = self.plot.plot(
            pen=None, symbol="o", symbolSize=6
        )
        self.plot_item.scatter.setData(hoverable=True, tip=self.point_hover_tooltip)

        # set up axes
        leftAxis: pg.AxisItem = self.plot.getPlotItem().getAxis("left")
        bottomAxis: pg.AxisItem = self.plot.getPlotItem().getAxis("bottom")
        leftAxis.setLabel(text="Action Potential Duration (ms)")
        bottomAxis.setLabel(text="Diastolic Interval (ms)")

        self.update_plot(0, 0)

    def update_plot(self, x, y):
        apdData = self.apd_data[..., y, x]
        diData = self.di_data[..., y, x]

        # only use apds with a preceding DI
        if self.flags[y * IMAGE_SIZE + x]:
            apdData = apdData[1:]

        xyData = tuple(zip(diData, apdData))

        # remove zero values
        xyData = [pt for pt in xyData if pt != (0.0, 0.0)]

        self.plot_item.setData(np.array(xyData))

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
        self.init_controller_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.controller_bar)
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
        self.image_view.ui.histogram.hide()
        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable red dot
        self.marker = pg.ScatterPlotItem(
            pos=[[64, 64]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )
        self.image_view.getView().addItem(self.marker)

        return self.image_view

    def init_controller_bar(self):
        self.controller_bar = QToolBar()

    def set_image(self):
        self.image_view.setImage(
            self.parent.parent.signal.transformed_data[0],
            autoRange=False,
            autoLevels=False,
        )
        self.image_view.update()

    def update_marker(self, x, y):
        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.marker.setData(pos=[[x, y]])
        self.update_scatter(x, y)

    def update_scatter(self, x, y):
        # call update_plot in ScatterPanel
        self.parent.APD_DI_tab.update_plot(x, y)
