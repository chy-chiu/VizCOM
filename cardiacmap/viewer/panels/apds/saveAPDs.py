import numpy as np
import pyqtgraph as pg

from scipy.io import savemat
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QFileDialog,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
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
        row_0 = QHBoxLayout()
        row_1 = QHBoxLayout()
        row_2 = QHBoxLayout()
        
        self.load_coords = QPushButton("Load Coordinates")
        self.edit_roi_button = QPushButton("Edit R.O.I.")
        self.edit_roi_button.setCheckable(True)
        self.reset_roi_button = QPushButton("Reset")
        self.save_roi_button = QPushButton("Save APD/DI Data")
        
        row_0.addWidget(self.load_coords)
        row_1.addWidget(self.edit_roi_button)
        row_1.addWidget(self.reset_roi_button)
        row_2.addWidget(self.save_roi_button)
        self.button_layout.addLayout(row_0)
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
        self.load_coords.clicked.connect(self.upload_coords)
        self.edit_roi_button.clicked.connect(self.toggle_drawing_mode)
        self.reset_roi_button.clicked.connect(self.remove_roi)
        self.save_roi_button.clicked.connect(self.confirm_roi)

        self.roi = None
        self.drawing = False
        self.points = []
        self.coords = None

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
            
        if self.coords is not None:
            self.coords = None
            self.image_data = self.parent.img_data[:, :]
            self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)

    def confirm_roi(self):
        self.edit_roi_button.setChecked(False)
        self.drawing = False

        #print(self.drawing)
        if self.roi is None and self.coords is None:
            mask = np.ones((128, 128))
        elif self.roi is not None:
            mask = self.get_roi_mask((IMAGE_SIZE, IMAGE_SIZE))
        elif self.coords is not None:
            mask = np.zeros((128, 128), dtype=np.uint8)
            mask[self.coords[:, 0], self.coords[:, 1]] = 1
            
        APDdata = []
        DIdata = []
        for i in range(len(self.parent.data[0])):
            APDdata.extend(self.parent.data[0][i])
            DIdata.extend(self.parent.data[1][i])
        APDdata = np.array(APDdata, dtype=np.float16) * mask
        DIdata = np.array(DIdata, dtype=np.float16) * mask
            
        self.export_data(APDdata, DIdata, self.parent.tOffsets)


    def get_roi_mask(self, shape):
        self.points = np.array(
            [(p.x(), p.y()) for p in np.array(self.roi.getLocalHandlePositions(), dtype="object")[:, 1]]
        )  # Convert to (row, col) format
        #print(points)
        rr, cc = polygon(self.points[:, 0], self.points[:, 1], shape)
        mask = np.zeros(shape, dtype=np.uint8)
        mask[rr, cc] = 1
        return mask
    
    def upload_coords(self):
        self.loading = True
        # file popup
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Coordinates", "coords.txt", "Text File(*.txt);;All Files (*)"
        )
        
        # read coords
        self.coords = np.loadtxt(file_path, delimiter=',', dtype=np.int16)
        
        mask = np.zeros((128, 128))
        mask[self.coords[:, 0], self.coords[:, 1]] = 1
        
        # update image
        self.image_data = self.image_data * mask
        self.img_view.setImage(self.image_data, autoLevels=False, autoRange=False)

    def export_data(self, apds, dis, tOffsets):
        # swap axes
        apds = np.moveaxis(apds, 0, -1)
        dis = np.moveaxis(dis, 0, -1)
        # open export menu
        self.exportWindow = ExportAPDsWindow(self, apds, dis, tOffsets)
        self.exportWindow.show()
        
class ExportAPDsWindow(QMainWindow):
    def __init__(self, parent, apdData, diData, tOffsets):
        QMainWindow.__init__(self)
        self.setWindowTitle("Export APD Data")

        self.parent = parent
        self.apds = apdData.reshape((-1, apdData.shape[2]))
        self.dis = diData.reshape((-1, diData.shape[2]))
        self.tOffsets = tOffsets.reshape((-1))
       
        self.Mean_label = QLabel("Mean/STD: ")
        self.APD_label = QLabel("APD/DI: ")

        self.APD_box = QCheckBox()
        self.APD_box.setChecked(True)
        
        self.Mean_box = QCheckBox()
        self.Mean_box.setChecked(True)
        
        self.npy_button = QRadioButton("NumPy (.npy)")
        self.npy_button.setChecked(True)
        self.npy_button.toggled.connect(self.set_file_ext)
        self.mat_button = QRadioButton("MATLAB (.mat)")
        self.mat_button.toggled.connect(self.set_file_ext)
        self.file_ext = ".npy"
        
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("filename (*.npy)")
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        
        layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(self.APD_label)
        row1.addWidget(self.APD_box)
        row1.addWidget(self.Mean_label)
        row1.addWidget(self.Mean_box)
        
        row2 = QHBoxLayout()
        row2.addWidget(self.npy_button)
        row2.addWidget(self.mat_button)
        
        
        row3 = QHBoxLayout()
        row3.addWidget(self.filename)
        row3.addWidget(self.save_button)
        
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        
        mainWidget = QWidget()
        mainWidget.setLayout(layout)
        self.setCentralWidget(mainWidget)
        
    def save(self):
        textStr = self.filename.text()
        if len(textStr) == 0:
            textStr = "output" + self.file_ext
        if len(textStr) <= 4 or textStr[-4:] != self.file_ext:
            textStr += self.file_ext
            
        output = self.getSelectedData()
        if output is None:
            return

        output = output.reshape((128,128, output.shape[1]))

        if self.file_ext == ".npy":
            np.save(textStr, output)
        else:
            output = {"data": output}
            savemat(textStr, output)

        print("Saved to", textStr)
        self.close()
                
    def getSelectedData(self):
        if self.APD_box.isChecked():
            output = np.zeros((16384, self.apds.shape[1] + self.dis.shape[1] + 1))
            output[:, 1::2] = self.dis
            output[:, 2::2] = self.apds
            output[:, 0] = self.tOffsets
            if self.Mean_box.isChecked():
                output2 = np.zeros((16384, 5))
                output2[:, 0] = np.mean(self.dis, axis=1)
                output2[:, 1] = np.mean(self.apds, axis=1)
                output2[:, 2] = np.std(self.dis, axis=1)
                output2[:, 3] = np.std(self.apds, axis=1)
                output2[:, 4] = -1
                output = np.hstack((output2, output))

        elif self.Mean_box.isChecked():
            output = np.zeros((16384, 5))
            output[:, 0] = np.mean(self.dis, axis=1)
            output[:, 1] = np.mean(self.apds, axis=1)
            output[:, 2] = np.std(self.dis, axis=1)
            output[:, 3] = np.std(self.apds, axis=1)
            output[:, 4] = -1
        else:
            print("No data selected for saving")
            return None

        return output
    
    def set_file_ext(self, button):
        if self.mat_button.isChecked():
            self.file_ext = ".mat"
            self.filename.setPlaceholderText("filename (*.mat)")
        else:
            self.file_ext = ".npy"
            self.filename.setPlaceholderText("filename (*.npy)")
         
        

        
        
