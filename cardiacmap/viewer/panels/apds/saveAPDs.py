import numpy as np
import pyqtgraph as pg

from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QLabel,
    QHBoxLayout,
    QFileDialog,
    QMainWindow,
    QPushButton,
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
            
        self.export_data(APDdata, DIdata, mask)
        # flatten x & ys, swap axes so each line is a pixel over time
        # APDdata = APDdata.reshape((APDdata.shape[0], -1)).swapaxes(0, 1)
        # DIdata = DIdata.reshape((DIdata.shape[0], -1)).swapaxes(0, 1)
        # print(APDdata.shape, DIdata.shape)
        # print("Saving APDs")
        # np.savetxt("APDs.txt", APDdata, delimiter=',')
        # print("Saving DIs")
        # np.savetxt("DIs.txt", DIdata, delimiter=',')
        # print("Saved as APDs.txt & DIs.txt")


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

    def export_data(self, apds, dis, mask):
        # mask out invalid pixels
        validCoords = np.argwhere(mask==1)
        apds = apds[:, validCoords[:, 0], validCoords[:, 1]]
        dis = dis[:, validCoords[:, 0], validCoords[:, 1]]
        # swap axes
        apds = np.moveaxis(apds, 0, -1)
        dis = np.moveaxis(dis, 0, -1)
        # mask out zero values
        mAPD = np.ma.masked_equal(apds, 0)
        mDI = np.ma.masked_equal(dis, 0)
        # open export menu
        self.exportWindow = ExportAPDsWindow(self, mAPD, mDI)
        self.exportWindow.show()
        
class ExportAPDsWindow(QMainWindow):
    def __init__(self, parent, apdData, diData):
        QMainWindow.__init__(self)
        self.setWindowTitle("Export APD Data")

        self.parent = parent
        self.apds = apdData
        self.dis = diData
        
        self.Alternans_label = QLabel("Alternans: ")
        self.Mean_label = QLabel("Mean: ")
        self.Std_label = QLabel("Standard Dev: ")
        self.APD_label = QLabel("APDs: ")
        self.DI_label = QLabel("DIs: ")
        self.Raw_label = QLabel("Raw Data:")

        self.APD_box = QCheckBox()
        self.APD_box.setChecked(True)
        self.DI_box = QCheckBox()
        self.DI_box.setChecked(True)
        
        self.Alternans_box = QCheckBox()
        self.Mean_box = QCheckBox()
        self.Mean_box.setChecked(True)
        self.Std_box = QCheckBox()
        self.Std_box.setChecked(True)
        self.Raw_box = QCheckBox()
        
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("filename (*.txt)")
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save)
        
        layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        row1.addWidget(self.APD_label)
        row1.addWidget(self.APD_box)
        row1.addWidget(self.DI_label)
        row1.addWidget(self.DI_box)
        
        row2 = QHBoxLayout()
        row2.addWidget(self.Alternans_label)
        row2.addWidget(self.Alternans_box)
        row2.addWidget(self.Mean_label)
        row2.addWidget(self.Mean_box)
        row2.addWidget(self.Std_label)
        row2.addWidget(self.Std_box)
        row2.addWidget(self.Raw_label)
        row2.addWidget(self.Raw_box)
        
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
            textStr = "output.txt"
        if len(textStr) <= 4 or textStr[-4:] != ".txt":
            textStr += ".txt"
            
        if self.Alternans_box.isChecked():
            out1, eLabels = self.getSelectedData(self.apds[:, ::2], self.dis[:, ::2])
            out2, oLabels = self.getSelectedData(self.apds[:, 1::2], self.dis[:, 1::2])
            out2 = out2[:, 1:] # trim index column
            output = np.hstack((out1, out2)) # concatenate evens and odds
            eLabels = eLabels.replace(",", " (even),")
            oLabels = oLabels.replace(",", " (odd),")
            outputLabels = eLabels + oLabels
        else:
            output, outputLabels = self.getSelectedData(self.apds, self.dis)
         
        output = output[:, 1:] # trim index column
        #print(output.shape)
        np.savetxt(textStr, output, header=outputLabels, delimiter=",", fmt="%1.5f")
        print("Saved to", textStr)
        self.close()
                
    def getSelectedData(self, apds, dis):
        outputLabels = " "
        output = np.arange(apds.shape[0])
        if self.Mean_box.isChecked():
            if self.APD_box.isChecked():
                output = np.vstack((output, apds.mean(axis=1)))
                outputLabels += "APD Mean, "
            if self.DI_box.isChecked():
                output = np.vstack((output, dis.mean(axis=1)))
                outputLabels += "DI Mean, "
                
        if self.Std_box.isChecked():
            if self.APD_box.isChecked():
                output = np.vstack((output, apds.std(axis=1)))
                outputLabels += "APD Std, "
            if self.DI_box.isChecked():
                output = np.vstack((output, dis.std(axis=1)))
                outputLabels += "DI Std, "

        if output.ndim > 1:
            output = output.swapaxes(0, 1)
        else:
            output = output[:, None]
            
        if self.Raw_box.isChecked():
            if self.APD_box.isChecked():
                output = np.hstack((output, apds))
                outputLabels += str(len(apds[0])) + " APD Values, "
            if self.DI_box.isChecked():
                output = np.hstack((output, dis))
                outputLabels += str(len(dis[0])) + " DI Values, "
                
        return output, outputLabels
        

        
        
