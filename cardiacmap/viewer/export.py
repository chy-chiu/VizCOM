import numpy as np
import cv2
import os
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
    QFileDialog
)

from cardiacmap.viewer.components import Spinbox
from scipy.io import savemat

QTOOLBAR_STYLE = """
            QToolBar {spacing: 5px;} 
            """

VIEWPORT_MARGIN = 2
IMAGE_SIZE = 128

class ImportExportDirectories(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            # new instance
            cls.instance = super(ImportExportDirectories, cls).__new__(cls)
            try:
               # check for previously saved files
               file = open("directories.txt", "r")
               cls.importDir = file.readline()
               cls.exportDir = file.readline()
               file.close()
            except:
                # no previous files
                cwd = os.getcwd().replace("\\", "/") + "/"
                cls.importDir = cwd
                cls.exportDir = cwd
        return cls.instance

    def SaveDirectories(self):
        file = open("directories.txt", "w")
        file.write(self.importDir + "\n" + self.exportDir)
        file.close()
    
        
class ExportAPDsWindow(QMainWindow):
    def __init__(self, parent, apdData, diData, tOffsets, filename=""):
        QMainWindow.__init__(self)
        self.setWindowTitle("Export APD Data")

        self.parent = parent
        self.apds = apdData.reshape((-1, apdData.shape[2]))
        self.dis = diData.reshape((-1, diData.shape[2]))
        self.tOffsets = tOffsets.reshape((-1))
        self.filename = filename
       
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
        row3.addWidget(self.save_button)
        
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        
        mainWidget = QWidget()
        mainWidget.setLayout(layout)
        self.setCentralWidget(mainWidget)
        
    def save(self):
        output = self.getSelectedData()
        if output is None:
            return

        output = output.reshape((128,128, output.shape[1]))

        dirs = ImportExportDirectories() # get export directory
        file_path, _ = QFileDialog.getSaveFileName(
            None, "Save APD/DI Data", dirs.exportDir+self.filename+ "-APD-DI" + self.file_ext,
        )
        if file_path:
            dirs.exportDir = file_path[:file_path.rindex("/") + 1] # update export directory
            dirs.SaveDirectories()
            if self.file_ext == ".npy":
                np.save(file_path, output)
            else:
                output = {"data": output}
                savemat(file_path, output)
            print("Saved APD/DI data to: ", file_path)

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
        else:
            self.file_ext = ".npy"
    
class ExportVideoWindow(QMainWindow):

    def __init__(self, parent, filename=""):

        super().__init__()
        self.parent = parent
        self.ms = parent.signal_panel.ms_per_frame.value()
        self.mask = parent.signal.mask
        self.overlay = None
        self.setWindowTitle("Export Video")

        self.init_options()
        self.cm = pg.colormap.get("nipy_spectral", source="y")
        self.image_item = pg.ImageItem()
        self.update_keyframe()
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
        self.image_view.setMinimumWidth(380)
        self.image_view.setMinimumHeight(500)
        self.image_view.setColorMap(self.cm)

        layout = QVBoxLayout()
        layout.addWidget(self.image_view)
        layout.addWidget(self.options_widget)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def init_options(self):
        self.options_widget = QWidget()
        layout = QVBoxLayout()
        self.options_1 = QToolBar()
        self.options_2 = QToolBar()
        self.options_3 = QToolBar()
        self.options_4 = QToolBar()
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

        self.rotation = Spinbox(min=0, max=359, val=0, step=1, min_width=60, max_width=60)
        self.rotation.valueChanged.connect(self.update_keyframe)
        self.xShift = Spinbox(min=0, max=500, val=0, step=1, min_width=60, max_width=60)
        self.xShift.valueChanged.connect(self.update_keyframe)
        self.yShift = Spinbox(min=0, max=500, val=0, step=1, min_width=60, max_width=60)
        self.yShift.valueChanged.connect(self.update_keyframe)
        self.xScale = Spinbox(min=.1, max=2, val=1, step=.1, min_width=60, max_width=60)
        self.xScale.valueChanged.connect(self.update_keyframe)
        self.yScale = Spinbox(min=.1, max=2, val=1, step=.1, min_width=60, max_width=60)
        self.yScale.valueChanged.connect(self.update_keyframe)

        self.overlay_threshold = Spinbox(min=0, max=1, val=.5, step=.1, min_width=60, max_width=60)
        self.overlay_threshold.valueChanged.connect(self.update_keyframe)
        
        #self.use_color = QCheckBox()
        self.use_overlay = QPushButton("Add Overlay Image")
        self.use_overlay.clicked.connect(self.load_overlay_image)

        self.options_1.addWidget(QLabel("Start Time: "))
        self.options_1.addWidget(self.start_time)
        self.options_1.addWidget(QLabel("End Time: "))
        self.options_1.addWidget(self.end_time)

        self.options_1.addWidget(QLabel("FPS: "))
        self.options_1.addWidget(self.fps)
        #self.options_2.addWidget(QLabel("Use Color: "))
        self.options_2.addWidget(self.use_overlay)

        self.options_3.addWidget(QLabel("Rotation: "))
        self.options_3.addWidget(self.rotation)
        self.options_3.addWidget(QLabel("X Scale: "))
        self.options_3.addWidget(self.xScale)
        self.options_3.addWidget(QLabel("Y Scale: "))
        self.options_3.addWidget(self.yScale)

        self.options_4.addWidget(QLabel("X Shift: "))
        self.options_4.addWidget(self.xShift)
        self.options_4.addWidget(QLabel("Y Shift: "))
        self.options_4.addWidget(self.yShift)
        self.options_4.addWidget(QLabel("Threshold: "))
        self.options_4.addWidget(self.overlay_threshold)

        self.options_1.setStyleSheet(QTOOLBAR_STYLE)
        self.options_2.setStyleSheet(QTOOLBAR_STYLE)
        self.options_3.setStyleSheet(QTOOLBAR_STYLE)
        self.options_4.setStyleSheet(QTOOLBAR_STYLE)

        self.start_time.valueChanged.connect(self.update_keyframe)

        self.confirm = QPushButton("Export")
        self.confirm.clicked.connect(self.export_video)
        self.actions_bar.addWidget(self.confirm)
        # TODO: Overlay
        # self.overlay = QCheckBox()

        layout.addWidget(self.options_1)
        layout.addSpacing(5)
        layout.addWidget(self.options_2)
        layout.addSpacing(5)
        layout.addWidget(self.options_3)
        layout.addSpacing(5)
        layout.addWidget(self.options_4)
        layout.addSpacing(5)
        layout.addWidget(self.actions_bar)

        self.options_3.hide()
        self.options_4.hide()

        self.options_widget.setLayout(layout)

    def update_keyframe(self):
        output = np.zeros((128,128, 3))
        i = self.start_time.value()
        data = self.parent.signal.transformed_data[int(i // self.ms)] * self.mask
        intData = data * 511
        intData = intData.astype(np.uint16)
        intData = np.swapaxes(intData, 0, 1) # swap xs and ys (OpenCV)
        lut = self.cm.getLookupTable()
        intData = np.take(lut, intData, axis=0)
        if self.overlay is not None:
            h, w = self.overlay.shape[:2]
            scaledH = int(h * self.yScale.value())
            scaledW = int(w * self.xScale.value())
            # resize output
            if scaledW < 128:
                scaledW = 128
            if scaledH < 128:
                scaledH = 128
            output = np.zeros((scaledW,scaledH, 3))

            # apply transformations
            M = cv2.getRotationMatrix2D((w//2, h//2), self.rotation.value(), 1)
            img = self.overlay
            img = cv2.warpAffine(img, M, (w, h))
            img = cv2.resize(img, (scaledW, scaledH))

            # add overlayed image to output
            output[0: len(img[0]), 0: len(img), :] = img.swapaxes(0,1)[:, :, :]

            # use shift values
            tooWide = (int(self.xShift.value()) + 128 > scaledW)
            tooTall = (int(self.yShift.value()) + 128 > scaledH)
            if tooWide:
                xs = int(scaledW - 128)
            else:
                xs = int(self.xShift.value())
            if tooTall:
                ys = int(scaledH - 128)
            else:
                ys = int(self.yShift.value())

            # hide data below threshold
            transparent = np.argwhere(data < self.overlay_threshold.value())
            intData[transparent[:, 1], transparent[:, 0], :] = img[ys + transparent[:, 1], xs + transparent[:, 0], :]
        # no overlay
        else:
            # ignore shift values
            xs = ys = 0

        output[xs: xs+128, ys: ys+128] = intData.swapaxes(0,1)
        self.image_item.setImage(output)

    def generate_overlay_video(self, data):
        output = np.zeros((128,128, 3))
        intData = data * 511
        intData = intData.astype(np.uint16)
        intData = np.swapaxes(intData, 1, 2) # swap xs and ys (OpenCV)
        lut = self.cm.getLookupTable()
        intData = np.take(lut, intData, axis=0)
        h, w = self.overlay.shape[:2]
        scaledH = int(h * self.yScale.value())
        scaledW = int(w * self.xScale.value())
        # resize output
        if scaledW < 128:
            scaledW = 128
        if scaledH < 128:
            scaledH = 128
        output = np.zeros((len(intData), scaledW,scaledH, 3))

        # transform overlay
        M = cv2.getRotationMatrix2D((w//2, h//2), self.rotation.value(), 1)
        img = self.overlay
        img = cv2.warpAffine(img, M, (w, h))
        img = cv2.resize(img, (scaledW, scaledH))

        # add overlayed image to output
        output[:, 0: len(img[0]), 0: len(img), :] = img.swapaxes(0,1)[:, :, :]

        # use shift values
        tooWide = (int(self.xShift.value()) + 128 > scaledW)
        tooTall = (int(self.yShift.value()) + 128 > scaledH)
        if tooWide:
            xs = int(scaledW - 128)
        else:
            xs = int(self.xShift.value())
        if tooTall:
            ys = int(scaledH - 128)
        else:
            ys = int(self.yShift.value())

        for i in range(len(intData)):
            # hide data below threshold
            transparent = np.argwhere(data[i] < self.overlay_threshold.value())
            intData[i, transparent[:, 1], transparent[:, 0], :] = img[ys + transparent[:, 1], xs + transparent[:, 0], :]
            output[i, xs: xs+128, ys: ys+128] = intData[i].swapaxes(0,1)

        return output
        
    def export_video(self):
        # slice data and apply mask
        s_frame = int(self.start_time.value() // self.ms)
        e_frame = int(self.end_time.value() // self.ms)
        if e_frame <= s_frame:
            e_frame = len(self.parent.signal.transformed_data)
        data = self.parent.signal.transformed_data[s_frame: e_frame] * self.mask

        # set params
        fps = self.fps.value()
        color = True # self.use_color.isChecked()
        filename = self.parent.signal.signal_name
        
        if filename[-4:] != ".avi":
            filename = str(filename) + ".avi"

        fourCC = cv2.VideoWriter_fourcc(*'MJPG')
        if self.overlay is not None:
            video = self.generate_overlay_video(data).astype(np.uint8)
            outShape = video.shape[1:3]
        else:
            intData = data * 511
            intData = intData.astype(np.uint16)
            intData = np.swapaxes(intData, 1, 2) # swap xs and ys (OpenCV)
    
            outShape = intData[0].shape
            if color:
                lut = self.cm.getLookupTable()
                intData = np.take(lut, intData, axis=0)
                outShape = intData[0].shape[:2]
        
        dirs = ImportExportDirectories() # get export directory
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", dirs.exportDir+filename, "AVI (*.avi);;All Files (*)"
        )
        if file_path:
            dirs.exportDir = file_path[:file_path.rindex("/") + 1] # update export directory
            dirs.SaveDirectories()
            out = cv2.VideoWriter(file_path, fourCC, fps, outShape, isColor=color)
            for i in range(len(data)):
                if self.overlay is not None:
                    frame = video[i].swapaxes(0, 1)[:, :, ::-1]
                else:
                    frame = intData[i]
                out.write(frame)
            
            print(filename, "exported at", fps, "fps")
            out.release()

    def load_overlay_image(self):
        dirs = ImportExportDirectories() # get export directory
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Overlay Image", dirs.importDir, "JPG (*.jpg);;All Files (*)"
        )
        self.overlay = cv2.imread(file_path)[...,::-1] #BGR to RGB
        self.update_keyframe()
        self.image_view.view.autoRange()
        self.xShift.setValue(self.overlay.shape[1]//2 - 64)
        self.yShift.setValue(self.overlay.shape[0]//2 - 64)
        self.options_3.show()
        self.options_4.show()

def export_histogram(data, binSize = 1, filename=""):
    bins = np.arange(np.floor(data.min()), np.ceil(data.max()), binSize)
    counts, ranges = np.histogram(data,bins)
    output = np.zeros((2, counts.shape[0]))
    output[0, :] = ranges[:-1]
    output[1, :] = counts
    dirs = ImportExportDirectories() # get export directory
    file_path, _ = QFileDialog.getSaveFileName(
        None, "Save Histogram", dirs.exportDir+filename+"-histogram.csv", "Comma Seperated Value (*.csv);"
    )
    if file_path:
        dirs.exportDir = file_path[:file_path.rindex("/") + 1] # update export directory
        dirs.SaveDirectories()
        np.savetxt(file_path, output, delimiter=",", fmt="%.2f")
        print("Saved histogram data to: ", file_path)