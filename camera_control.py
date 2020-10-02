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
from pymba import Vimba, Frame

from PySide2 import QtGui
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import Signal, Slot, Qt, QPoint, QRect, QSize
from PySide2.QtGui import QPixmap

from resizable_rubberband import ResizableRubberBand
from baseline import Baseline
from evaluate_droplet import evaluate_droplet


# TODO 
#   ROI selection
#   droplet detection
#   
#
#
#


class CameraControl(QLabel):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.roi_origin = QPoint()
        self.is_running = False
        self.vimba = Vimba()
        self.vimba.startup()
        self.cam = self.vimba.camera(0)
        try:
            self.cam.close()
        except:
            pass
        self.cam.open()
        self.roi_rubber_band = ResizableRubberBand(self)
        self.baseline = Baseline(self)
        self.change_pixmap_signal.connect(self.update_image)
        self.setup_camera()
        self.display_snaphot()
        #self.set_image('./untitled1.png')

    def __del__(self):
        try:
            self.cam.stop_frame_acquisition()
            self.cam.disarm()
            self.cam.close()
        except:
            pass
        del self.vimba

    def stop_preview(self):
        self.is_running = False
        self.cam.stop_frame_acquisition()
        self.cam.disarm()

    def start_preview(self):
        self.cam.arm('Continuous', self.frame_handler)
        self.cam.start_frame_acquisition()
        self.is_running = True

    def setup_camera(self):
        self.cam.feature('ExposureTime').value = 1000.0
        self.cam.feature('ExposureTime').value = 1000.0
        self.cam.feature('ReverseY').value = 'False'
        #self.set_roi(800, 530, 301, 280)
        #self.cam.arm('Continuous', self.frame_handler)
    
    def display_snaphot(self):
        self.cam.arm('SingleFrame')
        frame = self.cam.acquire_frame()
        img = frame.buffer_data_numpy()
        self.change_pixmap_signal.emit(img)
        self.update()
        self.cam.disarm()

    def frame_handler(self, frame: Frame, delay: Optional[int] = 1) -> None:
        img = frame.buffer_data_numpy()
        try:
            drplt, img = evaluate_droplet(img, self.baseline.get_y_level())
        except Exception as ex:
            print(ex)
        # do image detection
        # cv.ellipse(img, (x,y),(a,b),phi, 0 ,2*math.pi, 'm')
        self.change_pixmap_signal.emit(img)

    def show_baseline(self):
        self.baseline.show()

    def hide_baseline(self):
        self.baseline.hide()

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
        self.set_roi(0,0, 2064, 1542)

    def set_roi(self, x, y, w, h):
        self.cam.feature('OffsetX').value = x
        self.cam.feature('OffsetY').value = y
        # width and height need be multiple of 8
        w = 8 * round(w/8)
        h = 8 * round(h/8)
        self.cam.feature('Width').value = w
        self.cam.feature('Height').value = h

    def set_image(self, file):
        img = QPixmap(file)
        self.setPixmap(img.scaled(self.size(), Qt.KeepAspectRatio))

    @Slot(np.ndarray)
    def update_image(self, cv_img):
        """ Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(cv_img)
        self.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)