from functools import partial

import pyqtgraph as pg
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

TITLE_STYLE = """QDockWidget::title
{
font-family: "Roboto Lt";
font-size: 18pt;
background: #DCDCDC;
padding-left: 10px;
padding-top: 4px;
}
"""


class ColorPaletteButton(QAction):
    """Button for Opening Color Palette Window"""

    def __init__(self, parent, label="Color Palette"):
        super().__init__(label)
        self.parent = parent
        self.triggered.connect(self.open_color_palette)

    def open_color_palette(self):
        self.window = ColorPalette(self, self.parent.colors)
        self.window.show()

    def new_colors(self, key, newColor):
        self.parent.colors[key] = newColor
        self.parent.update_pens()


class ColorPalette(QMainWindow):
    """Window for color customization"""

    def __init__(self, parent, colors):
        super().__init__()
        self.parent = parent
        self.resize(200, 0)
        self.setStyleSheet(TITLE_STYLE)
        self.color_buttons = []

        self.default_widget = QWidget()
        if len(colors) == 0:
            layout = QHBoxLayout()
            layout.addStretch()
            layout.addWidget(QLabel("No Colors"))
            layout.addStretch()
        else:
            layout = QVBoxLayout()
            for c in colors:
                self.color_buttons.append(pg.ColorButton(color=colors[c]))
                self.color_buttons[-1].sigColorChanged.connect(
                    partial(self.update_color, key=c)
                )

                row = QHBoxLayout()
                row.addWidget(QLabel(c + " "))
                row.addWidget(self.color_buttons[-1])

                layout.addLayout(row)
            layout.addStretch()

        self.default_widget.setLayout(layout)
        self.default_widget.setStyleSheet("QLabel {font-size:20px; }")
        self.setCentralWidget(self.default_widget)

    def update_color(self, colorButton, key="none"):
        print("Updating", key)
        self.parent.new_colors(key, colorButton.color())
