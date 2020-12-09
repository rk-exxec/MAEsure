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

from threading import Thread
import numpy as np
import logging
from datetime import datetime

from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter as VidWriter
import cv2
from PySide2 import QtGui
from PySide2.QtWidgets import QFileDialog, QGroupBox, QInputDialog
from PySide2.QtCore import QSignalBlocker, Signal, Slot

from camera import AbstractCamera, TestCamera, HAS_VIMBA
if HAS_VIMBA:
    from camera import VimbaCamera

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main


# TODO camera control
#   pause running while setting roi - needs testing

# TODO add ability to load video instead of using camera, with new camera class and moviepy ffmpeg reader?

USE_TEST_IMAGE = False

class CameraControl(QGroupBox):
    """ Class to control camera preview, camera object and evaluate button inputs """
    update_image_signal = Signal(np.ndarray, bool)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        logging.info("Init CameraControl")
        self.ui: Ui_main = self.window().ui
        self._first_show = True # whether form is shown for the first time
        self.cam: AbstractCamera = None # AbstractCamera as interface class for different cameras
        self.video_dir = "."
        self.recorder: VidWriter = None
        #self.recorder = cv2.VideoWriter()
        # if vimba software is installed
        if HAS_VIMBA and not USE_TEST_IMAGE:
            self.cam = VimbaCamera()
        else:
            self.cam = TestCamera()
            if not USE_TEST_IMAGE: logging.error('No camera found! Fallback to test cam!')       
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
        #self.recorder.release()
        self.recorder.close()
        self.cam.stop_streaming()
        

    def connect_signals(self):
        self.cam.new_image_available.connect(self.update_image)
        self.update_image_signal.connect(self.ui.camera_prev.update_image)
        # button signals
        self.ui.startCamBtn.clicked.connect(self.prev_start_pushed)
        self.ui.setROIBtn.clicked.connect(self.apply_roi)
        self.ui.resetROIBtn.clicked.connect(self.cam.reset_roi)
        self.ui.actionVideo_Path.triggered.connect(self.set_video_path)

    def is_streaming(self) -> bool:
        """ Return whether camera object is aquiring frames """
        return self.cam.is_running

    @Slot()
    def prev_start_pushed(self, event):
        if self.ui.startCamBtn.text() != 'Stop':
            if self.ui.record_chk.isChecked():
                now = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.recorder = VidWriter(filename=self.video_dir + f"/{now}.mp4",
                                            size=self.cam.get_resolution(),
                                            fps=self.cam.get_framerate(),
                                            codec='mpeg4',
                                            preset='ultrafast',
                                            bitrate='5000k')
                #self.recorder.open(self.video_dir + f"/{now}.mp4", 0x21 ,self.cam.get_framerate(),self.cam.get_resolution())
                logging.info(f"Start video recording. File: {self.video_dir}/{now}.mp4 Resolution:{str(self.cam.get_resolution())}@{self.cam.get_framerate()}")
            self.cam.start_streaming()
            logging.info("Start camera stream")
            self.ui.startCamBtn.setText('Stop')
            self.ui.record_chk.setEnabled(False)
            self.ui.frameInfoLbl.setText('Running')
        else:
            self.cam.stop_streaming()
            if self.ui.record_chk.isChecked():
                self.recorder.close()
                #self.recorder.release()
                logging.info("Stoped video recording")
            self.ui.record_chk.setEnabled(True)
            logging.info("Stop camera stream")
            self.ui.startCamBtn.setText('Start')
            self.cam.snapshot()
            self.ui.frameInfoLbl.setText('Stopped')
            self.ui.drpltDataLbl.setText(str(self.ui.camera_prev._droplet))

    @Slot()
    def apply_roi(self):
        """ Apply the ROI selected by the rubberband rectangle """
        x,y,w,h = self.ui.camera_prev.get_roi()
        self.cam.set_roi(x,y,w,h)

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ gets called when a new image is available from the camera """
        # block image signal to prevent overloading
        blocker = QSignalBlocker(self.cam)
        if self.cam.is_running:
            eval = self.ui.evalChk.isChecked()
            self.ui.frameInfoLbl.setText('Running | FPS: ' + str(self.cam.get_framerate()))
            # save image frame if recording
            if self.ui.record_chk.isChecked():
                self.recorder.write_frame(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
                #self.recorder.write(cv_img)
        elif self._oneshot_eval:
            eval = True
            self._oneshot_eval = False
        else:
            eval = False

        if self.cam._image_size_invalid:
            self.ui.camera_prev.invalidate_imagesize()
            self.cam._image_size_invalid = False
        # thread = Thread(target=self.ui.camera_prev.update_image, args=(cv_img, eval),)
        self.ui.camera_prev.update_image(cv_img, eval)
        # thread.start()
        #self.update_image_signal.emit(cv_img, eval)

        self.ui.drpltDataLbl.setText(str(self.ui.camera_prev._droplet))
        blocker.unblock()

    @Slot()
    def set_video_path(self):
        res = QFileDialog.getExistingDirectory(self, "Select default video directory", ".")
        self.video_dir = res
