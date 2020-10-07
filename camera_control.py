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
from typing import Optional
import cv2
import numpy as np
#from pymba import Vimba, Frame

from PySide2 import QtGui
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import Signal, Slot, Qt, QPoint, QRect, QSize
from PySide2.QtGui import QPixmap
#from pymba.vimba_exception import VimbaException
from vimba import Vimba, Frame, Camera
from vimba.frame import FrameStatus

from resizable_rubberband import ResizableRubberBand
from baseline import Baseline
from evaluate_droplet import evaluate_droplet


# TODO 
#   ROI selection
#   droplet detection
#   setText() crash https://stackoverflow.com/questions/64211299/pyside2-qpushbutton-settext-crashes-my-application-after-halting-video-feed 
#
#
#


class CameraControl(QLabel):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.roi_origin = QPoint()
        self._first_show = True # whether form is shown for the first time
        self.is_running = False
        self.change_pixmap_signal.connect(self.update_image)
        # self.vimba = Vimba()
        # self.vimba.startup()
        # self.cam = self.vimba.camera(0)
        self.cam : Camera = None
        self.vimba: Vimba = Vimba.get_instance()
        self.init_camera()
        self.setup_camera()
        self.update()
        self.roi_rubber_band = ResizableRubberBand(self)
        self.baseline = Baseline(self)
        #self.set_image('./untitled1.png')

    def __del__(self):
        # if self.cam._is_armed:
        #     self.cam.disarm()
        # try:
        #     #self.cam.stop_frame_acquisition()
        #     self.cam.close()
        # except VimbaException as vex:
        #     print(vex)
        # self.vimba.shutdown()
        del self.cam
        del self.vimba

    @Slot()
    def stop_preview(self):
        # with self.vimba:
        #     with self.cam:
        self.cam.stop_streaming()
        self.cam.__exit__(None, None, None)
        self.vimba.__exit__(None, None, None)
        self.is_running = False
        #self.cam.stop_frame_acquisition()
        #self.cam.disarm()

    @Slot()
    def start_preview(self):
        # self.cam.arm('Continuous', self.frame_handler)
        # self.cam.start_frame_acquisition()
        # with self.vimba:
        #     with self.cam:
        self.vimba.__enter__()
        self.cam.__enter__()
        self.cam.start_streaming(handler=self.frame_handler, buffer_count=10)
        self.is_running = True

    def init_camera(self):
        with self.vimba as vimba:
            cams = vimba.get_all_cameras()
            self.cam = cams[0]

    def reset_camera(self):
        # try: 
        #     self.cam.open()
        # except VimbaException as vex:
        #     print(vex)
        #self.cam.run_feature_command('DeviceReset')
        # self.cam.close()
        with self.cam:
            self.cam.DeviceReset.run()

    def setup_camera(self):
        #self.reset_camera()
        with self.vimba:
            with self.cam:
                self.cam.ExposureTime.set(1000.0)
                self.cam.ReverseY.set(True)
        # self.cam.open()
        # self.cam.feature('ExposureTime').value = 1000.0
        # self.cam.feature('ReverseY').value = False
        # self.reset_roi()
        #self.cam.arm('Continuous', self.frame_handler)
    
    def display_snapshot(self):
        #self.cam.arm('SingleFrame')
        #frame = self.cam.acquire_frame()
        #img = frame.buffer_data_numpy()
        with self.vimba:
            with self.cam:
                frame: Frame = self.cam.get_frame()
                self.change_pixmap_signal.emit(frame.as_opencv_image())
        #self.update()
        #self.cam.disarm()

    def frame_handler(self, cam: Camera, frame: Frame) -> None:
        if frame.get_status() != FrameStatus.Incomplete:
            img = frame.as_opencv_image()
            try:
                #img = frame.buffer_data_numpy()
                has_img = True
                drplt, img = evaluate_droplet(img, self.baseline.get_y_level())
            except Exception as ex:
                print(ex)
            # #do image detection
            # #cv.ellipse(img, (x,y),(a,b),phi, 0 ,2*math.pi, 'm')
            self.change_pixmap_signal.emit(img)
            
            #self.change_frametime_signal.emit()
            print(frame.get_timestamp())
        cam.queue_frame(frame)

    def show_baseline(self):
        self.baseline.show()

    def hide_baseline(self):
        self.baseline.hide()

    def showEvent(self, event):
        if self._first_show:
            self.display_snapshot()
            self._first_show = False

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.roi_origin = QPoint(event.pos())
            self.roi_rubber_band.setGeometry(QRect(self.roi_origin, QSize()))
            self.roi_rubber_band.show()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.NoButton:
            pass
        elif event.buttons() == Qt.LeftButton:
            if not self.roi_origin.isNull():
                self.roi_rubber_band.setGeometry(QRect(self.roi_origin, event.pos()).normalized())
        elif event.buttons() == Qt.RightButton:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter:
            self.apply_roi()
        elif event.key() == Qt.Key_Escape:
            self.abort_roi()
            
    def apply_roi(self):
        x,y,w,h = self.roi_rubber_band.rect().getRect()
        self.roi_rubber_band.hide()
        self.set_roi(x,y,w,h)
        #self.cam.
        #TODO set camera

    def abort_roi(self):
        self.roi_rubber_band.hide()

    def start_roi_sel(self):
        pass

    def reset_roi(self):
        #sens_h = self.cam.feature('SensorHeight').value
        #sens_w = self.cam.feature('SensorWidth').value
        #self.set_roi(0,0, sens_w, sens_h)
        #self.set_roi(0,0, 2064, 1544)
        with self.vimba:
            with self.cam:
                h = self.cam.SensorHeight.get()
                w = self.cam.SensorWidth.get()
                self.set_roi(0, 0, w, h)

    def set_roi(self, x, y, w, h):
        # x, y, width and height need be multiple of 8
        x = int(8 * round(x/8))
        y = int(8 * round(y/8))
        w = int(8 * round(w/8))
        
        h = int(8 * round(h/8))
        if h > 1542:
            h = 1542

        # self.cam.feature('Width').value = w
        # self.cam.feature('Height').value = h
        # self.cam.feature('OffsetX').value = x
        # self.cam.feature('OffsetY').value = y 
        with self.vimba:
            with self.cam:
                self.cam.Width.set(w)
                self.cam.Height.set(h)
                self.cam.OffsetX.set(x)
                self.cam.OffsetY.set(y)
        self.display_snapshot()

    def set_image(self, file):
        img = QPixmap(file)
        self.setPixmap(img.scaled(self.size(), Qt.KeepAspectRatio))

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            qt_img = self.convert_cv_qt(cv_img)
            self.setPixmap(qt_img)
        except Exception:
            pass

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)