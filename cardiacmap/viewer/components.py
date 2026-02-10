from typing import List, Optional
import numpy as np
import psutil
import os
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidgetAction,
    QDialogButtonBox,
    QMessageBox,
    QVBoxLayout,
)

SPINBOX_STYLE = """SpinBox
            {
                border: 1px solid;
                border-radius: 2px;
            }

            SpinBox::up-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                top: -5px;
                right: 0px;
            }

            SpinBox::down-button
            {
                min-width: 5px;
                min-height: 5px;
                subcontrol-origin: margin;
                subcontrol-position: right;
                bottom: -5px;
                right: 0px;
            }"""

COMPOSITE_BUTTON_STYLE = """
            QGroupBox  {
                border: 1px solid #C0C0C0;
                border-radius: 5px;
                background: transparent;

            }
            QPushButton {
            border: 1px;
            background: transparent;
            }

            QPushButton:hover {
                background: #D3D3D3;
            }
            
            QPushButton:menu-indicator {
                left: -3px;
                top: -1px;
            }
            
            """

PARAMETER_BUTTON_STYLE = """
            QToolButton {
                border: 1px solid #C0C0C0;
                border-radius: 5px;
                background: transparent;
            }

            QToolButton:hover {
                background: #D3D3D3;
            }
            
            QToolButton:menu-button {
                background: transparent;
                left: -3px;
                top: 1px;
            }
            """


class ParameterButton(QToolButton):

    def __init__(
        self, label, params: Parameter, actions: Optional[List[QAction]] = None
    ):

        super().__init__()

        menu = QMenu(self)

        tree_widget = ParameterTree()
        tree_widget.setParameters(params, showTop=False)

        widgetaction = QWidgetAction(self)
        widgetaction.setDefaultWidget(tree_widget)

        if actions:
            for action in actions:
                menu.addAction(action)
        menu.addAction(widgetaction)

        self.setText(label + "   ")
        self.setMenu(menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        self.setStyleSheet(PARAMETER_BUTTON_STYLE)

        self.show()


class ParameterConfirmButton(QGroupBox):
    def __init__(self, label: str, params: Parameter, callback = None):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(2, 2, 2, 2)

        self.action = QPushButton(label)
        self.action.setStyleSheet("QPushButton {margin-left: 5px;}")
        self.confirm = QPushButton("✔")
        self.reset = QPushButton("✖")

        self.menu_button = QPushButton(" ")
        # self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        menu = QMenu(self)
        tree_widget = ParameterTree()
        tree_widget.setParameters(params, showTop=False)

        # connect a callback for updating preview
        if callback is not None:
            for param in params:
                param.sigValueChanged.connect(lambda: callback(action = "calculate"))

        widgetaction = QWidgetAction(self)
        widgetaction.setDefaultWidget(tree_widget)
        menu.addAction(widgetaction)
        self.menu_button.setMenu(menu)

        # Add buttons to layout
        layout.addWidget(self.action)
        layout.addWidget(self.confirm)
        layout.addWidget(self.reset)
        layout.addWidget(self.menu_button)

        self.disable_confirm_buttons()

        self.setStyleSheet(COMPOSITE_BUTTON_STYLE)

        # # Set rounded corners and margin to the outer widget
        self.setLayout(layout)
        # self.setFixedSize(300, 50)

    def enable_confirm_buttons(self):
        self.confirm.setDisabled(False)
        self.reset.setDisabled(False)

        self.confirm.setStyleSheet(
            "QPushButton {background-color: #6A9F58; color: white;} QPushButton:hover { background-color: #808080; color: white;}"
        )
        self.reset.setStyleSheet(
            "QPushButton {background-color: #D1615D; color: white;} QPushButton:hover { background-color: #808080; color: white;}"
        )

    def disable_confirm_buttons(self):
        self.confirm.setStyleSheet(
            "QPushButton {background: transparent; color: #808080;}"
        )
        self.reset.setStyleSheet(
            "QPushButton {background: transparent; color: #808080;}"
        )


class Spinbox(pg.SpinBox):

    def __init__(self, min=0, max=10000, val=1, min_width=30, max_width=60, step=1):
        super().__init__()
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        self.setMinimum(min)
        self.setMaximum(max)
        self.setValue(val)
        self.setSingleStep(step)
        self.setStyleSheet(SPINBOX_STYLE)

    def resetMax(self, max):
        self.setMaximum(max)


def LargeFilePopUp(tLen, maxFrames):
    print("Max Possible Frames:", maxFrames)

    dialog = FrameInputDialog(tLen, maxFrames)
    if dialog.exec() == QDialog.Accepted:
        return dialog.getValues()
    else:
        return None, None

class FrameInputDialog(QDialog):
    def __init__(self, tLen, maxFrames, parent=None):
        super(FrameInputDialog, self).__init__(parent)
        self.tLen = tLen
        self.maxFrames = maxFrames

        self.setWindowTitle("Large File Handler")

        layout = QVBoxLayout(self)
        sublayout1 = QHBoxLayout()
        sublayout2 = QHBoxLayout()

        startLabel = QLabel(f"Start Frame (0, {tLen}):")
        self.startInput = Spinbox(0, tLen, 0, min_width=100, max_width=100)
        endLabel = QLabel(f"End Frame (1, {tLen}):")
        self.endInput = Spinbox(maxFrames, tLen, tLen, min_width=100, max_width=100)
        sublayout1.addWidget(startLabel)
        sublayout1.addWidget(self.startInput)
        sublayout1.addWidget(endLabel)
        sublayout1.addWidget(self.endInput)

        checkbox_label = QLabel("Large File Mode (Disable \"undo\" and \"reset\"):")
        self.large_file_mode_checkbox = QCheckBox()
        self.large_file_mode_checkbox.checkStateChanged.connect(self.change_maxframes)
        sublayout2.addWidget(checkbox_label)
        sublayout2.addWidget(self.large_file_mode_checkbox)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        sublayout2.addWidget(self.buttons)

        self.framesLabel1 = QLabel(f"This file contains {tLen} frames. This machine has free memory for {maxFrames} frames.")
        self.framesLabel2 = QLabel(f"This file contains {tLen} frames. This machine has free memory for {maxFrames * 3} frames.")
        self.framesLabel2.hide()

        layout.addWidget(self.framesLabel1)
        layout.addWidget(self.framesLabel2)
        layout.addSpacing(15)
        layout.addWidget(QLabel(f"Please select a subset of frames from the file, or enable \"Large File Mode\""))
        layout.addSpacing(30)
        layout.addLayout(sublayout1)
        layout.addLayout(sublayout2)
        layout.addStretch()

    def change_maxframes(self):
        if self.large_file_mode_checkbox.isChecked():
            self.framesLabel2.show()
            self.framesLabel1.hide()
            self.maxFrames = int(self.maxFrames * 3)
        else:
            self.framesLabel1.show()
            self.framesLabel2.hide()
            self.maxFrames = int(self.maxFrames / 3)

    def accept(self):
        start = int(self.startInput.value())
        end = int(self.endInput.value())

        if end and start:

            if start < 0 or start >= self.tLen:
                QMessageBox.warning(self, "Invalid Input", f"Start frame must be between 0 and {self.tLen - 1}.")
                return

            if end <= start or end > self.tLen:
                QMessageBox.warning(self, "Invalid Input", f"End frame must be between {start + 1} and {self.tLen}.")
                return

            if end - start > self.maxFrames:
                QMessageBox.warning(self, "Invalid Input", f"Maximum frame range is {self.maxFrames}.")
                return

        self.start = start
        self.end = end
        super().accept()

    def reject(self):
        super().reject()

    def getValues(self):
        return self.start, self.end, self.large_file_mode_checkbox.isChecked()

def large_file_check(filepath, _callback, fileLen):
    """Helper method to check a Cascade file against available RAM to avoid OOM error
    Args:
        filepath(str): Input file path
    Returns:
        tuple: (skip_frames, read_frames) or (0, 0) if file is small enough to handle
    """
    USAGE_THRESHOLD = .6
    ram = psutil.virtual_memory()
    print(f"Total RAM (GB): {round(ram.total / 1e9, 2)}")
    print(f"Available RAM (GB): {round(ram.available / 1e9, 2)}")
    print(f"File Size (GB): {round(os.path.getsize(filepath) / 1e9, 2)}")
    freeMem = ram.available
    dataSize = (
        os.path.getsize(filepath) * 6
    )  # estimate conversion to float32 and 3 data sets (raw, transformed, previous)


    # default return vals
    (skip, size) = (0, 0)
    large_file = False

    usePercentage = dataSize / freeMem

    # use 70% threshold to leave room for apd, di, fft, etc.
    if usePercentage > USAGE_THRESHOLD:
        maxFrames = int((freeMem * .6) / 524288) # ESTIMATE (32 bits * 128 * 128)
        start, end, large_file = _callback(fileLen, maxFrames)  # pauses execution until popup is closed

        print(start, end)

        if start is not None and end is not None:
            skip = start
            size = end - start
        else:
            return None

    return (skip, size), large_file