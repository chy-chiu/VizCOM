from functools import partial

import numpy as np
import pyqtgraph as pg
from pyqtgraph.GraphicsScene.mouseEvents import HoverEvent, MouseDragEvent
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QToolBar,
    QVBoxLayout,
    QWidget,
)
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
INITIAL_POSITION = (64, 64)
POSITION_MARKER_SIZE = 5
VIEWPORT_MARGIN = 2


class DraggablePlot(pg.PlotItem):

    # Draggable PlotItem that takes in a callback function.
    def __init__(self, callback):
        super().__init__()

        self.callback = callback

    def mouseClickEvent(self, event: MouseDragEvent):
        pos = self.vb.mapSceneToView(event.scenePos())

        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def mouseDragEvent(self, event: MouseDragEvent):

        pos = self.vb.mapSceneToView(event.scenePos())

        self.callback(int(pos.x()), int(pos.y()))
        return event.pos()

    def hoverEvent(self, event: HoverEvent):
        if not event.isExit():
            # the mouse is hovering over the image; make sure no other items
            # will receive left click/drag events from here.
            event.acceptDrags(Qt.MouseButton.LeftButton)


class PositionView(QWidget):

    def __init__(self, parent):

        super().__init__(parent=parent)
        self.parent = parent

        self.init_image_view()
        self.init_player_bar()

        layout = QVBoxLayout()
        layout.addWidget(self.data_bar)
        layout.addWidget(self.image_view)
        layout.addWidget(self.player_bar)
        layout.addWidget(self.settings_bar)
        layout.addWidget(self.px_bar)
        self.setLayout(layout)
        
        self.init_colormap()

        self.update_data()

        # self.position_callback = position_callback

    def init_image_view(self):

        # Set up Image View
        view = DraggablePlot(self.update_position)
        self.image_view = pg.ImageView(view=view)
        self.image_view.setMinimumSize(QSize(256, 256))
        self.image_view.view.enableAutoRange(enable=True)
        self.image_view.view.setMouseEnabled(False, False)

        self.image_view.view.setRange(
            xRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
            yRange=(-VIEWPORT_MARGIN, IMAGE_SIZE + VIEWPORT_MARGIN),
        )

        # Hide UI stuff not needed
        self.image_view.ui.roiBtn.hide()
        self.image_view.ui.menuBtn.hide()
        #self.image_view.ui.histogram.hide()

        self.image_view.view.showAxes(False)
        self.image_view.view.invertY(True)

        # Draggable posiiton marker
        self.position_marker = pg.ScatterPlotItem(
            pos=[INITIAL_POSITION],
            size=POSITION_MARKER_SIZE,
            pen=pg.mkPen("r"),
            brush=pg.mkBrush("r"),
        )

        self.image_view.getView().addItem(self.position_marker)

        self.image_view.sigTimeChanged.connect(
            self.parent.signal_panel.update_signal_marker
        )

        return self.image_view

    def init_player_bar(self):
        self.px_bar = QToolBar()
        self.player_bar = QToolBar()
        self.settings_bar = QToolBar()
        self.data_bar = QToolBar()

        play_button = QAction("⏯", self)
        forward_button = QAction("⏭", self)
        back_button = QAction("⏮", self)

        font = QFont("Arial", 15)
        play_button.setFont(font)
        forward_button.setFont(font)
        back_button.setFont(font)

        self.skiprate = Spinbox(
            min=1, max=10000, val=10, min_width=60, max_width=60, step=10
        )

        play_button.triggered.connect(self.image_view.togglePause)
        forward_button.triggered.connect(partial(self.jump_frames, forward=True))
        back_button.triggered.connect(partial(self.jump_frames, forward=False))

        # Need to update it for the first time first
        self.framerate = Spinbox(
            min=1, max=10000, val=50, min_width=60, max_width=60, step=10
        )
        self.update_framerate()
        self.framerate.valueChanged.connect(self.update_framerate)

        self.player_bar.addAction(back_button)
        self.player_bar.addAction(play_button)
        self.player_bar.addAction(forward_button)
        self.settings_bar.addWidget(QLabel("   FPS: "))
        self.settings_bar.addWidget(self.framerate)
        self.settings_bar.addWidget(QLabel("   Skip Frames: "))
        self.settings_bar.addWidget(self.skiprate)

        self.data_select = QComboBox()
        self.data_select.addItems(["Base", "Transformed"])
        self.data_select.currentTextChanged.connect(self.update_data)

        self.show_marker = QCheckBox()
        self.show_marker.setChecked(True)
        self.show_marker.stateChanged.connect(self.toggle_marker)

        self.x_box = Spinbox(
            min=0, max=127, val=64, min_width=50, max_width=50, step=1
        )
        self.y_box = Spinbox(
            min=0, max=127, val=64, min_width=50, max_width=50, step=1
        )
            
        self.x_box.valueChanged.connect(self.update_position_boxes)
        self.y_box.valueChanged.connect(self.update_position_boxes)

        self.data_bar.addWidget(QLabel("Data: "))
        self.data_bar.addWidget(self.data_select)
        
        self.px_bar.addWidget(QLabel("   X: "))
        self.px_bar.addWidget(self.x_box)
        self.px_bar.addWidget(QLabel("   Y: "))
        self.px_bar.addWidget(self.y_box)
        self.px_bar.addWidget(QLabel("   Marker: "))
        self.px_bar.addWidget(self.show_marker)

    def update_framerate(self):
        framerate = self.framerate.value()
        self.image_view.playRate = framerate

    def jump_frames(self, forward=True):
        skip_frames = int(self.skiprate.value() * self.parent.ms)
        (
            self.image_view.jumpFrames(skip_frames)
            if forward
            else self.image_view.jumpFrames(-skip_frames)
        )

    def update_position(self, x, y):

        y = np.clip(y, 0, IMAGE_SIZE - 1)
        x = np.clip(x, 0, IMAGE_SIZE - 1)

        self.update_marker(x, y)
        self.parent.x = x
        self.parent.y = y
        self.parent.update_signal_plot()
        self.update_position_boxes(val=None)
            
    def update_position_boxes(self, val=None):
        #print("Update Boxes val", val)
        if val is not None:
            # set position to box values
            x = int(self.x_box.value())
            y = int(self.y_box.value())
            self.update_marker(x, y)
            self.parent.x = x
            self.parent.y = y
            self.parent.update_signal_plot()
        else:
            # set box values to position
            self.x_box.blockSignals(True) # block signals to avoid
            self.y_box.blockSignals(True) # circular callback
            self.x_box.setValue(self.parent.x)
            self.y_box.setValue(self.parent.y)
            self.x_box.blockSignals(False)
            self.y_box.blockSignals(False)

    def init_colormap(self):
        cmap_name = "nipy_spectral"
        self.cmap = pg.colormap.get(cmap_name, source="matplotlib")
        
    def update_colormap(self):
        print("colormap update")

    def update_data(self):
        mode = self.data_select.currentText() or "Base"
        mask = np.ones((self.parent.signal.span_X, self.parent.signal.span_X))
        if self.parent.signal.mask is not None:
            mask = self.parent.signal.mask
            #print(mask)
        if mode == "Base":
            self.image_view.setImage(
                self.parent.signal.image_data * mask, autoLevels=False, autoRange=False
            )
        elif mode == "Transformed":
            self.image_view.setImage(
                self.parent.signal.transformed_data * mask, autoLevels=False, autoRange=False
            )
            
        self.image_view.setColorMap(self.cmap)

    def update_marker(self, x, y):
        self.position_marker.setData(pos=[[x, y]])

    def toggle_marker(self):
        (
            self.position_marker.setVisible(True)
            if self.show_marker.isChecked()
            else self.position_marker.setVisible(False)
        )
