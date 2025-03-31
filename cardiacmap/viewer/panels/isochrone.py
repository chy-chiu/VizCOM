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
from scipy.ndimage.morphology import binary_fill_holes
from skimage.morphology import reconstruction
from scipy.ndimage import label

import heapq


QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128

def fill_contours(arr):
    # Copy the input array to avoid modifying the original data
    result = arr.copy()
    # Get unique contour levels, excluding zero (background)
    levels = sorted(set(arr.flatten()))
    levels = [level for level in levels if level > 0]
    # Process levels in decreasing order to handle higher contours first
    for level in reversed(levels):
        # Create a mask for the current contour level
        mask = (arr == level)
        # Fill holes within the contour
        filled_mask = binary_fill_holes(mask)
        # Update the result where the filled mask is True and the current value is less than the contour level
        result[filled_mask & (result < level)] = level
    return result

def fill_contours_with_morphology(arr):
    seed = arr.copy()
    seed[arr == 0] = np.max(arr) + 1
    mask = arr
    filled = reconstruction(seed, mask, method='erosion')
    return filled

def fill_zeros_with_min_adjacent(arr):
    nrows, ncols = arr.shape
    filled = np.full((nrows, ncols), np.inf)
    visited = np.zeros((nrows, ncols), dtype=bool)

    # Initialize the priority queue with non-zero elements
    heap = []
    for i in range(nrows):
        for j in range(ncols):
            if arr[i, j] != 0:
                filled[i, j] = arr[i, j]
                heapq.heappush(heap, (arr[i, j], i, j))
                visited[i, j] = True

    # Directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while heap:
        value, i, j = heapq.heappop(heap)
        for di, dj in directions:
            ni, nj = i + di, j + dj
            if 0 <= ni < nrows and 0 <= nj < ncols and not visited[ni, nj]:
                # Assign the current minimal value to the neighbor
                filled[ni, nj] = value
                visited[ni, nj] = True
                # Push the neighbor onto the heap with the same value
                heapq.heappush(heap, (value, ni, nj))

    # Replace any remaining infinities with zeros (if any)
    filled[np.isinf(filled)] = 0
    return filled


def fill_zeros_with_max_adjacent(arr):
    nrows, ncols = arr.shape
    filled = np.full((nrows, ncols), -np.inf)
    visited = np.zeros((nrows, ncols), dtype=bool)

    # Initialize the priority queue with non-zero elements
    heap = []
    for i in range(nrows):
        for j in range(ncols):
            if arr[i, j] != 0:
                filled[i, j] = arr[i, j]
                # Push negative value to simulate max-heap
                heapq.heappush(heap, (-arr[i, j], i, j))
                visited[i, j] = True

    # Directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    while heap:
        # Pop the largest value (smallest negative value)
        neg_value, i, j = heapq.heappop(heap)
        value = -neg_value  # Convert back to positive
        for di, dj in directions:
            ni, nj = i + di, j + dj
            if 0 <= ni < nrows and 0 <= nj < ncols and not visited[ni, nj]:
                # Assign the current maximal value to the neighbor
                filled[ni, nj] = value
                visited[ni, nj] = True
                # Push the neighbor onto the heap with the same value
                heapq.heappush(heap, (-value, ni, nj))

    # Replace any remaining negative infinities with zeros (if any)
    filled[filled == -np.inf] = 0
    return filled

def fill_zeros_with_mean_of_neighbors(arr):
    nrows, ncols = arr.shape
    filled = arr.copy()

    # Label connected components of zeros
    zero_mask = (arr == 0)
    labeled_array, num_features = label(zero_mask)

    # Directions: up, down, left, right
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    for region_label in range(1, num_features + 1):
        # Find the coordinates of the current region
        region_coords = np.argwhere(labeled_array == region_label)
        neighbor_values = []

        # Collect non-zero neighbors for the entire region
        for i, j in region_coords:
            for di, dj in directions:
                ni, nj = i + di, j + dj
                if 0 <= ni < nrows and 0 <= nj < ncols and arr[ni, nj] != 0:
                    neighbor_values.append(arr[ni, nj])

        # Calculate the mean of the non-zero neighbors
        if neighbor_values:
            mean_value = int(np.mean(neighbor_values))
        else:
            mean_value = 0  # If no non-zero neighbors, default to zero

        # Fill the entire region with the mean value
        for i, j in region_coords:
            filled[i, j] = mean_value

    return filled

def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140]) / 255


@loading_popup
def _calculate_isochrone(
    sig: np.ndarray, t: float, start_frame, cycles, skip_frame, line=False, update_progress=None
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

    if line: 
        img = np.where(_c > 0, 0, sig[start_frame])
        return img
    else:
        return _c

# def _calculate_isochrome_filled(
#     sig: np.ndarray, t: float, start_frame, cycles, skip_frame
# ):
#     offset = cycles * skip_frame * 2
#     DPI = 128
#     figsize = (1, 1)  # Inches
#     fig, ax = plt.subplots(figsize=figsize, dpi=DPI)
#     ax.axis("off")
#     ax.contourf(
#         (sig[start_frame : start_frame + offset] > t).argmin(axis=0),
#         levels=range(0, cycles * skip_frame, skip_frame),
#         cmap="gray",
#     )
#     plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
#     ax.invert_yaxis()
#     ax.set_aspect("equal")
#     fig.canvas.draw()
#     image = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
#     image = image.reshape((DPI, DPI, 3))
#     return np.round(rgb2gray(image) * cycles) * skip_frame

def _calculate_isochrone_filled(
    sig: np.ndarray, t: float, start_frame, cycles, skip_frame
):
    C = _calculate_isochrone(sig, t, start_frame, cycles, skip_frame)

    return fill_zeros_with_mean_of_neighbors(fill_contours(C))

class IsochroneSignalPanel(SignalPanel):
    def __init__(self, parent, settings):
        super().__init__(parent=parent, settings=settings)
        self.parent = parent
        # self.plot = SignalPlot(self)
        # signal_size_policy = QtWidgets.QSizePolicy()
        # signal_size_policy.setHorizontalPolicy(
        #     QtWidgets.QSizePolicy.Policy.Expanding
        # )
        # self.plot.setSizePolicy(signal_size_policy)

        self.signal_marker = pg.InfiniteLine(angle=90, movable=True)
        self.threshold_marker = pg.InfiniteLine(angle=0, movable=True)
        self.threshold_marker.setPen(pg.mkPen("g"))

        self.signal_marker.sigPositionChangeFinished.connect(
            self.parent.update_signal_index
        )
        self.threshold_marker.sigPositionChangeFinished.connect(
            self.parent.update_threshold_marker
        )

        # self.signal_data: pg.PlotDataItem = self.plot.plot(
        #     pen=self.parent.parent.signal_panel.sig_pen, symbol="o", symbolSize=0
        # )
        self.plot.addItem(self.signal_marker, ignoreBounds=True)
        self.plot.addItem(self.threshold_marker, ignoreBounds=True)

        self.resize(600, 300)
        # self.plot.resize(self.width(), self.height())

    def update_signal_marker(self, idx):
        self.frame_idx = int(idx)
        self.signal_marker.setX(int(idx * self.parent.parent.ms))


class IsochroneWindow(QMainWindow):

    def __init__(self, parent):

        super().__init__()
        self.parent = parent
        self.mask = parent.signal.mask
        self.signal = self.parent.signal
        self.xVals = self.parent.xVals
        self.ms = self.parent.ms
        self.setWindowTitle("Isochrone View")
        self.settings = parent.settings

        self.signal_panel = IsochroneSignalPanel(self, settings=self.settings)

        img_layout = QVBoxLayout()
        central_layout = QHBoxLayout()

        self.x, self.y = 64, 64

        self.video_tab = PositionView(self)
        self.video_tab.image_view.setImage(
            self.parent.signal.transformed_data, autoLevels=True, autoRange=True
        )
        self.video_tab.framerate.setValue(10)
        self.video_tab.skiprate.setValue(1)

        self.image_item = pg.ImageItem(self.parent.signal.transformed_data[0])
        self.image_plot = pg.PlotItem()
        self.image_tab = pg.ImageView(view=self.image_plot, imageItem=self.image_item)
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
        self.signal_tab.setMinimumWidth(380)
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
        self.resize(800, 500)

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
            min=1, max=1000, val=10, step=1, min_width=60, max_width=60
        )
        self.skip = Spinbox(min=1, max=100, val=1, step=1, min_width=50, max_width=50)

        self.options_1.addWidget(QLabel("Threshold: "))
        self.options_1.addWidget(self.threshold)
        self.options_1.addWidget(QLabel("Start Time: "))
        self.options_1.addWidget(self.start_frame)
        self.options_2.addWidget(QLabel("# of Steps: "))
        self.options_2.addWidget(self.cycles)
        self.options_2.addWidget(QLabel("Step Interval: "))
        self.options_2.addWidget(self.skip)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)

        self.start_frame.valueChanged.connect(self.update_keyframe)

        self.cal_iso_color = QPushButton("Calculate Color")
        self.cal_iso_lines = QPushButton("Calculate Lines")
        self.cal_iso_filled = QPushButton("Calculate Filled")
        self.cal_iso_video = QPushButton("Calculate Video")

        self.reset = QPushButton("Reset")
        self.cal_iso_color.clicked.connect(partial(self.calculate_isochrone, line=False))
        self.cal_iso_lines.clicked.connect(partial(self.calculate_isochrone, line=True))
        self.cal_iso_filled.clicked.connect(self.calculate_isochrone_filled)
        self.cal_iso_video.clicked.connect(self.calculate_contour_video)
        self.reset.clicked.connect(partial(self.update_keyframe))
        self.actions_bar.addWidget(self.cal_iso_color)
        self.actions_bar.addWidget(self.cal_iso_lines)
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
    def calculate_isochrone(self, line=False):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())
        start_frame = int(self.start_frame.value() / self.ms)

        isochrone = (
            _calculate_isochrone(
                self.parent.signal.transformed_data,
                t=self.threshold.value(),
                start_frame=start_frame,
                cycles=cycles,
                skip_frame=skip_frames,
                line=line
            )
            * self.parent.ms
        )

        self.image_item.setImage(isochrone)
        if not line: 
            self.colorbar.setLevels((0, cycles * self.parent.ms * skip_frames))
        
        self.colorbar.setLabel("right", "ms")

    def calculate_isochrone_filled(self):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())

        start_frame = int(self.start_frame.value() / self.ms)

        isochrone = (
            _calculate_isochrone_filled(
                self.parent.signal.transformed_data,
                t=self.threshold.value(),
                start_frame=start_frame,
                cycles=cycles,
                skip_frame=skip_frames,
            )
            * self.parent.ms
        )

        self.image_item.setImage(isochrone)
        self.colorbar.setLevels((0, cycles * self.parent.ms * skip_frames))
        self.colorbar.setLabel("right", "ms")

    def calculate_contour_video(self):

        self.contour_data = deepcopy(self.signal.transformed_data)
        t = self.threshold.value()
        cycles = int(self.cycles.value()) * int(self.skip.value())
        start_frame = int(self.start_frame.value() / self.ms)

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
            self.contour_data[idx][c > 0] = 0

        self.video_tab.image_view.setImage(self.contour_data)
        self.video_tab.image_view.setCurrentIndex(start_frame)

    def update_keyframe(self, i):
        idx = self.start_frame.value()
        self.signal_panel.update_signal_marker(idx)
        idx = self.signal_panel.signal_marker.getXPos()
        idx = int(idx / self.ms)
        self.image_item.setImage(
            self.parent.signal.transformed_data[idx] * self.mask,
            autoLevels=True,
            autoRange=True,
        )
        
        
