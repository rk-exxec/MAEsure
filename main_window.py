#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2020  Raphael Kriegl

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https://www.gnu.org/licenses/>.

# This Python file uses the following encoding: utf-8
import os
import atexit

from PySide2.QtWidgets import QMainWindow
from PySide2.QtCore import QFile, Signal
from PySide2.QtUiTools import QUiLoader
#from ui_main import Ui_main

from camera_control import CameraControl

class MainWindow(QMainWindow):
    start_acquisition_signal = Signal()
    stop_acquisition_signal = Signal()
    def __init__(self):
        super(MainWindow, self).__init__()
        loader = QUiLoader(self)
        file = QFile("./form.ui")
        file.open(QFile.ReadOnly)
        loader.registerCustomWidget(CameraControl)
        self.ui = loader.load(file)
        file.close()
        self.setCentralWidget(self.ui)
        resizing!!!
        self.resize()
        # self.ui = Ui_main()
        # self.ui.setupUi(self)
        atexit.register(self.cleanup)
        #self.ui.btn_prev_st.clicked.connect(self.prev_start_pushed)
        #self.ui.btn_set_roi.clicked.connect(self.ui.camera_prev.apply_roi)
        #self.ui.btn_reset_roi.clicked.connect(self.ui.camera_prev.reset_roi)
        #self.start_acquisition_signal.connect(self.ui.camera_prev.start_preview)
        #self.stop_acquisition_signal.connect(self.ui.camera_prev.stop_preview)
        self.show()
        

    def __del__(self):
        del self.ui.camera_prev

    def cleanup(self):
        del self

    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()

    def prev_start_pushed(self, event):
        if self.ui.btn_prev_st.text() != 'Stop':
            self.start_acquisition_signal.emit()
            #self.ui.camera_prev.start_preview()
            self.ui.btn_prev_st.setText('Stop')
        else:
            #self.ui.camera_prev.stop_preview()
            self.stop_acquisition_signal.emit()
            self.ui.btn_prev_st.setText('Start')