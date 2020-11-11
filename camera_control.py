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

import numpy as np
import logging

from PySide2 import QtGui
from PySide2.QtWidgets import QGroupBox
from PySide2.QtCore import Signal, Slot

from camera import AbstractCamera, TestCamera, HAS_VIMBA
if HAS_VIMBA:
    from camera import VimbaCamera

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main


# TODO camera control
#   pause running while setting roi - needs testing

USE_TEST_IMAGE = False

class CameraControl(QGroupBox):
    """ Class to control camera preview, camera object and evaluate button inputs """
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        self._first_show = True # whether form is shown for the first time
        self.cam: AbstractCamera = None # AbstractCamera as interface class for different cameras
        # if vimba software is installed
        if HAS_VIMBA and not USE_TEST_IMAGE:
            self.cam = VimbaCamera()
        else:
            self.cam = TestCamera()
            if not USE_TEST_IMAGE: logging.error('No camera found! Fallback to test cam!')

        self.cam.new_image_available.connect(self.update_image)
        self.update()
        self._oneshot_eval = False

    def __del__(self):
        # self.cam.stop_streaming()
        del self.cam

    def showEvent(self, event):
        if self._first_show:
            self.connect_signals()
            self.cam.snapshot()
            self.ui.camera_prev.prepare()

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.cam.stop_streaming()

    def connect_signals(self):
        # button signals
        self.ui.startCamBtn.clicked.connect(self.prev_start_pushed)
        self.ui.setROIBtn.clicked.connect(self.apply_roi)
        self.ui.resetROIBtn.clicked.connect(self.cam.reset_roi)

    def is_streaming(self) -> bool:
        """ Return whether camera object is aquiring frames """
        return self.cam.is_running

    @Slot()
    def prev_start_pushed(self, event):
        if self.ui.startCamBtn.text() != 'Stop':
            self.cam.start_streaming()
            self.ui.startCamBtn.setText('Stop')
            self.ui.frameInfoLbl.setText('Running')
        else:
            self.cam.stop_streaming()
            self.ui.startCamBtn.setText('Start')
            self.cam.snapshot()
            self.ui.frameInfoLbl.setText('Stopped')
            self.ui.drpltDataLbl.setText(str(self.ui.camera_prev._droplet))

    @Slot()
    def apply_roi(self):
        """ Apply the ROI selected by the rubberband rectangle """
        x,y,h,w = self.ui.camera_prev.get_roi()
        self.cam.set_roi(x,y,w,h)

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ gets called when a new image is available from the camera """
        if self.cam.is_running:
            eval = True
            self.ui.frameInfoLbl.setText('Running | FPS: ' + str(self.cam.get_framerate()))
        elif self._oneshot_eval:
            eval = True
            self._oneshot_eval = False
        else:
            eval = False

        self.ui.camera_prev.update_image(cv_img, eval)

        self.ui.drpltDataLbl.setText(str(self.ui.camera_prev._droplet))
