from functools import partial

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
from skimage.measure import find_contours

from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.utils import loading_popup
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

# def _calculate_isochrone_filled(
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

class APDIsochroneWindow(QMainWindow):

    def __init__(self, parent, img, data):

        super().__init__()
        self.parent = parent
        self.mask = parent.mask
        self.ms = parent.ms
        self.data = data

        self.setWindowTitle("Isochrone View")

        img_layout = QVBoxLayout()

        self.x, self.y = 64, 64
        print("SHAPE: ", data.shape)

        self.image_view = pg.ImageView()
        self.image_view.setImage(img)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        self.image_views = QTabWidget()
        self.image_views.addTab(self.image_view, "Image")

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()

        #self.image_view.view.showAxes(False)
        #self.image_view.view.invertY(True)

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_view.setColorMap(cm)

        img_layout.addWidget(self.image_views)

        self.init_options()
        img_layout.addWidget(self.options_widget)

        widget = QWidget()
        widget.setLayout(img_layout)
        self.setCentralWidget(widget)
        self.resize(400, 500)

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options_1 = QToolBar()
        self.options_2 = QToolBar()
        self.actions_bar = QToolBar()

        self.threshold = Spinbox(
            min=0, max=1000, val=25, step=1, min_width=60, max_width=60
        )
        self.threshold.valueChanged.connect(self.update_threshold)
        self.start_frame = Spinbox(
            min=0,
            max=1000, # SET MAX TO NUMBER OF BEATS
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
        self.options_1.addWidget(QLabel("Start Beat: "))
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

        self.reset = QPushButton("Reset")
        self.cal_iso_color.clicked.connect(partial(self.calculate_isochrone, line=False))
        self.cal_iso_lines.clicked.connect(partial(self.calculate_isochrone, line=True))
        self.cal_iso_filled.clicked.connect(self.calculate_isochrone_filled)
        self.reset.clicked.connect(partial(self.update_keyframe))
        self.actions_bar.addWidget(self.cal_iso_color)
        self.actions_bar.addWidget(self.cal_iso_lines)
        self.actions_bar.addWidget(self.cal_iso_filled)
        self.actions_bar.addWidget(self.reset)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.options_2)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.update_threshold()
        self.options_widget.setLayout(layout)


    def update_threshold_marker(self):
        self.threshold.setValue(round(self.signal_panel.threshold_marker.getYPos(), 2))

    def update_threshold(self):
        print("Threshold Value", self.threshold.value())

    # TODO: Fix colorscale, add overlay mode, adjust y-axis value.
    def calculate_isochrone(self, line=False):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())
        start_frame = int(self.start_frame.value())

        isochrone = (
            _calculate_isochrone(
                self.data,
                t=self.threshold.value(),
                start_frame=start_frame,
                cycles=cycles,
                skip_frame=skip_frames,
                line=line
            )
        )

        self.image_view.setImage(isochrone)

    def calculate_isochrone_filled(self):

        cycles = int(self.cycles.value())
        skip_frames = int(self.skip.value())

        start_frame = int(self.start_frame.value())

        isochrone = (
            _calculate_isochrone_filled(
                self.data,
                t=self.threshold.value(),
                start_frame=start_frame,
                cycles=cycles,
                skip_frame=skip_frames,
            )
        )

        self.image_view.setImage(isochrone)

    def update_keyframe(self):
        levels = self.image_view.ui.histogram.item.getLevels()

        self.image_view.setImage(self.data[int(self.start_frame.value())])

        self.image_view.setLevels(levels[0], levels[1])
        self.image_view.ui.histogram.item.setHistogramRange(levels[0] - 5, levels[1] + 5)
        #self.update_threshold()
        
        
