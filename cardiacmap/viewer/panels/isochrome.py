from PySide6.QtWidgets import (
    QApplication,
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
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
    QSizePolicy,
)
from cardiacmap.viewer.panels.position import PositionView
from skimage.measure import find_contours
import numpy as np
import pyqtgraph as pg
from cardiacmap.viewer.components import Spinbox

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128


def _calculate_isochrome(sig: np.ndarray, t: float, start_frame, cycles, skip_frame):

    all_c = []

    for i in range(cycles):

        idx = i * skip_frame + start_frame

        if idx < len(sig):

            print(i)

            c = np.zeros((128, 128))
            print(sig[idx])
            for p in find_contours(sig[idx], level=t):
                for j in p:
                    c[int(j[0]), int(j[1])] = 1
            print(c.sum())
            all_c.append(c)

    all_c = [c * (i + 1) for i, c in enumerate(all_c)]

    _c = np.array(all_c).max(axis=0)
    _c = _c / len(all_c)

    return _c


class IsochromeWindow(QMainWindow):

    def __init__(self, parent):

        super().__init__()
        self.parent = parent
        self.setWindowTitle("Isochrome View")

        central_widget = QWidget()
        layout = QVBoxLayout()

        self.image_item = pg.ImageItem(self.parent.signal.image_data[0])
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
        self.colorbar = self.plot_item.addColorBar(
            self.image_item,
            colorMap="CET-L9",
            limits=(0, 1),
            values=(0, 1),
            rounding=0.05,
        )

        cm = pg.colormap.get("gray", source="matplotlib")
        self.image_view.setColorMap(cm)
        self.colorbar.setColorMap(cm)

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

        # t: float, start_frame, end_frame, skip_frame

        self.threshold = Spinbox(
            min=0, max=1, val=0.5, step=0.1, min_width=60, max_width=60
        )
        self.start_frame = Spinbox(
            min=0,
            max=len(self.parent.signal.image_data),
            val=0,
            step=1,
            min_width=70,
            max_width=70,
        )
        self.cycles = Spinbox(min=1, max=100, val=1, step=1, min_width=50, max_width=50)
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

        self.confirm = QPushButton("Calculate")
        self.reset = QPushButton("Reset")
        self.confirm.clicked.connect(self.calculate_isochrome)
        self.reset.clicked.connect(self.update_keyframe(int(self.start_frame.value())))
        self.actions_bar.addWidget(self.confirm)
        self.actions_bar.addWidget(self.reset)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.options_2)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.options_widget.setLayout(layout)


    # TODO: Fix colorscale, add overlay mode, adjust y-axis value.
    def calculate_isochrome(self):

        isochrome = _calculate_isochrome(
            self.parent.signal.transformed_data,
            t=self.threshold.value(),
            start_frame=int(self.start_frame.value()),
            cycles=int(self.cycles.value()),
            skip_frame=int(self.skip.value()),
        )

        print(isochrome)
        self.image_item.setImage(isochrome)

        return

    def update_keyframe(self, i):
        self.image_item.setImage(
            self.parent.signal.image_data[int(i)], autoLevels=False, autoRange=False
        )
