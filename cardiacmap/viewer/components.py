from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QHBoxLayout,
                               QInputDialog, QLabel, QMainWindow, QMenu,
                               QMenuBar, QPlainTextEdit, QPushButton,
                               QSplitter, QTabWidget, QToolBar, QToolButton,
                               QVBoxLayout, QWidget, QWidgetAction)
from PySide6.QtGui import QAction
from typing import Optional, List

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