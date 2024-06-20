import os
import sys
from functools import partial

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.PlotDataItem import PlotDataItem
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QToolBar,
    QPlainTextEdit,
)

from cardiacmap.model.signal import CascadeSignal
from cardiacmap.model.data import CascadeDataFile

from cardiacmap.viewer.parameter import ParameterWidget


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


class PositionTab(QWidget):

    def __init__(self, position_callback):

        super().__init__()

        self.init_image_view()
        # self.init_player_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        # layout.addWidget(self.player_bar)
        self.setLayout(layout)

        self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        view = DraggablePlot(self.update_position)
        self.image_view = pg.ImageView(view=view)
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

        # Draggable Red Dot
        # Add posiiton marker
        self.position_marker = pg.ScatterPlotItem(
            pos=[[0, 0]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )

        self.image_view.getView().addItem(self.position_marker)

        return self.image_view

    def init_player_bar(self):
        self.player_bar = QToolBar()

        play_button = QPushButton("Play")
        forward_button = QPushButton("Play")
        back_button = QPushButton("Play")
        skip_frames = QtWidgets.QSpinBox()
        skip_frames.setFixedWidth(80)
        skip_frames.setMaximum(10000)
        skip_frames.setValue(500)
        skip_frames.setSingleStep(10)
        skip_frames.setStyleSheet(
            """QSpinBox
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
        )

        colormap = QToolButton()
        normalize = QToolButton()

        play_button.clicked.connect(self.image_view.play(rate=100))
        # forward_button.clicked.connect(self.image_view.)

        self.player_bar.addWidget(play_button)
        self.player_bar.addWidget(forward_button)
        # self.player_bar.addAction()
        self.player_bar.addWidget(back_button)
        self.player_bar.addWidget(skip_frames)
        self.player_bar.addWidget(colormap)
        self.player_bar.addWidget(normalize)

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.position_callback(x, y)

    def update_marker(self, x, y):
        self.position_marker.setData(pos=[[x, y]])


# class AnnotateView(QtWidgets.QWidget):

#     def __init__(self, array):

#         # Button Layout
#         button_layout = QHBoxLayout()
#         add_roi_button = QPushButton("Add Mask")
#         add_roi_button.setCheckable(True)
#         remove_roi_button = QPushButton("Remove Mask")
#         confirm_roi_button = QPushButton("Confirm Mask")

IMAGE_SIZE = 128


class SignalWidget(QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent

        self.resize(600, self.height())

        self.init_button_bar()
        self.init_label()

        self.plot = pg.PlotWidget()
        self.data: pg.PlotDataItem = self.plot.plot()

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(self.label)
        splitter.addWidget(self.button_bar)
        splitter.addWidget(self.plot)
        splitter.setStyleSheet(
            """QSplitter::handle {
                background-color: grey;
                width: 2
            }"""
        )

        layout = QHBoxLayout()
        layout.addWidget(splitter)
        self.setLayout(layout)

    def init_button_bar(self):
        self.button_bar = QToolBar()

        trim = QAction("Trim", self)
        time_average = QAction("Time Average", self)
        spatial_average = QAction("Spatial Average", self)

        self.button_bar.addAction(trim)
        self.button_bar.addAction(time_average)
        self.button_bar.addAction(spatial_average)

        # For some reason stylesheet here doesn't show text as black
        self.button_bar.setStyleSheet("QToolButton:!hover {color:black;}")

        trim.triggered.connect(self.parent.test)

    def init_label(self):
        self.label = QWidget()
        layout = QHBoxLayout()

        # TODO: Add real metadata + refactor this nicely later to use QFormLayout
        layout.addWidget(QLabel("File:\nFrames:\nOdd / Even:"))
        layout.addWidget(QLabel("test.dat\n5000\nSingle Channel"))
        layout.addStretch()

        self.label.setLayout(layout)


class ImageSignalViewer(QWidget):

    def __init__(self, signal: CascadeSignal):

        super().__init__()

        self.resize(1200, 400)

        # TODO: Refactor here
        self.signal = signal
        self.array = self.signal.base_data.transpose(0, 2, 1)

        # Create viewer tabs
        self.position_tab = PositionTab(position_callback=self.update_signal_plot)
        self.position_tab.image_view.setImage(
            self.array, autoLevels=True, autoRange=False
        )

        self.image_tabs = QTabWidget()
        size_policy = QtWidgets.QSizePolicy()
        size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Preferred)
        size_policy.setHeightForWidth(True)
        self.image_tabs.setSizePolicy(size_policy)
        self.image_tabs.setMinimumWidth(256)
        self.image_tabs.setMaximumWidth(1024)

        self.image_tabs.addTab(self.position_tab, "Image / Video")

        # Create Signal View
        self.signal_view = SignalWidget(self)

        # Create settings widget
        # TODO: Refactor here
        params = [
            {"name": "Parameter 1", "type": "int", "value": 10, "limits": (0, 100)},
            {
                "name": "Parameter 2",
                "type": "float",
                "value": 0.5,
                "limits": (0.0, 1.0),
            },
            {"name": "Parameter 3", "type": "bool", "value": True},
        ]

        self.params = Parameter.create(name="parameters", type="group", children=params)
        # self.params2 = Parameter.create(name="parameters", type="group", children=params)
        
        # self.params_parent = Parameter.create(name="parent", type="group", children={'name': 'test', 'type': 'group', 'value':self.params})

        print(self.params['Parameter 1'])

        settings_widget = ParameterWidget(self.params)

        # Create main layout
        self.splitter = QSplitter()
        self.splitter.addWidget(self.image_tabs)
        self.splitter.addWidget(self.signal_view)
        self.splitter.addWidget(settings_widget)

        for i in range(self.splitter.count()):
            self.splitter.setCollapsible(i, False)
        layout = QHBoxLayout()
        layout.addWidget(self.splitter)

        self.setLayout(layout)

    def update_signal_plot(self, x, y):

        signal = self.array[:, y, x]
        self.signal_view.data.setData(signal)

    def test(self):

        print("test")


class CardiacMapWindow(QMainWindow):
    # This is the main window that allows you to open a new widget etc.
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CardiacMap v0.0.5")
        self.setGeometry(100, 100, 1080, 720)

        self.menu_bar = QMenuBar(self)
        self.setMenuBar(self.menu_bar)

        self.file_menu = self.menu_bar.addMenu("File")
        self.load_voltage_action = QAction("Load Voltage Data", self)
        self.load_voltage_action.triggered.connect(
            partial(self.create_viewer, calcium_mode=False)
        )
        self.load_calcium_action = QAction("Load Voltage / Calcium Data", self)
        self.load_calcium_action.triggered.connect(
            partial(self.create_viewer, calcium_mode=True)
        )

        self.file_menu.addAction(self.load_voltage_action)
        self.file_menu.addAction(self.load_calcium_action)

        self.docks = []

    def create_viewer(self, signal=None, calcium_mode=False):

        filepath = QtWidgets.QFileDialog.getOpenFileName()[0]

        if filepath and ".dat" in filepath:

            filename = os.path.split(filepath)[-1]

            cascade_file = CascadeDataFile.load_data(filepath, dual_mode=calcium_mode)

            if calcium_mode:

                signal_odd = cascade_file.signals[1]
                signal_even = cascade_file.signals[0]

                for signal, suffix in [(signal_odd, "_odd"), (signal_even, "_even")]:
                    viewer = ImageSignalViewer(signal)

                    dock = QDockWidget(filename + suffix, self)

                    dock.setWidget(viewer)
                    # dock.setFixedSize(IMAGE_SIZE * 3.05, IMAGE_SIZE * 1.1)
                    self.addDockWidget(Qt.RightDockWidgetArea, dock)
                    self.docks.append(dock)

            else:
                signal = cascade_file.signals[0]

                viewer = ImageSignalViewer(signal)

                dock = QDockWidget(filename, self)

                dock.setWidget(viewer)
                # dock.setFixedSize(IMAGE_SIZE * 3.05, IMAGE_SIZE * 1.1)
                self.addDockWidget(Qt.RightDockWidgetArea, dock)
                self.docks.append(dock)

    def create_plot_widget(self):
        plot_widget = pg.PlotWidget()
        plot_data = [1, 2, 3, 4, 5]
        plot_widget.plot(plot_data)
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(plot_widget)
        container.setLayout(layout)
        return container


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    # datafile, sigarray = CascadeDataFile.from_dat(
    #     "2011-08-23_Exp000_Rec112_Cam1-Blue.dat"
    # )

    cascade_file = CascadeDataFile.load_data(
        "2011-08-23_Exp000_Rec112_Cam1-Blue.dat",
        "C:\\Users\\Chris\\repos\\pyui_sandbox\\data",
    )

    signal = cascade_file.signals[0]

    viewer = ImageSignalViewer(signal)

    viewer.show()

    # main_window = CardiacMapWindow()
    # main_window.show()

    sys.exit(app.exec())
