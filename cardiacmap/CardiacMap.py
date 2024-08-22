import sys
from PySide6 import QtWidgets
from cardiacmap.viewer.windows import CardiacMapWindow

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    main_window = CardiacMapWindow()
    main_window.show()

    sys.exit(app.exec())
