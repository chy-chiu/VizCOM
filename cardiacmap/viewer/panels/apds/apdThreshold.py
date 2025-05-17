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
from cv2 import dilate
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
        self.options_layout = QVBoxLayout()
        self.options_1 = QToolBar()

        self.num_thresholds = Spinbox(
            min=1, max=100, val=1, step=1, min_width=60, max_width=60
        )

        self.start_frame = Spinbox(
            min=self.initFrame,
            max=100000, # SET MAX TO NUMBER OF BEATS
            val=0,
            step=1,
            min_width=70,
            max_width=70,
        )

        self.thickness = Spinbox(
            min=1,
            max=10,
            val=1,
            step=1,
            min_width=70,
            max_width=70,
        )

        self.contour_list_layout = QVBoxLayout()
        self.contour_list = []

        # set listeners
        self.start_frame.valueChanged.connect(self.update_keyframe)
        self.num_thresholds.valueChanged.connect(self.update_threshold)
        self.thickness.valueChanged.connect(self.update_threshold)

        # set up toolbars
        self.options_1.addWidget(QLabel("Beat: "))
        self.options_1.addWidget(self.start_frame)

        self.options_1.addWidget(QLabel("# of Contours: "))
        self.options_1.addWidget(self.num_thresholds)

        self.options_1.addWidget(QLabel("Thickness: "))
        self.options_1.addWidget(self.thickness)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)

        # initialize layout
        self.options_layout.addWidget(self.options_1)
        self.options_layout.addSpacing(5)

        self.update_threshold()
        self.options_widget.setLayout(self.options_layout)


    def update_threshold_marker(self):
        self.threshold.setValue(round(self.signal_panel.threshold_marker.getYPos(), 2))

    def update_contour_list(self):
        num = int(self.num_thresholds.value())
        listLen = len(self.contour_list)
        diff = listLen - num
        if diff != 0:
            if diff < 0:
                #add threshold
                for i in range(-diff):
                    cli = self.ContourListItem(self)
                    self.contour_list.append(cli)

                    if len(self.contour_list) == 1:
                            self.threshold = cli.threshold
                            self.threshold_color_button = cli.color_button

                    self.options_layout.addWidget(cli)
            else:
                #remove threshold
                for i in range(diff):
                    cli = self.contour_list[-1]
                    self.contour_list.remove(cli)
                    self.options_layout.removeWidget(cli)
                    cli.delete()

    def update_threshold(self):
        self.update_contour_list()
        start_frame = int(self.start_frame.value())

        outputImage = np.copy(self.data[start_frame])

        thickness = int(self.thickness.value())

        # contouring 
        c = []
        for i in range(int(self.num_thresholds.value())):
            contours = find_contours(outputImage, self.contour_list[i].threshold.value())
            c.append(contours)

        # normalize, [0-511]
        levels = self.image_view.ui.histogram.item.getLevels()
        outputImage -= levels[0]
        outputImage /= levels[1] - levels[0]
        outputImage *= 511
        outputImage[outputImage > 511] = 511
        outputImage[outputImage < 0] = 0
        outputImage = outputImage.astype(np.uint16)

        #print(outputImage.min(), outputImage.max())

        # convert to color
        lut = self.image_view.getHistogramWidget().gradient.colorMap().getLookupTable()
        outputImage = np.take(lut, outputImage, axis=0)

        # color contours
        contour_image = np.zeros((128,128))
        for i in range(int(self.num_thresholds.value())):
            contours = c[i]
            for contour in contours:
                for p in contour:
                    #print(self.contour_list[i].color_button.color().getRgb()[:3])
                    contour_image[int(p[0]), int(p[1])] = 1

        # add thickness
        if thickness > 1:
            contour_image = dilate(contour_image, np.ones((thickness, thickness)))

        # apply to image
        coords = np.argwhere(contour_image > 0)
        for r,c in coords:
            outputImage[r, c, :] = self.contour_list[i].color_button.color().getRgb()[:3]

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

    class ContourListItem(QWidget):
        def  __init__(self, parent):
            QWidget.__init__(self)

            self.parent = parent

            self.threshold = Spinbox(
                min=0, max=1000, val=5*len(parent.contour_list), step=1, min_width=60, max_width=60
            )
            self.threshold.valueChanged.connect(parent.update_threshold)

            self.color_button = pg.ColorButton(color = (255, 255, 255))
            self.color_button.sigColorChanged.connect(parent.update_threshold)

            self.t_label = QLabel("Threshold:")
            self.tc_label = QLabel("Threshold Color:")

            self.layout = QHBoxLayout()
            self.layout.addWidget(self.t_label)
            self.layout.addWidget(self.threshold)
            self.layout.addWidget(self.tc_label)
            self.layout.addWidget(self.color_button)
            self.layout.addStretch()

            self.setLayout(self.layout)

        def delete(self):
            self.color_button.setParent(None)
            self.threshold.setParent(None)
            self.t_label.setParent(None)
            self.tc_label.setParent(None)
            self.setLayout(None)
            self.destroy()



        
