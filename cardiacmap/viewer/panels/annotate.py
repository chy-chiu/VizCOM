import sys

import numpy as np
import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import MouseDragEvent
from PySide6 import QtCore, QtWidgets
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMainWindow,
                               QPushButton, QVBoxLayout, QWidget)
from skimage.draw import polygon
from skimage.transform import resize
from cardiacmap.model.cascade import load_cascade_file

IMAGE_SIZE = 128

class AnnotateView(QtWidgets.QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent=parent
        
        # Create Image View
        layout = QVBoxLayout()

        # Button Layout
        self.button_layout = QHBoxLayout()
        self.add_mask_button = QPushButton("Add Mask")
        self.add_mask_button.setCheckable(True)
        self.confirm_mask_button = QPushButton("Confirm Mask")
        self.reset_mask_button = QPushButton("Reset Mask")
        
        self.button_layout.addWidget(self.add_mask_button)
        self.button_layout.addWidget(self.confirm_mask_button)
        self.button_layout.addWidget(self.reset_mask_button)

        self.img_view: pg.ImageView = pg.ImageView(view=pg.PlotItem())
        
        self.img_view.view.enableAutoRange(enable=False)
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
        
            self.image_data = self.parent.signal.image_data
            self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)


    def confirm_roi(self):

        self.add_mask_button.setChecked(False)
        self.drawing = False

        print(self.drawing)
        if self.roi is None:
            return

        self.roi.setPoints(self.points)
        mask = self.get_roi_mask((IMAGE_SIZE, IMAGE_SIZE))
        self.parent.signal.apply_mask(mask)

        
        print(mask)
        # mask = resize(mask, (128, 128), order=0)

        self.image_data = self.parent.signal.image_data
        
        self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)
        
        # self.img_view.getImageItem().setTransform(pg.QtGui.QTransform.fromScale(4, 4))
        # self.img_view.setFixedSize(512, 512)

    def get_roi_mask(self, shape):
        points = np.array([p[::-1] for p in self.points])  # Convert to (row, col) format
        rr, cc = polygon(points[:, 1], points[:, 0], shape)
        mask = np.zeros(shape, dtype=np.uint8)
        mask[rr, cc] = 1
        return mask


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    signals = load_cascade_file("2011-08-23_Exp000_Rec112_Cam1-Blue.dat", None)
        
    signal = signals[0]

    viewer = AnnotateView(signal)
    
    viewer.show()
    
    # main_window = CardiacMapWindow()
    # main_window.show()

    sys.exit(app.exec())