from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QLabel, QSplitter,
                               QWidget)

from cardiacmap.model.data import CascadeSignal
from cardiacmap.viewer.panels.settings import ParameterWidget


class MetadataPanel(QWidget):

    def __init__(self, signal: CascadeSignal, parent):
        super().__init__(parent=parent)
        self.parent = parent

        label_layout = QHBoxLayout()
        self.signal = signal
        metadata = self.signal.metadata
        # TODO: Refactor this nicely later using QFormLayout

        self.filename = QLabel(metadata["filename"])
        self.frames = QLabel(str(self.signal.span_T))
        self.channel = QLabel(self.signal.channel)

        self.img_position = QLabel(f"{self.parent.x}, {self.parent.y}\n\n")
        self.frame_index = QLabel("64")
        self.signal_value = QLabel("64")

        left_col = QFormLayout()
        left_col.addRow(QLabel("File: "), self.filename)
        left_col.addRow(QLabel("Frames: "), self.frames)
        left_col.addRow(QLabel("Channel: "), self.channel)

        mid_col = QFormLayout()
        mid_col.addRow(QLabel("Position (x, y): "), self.img_position)
        mid_col.addRow(QLabel("Frame Index: "), self.frame_index)
        mid_col.addRow(QLabel("Signal Value: "), self.signal_value)

        label_layout.addLayout(left_col)
        label_layout.addLayout(mid_col)
        label_layout.addStretch()
        # label_layout.addWidget(self.parent.console)

        label = QWidget()
        label.setLayout(label_layout)

        self.setLayout(label_layout)
