import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
import cv2
from skimage.measure import find_contours
from cardiacmap.viewer.components import Spinbox


QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128

def threshold(sig: np.ndarray, threshold: float):
    output = np.zeros(sig.shape)
    output[sig >= threshold] = 1
    return output

class APDThresholdWindow(QMainWindow):

    def __init__(self, parent, imgIdx, data):

        super().__init__()
        self.parent = parent
        self.mask = parent.mask
        self.ms = parent.ms
        self.data = data * self.mask
        self.initFrame = imgIdx

        self.setWindowTitle("Thresholding")

        img_layout = QVBoxLayout()

        self.x, self.y = 64, 64

        self.image_view = pg.ImageView()
        self.image_view.setImage(self.data[imgIdx])
        self.image_view.ui.histogram.item.sigLevelChangeFinished.connect(self.update_keyframe)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )
        self.output_view = pg.ImageView()
        self.output_view.setImage(self.data[imgIdx])
        self.output_view.view.setMouseEnabled(False, False)

        self.output_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        #self.image_views = QTabWidget()
        #self.image_views.addTab(self.image_view, "Image")
        #self.image_views.addTab(self.output_view, "Output")
        self.image_views = QHBoxLayout()
        self.image_views.addWidget(self.image_view)
        self.image_views.addWidget(self.output_view)

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.output_view.ui.roiBtn.hide()
        self.output_view.ui.menuBtn.hide()

        #self.image_view.view.showAxes(False)
        #self.image_view.view.invertY(True)

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_view.setColorMap(cm)
        self.output_view.setColorMap(cm)

        img_layout.addLayout(self.image_views)

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
        self.actions_bar = QToolBar()

        self.threshold = Spinbox(
            min=0, max=1000, val=25, step=1, min_width=60, max_width=60
        )
        self.threshold.valueChanged.connect(self.update_threshold)
        self.start_frame = Spinbox(
            min=self.initFrame,
            max=1000, # SET MAX TO NUMBER OF BEATS
            val=0,
            step=1,
            min_width=70,
            max_width=70,
        )
        self.kernel_width = Spinbox(
            min=0,
            max=64,
            val=2,
            step=1,
            min_width=70,
            max_width=70,
        )

        self.options_1.addWidget(QLabel("Threshold: "))
        self.options_1.addWidget(self.threshold)
        self.options_1.addWidget(QLabel("Beat: "))
        self.options_1.addWidget(self.start_frame)
        self.options_1.addWidget(QLabel("Kernel Width: "))
        self.options_1.addWidget(self.kernel_width)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)

        self.start_frame.valueChanged.connect(self.update_keyframe)
        self.kernel_width.valueChanged.connect(self.update_threshold)

        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.update_threshold()
        self.options_widget.setLayout(layout)


    def update_threshold_marker(self):
        self.threshold.setValue(round(self.signal_panel.threshold_marker.getYPos(), 2))

    def update_threshold(self):
        start_frame = int(self.start_frame.value())
        kernel_width = int(self.kernel_width.value())
        threshMask = threshold(self.data[start_frame], self.threshold.value())
        outputImage = self.data[start_frame] * threshMask

        if kernel_width > 1:
            kernel = np.ones((kernel_width, kernel_width))
            # opening
            outputImage = cv2.erode(outputImage, kernel)
            outputImage = cv2.dilate(outputImage, kernel)

            # closing
            outputImage = cv2.dilate(outputImage, kernel)
            outputImage = cv2.erode(outputImage, kernel)

        self.output_view.setImage(outputImage)

        # contouring 
        contours = find_contours(outputImage, self.threshold.value())
        for contour in contours:
            for p in contour:
                outputImage[int(p[0]), int(p[1])] = self.data[start_frame].max()

        # set levels
        levels = self.image_view.ui.histogram.item.getLevels()
        self.output_view.setLevels(levels[0], levels[1])
        self.output_view.ui.histogram.item.setHistogramRange(levels[0], levels[1])

    def update_keyframe(self):
        levels = self.image_view.ui.histogram.item.getLevels()
        # block signals to avoid recursive callback
        self.image_view.ui.histogram.item.blockSignals(True)

        # set image
        self.image_view.setImage(self.data[int(self.start_frame.value())])

        # set levels
        self.image_view.setLevels(levels[0], levels[1])
        self.image_view.ui.histogram.item.setHistogramRange(levels[0], levels[1])

        # unblock signals
        self.image_view.ui.histogram.item.blockSignals(False)

        self.update_threshold()
        
        
