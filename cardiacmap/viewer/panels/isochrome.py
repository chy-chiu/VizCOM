from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget, QComboBox, QCheckBox, QSizePolicy)
from cardiacmap.viewer.panels.position import PositionView
from skimage.measure import find_contours
import numpy as np
import pyqtgraph as pq
from cardiacmap.viewer.components import Spinbox


VIEWPORT_MARGIN = 2
IMAGE_SIZE=128

def calculate_isochrome(sig: np.ndarray, t: float, start_frame, end_frame, skip_frame):
    
    all_c = []
    
    for i in range(start_frame, end_frame, skip_frame):
        c = np.zeros((128, 128))

        for p in find_contours(sig[i], level=t):
            for j in p:
                c[int(j[0]), int(j[1])] = 1
        all_c.append(c)

    all_c = [c * (i + 1) for i, c in enumerate(all_c)]

    _c = np.array(all_c).max(axis=0)

    return _c

class IsochromeWindow(QMainWindow):

    def __init__(self, parent):

        super().__init__()
        self.parent = parent

        central_widget = QWidget()
        layout = QVBoxLayout()

        self.image_view = pq.ImageView()
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN), yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN)
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        self.image_view.ui.histogram.hide()
       
        self.image_view.view.invertY(True)

        size_policy = QSizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.Policy.Fixed)
        size_policy.setHorizontalPolicy(QSizePolicy.Policy.Fixed)
        self.image_view.setSizePolicy(size_policy)
        self.image_view.setMinimumWidth(380)
        self.image_view.setMinimumHeight(500)

        self.update_keyframe(0)
        
        layout.addWidget(self.image_view)

        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)


    def init_options(self):
        self.options_bar = QToolBar()

        t: float, start_frame, end_frame, skip_frame

        self.threshold = Spinbox(min=0, max=1, val=0.5, step=0.1)
        self.start_frame = Spinbox(min=0, max=100, val=0, step=1)


    def update_keyframe(self, i):
        self.image_view.setImage(
            self.parent.signal.image_data[i], autoLevels=False, autoRange=False
        )
        

