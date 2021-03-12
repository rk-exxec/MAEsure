#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2021  Raphael Kriegl

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
sys.path.append('./src')
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

# FIXME sometimes doenst kill process on close, camera?

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

def initialize_logger(out_dir):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
     
    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    #formatter = logging.Formatter("%(levelname)s - %(message)s")
    #handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(out_dir, "error.log"),"w", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    #formatter = logging.Formatter("%(levelname)s - %(message)s")
    #handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # create debug file handler and set level to debug
    handler = logging.FileHandler(os.path.join(out_dir, "all.log"),"w")
    handler.setLevel(logging.DEBUG)
    #formatter = logging.Formatter("%(levelname)s - %(message)s")
    #handler.setFormatter(formatter)
    logger.addHandler(handler)

if __name__ == "__main__":
    # compile python qt form into python file
    os.system('pyside2-uic -o src/ui_form.py qt_resources/form.ui')
    # setup logging
    #logging.basicConfig(filename='app.log', filemode='w', level=logging.DEBUG)
    initialize_logger("./log")
    # pysde2 settings config
    QCoreApplication.setOrganizationName("OTH Regensburg")
    QCoreApplication.setApplicationName("MAEsure")
    # init application
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
    # execute qt main loop
    sys.exit(app.exec_())
