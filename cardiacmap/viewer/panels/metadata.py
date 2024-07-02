from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget, QSplitter
from cardiacmap.model.signal import CascadeSignal
from cardiacmap.viewer.panels.settings import ParameterWidget

class MetadataPanel(QWidget):

    def __init__(self, signal: CascadeSignal, parent):
        super().__init__(parent=parent)
        self.parent=parent

        label_layout = QHBoxLayout()
        self.signal = signal
        metadata = self.signal.metadata
        # TODO: Refactor this nicely later using QFormLayout
        label_layout.addWidget(QLabel("File:\nFrames:\nChannel:"))
        label_layout.addWidget(QLabel(f"{metadata['filename']}\n{self.parent.signal.span_T}\n{self.parent.signal.channel}"))
        label_layout.addWidget(QLabel("    Position (x, y):\n\n"))
        self.position_label = QLabel(f"{self.parent.x}, {self.parent.y}\n\n")
        label_layout.addWidget(self.position_label)
        label_layout.addStretch()

        label = QWidget()
        label.setLayout(label_layout)

        settings_widget = ParameterWidget(self.parent.params_parent)

        splitter = QSplitter()

        splitter.addWidget(label)
        splitter.addWidget(settings_widget)

        main_layout = QHBoxLayout()
        main_layout.addWidget(splitter)

        self.setLayout(label_layout)

