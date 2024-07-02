
from pyqtgraph.parametertree import ParameterTree
from PySide6 import QtWidgets
from PySide6.QtWidgets import (QHBoxLayout, QPushButton, QWidget)

class ParameterWidget(QWidget):
    def __init__(self, params):
        super().__init__()
        self.toggle = QPushButton(self)
        self.toggle.setText("◀")
        self.toggle.setCheckable(True)
        self.toggle.clicked.connect(self.toggle_parameter_tree)
        self.toggle.setStyleSheet(
            """QPushButton {
                background-color: grey;
                border: none;
                color: #FFFFFF;
                font: bold 20px;
                height: 100%;
            }
            QPushButton:hover {
                background-color: #2B5DD1;
            }"""
        )
        self.toggle.setMinimumWidth(18)
        self.toggle.setMaximumWidth(18)
        self.toggle.resize(18, self.height())
        self.toggle.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        # Hide the ParameterTree initially

        self.tree_widget = ParameterTree()
        self.tree_widget.setParameters(params, showTop=True)
        self.tree_widget.setVisible(False)

        settings_layout = QHBoxLayout()
        settings_layout.addWidget(self.toggle)
        settings_layout.addWidget(self.tree_widget)

        self.setLayout(settings_layout)
        # Toggle ParameterTree visibility when the dropdown button is clicked
        # self.custom_tool_button.dropdown_button.clicked.connect(self.toggle_parameter_tree)

    def toggle_parameter_tree(self):
        visible = self.tree_widget.isVisible()
        self.tree_widget.setVisible(not visible)
        if visible:
            self.toggle.setText("◀")
            self.setMinimumWidth(0)
        else:
            self.toggle.setText("▶")
            self.resize(1000, self.height())
            self.setMinimumWidth(500)