import pickle
import os
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from cardiacmap.viewer.export import ImportExportDirectories
from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.scimedia import load_scimedia_data

from cardiacmap.viewer.components import FrameInputDialog, LargeFilePopUp

from cardiacmap.viewer.utils import load_settings, save_settings


class ParameterWidget(QWidget):
    def __init__(self, params):
        super().__init__()

class FileWidget(QWidget):
    def __init__(self, parent, filename):
        super().__init__()
        self.parent = parent
        self.label = QLabel(filename)
        self.delButton = QPushButton("X")
        self.delButton.setMaximumSize(20, 20)
        self.delButton.clicked.connect(self.delete)
        self.status = QLabel("                                  ") # empty label allows for progress updates

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.delButton)
        self.layout.addWidget(self.label)
        self.layout.addStretch(10)
        self.layout.addWidget(self.status)
        self.setLayout(self.layout)

    def delete(self):
        self.parent.delete_file(self)
        self.delButton.setParent(None)
        self.delButton.destroy()
        self.label.setParent(None)
        self.label.destroy()
        self.setLayout(None)
        self.destroy()

class InstructionWidget(QWidget):
    def __init__(self, parent, settings):
        super().__init__()
        self.parent = parent
        
        self.hlayout = QHBoxLayout()

        self.cbox = QComboBox()
        self.cbox.addItems(["Trim","Time Average","Spatial Average", "Baseline Drift Removal", "Normalize Peaks", "Normalize Signal", "Invert"])

        self.avgModeCBox = QComboBox()
        self.avgModeCBox.addItems(["Gaussian", "Uniform"])

        self.normModeCBox = QComboBox()
        self.normModeCBox.addItems(["Per-Pixel", "Global"])

        self.hlayout.addWidget(self.cbox)               # 0
        self.hlayout.addWidget(QLabel("Trim Start:"))   # 1
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Trim Parameters").child("Left").value()))       # 2
        self.hlayout.addWidget(QLabel("Trim End:"))     # 3
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Trim Parameters").child("Right").value()))       # 4
        self.hlayout.addWidget(QLabel("Mode:"))         # 5
        self.hlayout.addWidget(self.avgModeCBox)        # 6
        self.hlayout.addWidget(QLabel("Sigma:"))        # 7
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Spatial Average").child("Sigma").value()))       # 8
        self.hlayout.addWidget(QLabel("Radius:"))       # 9
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Spatial Average").child("Radius").value()))       # 10
        self.hlayout.addWidget(QLabel("Alternans:"))    # 11
        self.hlayout.addWidget(QCheckBox())             # 12
        self.hlayout.addWidget(QLabel("Prominence:"))   # 13
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Baseline Drift").child("Prominence").value()))       # 14
        self.hlayout.addWidget(QLabel("Min Distance:"))# 15
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Baseline Drift").child("Period Len").value()))       # 16
        self.hlayout.addWidget(QLabel("Threshold:"))    # 17
        self.hlayout.addWidget(MinWidthSpinbox(settings.child("Baseline Drift").child("Threshold").value()))       # 18
        self.hlayout.addWidget(QLabel("Mode:"))         # 19
        self.hlayout.addWidget(self.normModeCBox)       # 20
        self.hlayout.addStretch(10)
        self.paramsList = [[1, 5], [5, 11], [5, 11], [11, 19], [11, 19], [19, 21], [0, 0]] # indicies of needed parameters

        self.setLayout(self.hlayout)
        
        self.cbox.currentIndexChanged.connect(self.changeParams)
        self.changeParams()

    def delete(self):
        pass

    def changeParams(self):
        # show needed params, hide unneeded 
        paramIdx = self.paramsList[self.cbox.currentIndex()]
        for i in range(self.hlayout.count()-1):
            if (i >= paramIdx[0] and i < paramIdx[1]) or (i == 0):
                self.hlayout.itemAt(i).widget().show()
            else:
                self.hlayout.itemAt(i).widget().hide()

class MinWidthSpinbox(pg.SpinBox):
    def __init__(self, value):
        super().__init__()
        self.setMinimumWidth(80)
        self.setMaximum(1000)
        self.setValue(value)

class MultipleFilesWindow(QDialog):

    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("Process Multiple Files")
        self.setMinimumSize(700, 400)

        self.parent = parent
        self.settings = parent.settings

        self.file_list = []
        self.instruction_list = []
        self.instruction_params = []

        self.add_file_button = QPushButton("+ Add a file")
        self.add_file_button.clicked.connect(self.add_file)
        self.file_list_layout = QVBoxLayout()
        self.file_parent_layout = QVBoxLayout()
        self.file_parent_layout.addLayout(self.file_list_layout)
        self.file_parent_layout.addWidget(self.add_file_button)


        self.add_instruction_button = QPushButton("+ Add an instruction")
        self.add_instruction_button.clicked.connect(self.add_instruction)
        self.instruction_list_layout = QVBoxLayout()
        self.instruction_parent_layout = QVBoxLayout()
        self.instruction_parent_layout.addLayout(self.instruction_list_layout)
        self.instruction_parent_layout.addWidget(self.add_instruction_button)

        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.clicked.connect(self.process_multiple_files)

        self.file_suffix = QLineEdit("_processed")
        
        suffix_layout = QHBoxLayout()
        suffix_layout.addWidget(QLabel("Saved File Suffix:"))
        suffix_layout.addWidget(self.file_suffix)

        main_layout = QVBoxLayout()
        main_layout.addWidget(QLabel("Files:"))
        main_layout.addLayout(self.file_parent_layout)
        main_layout.addWidget(QLabel("Instructions:"))
        main_layout.addLayout(self.instruction_parent_layout)
        main_layout.addStretch(10)
        main_layout.addLayout(suffix_layout)
        main_layout.addWidget(self.confirm_button)

        self.setLayout(main_layout)


    def add_file(self):
        dirs = ImportExportDirectories() # get import directory
        filepaths = QFileDialog.getOpenFileNames(
            self,
            "Load File",
            dirs.importDir,
            "All Files (*)",
        )[0]
        for filepath in filepaths:
            if filepath:
                # add file to GUI
                newFile = FileWidget(self, filepath[filepath.rindex("/") + 1:])
                self.file_list_layout.addWidget(newFile)
                # add file to file list
                self.file_list.append(filepath)
                # update import directory
                dirs.importDir = filepath[:filepath.rindex("/") + 1]
                dirs.SaveDirectories()

    def delete_file(self, fileWidget):
        self.file_list_layout.removeWidget(fileWidget)

    def add_instruction(self):
        newInstruction = InstructionWidget(self, self.settings)
        self.instruction_list_layout.addWidget(newInstruction)
    
    def delete_instruction(self, instructionWidget):
        self.instruction_list_layout.removeWidget(instructionWidget)

    def process_multiple_files(self):
        for i in range(len(self.file_list)):
            file_item = self.file_list_layout.itemAt(i).widget()
            # load file
            file_item.status.setText("Loading File...")
            self.repaint()

            filepath = self.file_list[i]
            file_ext = filepath[filepath.rindex(".") + 1:]
            filename = os.path.split(filepath)[-1]

            if file_ext == "signal":
                with open(filepath, "rb") as f:
                    signal = pickle.load(f)
                    if signal.transformed_data is None:
                        # repopulate data fields
                        signal.transformed_data = signal.base_data
                        signal.previous_transform = signal.base_data

            elif file_ext == "dat":
                signal = load_cascade_file(filepath, LargeFilePopUp, False)[0]
            elif file_ext == "gsd":
                signal = load_scimedia_data(filepath, LargeFilePopUp)[0]
            elif file_ext == "mat":
                print("MatLab format not yet supported.")
            else: print("Error loading file: skipping " + filename + "...")

            # perform each instruction on the file
            for j in range(self.instruction_list_layout.count()):
                widget = self.instruction_list_layout.itemAt(j).widget()
                operation = widget.cbox.currentIndex()
                # execute operation
                match operation:
                    case 0:
                        l = widget.paramsList[operation][0] + 1
                        r = widget.paramsList[operation][0] + 3
                        lSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(l).widget()
                        rSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(r).widget()
                        left_trim = lSpinbox.value()
                        right_trim = rSpinbox.value()
                        
                        file_item.status.setText("Trimming...")
                        self.repaint()
                        signal.trim_data(int(left_trim), int(right_trim))
                    case 1:
                        m = widget.paramsList[operation][0] + 1
                        s = widget.paramsList[operation][0] + 3
                        r = widget.paramsList[operation][0] + 5

                        modeCombo: QComboBox = widget.hlayout.itemAt(m).widget()
                        sSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(s).widget()
                        rSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(r).widget()
                        mode = str(modeCombo.currentText())
                        sigma = sSpinbox.value()
                        radius = rSpinbox.value()

                        file_item.status.setText("Time Averaging...")
                        self.repaint()
                        signal.perform_average("time", sigma, int(radius), mode)
                    case 2:
                        m = widget.paramsList[operation][0] + 1
                        s = widget.paramsList[operation][0] + 3
                        r = widget.paramsList[operation][0] + 5

                        modeCombo: QComboBox = widget.hlayout.itemAt(m).widget()
                        sSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(s).widget()
                        rSpinbox: MinWidthSpinbox = widget.hlayout.itemAt(r).widget()
                        mode = str(modeCombo.currentText())
                        sigma = sSpinbox.value()
                        radius = rSpinbox.value()

                        file_item.status.setText("Spatial Averaging...")
                        self.repaint()
                        signal.perform_average("spatial", sigma, int(radius), mode)
                    case 3:
                        a = widget.paramsList[operation][0] + 1
                        p = widget.paramsList[operation][0] + 3
                        d = widget.paramsList[operation][0] + 5
                        t = widget.paramsList[operation][0] + 7

                        alternans = widget.hlayout.itemAt(a).widget().isChecked()
                        prominence = widget.hlayout.itemAt(p).widget().value()
                        distance = widget.hlayout.itemAt(d).widget().value()
                        if int(distance) == 0: distance = 1
                        thresh = widget.hlayout.itemAt(t).widget().value()

                        paramDict = {"alternans": alternans, "prominence": prominence, "distance": int(distance), "threshold": thresh}
                        file_item.status.setText("Removing Drift...")
                        self.repaint()
                        signal.remove_baseline(paramDict)
                    case 4:
                        a = widget.paramsList[operation][0] + 1
                        p = widget.paramsList[operation][0] + 3
                        d = widget.paramsList[operation][0] + 5
                        t = widget.paramsList[operation][0] + 7

                        alternans = widget.hlayout.itemAt(a).widget().isChecked()
                        prominence = widget.hlayout.itemAt(p).widget().value()
                        distance = widget.hlayout.itemAt(d).widget().value()
                        if int(distance) == 0: distance = 1
                        thresh = widget.hlayout.itemAt(t).widget().value()

                        paramDict = {"alternans": alternans, "prominence": prominence, "distance": int(distance), "threshold": thresh}
                        file_item.status.setText("Normalizing Peaks...")
                        self.repaint()
                        signal.remove_baseline(paramDict, peaks=True)
                    case 5:
                        m = widget.paramsList[operation][0] + 1
                        modeCombo: QComboBox = widget.hlayout.itemAt(m).widget()
                        globalMode: bool = modeCombo.currentIndex() == 1

                        file_item.status.setText("Normalizing Signal...")
                        self.repaint()
                        signal.normalize(globalMode)
                    case 6:
                        file_item.status.setText("Inverting Signal...")
                        self.repaint()
                        signal.invert_data()
                    case _:
                        print("Error")
            # save file
            with open(filepath[:filepath.rindex(".")] + str(self.file_suffix.text()) + ".signal", "wb") as f:
                signal.base_data = signal.transformed_data
                # empty these copies to save space
                signal.transformed_data = None
                signal.previous_transform = None
                pickle.dump(signal, f)
            file_item.status.setText("Done!")
            self.repaint()


