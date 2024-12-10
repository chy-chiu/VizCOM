from functools import partial
from PySide6 import QtCore, QtGui, QtWidgets

import numpy as np
import pyqtgraph as pg
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
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from skimage.measure import find_contours

from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.panels.position import PositionView
from cardiacmap.viewer.panels.signal import SignalPanel, SignalPlot
from cardiacmap.viewer.utils import loading_popup
import matplotlib.pyplot as plt
from copy import deepcopy

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128


def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140]) / 255


@loading_popup
def _calculate_isochrome(
    sig: np.ndarray, t: float, start_frame, cycles, skip_frame, update_progress=None
):

    all_c = []

    for i in range(cycles):

        idx = i * skip_frame + start_frame

        if idx < len(sig):
            c = np.zeros((128, 128))
            for p in find_contours(sig[idx], level=t):
                for j in p:
                    c[int(j[0]), int(j[1])] = 1
            all_c.append(c)

        if update_progress:
            update_progress(i / cycles)

    all_c = [c * (i + 1) for i, c in enumerate(all_c)]

    _c = np.array(all_c).max(axis=0) * skip_frame

    return _c


def _calculate_isochrome_filled(
    sig: np.ndarray, t: float, start_frame, cycles, skip_frame
):
    offset = cycles * skip_frame * 2
    DPI = 128
    figsize = (1, 1)  # Inches
    fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
    ax.axis("off")
    ax.contourf(
        (sig[start_frame : start_frame + offset] > t).argmin(axis=0),
        levels=range(0, cycles * skip_frame, skip_frame),
        cmap="gray",
    )
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    fig.canvas.draw()
    image = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    image = image.reshape((DPI, DPI, 3))
    return np.round(rgb2gray(image) * cycles) * skip_frame

class IsochromeSignalPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent = parent
        self.plot = SignalPlot(self)
        signal_size_policy = QtWidgets.QSizePolicy()
        signal_size_policy.setHorizontalPolicy(
            QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.plot.setSizePolicy(signal_size_policy)
        self.signal_marker = pg.InfiniteLine(angle=90, movable=True)
        self.threshold_marker = pg.InfiniteLine(angle=0, movable=True)
        self.threshold_marker.setPen(pg.mkPen("g"))

        self.signal_marker.sigPositionChangeFinished.connect(self.parent.update_signal_index)
        self.threshold_marker.sigPositionChangeFinished.connect(self.parent.update_threshold_marker)

        self.signal_data: pg.PlotDataItem = self.plot.plot(
            pen=self.parent.parent.signal_panel.sig_pen, symbol="o", symbolSize=0
        )
        self.plot.addItem(self.signal_marker, ignoreBounds=True)
        self.plot.addItem(self.threshold_marker, ignoreBounds=True)
        
        self.resize(600, 300)
        self.plot.resize(self.width(), self.height())
    
    def update_signal_marker(self, idx):
        self.frame_idx = int(idx)
        self.signal_marker.setX(int(idx * self.parent.parent.ms))        
    
class IsochromeWindow(QMainWindow):

    def __init__(self, parent):

        super().__init__()
        self.parent = parent
        self.mask = parent.signal.mask
        self.signal = self.parent.signal
        self.xVals = self.parent.xVals
        self.ms = self.parent.ms
        self.setWindowTitle("Isochrome View")

        self.signal_panel = IsochromeSignalPanel(
            self
        )

        img_layout = QVBoxLayout()
        central_layout = QHBoxLayout()

        self.x, self.y = 64, 64

        self.video_tab = PositionView(self)
        self.video_tab.image_view.setImage(self.parent.signal.transformed_data, autoLevels=True, autoRange=False)

        self.image_item = pg.ImageItem(self.parent.signal.transformed_data[0])
        self.image_plot = pg.PlotItem()
        self.image_tab = pg.ImageView(view=self.image_plot, imageItem=self.image_item)
        self.image_tab.view.enableAutoRange(enable=False)
        self.image_tab.view.setMouseEnabled(False, False)

        self.image_tab.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Image")
        self.image_tabs.addTab(self.video_tab, "Video")

        self.signal_tab = QTabWidget()
        self.signal_tab.addTab(self.signal_panel, "Signal")

        # Hide UI stuff not needed
        self.image_tab.ui.roiBtn.hide()
        self.image_tab.ui.menuBtn.hide()
        self.image_tab.ui.histogram.hide()

        self.image_tab.view.showAxes(False)
        self.image_tab.view.invertY(True)

        # size_policy = QSizePolicy()
        # size_policy.setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)
        # size_policy.setHorizontalPolicy(QSizePolicy.Policy.MinimumExpanding)
        # self.image_tab.setSizePolicy(size_policy)
        # self.image_tab.setMinimumWidth(380)
        # self.image_tab.setMinimumHeight(500)

        # signal_size_policy.setHorizontalStretch(5)
        # self.plot.setMinimumWidth(300)
        # self.plot.setMinimumHeight(600)

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_tab.setColorMap(cm)

        self.colorbar = self.image_plot.addColorBar(
            self.image_item,
            colorMap=cm,
            values=(0, 1),
            rounding=0.05,
        )

        img_layout.addWidget(self.image_tabs)


        self.init_options()
        self.update_signal_plot()
        img_layout.addWidget(self.options_widget)

        left_widget = QWidget()
        left_widget.setLayout(img_layout)

        central_layout.addWidget(left_widget)
        central_layout.addWidget(self.signal_tab)
        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options_1 = QToolBar()
        self.options_2 = QToolBar()
        self.actions_bar = QToolBar()

        self.threshold = Spinbox(
            min=0, max=1, val=0.5, step=0.1, min_width=60, max_width=60
        )
        self.threshold.valueChanged.connect(self.update_threshold_spinbox)
        self.start_frame = Spinbox(
            min=0,
            max=len(self.parent.signal.image_data) * self.ms,
            val=0,
            step=1,
            min_width=70,
            max_width=70,
        )
        self.cycles = Spinbox(
            min=1, max=1000, val=10, step=1, min_width=50, max_width=50
        )
        self.skip = Spinbox(min=1, max=100, val=1, step=1, min_width=50, max_width=50)

        self.options_1.addWidget(QLabel("Threshold: "))
        self.options_1.addWidget(self.threshold)
        self.options_1.addWidget(QLabel("Start Frame: "))
        self.options_1.addWidget(self.start_frame)
        self.options_2.addWidget(QLabel("Cycles: "))
        self.options_2.addWidget(self.cycles)
        self.options_2.addWidget(QLabel("Skip Frames: "))
        self.options_2.addWidget(self.skip)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)

        self.start_frame.valueChanged.connect(self.update_keyframe)

        self.cal_iso = QPushButton("Calculate")
        self.cal_iso_filled = QPushButton("Calculate Filled")
        self.cal_iso_video = QPushButton("Calculate Video")

        self.reset = QPushButton("Reset")
        self.cal_iso.clicked.connect(self.calculate_isochrome)
        self.cal_iso_filled.clicked.connect(self.calculate_isochrome_filled)
        self.cal_iso_video.clicked.connect(self.calculate_contour_video)        
        self.reset.clicked.connect(
            partial(self.update_keyframe)
        )
        self.actions_bar.addWidget(self.cal_iso)
        self.actions_bar.addWidget(self.cal_iso_filled)
        self.actions_bar.addWidget(self.cal_iso_video)
        self.actions_bar.addWidget(self.reset)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.options_2)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.update_threshold_spinbox()
        self.options_widget.setLayout(layout)

    def update_signal_plot(self):
        signal_data = self.signal.transformed_data[:, self.x, self.y]

        xs = self.xVals[0 : len(signal_data)]  # ensure len(xs) == len(signal_data)
        self.signal_panel.signal_data.setData(x=xs, y=signal_data)

    def update_signal_index(self, evt, idx=None):
        if not idx:
            idx = self.signal_panel.signal_marker.getXPos()
        self.start_frame.setValue(int(idx))
        idx = int(idx / self.ms)

        self.video_tab.image_view.setCurrentIndex(idx)
        self.image_tab.setImage(self.parent.signal.transformed_data[idx])

    def update_threshold_marker(self):
        self.threshold.setValue(round(self.signal_panel.threshold_marker.getYPos(), 2))
    
    def update_threshold_spinbox(self):
        self.signal_panel.threshold_marker.setValue(self.threshold.value())

    # TODO: Fix colorscale, add overlay mode, adjust y-axis value.
    def calculate_isochrome(self):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())

        isochrome = (
            _calculate_isochrome(
                self.parent.signal.transformed_data,
                t=self.threshold.value(),
                start_frame=int(self.start_frame.value()),
                cycles=cycles,
                skip_frame=skip_frames,
            )
            * self.parent.ms
        )

        self.image_item.setImage(isochrome)
        self.colorbar.setLevels((0, cycles * self.parent.ms * skip_frames))
        self.colorbar.setLabel("right", "ms")

    def calculate_isochrome_filled(self):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())

        isochrome = (
            _calculate_isochrome_filled(
                self.parent.signal.transformed_data,
                t=self.threshold.value(),
                start_frame=int(self.start_frame.value()),
                cycles=cycles,
                skip_frame=skip_frames,
            )
            * self.parent.ms
        )

        self.image_item.setImage(isochrome)
        self.colorbar.setLevels((0, cycles * self.parent.ms * skip_frames))
        self.colorbar.setLabel("right", "ms")
    
    def calculate_contour_video(self):

        self.contour_data = deepcopy(self.signal.transformed_data)
        t = self.threshold.value()
        cycles = int(self.cycles.value()) * int(self.skip.value())
        start_frame = int(self.start_frame.value())

        for _c in range(cycles):
            idx = start_frame + _c
            c = np.zeros((128, 128))
            for p in find_contours(self.contour_data[idx], level=t):
                for j in p:
                    c[int(j[0]), int(j[1])] = 1
                    c[int(j[0]), int(j[1])] = 1
                    c[int(j[0]), int(j[1])] = 1
                    c[int(j[0]), int(j[1])] = 1
                    c[int(j[0] - 1), int(j[1]) - 1] = 1
                    c[int(j[0]), int(j[1]) - 1] = 1
                    c[int(j[0] - 1), int(j[1])] = 1
            self.contour_data[idx][c>0] = 0

        self.video_tab.image_view.setImage(self.contour_data)
        

    def update_keyframe(self, i):
        idx = self.start_frame.value()
        self.signal_panel.update_signal_marker(idx)
        idx = self.signal_panel.signal_marker.getXPos()
        idx = int(idx / self.ms) 
        self.image_item.setImage(
            self.parent.signal.transformed_data[idx] * self.mask,
            autoLevels=True,
            autoRange=False,
        )
