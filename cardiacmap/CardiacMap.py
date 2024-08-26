import sys
from PySide6 import QtWidgets
from cardiacmap.viewer.windows import CardiacMap

if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    main_window = CardiacMap()
    main_window.show()

    sys.exit(app.exec())
