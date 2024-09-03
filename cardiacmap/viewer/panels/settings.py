from pyqtgraph.parametertree import Parameter, ParameterTree
from PySide6 import QtWidgets
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cardiacmap.viewer.utils import load_settings, save_settings


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
        self.toggle.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding
        )
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


class SettingsDialog(QDialog):

    def __init__(self, settings: Parameter):
        super().__init__()

        self.setWindowTitle("Settings")
        self.settings = settings
        
        main_layout = QVBoxLayout()

        self.param_tree = ParameterTree()

        self.param_tree.setParameters(settings, showTop=True)

        main_layout.addWidget(self.param_tree)

        button_layout = QHBoxLayout()
        load_button = QPushButton("Load from file")
        load_button.clicked.connect(self._load_from_path)  # Load button action

        save_button = QPushButton("Save to file")
        save_button.clicked.connect(self._save_settings)  # Save button action

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)  # Save button action

        button_layout.addWidget(apply_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def _save_settings(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Settings", "settings.json", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            save_settings(self.settings, file_path)
        self.accept()

    def _load_from_path(self):

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Settings", "", "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            self.settings = load_settings(settings_path=file_path)
