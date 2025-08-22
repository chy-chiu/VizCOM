from functools import partial

import pyqtgraph as pg
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from cardiacmap.viewer.components import Spinbox
from cardiacmap.viewer.utils import load_settings, save_settings

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
        self.settings = parent.settings
        self.triggered.connect(self.open_color_palette)

    def open_color_palette(self):
        self.window = ColorPalette(self, self.parent.colors)
        self.window.show()

    def new_colors(self, key, newColor):
        self.parent.colors[key] = newColor
        self.parent.update_pens()
        
    def new_thickness(self, spinbox):
        self.parent.thickness = spinbox.value()
        self.parent.update_pens()

    def new_font_size(self, spinbox):
        self.parent.fontSize = spinbox.value()
        self.parent.update_pens()


class ColorPalette(QMainWindow):
    """Window for color customization"""

    def __init__(self, parent, colors):
        super().__init__()
        self.parent = parent
        self.settings = parent.settings
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

                if c == "points":
                    row.addWidget(QLabel("Size: "))
                    initVal = self.settings.child("Signal Plot Colors").child("ptSize").value()
                    self.sizeSpinbox = Spinbox(1, 100, initVal, 45, 45, 1)
                    self.sizeSpinbox.sigValueChanged.connect(
                        partial(self.save_spinbox, itemKey="ptSize")    
                    )
                    row.addWidget(self.sizeSpinbox)

                elif c == "axis":
                    row.addWidget(QLabel("Font Size: "))
                    initVal = self.settings.child("Signal Plot Colors").child("fontSize").value()
                    self.fontSizeSpinbox = Spinbox(1, 100, initVal, 45, 45, 1)
                    self.fontSizeSpinbox.sigValueChanged.connect(self.update_font_size)
                    row.addWidget(self.fontSizeSpinbox)


                layout.addLayout(row)
                
            row = QHBoxLayout()
            row.addWidget(QLabel("Line Thickness: "))
            initVal = self.settings.child("Signal Plot Colors").child("thickness").value()
            self.thickSpinbox = Spinbox(1, 100, initVal, 45, 45, 1)
            self.thickSpinbox.sigValueChanged.connect(self.update_thickness)
            row.addWidget(self.thickSpinbox)
            layout.addLayout(row)
            layout.addStretch()

        self.default_widget.setLayout(layout)
        self.default_widget.setStyleSheet("QLabel {font-size:20px; }")
        self.setCentralWidget(self.default_widget)

    def update_color(self, colorButton, key="none"):
        self.parent.new_colors(key, colorButton.color())
        self.save_color(colorButton.color(), key)
        
    def save_color(self, color: QColor, itemKey):
        print("Signal Plot Colors", itemKey, color)
        self.parent.settings.child("Signal Plot Colors").child(itemKey).setValue(color.getRgb())
        save_settings(self.parent.settings)
        
    def update_thickness(self, thickness):
        self.save_spinbox(self.thickSpinbox, "thickness")
        self.parent.new_thickness(thickness)

    def update_font_size(self, size):
        self.save_spinbox(self.fontSizeSpinbox, "fontSize")
        self.parent.new_font_size(size)
        
    def save_spinbox(self, spinbox, itemKey="none"):
        self.parent.settings.child("Signal Plot Colors").child(itemKey).setValue(spinbox.value())
        save_settings(self.parent.settings)
        self.parent.parent.toggle_points()
