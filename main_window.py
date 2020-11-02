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
from PySide2.QtGui import QResizeEvent, QShowEvent

from PySide2.QtWidgets import QComboBox, QMainWindow
from PySide2.QtCore import QFile, Qt, Signal, Slot
from PySide2.QtUiTools import QUiLoader
from ui_form import Ui_main

from camera_control import CameraControl
from magnet_control import MagnetControl
#from pump_control import PumpControl
from data_control import DataControl
#from measurement_control import MeasurementControl
from light_widget import LightWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        #cctl = CameraControl() # test for syntax errors
        #del cctl
        #self.ui = None
        #self._first_show = True
        #self.load_ui()
        #self.resize(self.ui.size())
        self.ui = Ui_main()
        self.ui.setupUi(self)
        atexit.register(self.cleanup)
        self.ui.statusbar.showMessage('Welcome!')
        self._size = self.size()
        #self.magnet_ctl = MagnetControl(self)
        #self.meas_ctl = MeasurementControl()

        self.show()

    def __del__(self):
        del self.ui.camera_prev

    def resizeEvent(self, event: QResizeEvent):
        self.setFixedSize(self._size)

    def closeEvent(self, event):
        self.ui.camera_prev.closeEvent(event)

    def cleanup(self):
        del self

    def load_ui(self):
        loader = QUiLoader(self)
        file = QFile("./form.ui")
        file.open(QFile.ReadOnly)
        loader.registerCustomWidget(CameraControl)
        loader.registerCustomWidget(MagnetControl)
        loader.registerCustomWidget(DataControl)
        loader.registerCustomWidget(LightWidget)
        self.ui = loader.load(file)
        file.close()
        self.setCentralWidget(self.ui)
