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

import sys
import os
import pydevd
import gc
import atexit
import logging
from PySide2.QtGui import QResizeEvent, QPixmap
from PySide2.QtWidgets import QMainWindow, QApplication, QSplashScreen
from PySide2.QtCore import QCoreApplication, QSettings

from ui_form import Ui_main

from camera_control import CameraControl
from magnet_control import MagnetControl
# from pump_control import PumpControl
from data_control import DataControl
#from measurement_control import MeasurementControl
from light_widget import LightWidget

# TODO use QSettings to store settings ( also maybe put some stuff in dialog boxes)

# TODO comments for droplet, camera control etc

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_main()
        self.ui.setupUi(self)
        atexit.register(self.cleanup)
        self.ui.statusbar.showMessage('Welcome!', timeout=5)
        self._size = self.size()
        self.show()

    def __del__(self):
        del self.ui.camera_prev

    def resizeEvent(self, event: QResizeEvent):
        # prevent resizing of window
        self.setFixedSize(self._size)

    def closeEvent(self, event):
        self.ui.camera_prev.closeEvent(event)

    def cleanup(self):
        del self

if __name__ == "__main__":
    os.system('pyside2-uic -o ui_form.py qt_resources/form.ui')
    logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)
    QCoreApplication.setOrganizationName("OTH Regensburg")
    QCoreApplication.setApplicationName("MAEsure")
    app = QApplication(sys.argv)
    pic = QPixmap('qt_resources/maesure.png')
    splash = QSplashScreen(pic)#, Qt.WindowStaysOnTopHint)
    #splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setMask(pic.mask())
    splash.show()
    app.processEvents()
    widget = MainWindow()
    #widget.show()
    splash.finish(widget)
    sys.exit(app.exec_())
