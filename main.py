
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
import sys
import os
import atexit
from typing import Optional
import cv2
import numpy as np
#import threading
#from vimba import *
from pymba import Vimba, Frame

from PySide2 import QtGui
from PySide2.QtWidgets import QApplication, QMainWindow
from PySide2.QtCore import QFile, Signal, Slot, Qt, QThread, QObject
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QPixmap
from ui_main import Ui_main


class VideoThread(QThread):
    change_pixmap_signal = Signal(np.ndarray)

    def run(self):
        cap = cv2.VideoCapture(0)
        while True:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)


# class Handler(QObject):
#     change_pixmap_signal = Signal(np.ndarray)

#     def __init__(self):
#         super(Handler, self).__init__()
#         #self.shutdown_event = threading.Event()

#     def __call__(self, cam: Camera, frame: Frame):
#         if frame.get_status() == FrameStatus.Complete:
#             print('{} acquired {}'.format(cam, frame), flush=True)

#         #msg = 'Stream from \'{}\'. Press <Enter> to stop stream.'
#             # cv2.imshow(msg.format(cam.get_name()), frame.as_opencv_image())
#             self.change_pixmap_signal.emit(frame.as_opencv_image())
#         cam.queue_frame(frame)


# class CameraControl:
#     def __init__(self, handler):
#         self.cam: Camera
#         self.is_running = False
#         with Vimba.get_instance() as vimba:
#             self.cam = vimba.get_all_cameras()[0]
#             with self.cam as cam:
#                 try:
#                     cam.stop_streaming()
#                 except:
#                     pass
#                 cv_fmts = intersect_pixel_formats(cam.get_pixel_formats(), OPENCV_PIXEL_FORMATS)
#                 mono_fmts = intersect_pixel_formats(cv_fmts, MONO_PIXEL_FORMATS)
#                 if mono_fmts:
#                     cam.set_pixel_format(mono_fmts[0])
    # def __del__(self):
    #     with self.cam as cam:
    #         cam.stop_streaming()

    # def start_stop_preview(self):
    #     if self.is_running:
    #         with self.cam as cam:
    #             try:
    #                 cam.stop_streaming()
    #                 self.is_running = False
    #             except: 
    #                 pass
    #     else:
    #         with self.cam as cam:
    #             try:
    #                 cam.start_streaming(handler=handler, buffer_count=10)
    #                 self.is_running = True
    #             except: 
    #                 pass

class CameraControl(QObject):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self):
        super(CameraControl, self).__init__()
        self.cam = ''
        self.is_running = False
        self.vimba = Vimba()
        self.vimba.startup()
        self.cam = self.vimba.camera(0)
        #self.cam.close()
        self.cam.open()

        self.cam.arm('Continuous', self.frame_handler)

    def __del__(self):
        self.cam.stop_frame_acquisition()
        self.cam.disarm()
        self.cam.close()
        del self.vimba

    def start_stop_preview(self):
        if self.is_running:
            self.cam.stop_frame_acquisition()
        else:
            self.cam.start_frame_acquisition()

    def frame_handler(self, frame: Frame, delay: Optional[int] = 1) -> None:
        img = frame.buffer_data_numpy()
        self.change_pixmap_signal.emit(img)


class main(QMainWindow):
    def __init__(self):
        super(main, self).__init__()
        self.ui = Ui_main()
        self.ui.setupUi(self)
        atexit.register(self.cleanup)
        #self.camera_handler = Handler()
        #self.camera_handler.change_pixmap_signal.connect(self.update_image)
        self.camera_ctl = CameraControl()
        self.camera_ctl.change_pixmap_signal.connect(self.update_image)

        self.ui.Btn_StartStopPreview.clicked.connect(self.prev_start_pushed)
        # self.thread.start()
        #self.load_ui()

    def __del__(self):
        del self.camera_ctl
    
    def cleanup(self):
        del self

    @Slot(np.ndarray)
    def update_image(self, cv_img):
        """ Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.ui.PreviewWidget.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(480, 360, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()

    def prev_start_pushed(self):
        self.camera_ctl.start_stop_preview()
        self.ui.Btn_StartStopPreview.setText('Stop')


if __name__ == "__main__":
    app = QApplication([])
    widget = main()
    widget.show()
    sys.exit(app.exec_())
