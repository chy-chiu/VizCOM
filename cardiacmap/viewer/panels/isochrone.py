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
from cv2 import dilate
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
        mask = arr == level
        # Fill holes within the contour
        filled_mask = binary_fill_holes(mask)
        # Update the result where the filled mask is True and the current value is less than the contour level
        result[filled_mask & (result < level)] = level
    return result


def fill_contours_with_morphology(arr):
    seed = arr.copy()
    seed[arr == 0] = np.max(arr) + 1
    mask = arr
    filled = reconstruction(seed, mask, method="erosion")
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
    zero_mask = arr == 0
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


def _calculate_isochrone(
    sig: np.ndarray,
    t: float,
    start_frame,
    cycles,
    skip_frame,
    lut,
    lutLevels,
    line=False,
    update_progress=None,
    upstroke=True,
    downstroke=False,
    color=np.array([255, 0, 255]),
    thickness=1
):

    all_c = []
    if line:
        # normalize, [0-511]
        output_img = np.copy(sig[start_frame])
        output_img -= lutLevels[0]
        output_img /= lutLevels[1] - lutLevels[0]
        output_img *= 511
        output_img[output_img > 511] = 511
        output_img[output_img < 0] = 0
        output_img = output_img.astype(np.uint16)
        # convert to color
        output_img = np.take(lut, output_img, axis=0)
    else:
        output_img = np.zeros((128, 128, 3))

    for i in range(cycles):

        idx = i * skip_frame + start_frame

        prev_idx = (i - 1) * skip_frame + start_frame if i > 0 else start_frame

        # Make sure it doesn't get past the end of signal
        if idx < len(sig):

            contour_points = find_contours(sig[idx], level=t)

            # Generate empty slice of where contours would be
            c = np.zeros((128, 128))

            for contour_line in contour_points:

                _countour_line = np.array(contour_line).astype(int)

                # Check if upstroke or downstroke, by majority
                # wave_direction = np.sign(sig[idx, _countour_line[:, 0], _countour_line[:, 1]] - sig[prev_idx, _countour_line[:, 0], _countour_line[:, 1]])
                # if np.mean(wave_direction) >= 0:
                #     is_upstroke = True
                # else:
                #     is_upstroke = False

                # if (is_upstroke and upstroke) or (not is_upstroke and downstroke):
                #     for c_point in contour_line:
                #         c[int(c_point[0]), int(c_point[1])] = 1

                # Alternate version: Single points only
                for point in _countour_line:
                    x, y = point
                    point_diff = sig[idx, x, y] - sig[prev_idx, x, y]
                    is_upstroke = True if point_diff >= 0 else False
                    if (is_upstroke and upstroke) or (not is_upstroke and downstroke):
                        c[x, y] = 1

            _c = np.array(c)
            if thickness > 1:
                _c = dilate(_c, np.ones((thickness, thickness)))

            coords = np.argwhere(_c > 0)
            for r,c in coords:
                output_img[r, c] =  color

            all_c.append(c)

        if update_progress:
            update_progress(i / cycles)

    return output_img

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
        self.video_tab.data_bar.hide()
        self.video_tab.image_view.setImage(
            np.zeros((128, 128)), autoLevels=True, autoRange=True
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

        self.output_item = pg.ImageItem(np.zeros((128,128)))
        self.output_plot = pg.PlotItem()
        self.output_tab = pg.ImageView(view=self.output_plot, imageItem=self.output_item)
        self.output_tab.view.setMouseEnabled(False, False)

        self.output_tab.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        self.image_tabs = QTabWidget()
        self.image_tabs.addTab(self.image_tab, "Input Image")
        self.image_tabs.addTab(self.output_tab, "Output Image")
        self.image_tabs.addTab(self.video_tab, "Video")

        self.signal_tab = QTabWidget()
        self.signal_tab.addTab(self.signal_panel, "Signal")

        # Hide UI stuff not needed
        self.image_tab.ui.roiBtn.hide()
        self.image_tab.ui.menuBtn.hide()
        self.image_tab.view.showAxes(False)
        self.image_tab.view.invertY(True)

        self.output_tab.ui.roiBtn.hide()
        self.output_tab.ui.menuBtn.hide()
        self.output_tab.ui.histogram.hide()
        self.output_tab.view.showAxes(False)
        self.output_tab.view.invertY(True)

        self.video_tab.image_view.ui.roiBtn.hide()
        self.video_tab.image_view.ui.menuBtn.hide()
        self.video_tab.image_view.ui.histogram.hide()
        self.video_tab.image_view.view.showAxes(False)
        self.video_tab.image_view.view.invertY(True)

        # size_policy = QSizePolicy()
        # size_policy.setVerticalPolicy(QSizePolicy.Policy.MinimumExpanding)
        # size_policy.setHorizontalPolicy(QSizePolicy.Policy.MinimumExpanding)
        # self.image_tab.setSizePolicy(size_policy)
        # self.signal_tab.setMinimumWidth(500)
        # self.image_tab.setMinimumHeight(500)

        # signal_size_policy.setHorizontalStretch(5)
        # self.plot.setMinimumWidth(300)
        # self.plot.setMinimumHeight(600)

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_tab.setColorMap(cm)

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
        self.resize(900, 500)

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

        self.showUpstroke = QCheckBox()
        self.showUpstroke.setChecked(True)
        self.showDownstroke = QCheckBox()
        self.showDownstroke.setChecked(True)

        self.color_button = pg.ColorButton(color = (255, 255, 255))
        self.thickness = Spinbox(
            min=1,
            max=10,
            val=1,
            step=1,
            min_width=70,
            max_width=70,
        )

        self.options_1.addWidget(QLabel("Threshold: "))
        self.options_1.addWidget(self.threshold)
        self.options_1.addWidget(QLabel("Upstroke: "))
        self.options_1.addWidget(self.showUpstroke)
        self.options_1.addWidget(QLabel("Downstroke: "))
        self.options_1.addWidget(self.showDownstroke)
        self.options_1.addWidget(QLabel("Color: "))
        self.options_1.addWidget(self.color_button)
        self.options_1.addWidget(QLabel("Thickness: "))
        self.options_1.addWidget(self.thickness)
        self.options_2.addWidget(QLabel("Start Time: "))
        self.options_2.addWidget(self.start_frame)
        self.options_2.addWidget(QLabel("# of Steps: "))
        self.options_2.addWidget(self.cycles)
        self.options_2.addWidget(QLabel("Step Size (frames): "))
        self.options_2.addWidget(self.skip)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)

        self.start_frame.valueChanged.connect(self.update_keyframe)

        self.cal_iso_color = QPushButton("Calculate Color")
        self.cal_iso_lines = QPushButton("Calculate Lines")
        self.cal_iso_filled = QPushButton("Calculate Filled")
        self.cal_iso_video = QPushButton("Calculate Video")

        self.reset = QPushButton("Reset")
        self.cal_iso_color.clicked.connect(
            partial(self.calculate_isochrone, line=False)
        )
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

        upstroke = self.showUpstroke.isChecked()
        downstroke = self.showDownstroke.isChecked()

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())
        start_frame = int(self.start_frame.value() / self.ms)

        lut = self.image_tab.getHistogramWidget().gradient.colorMap().getLookupTable()
        levels = self.image_tab.ui.histogram.item.getLevels()
        color = self.color_button.color().getRgb()[:3]
        thickness = int(self.thickness.value())

        isochrone = (
            _calculate_isochrone(
                self.parent.signal.transformed_data,
                t=self.threshold.value(),
                start_frame=start_frame,
                cycles=cycles,
                skip_frame=skip_frames,
                lut=lut,
                lutLevels=levels,
                line=line,
                upstroke=upstroke,
                downstroke=downstroke,
                color=color,
                thickness=thickness
            )
            * self.parent.ms
        )

        self.output_item.setImage(isochrone)
        self.image_tabs.setCurrentIndex(1)

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

        self.output_item.setImage(isochrone)
        self.image_tabs.setCurrentIndex(1)

    def calculate_contour_video(self):
        t = self.threshold.value()
        cycles = int(self.cycles.value()) * int(self.skip.value())
        start_frame = int(self.start_frame.value() / self.ms)

        self.contour_data = deepcopy(self.signal.transformed_data[start_frame: start_frame + cycles])
        video_output = np.zeros((len(self.contour_data), 128, 128, 3))

        lut = self.image_tab.getHistogramWidget().gradient.colorMap().getLookupTable()
        levels = self.image_tab.ui.histogram.item.getLevels()
        color = self.color_button.color().getRgb()[:3]
        thickness = int(self.thickness.value())

        for i in range(cycles):
            image = _calculate_isochrone(self.contour_data[None, i], t, 0, 1, 1, lut, levels, True, False, color=color, thickness=thickness )
            video_output[i] = image

        self.video_tab.image_view.setImage(video_output)
        self.video_tab.image_view.setCurrentIndex(start_frame)
        self.image_tabs.setCurrentIndex(2)

    def update_keyframe(self, i=None):
        idx = self.signal_panel.signal_marker.getXPos()
        idx = int(idx / self.ms)
        self.signal_panel.update_signal_marker(idx)
        self.image_item.setImage(
            self.parent.signal.transformed_data[idx] * self.mask,
            autoLevels=True,
            autoRange=True,
        )
