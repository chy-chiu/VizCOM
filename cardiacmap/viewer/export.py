import numpy as np
import cv2
import time
import pyqtgraph as pg
from functools import partial
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
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
from cardiacmap.viewer.utils import loading_popup

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128
    
class ExportVideoWindow(QMainWindow):

    def __init__(self, parent):

        super().__init__()
        self.parent = parent
        self.ms = parent.signal_panel.ms_per_frame.value()
        self.mask = parent.signal.mask
        self.setWindowTitle("Export Video")

        central_widget = QWidget()
        layout = QVBoxLayout()

        self.image_item = pg.ImageItem(self.parent.signal.transformed_data[0])
        self.plot_item = pg.PlotItem()
        self.image_view = pg.ImageView(view=self.plot_item, imageItem=self.image_item)
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.image_view.ui.histogram.hide()

        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        size_policy = QSizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        self.image_view.setSizePolicy(size_policy)
        self.image_view.setMinimumWidth(380)
        self.image_view.setMinimumHeight(500)

        self.image_view.view

        cm = pg.colormap.get("nipy_spectral", source="matplotlib")
        self.image_view.setColorMap(cm)

        self.colorbar = self.plot_item.addColorBar(
            self.image_item,
            colorMap=cm,
            values=(0, 1),
            rounding=0.05,
        )

        layout.addWidget(self.image_view)

        self.init_options()
        layout.addWidget(self.options_widget)

        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options_1 = QToolBar()
        self.options_2 = QToolBar()
        self.actions_bar = QToolBar()
        
        self.start_time = Spinbox(
            min=0,
            max=len(self.parent.signal.transformed_data) * self.ms - 1,
            val=0,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.end_time = Spinbox(
            min=1,
            max=len(self.parent.signal.transformed_data) * self.ms,
            val=len(self.parent.signal.transformed_data) * self.ms,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.fps = Spinbox(
            min=1,
            max=500,
            val=50,
            step=1,
            min_width=60,
            max_width=60,
        )
        self.filename = QLineEdit("video-" + str(int(time.time())) + ".mkv")
        self.use_color = QCheckBox()
        self.options_1.addWidget(QLabel("Start Time: "))
        self.options_1.addWidget(self.start_time)
        self.options_1.addWidget(QLabel("End Time: "))
        self.options_1.addWidget(self.end_time)
        self.options_2.addWidget(QLabel("FPS: "))
        self.options_2.addWidget(self.fps)
        self.options_2.addWidget(QLabel("Use Color: "))
        self.options_2.addWidget(self.use_color)
        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)

        self.start_time.valueChanged.connect(self.update_keyframe)

        self.confirm = QPushButton("Export")
        self.confirm.clicked.connect(self.export_video)
        self.actions_bar.addWidget(self.confirm)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.filename)
        layout.addSpacing(5)
        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.options_2)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.options_widget.setLayout(layout)

    def update_keyframe(self, i):
        self.image_item.setImage(
            self.parent.signal.transformed_data[int(i // self.ms)] * self.mask,
            autoLevels=False,
            autoRange=False,
        )
        
    def export_video(self):
        # slice data
        s_frame = int(self.start_time.value() // self.ms)
        e_frame = int(self.end_time.value() // self.ms)
        if e_frame <= s_frame:
            e_frame = len(self.parent.signal.transformed_data)
        data = self.parent.signal.transformed_data[s_frame: e_frame]
        
        # set params
        fps = self.fps.value()
        color = self.use_color.isChecked()
        filename = self.filename.text()
        
        if filename[-4:] != ".mkv":
            filename = str(filename) + ".mkv"
        
        fourCC = cv2.VideoWriter_fourcc(*'MJPG')
        intData = data * 255
        intData = intData.astype(np.uint8)
        intData = np.swapaxes(intData, 1, 2) # swap xs and ys (OpenCV)
    
        outShape = intData[0].shape
        if color:
            lut = self.image_item.getColorMap().getLookupTable()
            intData = np.take(lut, intData, axis=0)
            outShape = intData[0].shape[:2]
            print("WITH COLOR")

        # write video
        out = cv2.VideoWriter(filename, fourCC, fps, outShape, isColor=color)
        for i in range(len(data)):
            frame = intData[i]
            out.write(frame)
        
        print(filename, "exported at", fps, "fps")
        
        out.release()