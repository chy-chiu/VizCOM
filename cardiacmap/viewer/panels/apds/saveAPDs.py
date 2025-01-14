import numpy as np
import pyqtgraph as pg
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)
from skimage.draw import polygon

IMAGE_SIZE = 128


class SaveAPDView(QtWidgets.QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent

        # Create Image View
        layout = QVBoxLayout()

        # Button Layout
        self.button_layout = QVBoxLayout()
        row_1 = QHBoxLayout()
        row_2 = QHBoxLayout()
        self.edit_roi_button = QPushButton("Edit R.O.I.")
        self.edit_roi_button.setCheckable(True)
        self.reset_roi_button = QPushButton("Reset R.O.I.")
        self.save_roi_button = QPushButton("Save R.O.I.")
        
        row_1.addWidget(self.edit_roi_button)
        row_1.addWidget(self.reset_roi_button)
        row_2.addWidget(self.save_roi_button)
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

        self.image_data = self.parent.img_data[:, :]
        self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)
        self.img_view.view.invertY(True)

        # Set layout
        self.setLayout(layout)

        # Connect buttons to methods
        self.edit_roi_button.clicked.connect(self.toggle_drawing_mode)
        self.reset_roi_button.clicked.connect(self.remove_roi)
        self.save_roi_button.clicked.connect(self.confirm_roi)

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

    def confirm_roi(self):
        self.edit_roi_button.setChecked(False)
        self.drawing = False

        #print(self.drawing)
        if self.roi is None:
            return

        mask = self.get_roi_mask((IMAGE_SIZE, IMAGE_SIZE))
        APDdata = []
        DIdata = []
        for i in range(len(self.parent.data[0])):
            APDdata.extend(self.parent.data[0][i])
            DIdata.extend(self.parent.data[1][i])
        APDdata = np.array(APDdata, dtype=np.float16) * mask
        DIdata = np.array(DIdata, dtype=np.float16) * mask
        
        # flatten x & ys, swap axes so each line is a pixel over time
        APDdata = APDdata.reshape((APDdata.shape[0], -1)).swapaxes(0, 1)
        DIdata = DIdata.reshape((DIdata.shape[0], -1)).swapaxes(0, 1)
        print(APDdata.shape, DIdata.shape)
        print("Saving APDs")
        np.savetxt("APDs.txt", APDdata, delimiter=',')
        print("Saving DIs")
        np.savetxt("DIs.txt", DIdata, delimiter=',')
        print("Saved as APDs.txt & DIs.txt")


    def get_roi_mask(self, shape):
        self.points = np.array(
            [(p.x(), p.y()) for p in np.array(self.roi.getLocalHandlePositions(), dtype="object")[:, 1]]
        )  # Convert to (row, col) format
        #print(points)
        rr, cc = polygon(self.points[:, 0], self.points[:, 1], shape)
        mask = np.zeros(shape, dtype=np.uint8)
        mask[rr, cc] = 1
        return mask
