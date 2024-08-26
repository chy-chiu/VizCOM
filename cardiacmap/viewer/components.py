import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
    QSpinBox,
    QGroupBox,
)
from PySide6.QtGui import QAction
from typing import Optional, List
from PySide6.QtCore import Qt

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

PARAMETERBUTTON_STYLE = """
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

        self.setStyleSheet(PARAMETERBUTTON_STYLE)

        self.show()


class ParameterConfirmButton(QGroupBox):
    def __init__(self, label: str, params: Parameter):
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

        self.confirm.setStyleSheet("QPushButton {background-color: #6A9F58; color: white;} QPushButton:hover { background-color: #808080; color: white;}")
        self.reset.setStyleSheet("QPushButton {background-color: #D1615D; color: white;} QPushButton:hover { background-color: #808080; color: white;}")

    def disable_confirm_buttons(self):
        self.confirm.setStyleSheet("QPushButton {background: transparent; color: #808080;}")
        self.reset.setStyleSheet("QPushButton {background: transparent; color: #808080;}")


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
