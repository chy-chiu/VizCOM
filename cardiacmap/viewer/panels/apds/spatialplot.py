from math import floor
import numpy as np
import pyqtgraph as pg
import numpy.ma as ma

from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent, MouseClickEvent
from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QPushButton,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from cardiacmap.viewer.panels.apds.apdThreshold import APDThresholdWindow
from cardiacmap.viewer.export import export_histogram
from cardiacmap.viewer.components import Spinbox

SPINBOX_STYLE = """QSpinBox
            {
                border: 1px solid;
            }

            QSpinBox::up-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                top: -5px;
                right: 0px;
            }

            QSpinBox::down-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                bottom: -5px;
                right: 0px;
            }"""

IMAGE_SIZE = 128

class SpatialDragPlot(pg.PlotItem):
    # Position Plot used by APD/DI v.s. Space Plots
    def __init__(self, parent, sCallback, eCallback):
        super().__init__()
        self.setMenuEnabled(False)
        
        self.sCallback = sCallback
        self.eCallback = eCallback
        self.parent = parent

    def mouseDragEvent(self, event: MouseDragEvent):
        pass

    def mouseClickEvent(self, event: MouseClickEvent):
        pos = self.vb.mapSceneToView(event.scenePos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.sCallback(int(pos.x()), int(pos.y()))
        elif event.button() == Qt.MouseButton.RightButton:
            self.eCallback(int(pos.x()), int(pos.y()))
            
        # get coordinates that intersect the line
        xDiff = self.parent.x2 - self.parent.x1
        yDiff = self.parent.y2 - self.parent.y1
        maxDiff = max(abs(xDiff), abs(yDiff))
        coords = []
        for i in range(maxDiff):
            x = self.parent.x1 + i * xDiff / maxDiff
            y = self.parent.y1 + i * yDiff / maxDiff
            coords.append((floor(x), floor(y)))
        coords, idxs = np.unique(coords, axis=0, return_index=True)
        coords = coords[np.argsort(idxs)]
        self.parent.spatial_coords = coords
        self.parent.update_graph()
        
        return event.pos()

    def hoverEvent(self, event: HoverEvent):
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(Qt.MouseButton.LeftButton)


class SpatialPlotView(QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)

        self.parent = parent
        self.ms = parent.ms
        self.mask = parent.mask

        self.init_image_view()
        self.init_toolbars()

        self.contour_button = QPushButton(self)
        self.contour_button.setText("Contours")
        self.contour_button.clicked.connect(self.open_contour_window)

        self.histogram_button = QPushButton(self)
        self.histogram_button.setText("Save Histogram")
        self.histogram_button.clicked.connect(self.save_histogram)

        self.bin_size_label = QLabel("Histogram Bin Size: ")
        self.bin_size = Spinbox(0, 5, .5, 30, 60, .25)
        self.histogram_export = QHBoxLayout()
        self.histogram_export.addWidget(self.histogram_button)
        self.histogram_export.addWidget(self.bin_size_label)
        self.histogram_export.addWidget(self.bin_size)

        
        layout = QVBoxLayout()
        layout.addWidget(self.interval_bar)
        layout.addWidget(self.contour_button)
        layout.addLayout(self.histogram_export)
        layout.addWidget(self.image_view)
        layout.addWidget(self.beat_bar)
        layout.addWidget(self.display_bar)
        layout.addWidget(self.settings_bar)
        self.setLayout(layout)

        self.spatial_coords = None
        self.x1 = self.y1 = 32
        self.x2 = self.y2 = 64

        self.update_data()
        # self.position_callback = position_callback

    def init_image_view(self):
        # Set up Image View
        self.plot = SpatialDragPlot(self, self.line_start, self.line_end)

        self.image_view = pg.ImageView(view=self.plot)
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.divergent_cm = pg.ColorMap([0, .5, 1], ['r', 'w', 'b'])
        self.normal_cm = pg.ColorMap([0, 1], ['k', 'w'])
        self.image_view.imageItem.setColorMap(self.normal_cm)
        self.image_view.ui.histogram.item.sigLookupTableChanged.connect(self.on_lut_change)

        self.image_view.view.setRange(
            xRange=(-2, IMAGE_SIZE + 2), yRange=(-2, IMAGE_SIZE + 2)
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        # self.image_view.ui.histogram.hide()
        self.image_view.ui.histogram.item.sigLevelChangeFinished.connect(
            self.update_spinbox_values
        )
        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable red dots
        self.startPoint = pg.ScatterPlotItem(
            pos=[[32, 32]], size=5, pen=pg.mkPen("r"), brush=pg.mkBrush("r")
        )
        self.endPoint = pg.ScatterPlotItem(
            pos=[[64, 64]], size=5, pen=pg.mkPen("b"), brush=pg.mkBrush("b")
        )

        self.line = pg.PlotCurveItem(x=[32, 64], y=[32, 64])
        self.line_visable = True

        self.image_view.getView().addItem(self.startPoint)
        self.image_view.getView().addItem(self.endPoint)
        self.image_view.getView().addItem(self.line)

        return self.image_view

    def init_toolbars(self):
        self.interval_bar = QToolBar()
        self.beat_bar = QToolBar()
        self.display_bar = QToolBar()
        self.settings_bar = QToolBar()

        self.intervalIdx = QtWidgets.QSpinBox()
        self.intervalIdx.setFixedWidth(60)
        self.intervalIdx.setMaximum(len(self.parent.data_slices))
        self.intervalIdx.setMinimum(1)
        self.intervalIdx.setValue(1)
        self.intervalIdx.setSingleStep(1)
        self.intervalIdx.setStyleSheet(SPINBOX_STYLE)
        self.intervalIdx.valueChanged.connect(self.update_data)
        self.intervalIdx.valueChanged.connect(self.update_graph)
        
        self.frameIdx = QtWidgets.QSpinBox()
        self.frameIdx.setFixedWidth(60)
        self.frameIdx.setMaximum(len(self.parent.data_slices[0]))
        self.frameIdx.setMinimum(1)
        self.frameIdx.setValue(1)
        self.frameIdx.setSingleStep(1)
        self.frameIdx.setStyleSheet(SPINBOX_STYLE)
        self.frameIdx.valueChanged.connect(self.jump_frames)
        self.frameIdx.valueChanged.connect(self.update_graph)

        self.beatNumber = self.frameIdx.value()
        
        self.alternans = QtWidgets.QCheckBox()
        self.alternans.checkStateChanged.connect(self.update_graph)

        self.interval_bar.addWidget(QLabel("   Interval #: "))
        self.interval_bar.addWidget(self.intervalIdx)
        self.interval_bar.addWidget(QLabel(" of " + str(len(self.parent.data_slices))))
        self.beat_bar.addWidget(QLabel("   Beat #: "))
        self.beat_bar.addWidget(self.frameIdx)
        self.numBeatDisplay = QLabel(" of " + str(len(self.parent.data_slices[0])))
        self.beat_bar.addWidget(self.numBeatDisplay)
        self.beat_bar.addWidget(QLabel("   Alternans: "))
        self.beat_bar.addWidget(self.alternans)


        self.show_raw = QRadioButton("Raw")
        self.show_raw.setChecked(True)
        self.show_raw.toggled.connect(lambda: self.radio_state(self.show_raw))
        
        self.show_diff = QRadioButton("Difference")
        self.show_diff.setChecked(False)
        self.show_diff.toggled.connect(lambda: self.radio_state(self.show_diff))
        
        self.show_mean = QRadioButton("Mean")
        self.show_mean.setChecked(False)
        self.show_mean.toggled.connect(lambda: self.radio_state(self.show_mean))
        
        self.show_min = QRadioButton("Min")
        self.show_min.setChecked(False)
        self.show_min.toggled.connect(lambda: self.radio_state(self.show_min))
    
        self.show_max = QRadioButton("Max")
        self.show_max.setChecked(False)
        self.show_max.toggled.connect(lambda: self.radio_state(self.show_max))

        self.hide_line = QCheckBox()
        self.hide_line.setChecked(False)
        self.hide_line.checkStateChanged.connect(self.update_data)

        self.diff_range = QtWidgets.QSpinBox()
        self.diff_range.setFixedWidth(60)
        self.diff_range.setMinimum(0)
        self.diff_range.setMaximum(100000)
        self.diff_range.setValue(np.min(np.diff(self.parent.data_slices[0])))
        self.diff_range.setStyleSheet(SPINBOX_STYLE)
        self.diff_range.valueChanged.connect(self.update_data)

        self.zero_val = QtWidgets.QSpinBox()
        self.zero_val.setFixedWidth(60)
        self.zero_val.setMinimum(-100000)
        self.zero_val.setMaximum(100000)
        self.zero_val.setValue(0)
        self.zero_val.setStyleSheet(SPINBOX_STYLE)
        self.zero_val.valueChanged.connect(self.update_data)

        self.max_val = QtWidgets.QSpinBox()
        self.max_val.setFixedWidth(60)
        self.max_val.setMinimum(-100000)
        self.max_val.setMaximum(100000)
        self.max_val.setValue(np.max(self.parent.data_slices[0]))
        self.max_val.setStyleSheet(SPINBOX_STYLE)
        self.max_val.valueChanged.connect(self.update_data)

        self.display_bar.addWidget(self.show_raw)
        self.display_bar.addWidget(self.show_min)
        self.display_bar.addWidget(self.show_max)
        self.display_bar.addWidget(self.show_mean)
        self.display_bar.addWidget(self.show_diff)
        

        self.settings_bar.addWidget(QLabel("   Hide Line: "))
        self.settings_bar.addWidget(self.hide_line)

        self.diff_range_label = self.settings_bar.addWidget(QLabel("   Range: "))
        self.diff_range_spinbox = self.settings_bar.addWidget(self.diff_range)

        
        self.img_min_label = self.settings_bar.addWidget(QLabel("   Image Min: "))
        self.min_spinbox = self.settings_bar.addWidget(self.zero_val)

        
        self.img_max_label = self.settings_bar.addWidget(QLabel("   Image Max: "))
        self.max_spinbox = self.settings_bar.addWidget(self.max_val)
        
    def radio_state(self, b):
        #print(b.text())
        self.update_data()

    def update_spinbox_values(self):
        """Called When Range Changes"""
        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0], levels[1])

        # set numerical vals to their visual levels
        if self.show_diff.isChecked():
            self.diff_range.setValue(max(abs(levels[0]), abs(levels[1])))
        else:
            self.max_val.setValue((levels[1]))
            self.zero_val.setValue(levels[0])

    def update_ui(self):
        #print("UI Update Call")
        # show proper min
        if self.show_diff.isChecked():
            self.diff_range_label.setVisible(True)
            self.diff_range_spinbox.setVisible(True)
            self.img_min_label.setVisible(False)
            self.min_spinbox.setVisible(False)
            self.img_max_label.setVisible(False)
            self.max_spinbox.setVisible(False)
        else:
            self.diff_range_label.setVisible(False)
            self.diff_range_spinbox.setVisible(False)
            self.img_min_label.setVisible(True)
            self.min_spinbox.setVisible(True)
            self.img_max_label.setVisible(True)
            self.max_spinbox.setVisible(True)

        # scale histogram
        levels = self.image_view.ui.histogram.item.getLevels()
        self.image_view.ui.histogram.item.setHistogramRange(levels[0], levels[1])

    def jump_frames(self):
        if self.beatNumber < self.frameIdx.value():
            self.image_view.jumpFrames(1)
        else:
            self.image_view.jumpFrames(-1)

        self.beatNumber = self.frameIdx.value()
        self.update_data()

    def line_start(self, x, y):
        y = np.clip(y, 0, IMAGE_SIZE)
        x = np.clip(x, 0, IMAGE_SIZE)
        self.x1 = x
        self.y1 = y
        self.startPoint.setData(pos=[[x, y]])
        self.line.setData(x=[self.x1, self.x2], y=[self.y1, self.y2])
        # print("Start", self.x1, self.y1)

    def line_end(self, x, y):
        y = np.clip(y, 0, IMAGE_SIZE)
        x = np.clip(x, 0, IMAGE_SIZE)
        self.x2 = x
        self.y2 = y
        self.endPoint.setData(pos=[[x, y]])
        self.line.setData(x=[self.x1, self.x2], y=[self.y1, self.y2])
        # print("End", self.x2, self.y2)

    def update_data(self):
        interval_idx = self.intervalIdx.value()-1
        color_range = (self.zero_val.value(), self.max_val.value())
        self.frameIdx.setMaximum(len(self.parent.data_slices[interval_idx]))
        self.numBeatDisplay.setText(" of " + str(len(self.parent.data_slices[interval_idx])))

        # show difference between frameIdx and the previous frame
        if self.show_diff.isChecked():
            color_range = (-self.diff_range.value(), self.diff_range.value())
            self.frameIdx.setMaximum(len(self.parent.data_slices[interval_idx]) - 1)
            data = np.diff(self.parent.data_slices[interval_idx], axis=0)[self.frameIdx.value()-1] * self.ms
        # show global min value for each pixel (non 0)
        elif self.show_min.isChecked():
            d = self.parent.data_slices[interval_idx]
            md = ma.masked_array(d, mask = d==0)
            data = np.min(md, axis=0) * self.ms
            data = ma.filled(data, data.max())
        # show global max value for each pixel
        elif self.show_max.isChecked():
            data = np.max(self.parent.data_slices[interval_idx], axis=0) * self.ms
        # show global mean value for each pixel (non 0)
        elif self.show_mean.isChecked():
            d = self.parent.data_slices[interval_idx]
            md = ma.masked_array(d, mask = d==0)
            data = np.mean(md, axis=0) * self.ms
        # show normal data at frameIdx
        else:
            data = self.parent.data_slices[interval_idx][self.frameIdx.value()-1] * self.ms

        # apply mask
        data = data * self.mask

        # set colormap
        if self.show_diff.isChecked():
            if (self.image_view.imageItem.getColorMap().getLookupTable() != self.divergent_cm.getLookupTable()).any():
                self.image_view.imageItem.setColorMap(self.divergent_cm)
                self.image_view.setColorMap(self.divergent_cm)
        else:
            if (self.image_view.imageItem.getColorMap().getLookupTable() != self.normal_cm.getLookupTable()).any():
                self.image_view.imageItem.setColorMap(self.normal_cm)
                self.image_view.setColorMap(self.normal_cm)

        # set image
        self.image_view.setImage(data,levels=color_range,autoRange=False)
        #print(self.frameIdx.value())
        #print(self.parent.data.shape)

        self.update_line()
        self.update_ui()
        self.parent.update_tab_title(interval_idx)
        self.image_view.update()

    def update_graph(self):
        if self.spatial_coords is not None and len(self.spatial_coords) >= 1:
            self.parent.update_graph(self.spatial_coords, self.frameIdx.value())

    def update_line(self):
        imgVw = self.image_view.getView()
        if self.hide_line.isChecked():
            if self.line_visable:
                # hide line
                imgVw.removeItem(self.line)
                imgVw.removeItem(self.startPoint)
                imgVw.removeItem(self.endPoint)
                self.line_visable = False
        else:
            if not self.line_visable:
                # plot line
                imgVw.addItem(self.line)
                imgVw.addItem(self.startPoint)
                imgVw.addItem(self.endPoint)
                self.line_visable = True

    def open_contour_window(self):
        self.contour_window = APDThresholdWindow(
            self, 
            self.beatNumber-1, 
            self.parent.data_slices[self.intervalIdx.value()-1]
        )
        self.contour_window.show()

    def save_histogram(self):
        # parent.parent.parent.signal gotta be the worst code in this whole project
        export_histogram(self.image_view.image, self.bin_size.value(), self.parent.parent.parent.signal.signal_name)

    def on_lut_change(self):
        if self.show_diff.isChecked():
            if (self.divergent_cm.getLookupTable() != self.image_view.imageItem.getColorMap().getLookupTable()).any():
                print("Div Colormap Changed")
                self.divergent_cm = self.image_view.imageItem.getColorMap()
        else:
            if (self.normal_cm.getLookupTable() != self.image_view.imageItem.getColorMap().getLookupTable()).any():
                print("Normal Colormap Changed")
                self.normal_cm = self.image_view.imageItem.getColorMap()
