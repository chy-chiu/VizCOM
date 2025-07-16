import os
import pickle
import sys
import copy
from functools import partial
from typing import List, Literal, Optional
import numpy as np
import pyqtgraph as pg
import scipy.io
from pyqtgraph.console import ConsoleWidget
from pyqtgraph.parametertree import Parameter
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDockWidget,
    QFileDialog,
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
    QDialogButtonBox,
    QMessageBox,
    QLineEdit,
)

from cardiacmap.model.cascade import load_cascade_file
from cardiacmap.model.scimedia import load_scimedia_data
from cardiacmap.model.sql import load_sql_file
from cardiacmap.model.data import CardiacSignal

from cardiacmap.viewer.panels import (
    AnnotateView,
    APDWindow,
    FFTWindow,
    IsochroneWindow,
    MetadataPanel,
    PositionView,
    SettingsDialog,
    SignalPanel,
    StackingWindow,
)
from cardiacmap.viewer.components import FrameInputDialog
from cardiacmap.viewer.utils import load_settings, loading_popup, save_settings
from cardiacmap.viewer.export import ExportVideoWindow, ImportExportDirectories


TITLE_STYLE = """QDockWidget::title
{
font-family: "Roboto Lt";
font-size: 18pt;
background: #DCDCDC;
padding-left: 10px;
padding-top: 4px;
}
"""
INITIAL_POSITION = (64, 64)
WIDTH_SCALE = 0.6
HEIGHT_SCALE = 0.4


class CardiacMap(QMainWindow):
    """Main window for signal analysis"""

    def __init__(self, signal: Optional[CardiacSignal] = None, title: str = ""):

        super().__init__()

        self.title = title
        screen_size = QGuiApplication.primaryScreen().size()
        self.init_width = screen_size.width() * WIDTH_SCALE
        self.init_height = screen_size.height() * HEIGHT_SCALE
        self.settings = load_settings()

        self.resize(self.init_width, self.init_height)
        self.setStyleSheet(TITLE_STYLE)
        self.init_menu()

        # # TODO: Fix / Add Console Function
        # self.console = ConsoleWidget()
        # self.console.setMinimumWidth(500)
        # self.console.setMinimumHeight(100)

        # size_policy = QtWidgets.QSizePolicy()
        # size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        # size_policy.setHorizontalPolicy(QtWidgets.QSizePolicy.Policy.MinimumExpanding)
        # self.console.setSizePolicy(size_policy)

        self.signal = signal

        self.default_widget = QWidget()
        layout = QHBoxLayout()
        layout.addStretch()
        layout.addWidget(
            QLabel(
                'No files loaded. Load a Cascade Image File with "File → Load Data" to continue...'
            )
        )
        layout.addStretch()
        self.default_widget.setLayout(layout)
        self.default_widget.setStyleSheet("QLabel {font-size:20px; }")

        self.init_viewer()

    def init_menu(self):

        self.menubar = QMenuBar(self)
        self.menubar.setNativeMenuBar(False)
        self.menubar.setStyleSheet("QMenuBar {border-bottom: 1px solid #D3D3D3;}")

        self.file_menu = self.menubar.addMenu("File")
        # self.transforms_menu = self.menubar.addMenu("Transforms")
        self.windows_menu = self.menubar.addMenu("Windows")

        # Settings Menu
        self.settings_menu = self.menubar.addAction("Settings")
        self.settings_menu.triggered.connect(self.open_settings)

        # File Menu
        self.load_voltage = QAction("Load Voltage Data")
        self.load_voltage.triggered.connect(
            partial(self.load_cascade, calcium_mode=False)
        )

        self.load_calcium = QAction("Load Voltage / Calcium Data")
        self.load_calcium.triggered.connect(
            partial(self.load_cascade, calcium_mode=True)
        )

        self.load_scimedia_single = QAction("Load SciMedia Data (Beta)")
        self.load_scimedia_single.triggered.connect(self.load_scimedia)

        self.load_voltage_sql = QAction("Load SQL Data")
        self.load_voltage_sql.triggered.connect(
            partial(self.load_sql, calcium_mode=False)
        )

        self.load_calcium_sql = QAction("Load SQL VCa Data")
        self.load_calcium_sql.triggered.connect(
            partial(self.load_sql, calcium_mode=True)
        )

        self.load_saved_signal = QAction("Load Saved Signal")
        self.load_saved_signal.triggered.connect(self.load_preprocessed)

        self.save_signal = QAction("Save Signal Object")
        self.save_signal.triggered.connect(self.save_preprocessed)

        self.export_vid = QAction("Export Video")
        self.export_vid.triggered.connect(self.create_export_window)
        
        self.export_npy = QAction("Export Signal to NumPy")
        self.export_npy.triggered.connect(self.export_numpy)

        self.export_mat = QAction("Export Signal to MATLAB")
        self.export_mat.triggered.connect(self.export_matlab)

        self.file_menu.addAction(self.load_voltage)
        self.file_menu.addAction(self.load_calcium)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.load_voltage_sql)
        self.file_menu.addAction(self.load_calcium_sql)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.load_scimedia_single)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.load_saved_signal)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_signal)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_npy)
        self.file_menu.addAction(self.export_mat)
        self.file_menu.addAction(self.export_vid)
        
        # Windows Menu
        self.stacking = QAction("Stacking")
        self.stacking.triggered.connect(self.create_stacking_window)
        self.apd = QAction("APD / DI")
        self.apd.triggered.connect(self.create_apd_window)
        self.isochrone = QAction("Isochrone / Vector Map")
        self.isochrone.triggered.connect(self.create_isochrone_window)
        self.fft = QAction("FFT", self)
        self.fft.triggered.connect(self.create_fft_window)

        self.windows_menu.addAction(self.stacking)
        self.windows_menu.addAction(self.apd)
        self.windows_menu.addAction(self.isochrone)
        self.windows_menu.addAction(self.fft)

        # # TODO: Transforms Menu
        # self.transforms_menu.addAction("Spatial Average")
        # self.transforms_menu.addAction("Time Average")

        # Help Menu
        self.help = self.menubar.addAction("Help")
        self.help.triggered.connect(self.load_help)

        self.setMenuBar(self.menubar)

        return

    def _disable_menus(self, disable: bool):

        self.windows_menu.setDisabled(disable)
        self.settings_menu.setDisabled(disable)
        self.save_signal.setDisabled(disable)

    def init_viewer(self):

        self.setWindowTitle(
            self.title + " – CardiacMap" if self.title else "CardiacMap"
        )

        if self.signal:

            self.x, self.y = INITIAL_POSITION

            self.metadata_panel = MetadataPanel(self.signal, self)

            # Create Signal view
            self.signal_panel = SignalPanel(
                self, main_signal=True, settings=self.settings
            )

            # Create Image tabs
            self.position_tab = PositionView(self)
            self.position_tab.image_view.setImage(
                self.signal.image_data, autoLevels=True, autoRange=False
            )

            self.annotate_tab = AnnotateView(self)

            self.image_tabs = QTabWidget()

            self.image_tabs.addTab(self.position_tab, "Video")
            self.image_tabs.addTab(self.annotate_tab, "Mask")

            # Create docking windows for viewer and signa view.
            self.metadata_panel.setMaximumHeight(self.init_height * 0.2)
            self.setCentralWidget(self.metadata_panel)

            self.signal_dock = QDockWidget("Signal View", self)
            self.image_dock = QDockWidget("Image View", self)

            self.signal_dock.setWidget(self.signal_panel)
            self.image_dock.setWidget(self.image_tabs)

            self.signal_dock.setMinimumWidth(self.init_width * 0.4)

            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.image_dock)
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.signal_dock)

            self.ms_changed()  # initialize plot with scaled x values

            self.setGeometry(100, 100, self.init_width, self.init_height)

            self.default_widget.setVisible(False)
            self._disable_menus(False)

            self.resizeDocks(
                [self.image_dock, self.signal_dock],
                [500, 2500],
                Qt.Orientation.Horizontal,
            )
            self.resizeDocks(
                [self.image_dock, self.signal_dock],
                [1000, 1000],
                Qt.Orientation.Vertical,
            )

            image_size_policy = QtWidgets.QSizePolicy()
            image_size_policy.setHorizontalPolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
            image_size_policy.setHorizontalStretch(1)

            signal_size_policy = QtWidgets.QSizePolicy()
            signal_size_policy.setHorizontalPolicy(
                QtWidgets.QSizePolicy.Policy.MinimumExpanding
            )
            signal_size_policy.setHorizontalStretch(5)

            metadata_size_policy = QtWidgets.QSizePolicy()
            metadata_size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Policy.Minimum)

            self.image_dock.setSizePolicy(image_size_policy)
            self.signal_dock.setSizePolicy(signal_size_policy)
            self.metadata_panel.setSizePolicy(metadata_size_policy)

        else:

            self.setCentralWidget(self.default_widget)
            self._disable_menus(True)

    def load_cascade(self, calcium_mode: bool):
        dirs = ImportExportDirectories() # get import directory
        filepath = QFileDialog.getOpenFileName(
            self,
            "Load Cascade File",
            dirs.importDir,
            "Cascade File (*.dat);;All Files (*)",
        )[0]

        if filepath and ".dat" in filepath:
            # update import directory
            dirs.importDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            self._load_signal(filepath, calcium_mode=calcium_mode)

    def load_sql(self, calcium_mode: bool):
        dirs = ImportExportDirectories() # get import directory
        filepath = QFileDialog.getOpenFileName(
            self,
            "Load SQL File",
            dirs.importDir,
            "SQLite (*.sql);;All Files (*)",
        )[0]

        if filepath and ".sql" in filepath:
            # update import directory
            dirs.importDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            self._load_signal(filepath, calcium_mode=calcium_mode, mode="sql")

    @loading_popup
    def load_scimedia(self, update_progress=None):
        dirs = ImportExportDirectories() # get import directory
        filepath = QFileDialog.getOpenFileName(
            self,
            "Load SciMedia File",
            dirs.importDir,
            "SciMedia CMOS File(*.gsd);;All Files (*)",
        )[0]

        if filepath and ".gsd" in filepath:
            # update import directory
            dirs.importDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            self._load_signal(
                filepath,
                calcium_mode=False,
                mode="scimedia",
                update_progress=update_progress,
            )

    def _load_signal(
        self,
        filepath,
        calcium_mode: bool,
        mode: Literal["cascade", "scimedia", "sql"] = "cascade",
        update_progress=None,
    ):

        filename = os.path.split(filepath)[-1]

        if mode == "cascade":
            signals = load_cascade_file(
                filepath, self.largeFilePopUp, dual_mode=calcium_mode
            )
        elif mode == "scimedia":
            signals = load_scimedia_data(filepath, self.largeFilePopUp)

        elif mode == "sql":
            signals = load_sql_file(
                filepath, self.largeFilePopUp, dual_mode=calcium_mode
            )

        if update_progress:
            update_progress(0.5)

        if signals:

            if calcium_mode:

                signal_odd: CardiacSignal = signals[0]
                signal_even: CardiacSignal = signals[1]

                print(signal_odd.signal_name)

                for signal, suffix in [(signal_odd, "_odd"), (signal_even, "_even")]:
                    self.create_viewer(signal, filename + suffix)
            else:
                signal = signals[0]

                self.create_viewer(signal, filename)

        else: print("There was an Error loading that file.")

    def load_preprocessed(self):
        dirs = ImportExportDirectories() # get import directory
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Load Preprocessed Signal",
            dirs.importDir,
            "CardiacMap Signal (*.signal);;All Files (*)",
        )
        if filepath:
            # update import directory
            dirs.importDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            with open(filepath, "rb") as f:
                signal = pickle.load(f)
                if signal.transformed_data is None:
                    # repopulate data fields
                    signal.transformed_data = signal.base_data
                    signal.previous_transform = signal.base_data
                print(signal.transformed_data)
                self.create_viewer(signal, os.path.split(filepath)[-1])

    def save_preprocessed(self):
        dirs = ImportExportDirectories() # get import directory
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed Signal",
            dirs.exportDir + f"{self.signal.signal_name}.signal",
            "CardiacMap Signal (*.signal);;All Files (*)",
        )
        if filepath:
            # update import directory
            dirs.exportDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            with open(filepath, "wb") as f:
                print(self.signal.transformed_data)
                signal_copy = copy.deepcopy(self.signal)
                signal_copy.base_data = signal_copy.transformed_data
                # empty these copies to save space
                signal_copy.transformed_data = None
                signal_copy.previous_transform = None
                pickle.dump(signal_copy, f)
            
    def export_numpy(self):
        start_frame = self.signal_panel.start_frame
        end_frame = self.signal_panel.end_frame
        
        dirs = ImportExportDirectories() # get import directory
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporting Transformed Signal to NumPy binary",
            dirs.exportDir + f"{self.signal.signal_name}.npy",
            "NumPy binary (*.npy);;All Files (*)",
        )
        if filepath:
            # update import directory
            dirs.exportDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            np.save(filepath, self.signal.transformed_data[start_frame:end_frame])
        
    def export_matlab(self):
        start_frame = self.signal_panel.start_frame
        end_frame = self.signal_panel.end_frame
        
        dirs = ImportExportDirectories() # get import directory
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporting Transformed Signal to MATLAB binary",
            dirs.exportDir + f"{self.signal.signal_name}.mat",
            "MAT binary (*.mat);;All Files (*)",
        )
        if filepath:
            # update import directory
            dirs.exportDir = filepath[:filepath.rindex("/") + 1]
            dirs.SaveDirectories()
            scipy.io.savemat(filepath, {'data': self.signal.transformed_data[start_frame:end_frame]})
    

    # TODO: Fix scroll / header issue here
    def load_help(self):
        self.help_window = QtWidgets.QMainWindow(self)
        self.help_browser = QWebEngineView()
        self.help_toolbar = QtWidgets.QToolBar()
        # self.help_browser.urlChanged.connect(lambda url: print("New URL:", url))

        self.forward_button = QAction(">")
        self.forward_button.triggered.connect(self.help_browser.forward)
        self.back_button = QAction("<")
        self.back_button.triggered.connect(self.help_browser.back)

        self.help_toolbar.addAction(self.back_button)
        self.help_toolbar.addAction(self.forward_button)

        # Load Help Pages
        file_path = "./help/HelpGuide.html"
        url = QtCore.QUrl.fromLocalFile(QtCore.QFileInfo(file_path).absoluteFilePath())
        print(url)
        self.help_browser.load(url)

        # Help
        self.pages_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.help_toolbar)
        layout.addWidget(self.help_browser)
        self.pages_widget.setLayout(layout)

        self.help_window.setCentralWidget(self.pages_widget)

        self.help_window.setWindowTitle("Help")
        self.help_window.resize(600, 400)

        # Store the help window in the instance, so it doesn't get garbage collected
        self.help_window.show()

    def anchorClicked(self, x):
        print("clicked:", x)

    def create_viewer(self, signal: CardiacSignal, title: str):
        """IF there is a signal already, create a new viewer window. Otherwise
        load signal in current window"""

        if self.signal:

            viewer = CardiacMap(signal, title)
            viewer.show()

        else:
            self.title = title
            self.signal: CardiacSignal = signal
            self.init_viewer()

    def largeFilePopUp(self, tLen, maxFrames):
        print("Max Possible Frames:", maxFrames)

        dialog = FrameInputDialog(tLen, maxFrames, self)
        if dialog.exec() == QDialog.Accepted:
            return dialog.getValues()
        else:
            return None, None

    def update_signal_value(self, evt, idx=None):

        if self.signal_panel.signal_marker:
            if not idx:
                idx = self.signal_panel.signal_marker.getXPos()
            idx = int(idx / self.ms)
            if idx >= 0 and idx < len(self.signal_panel.signal_data.getData()[0]):

                self.metadata_panel.frame_index.setText(str(idx))
                self.metadata_panel.signal_value.setText(
                    f"{self.signal_panel.signal_data.getData()[1][idx]:.3f}"
                )

    def update_signal_index(self, evt, idx=None):
        if not idx:
            idx = self.signal_panel.signal_marker.getXPos()
        idx = int(idx / self.ms)

        self.position_tab.image_view.setCurrentIndex(idx)

    def update_signal_plot(self):
        signal_data = self.signal.transformed_data[:, self.x, self.y]

        xs = self.xVals[0 : len(signal_data)]  # ensure len(xs) == len(signal_data)
        self.signal_panel.signal_data.setData(x=xs, y=signal_data)

        self.metadata_panel.img_position.setText(f"{self.x}, {self.y}")

        self.update_signal_value(None, idx=self.signal_panel.frame_idx)

        self.start_frame_offset = self.signal_panel.start_spinbox.value() * self.ms

        if self.signal.show_baseline:
            self.signal_panel.show_baseline()
        else:
            self.signal_panel.baseline_data.setData()

        if self.signal.show_apd_threshold:

            sig_idx = self.x * self.signal.span_X + self.y
            indices, thresh = self.signal.get_apd_threshold()

            tX = indices[sig_idx] * self.ms
            tY = [thresh for t in tX]

            self.signal_panel.apd_data.setData(tX, tY)
        else:
            self.signal_panel.apd_data.setData()

    def ms_changed(self):
        self.ms = self.signal_panel.ms_per_frame.value()
        self.xVals = np.arange(0, self.ms * self.signal.span_T, self.ms)
        print("updated ms:", self.ms)
        self.update_signal_plot()
        self.signal_panel.update_range_spinbox()

    @loading_popup
    def signal_transform(
        self,
        transform: Literal[
            "spatial_average", "time_average", "trim", "normalize", "reset", "invert"
        ],
        update_progress=None,
    ):
        start_frame = self.signal_panel.start_frame
        end_frame = self.signal_panel.end_frame

        if update_progress:
            # print(update_progress)
            # print("progres update?")
            update_progress(0.1)
        # Calls a transform function within the signal item
        if transform == "spatial_average":
            sigma = self.settings.child("Spatial Average").child("Sigma").value()
            radius = self.settings.child("Spatial Average").child("Radius").value()
            mode = self.settings.child("Spatial Average").child("Mode").value()
            self.signal.perform_average(
                type="spatial",
                sig=sigma,
                rad=radius,
                mode=mode,
                update_progress=update_progress,
                start=start_frame,
                end=end_frame,
            )
            if (self.settings.child("Normalize").child("Auto").value()):
                normalize_global = self.settings.child("Normalize").child("Mode").value()
                normalize_global = True if normalize_global == "Global" else False
                self.signal.normalize(start=start_frame, end=end_frame, normalize_global=normalize_global)
            
        elif transform == "time_average":
            sigma = self.settings.child("Time Average").child("Sigma").value()
            radius = self.settings.child("Time Average").child("Radius").value()
            mode = self.settings.child("Time Average").child("Mode").value()
            self.signal.perform_average(
                type="time",
                sig=sigma,
                rad=radius,
                mode=mode,
                start=start_frame,
                end=end_frame,
            )
            if (self.settings.child("Normalize").child("Auto").value()):
                normalize_global = self.settings.child("Normalize").child("Mode").value()
                normalize_global = True if normalize_global == "Global" else False
                self.signal.normalize(start=start_frame, end=end_frame, normalize_global=normalize_global)

        elif transform == "trim":
            left = start_frame
            right = max(len(self.signal.transformed_data) - end_frame, 1)
            print("Trim Left", left, "Trim Right", right)
            self.signal.trim_data(startTrim=left, endTrim=right)
            if (self.settings.child("Normalize").child("Auto").value()):
                    normalize_global = self.settings.child("Normalize").child("Mode").value()
                    normalize_global = True if normalize_global == "Global" else False
                    self.signal.normalize(start=0, end=len(self.signal.transformed_data), normalize_global=normalize_global)
            
        elif transform == "normalize":
            normalize_global = self.settings.child("Normalize").child("Mode").value()
            normalize_global = True if normalize_global == "Global" else False
            self.signal.normalize(start=start_frame, end=end_frame, normalize_global=normalize_global)
        elif transform == "reset":
            self.signal.reset_data()
            
        elif transform == "undo":
            self.signal.undo()

        elif transform == "invert":
            self.signal.invert_data()
            if (self.settings.child("Normalize").child("Auto").value()):
                normalize_global = self.settings.child("Normalize").child("Mode").value()
                normalize_global = True if normalize_global == "Global" else False
                self.signal.normalize(start=start_frame, end=end_frame, normalize_global=normalize_global)
        self.update_signal_plot()
        self.position_tab.update_data()

    # @loading_popup
    def calculate_baseline_drift(
        self, action: Literal["calculate", "confirm", "reset"], update_progress=None
    ):
        start_frame = int(self.signal_panel.start_spinbox.value())
        end_frame = int(self.signal_panel.end_spinbox.value())

        dst = int(
            self.settings.child("Baseline Drift").child("Period Len").value() / self.ms
        )
        prominence = self.settings.child("Baseline Drift").child("Prominence").value()
        threshold = self.settings.child("Baseline Drift").child("Threshold").value()
        alternans = self.settings.child("Baseline Drift").child("Alternans").value()
        if dst < 1:
            dst = 1
        if prominence == 0:
            prominence = 0.00001
        params = dict(
            {
                "alternans": alternans,
                "threshold": threshold,
                "distance": dst,
                "prominence": prominence,
            }
        )
        if action == "calculate":
            self.signal_panel.show_baseline(2, params)
            self.signal_panel.baseline_drift.enable_confirm_buttons()
            self.signal.show_baseline = True
        else:
            if action == "confirm":
                self.signal.remove_baseline(
                    params, peaks=False, start=start_frame, end=end_frame
                )
                if (self.settings.child("Normalize").child("Auto").value()):
                    normalize_global = self.settings.child("Normalize").child("Mode").value()
                    normalize_global = True if normalize_global == "Global" else False
                    self.signal.normalize(start=start_frame, end=end_frame, normalize_global=normalize_global)

            self.signal_panel.show_baseline(0)
            self.signal.reset_baseline()
            self.signal.show_baseline = False

            self.signal_panel.baseline_drift.disable_confirm_buttons()

        self.update_signal_plot()

    def normalize_peaks(
        self, action: Literal["calculate", "confirm", "reset"], update_progress=None
    ):
        start_frame = int(self.signal_panel.start_spinbox.value())
        end_frame = int(self.signal_panel.end_spinbox.value())
        dst = int(
            self.settings.child("Baseline Drift").child("Period Len").value() / self.ms
        )
        prominence = self.settings.child("Baseline Drift").child("Prominence").value()
        threshold = self.settings.child("Baseline Drift").child("Threshold").value()
        alternans = self.settings.child("Baseline Drift").child("Alternans").value()

        if dst < 1:
            dst = 1
        if prominence == 0:
            prominence = 0.00001
        params = dict(
            {
                "alternans": alternans,
                "threshold": threshold,
                "distance": dst,
                "prominence": prominence,
            }
        )
        if action == "calculate":
            self.signal_panel.show_baseline(1, params)
            self.signal_panel.normalize_peaks.enable_confirm_buttons()
            self.signal.show_baseline = True
        else:
            if action == "confirm":
                self.signal.remove_baseline(
                    params, peaks=True, start=start_frame, end=end_frame
                )
            self.signal_panel.show_baseline(0)
            self.signal_panel.normalize_peaks.disable_confirm_buttons()
            self.signal.show_baseline = False

        self.update_signal_plot()

    def create_apd_window(self):
        self.apd_window = APDWindow(self)
        self.apd_window.show()

    def create_stacking_window(self):
        self.stacking_window = StackingWindow(self)
        self.stacking_window.show()

    def create_isochrone_window(self):
        self.isochrone_window = IsochroneWindow(self)
        self.isochrone_window.show()

    def create_export_window(self):
        self.export_window = ExportVideoWindow(self)
        self.export_window.show()

    def create_fft_window(self):
        self.fft_window = FFTWindow(self)
        self.fft_window.show()

    def open_settings(self):

        _settings = SettingsDialog(self.settings)
        _settings.exec()


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)

    # signals = load_cascade_file("2011-08-23_Exp000_Rec112_Cam1-Blue.dat", None)

    # signal = signals[0]

    # viewer = CardiacMap(signal)

    # viewer.show()

    main_window = CardiacMap()
    main_window.show()

    sys.exit(app.exec())
