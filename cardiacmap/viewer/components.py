import pyqtgraph as pq
from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction, QSpinBox)
from PySide6.QtGui import QAction
from typing import Optional, List

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

class ParameterButton(QToolButton):

    def __init__(self, label, params: Parameter, actions: Optional[List[QAction]]=None):

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

        self.setText(label)
        self.setMenu(menu)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        self.show()

class Spinbox(QSpinBox):

    def __init__(self, min=0, max=10000, val=1, min_width=30, max_width=60, step=1):
        super().__init__()
        self.setMinimumWidth(min_width)
        self.setMaximumWidth(max_width)
        self.setMinimum(min)
        self.setMaximum(max)
        self.setValue(val)
        self.setSingleStep(step)
        self.setStyleSheet(SPINBOX_STYLE)

 