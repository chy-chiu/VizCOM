import sys

import numpy as np
import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import MouseDragEvent
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog
)
from skimage.draw import polygon
from skimage.transform import resize

from cardiacmap.model.cascade import load_cascade_file

IMAGE_SIZE = 128


class AnnotateView(QtWidgets.QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent

        # Create Image View
        layout = QVBoxLayout()

        # Button Layout
        self.button_layout = QVBoxLayout()
        row_1 = QHBoxLayout()
        row_2 = QHBoxLayout()
        self.add_mask_button = QPushButton("Edit Mask")
        self.add_mask_button.setCheckable(True)
        self.confirm_mask_button = QPushButton("Set Mask")
        self.reset_mask_button = QPushButton("Reset Mask")
        self.save_mask_button = QPushButton("Save Mask")
        self.load_mask_button = QPushButton("Load Mask")
        
        row_1.addWidget(self.save_mask_button)
        row_1.addWidget(self.load_mask_button)
        row_2.addWidget(self.add_mask_button)
        row_2.addWidget(self.confirm_mask_button)
        row_2.addWidget(self.reset_mask_button)
        self.button_layout.addLayout(row_1)
        self.button_layout.addLayout(row_2)

        self.img_view: pg.ImageView = pg.ImageView(view=pg.PlotItem())

        self.img_view.view.enableAutoRange(enable=False)
        self.img_view.view.showAxes(False)
        self.img_view.view.setMouseEnabled(False, False)
        self.img_view.view.setRange(xRange=(-2, 128), yRange=(-2, 128))

        self.img_view.ui.roiBtn.hide()
        self.img_view.ui.menuBtn.hide()
        self.img_view.ui.histogram.hide()

        self.img_view.getView().setAspectLocked(True)

        layout.addLayout(self.button_layout)
        layout.addWidget(self.img_view)

        # Initialize Image View
        self.image_data = self.parent.signal.image_data[0, :, :]
        self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)
        self.img_view.view.invertY(True)

        # Set layout
        self.setLayout(layout)

        # Connect buttons to methods
        self.add_mask_button.clicked.connect(self.toggle_drawing_mode)
        self.reset_mask_button.clicked.connect(self.remove_roi)
        self.confirm_mask_button.clicked.connect(self.confirm_roi)
        self.save_mask_button.clicked.connect(self.save_mask)
        self.load_mask_button.clicked.connect(self.load_mask)

        self.roi = None
        self.drawing = False
        self.points = []

        # Connect mouse click to plot
        self.img_view.scene.sigMouseClicked.connect(self.add_point)

    def toggle_drawing_mode(self):
        self.drawing = not self.drawing
        # self.points = []

    def add_point(self, event):
        if not self.drawing:
            return

        pos = event.scenePos()
        mousePoint = self.img_view.view.vb.mapSceneToView(pos)

        # Get the x and y coordinates of the mouse click
        x = mousePoint.x()
        y = mousePoint.y()

        self.points.append((x, y))

        if len(self.points) > 1:
            if self.roi is not None:
                self.img_view.removeItem(self.roi)

            self.roi = pg.PolyLineROI(self.points, closed=True)
            self.img_view.addItem(self.roi)

    def remove_roi(self):
        if self.roi is not None:
            self.img_view.removeItem(self.roi)
            self.roi = None
            self.drawing = False
            self.points = []

            self.parent.signal.reset_image()
            self.image_data = self.parent.signal.image_data[0, :, :]

            self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)

            mask = np.ones((IMAGE_SIZE, IMAGE_SIZE))
            self.parent.signal.apply_mask(mask)
            self.parent.update_signal_plot()
            self.parent.position_tab.update_data()

    def confirm_roi(self):
        self.add_mask_button.setChecked(False)
        self.drawing = False

        #print(self.drawing)
        if self.roi is None:
            return

        mask = self.get_roi_mask((IMAGE_SIZE, IMAGE_SIZE))
        self.parent.signal.apply_mask(mask)
        self.parent.update_signal_plot()
        self.parent.position_tab.update_data()
        self.masked_image_data = self.image_data * self.parent.signal.mask

        self.img_view.setImage(self.masked_image_data, autoLevels=False, autoRange=False)


    def get_roi_mask(self, shape):
        self.points = np.array(
            [(p.x(), p.y()) for p in np.array(self.roi.getLocalHandlePositions(), dtype="object")[:, 1]]
        )  # Convert to (row, col) format
        #print(points)
        rr, cc = polygon(self.points[:, 0], self.points[:, 1], shape)
        mask = np.zeros(shape, dtype=np.uint8)
        mask[rr, cc] = 1
        return mask
    
    def save_mask(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Mask", "mask.npy", "Binary NumPy Object (*.npy);;All Files (*)"
        )
        np.save(file_path, self.points)
    
    def load_mask(self):
        self.loading = True
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Mask", "mask.npy", "Binary NumPy Object (*.npy);;All Files (*)"
        )
        self.points = np.load(file_path)
        if self.roi is not None:
            self.img_view.removeItem(self.roi)
        self.roi = pg.PolyLineROI(self.points, closed=True)
        self.img_view.addItem(self.roi)
        self.confirm_roi()


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    signals = load_cascade_file("2011-08-23_Exp000_Rec112_Cam1-Blue.dat", None)

    signal = signals[0]

    viewer = AnnotateView(signal)

    viewer.show()

    # main_window = CardiacMapWindow()
    # main_window.show()

    sys.exit(app.exec())
