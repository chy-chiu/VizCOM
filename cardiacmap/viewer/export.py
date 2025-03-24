import numpy as np
import cv2
import pyqtgraph as pg
from functools import partial
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSizePolicy,
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

        cm = pg.colormap.get("nipy_spectral", source="y")
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
        filename = self.parent.signal.signal_name
        
        if filename[-4:] != ".avi":
            filename = str(filename) + ".avi"

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

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Video", filename, "Lossless AVI (*.avi);;All Files (*)"
        )
        
        if file_path:
            out = cv2.VideoWriter(file_path, fourCC, fps, outShape, isColor=color)
            for i in range(len(data)):
                frame = intData[i]
                out.write(frame)
            
            print(filename, "exported at", fps, "fps")
            
            out.release()

def export_histogram(data, binSize = 1, signal_name = ""):
    bins = np.arange(np.floor(data.min()), np.ceil(data.max()), binSize)
    counts, ranges = np.histogram(data,bins)
    output = np.zeros((2, counts.shape[0]))
    output[0, :] = ranges[:-1]
    output[1, :] = counts
    file_path, _ = QFileDialog.getSaveFileName(None, "Save Histogram", signal_name+"_histogram.csv", "Comma Seperated Value (*.csv);")

    if file_path:
        np.savetxt(file_path, output, delimiter=",", fmt="%.2f")
        print("Saved histogram data to: ", file_path)