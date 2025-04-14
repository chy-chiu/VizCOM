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
        self.output_view = pg.ImageView(levelMode='rgba')
        self.output_view.setImage(self.data[imgIdx])
        self.output_view.view.setMouseEnabled(False, False)


        self.output_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        self.image_views = QHBoxLayout()
        self.image_views.addWidget(self.image_view)
        self.image_views.addWidget(self.output_view)

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.output_view.ui.roiBtn.hide()
        self.output_view.ui.menuBtn.hide()
        self.output_view.ui.histogram.hide()

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_view.setColorMap(cm)

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
        self.options_2 = QToolBar()
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
        self.threshold_color_button = pg.ColorButton(color = (255, 255, 255))
        self.kernel_width = Spinbox(
            min=1,
            max=64,
            val=1,
            step=1,
            min_width=70,
            max_width=70,
        )

        self.options_1.addWidget(QLabel("Threshold: "))
        self.options_1.addWidget(self.threshold)
        self.options_1.addWidget(QLabel("Beat: "))
        self.options_1.addWidget(self.start_frame)
        self.options_1.addWidget(QLabel("Threshold Color:"))
        self.options_1.addWidget(self.threshold_color_button)
        self.options_2.addWidget(QLabel("Noise Removal Kernel Size (1 = disabled): "))
        self.options_2.addWidget(self.kernel_width)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)

        self.start_frame.valueChanged.connect(self.update_keyframe)
        self.kernel_width.valueChanged.connect(self.update_threshold)
        self.threshold_color_button.sigColorChanged.connect(self.update_threshold)

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
        start_frame = int(self.start_frame.value())
        kernel_width = int(self.kernel_width.value())
        threshMask = threshold(self.data[start_frame], self.threshold.value())

        if kernel_width > 1:
            kernel = np.ones((kernel_width, kernel_width))
            # opening
            threshMask = cv2.erode(threshMask, kernel)
            threshMask = cv2.dilate(threshMask, kernel)

            # closing
            threshMask = cv2.dilate(threshMask, kernel)
            threshMask = cv2.erode(threshMask, kernel)
        
        # mask grayscale image
        outputImage = self.data[start_frame] * threshMask

        # contouring 
        contours = find_contours(outputImage, self.threshold.value())

        # normalize, [0-511]
        levels = self.image_view.ui.histogram.item.getLevels()
        outputImage -= levels[0]
        outputImage /= levels[1]
        outputImage *= 511
        outputImage[outputImage > 511] = 511

        # convert to color
        lut = self.image_view.getHistogramWidget().gradient.colorMap().getLookupTable()
        outputImage = np.take(lut, outputImage.astype(np.uint16), axis=0)

        # add color contours
        for contour in contours:
            for p in contour:
                outputImage[int(p[0]), int(p[1]), :] = self.threshold_color_button.color().getRgb()[:3]

        # set image
        self.output_view.setImage(outputImage)

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
        
        
