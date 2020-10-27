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
from camera import AbstractCamera, TestCamera, VimbaCamera
from typing import List, Tuple, Union
from threading import Thread, Event
import time
import cv2
import numpy as np
import pydevd

from PySide2 import QtGui
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import Signal, Slot, Qt, QPoint, QRect, QSize
from PySide2.QtGui import QBrush, QImage, QPaintEvent, QPainter, QPen, QPixmap, QTransform
from vimba import Vimba, Frame, Camera, LOG_CONFIG_TRACE_FILE_ONLY
from vimba.frame import FrameStatus

from resizable_rubberband import ResizableRubberBand
from baseline import Baseline
from evaluate_droplet import Droplet, evaluate_droplet


# TODO camera control
#   pause running while setting roi - needs testing
#   escape not removing rubberband

# TODO cleanup functions

# TODO try again with opengl

USE_TEST_IMAGE = True

class CameraControl(QLabel):
    #change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.ui = self.window().ui
        self.roi_origin = QPoint()
        self._double_buffer: QImage = None
        self._first_show = True # whether form is shown for the first time
        self._image_size = 0
        self._image_size_invalid = True
        self.cam: AbstractCamera = TestCamera() if USE_TEST_IMAGE else VimbaCamera()
        self._pixmap: QPixmap = QPixmap(480, 360)
        self._droplet = Droplet()
        self.cam.new_image_available.connect(self.update_image)
        self.update()
        self._roi_rubber_band = ResizableRubberBand(self)
        self._baseline = Baseline(self)
        self._oneshot_eval = False
        
        
    def __del__(self):
        # self.cam.stop_streaming()
        del self.cam

    def showEvent(self, event):
        if self._first_show:
            self.connect_signals()
            self.cam.snapshot()
            self._baseline.y_level= self.mapFromImage(y=250)
            self._first_show = False

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.cam.stop_streaming()

    def connect_signals(self):
        # Camera
        self.ui.startCamBtn.clicked.connect(self.prev_start_pushed)
        self.ui.setROIBtn.clicked.connect(self.apply_roi)
        self.ui.resetROIBtn.clicked.connect(self.cam.reset_roi)
   
    @Slot()
    def prev_start_pushed(self, event):
        if self.ui.startCamBtn.text() != 'Stop':
            self.cam.start_streaming()
            self.ui.startCamBtn.setText('Stop')
        else:
            self.cam.stop_streaming()
            self.ui.startCamBtn.setText('Start')
            self.cam.snapshot()

    def show_baseline(self):
        self._baseline.show()

    def hide_baseline(self):
        self._baseline.hide()

    def get_baseline_y(self) -> int:
        y_base = self._baseline.y_level
        y = self.mapToImage(y=y_base)
        return y

    def set_new_baseline_constraints(self):
        pix_size = self._pixmap.size()
        offset_y = int(round(abs(pix_size.height() - self.height())/2))
        self._baseline.max_level = pix_size.height() + offset_y
        self._baseline.min_level = offset_y

    def paintEvent(self, event: QPaintEvent):
        # completely override super.paintEvent() to use double buffering
        painter = QPainter(self)
        self.drawFrame(painter)
        if self._double_buffer is None:
            self._double_buffer = QImage(self.width(), self.height(), QImage.Format_RGB888)
        self._double_buffer.fill(Qt.black)
        # calculate offset and scale of droplet image pixmap
        scale_x, scale_y, offset_x, offset_y = self.get_from_image_transform()
        
        db_painter = QPainter(self._double_buffer)
        db_painter.setRenderHints(QPainter.Antialiasing | QPainter.NonCosmeticDefaultPen)
        db_painter.setBackground(QBrush(Qt.black))
        db_painter.setPen(QPen(Qt.black,0))
        db_painter.drawPixmap(offset_x, offset_y, self._pixmap)
        db_painter.setPen(QPen(Qt.magenta,2))
        if self.cam.is_running:
            fps_text = 'FPS: ' + str(self.cam.get_framerate())
            db_painter.drawText(2, 10, fps_text)
        # draw droplet outline and tangent only if evaluate_droplet was successful
        if self._droplet.is_valid:
            try:
                # transforming true image coordinates to scaled pixmap coordinates
                transform = QTransform()
                transform.translate(offset_x, offset_y)
                transform.scale(scale_x, scale_y)              
                db_painter.setTransform(transform)
                db_painter.drawLine(*self._droplet.line_l)
                db_painter.drawLine(*self._droplet.line_r)
                db_painter.drawLine(*self._droplet.int_l, *self._droplet.int_r)  
                # draw ellipse around origin, then move and rotate    
                transform.translate(*self._droplet.center)
                transform.rotate(self._droplet.tilt_deg)
                db_painter.setTransform(transform)
                db_painter.drawEllipse(QPoint(0,0), self._droplet.maj/2, self._droplet.min/2)   
            except Exception as ex:
                print(ex)
        db_painter.end()
        # painting the buffer pixmap to screen
        painter.drawImage(0, 0, self._double_buffer)
        painter.end()

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton:
            self.roi_origin = QPoint(event.pos())
            self._roi_rubber_band.setGeometry(QRect(self.roi_origin, QSize()))
            self._roi_rubber_band.show()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.NoButton:
            pass
        elif event.buttons() == Qt.LeftButton:
            if not self.roi_origin.isNull():
                self._roi_rubber_band.setGeometry(QRect(self.roi_origin, event.pos()).normalized())
        elif event.buttons() == Qt.RightButton:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter:
            self.apply_roi()
        elif event.key() == Qt.Key_Escape:
            self._abort_roi()
            
    def apply_roi(self):
        x,y = self._roi_rubber_band.mapToParent(QPoint(0,0)).toTuple()
        w,h = self._roi_rubber_band.size().toTuple()
        self._roi_rubber_band.hide()
        x,y = self.mapToImage(x=x, y=y)
        w,h = self.mapToImage(x=w, y=h)
        self.set_roi(x,y,w,h)

    def _abort_roi(self):
        self._roi_rubber_band.hide()

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            qt_img = self._convert_cv_qt(cv_img)
            self._pixmap = qt_img
            if self._image_size_invalid:
                self._image_size = np.shape(cv_img)
                self.set_new_baseline_constraints()
                self._image_size_invalid = False
            self._droplet = Droplet()
            # evaluate droplet only if camera is running or if a oneshot eval is requested
            if self.cam.is_running or self._oneshot_eval:
                try:
                    drplt = evaluate_droplet(cv_img, self.get_baseline_y())
                    self._droplet = drplt
                except Exception as ex:
                    print(ex.with_traceback(None))
                    pass
                if self._oneshot_eval: 
                    self._oneshot_eval = False
            self.update()
        except Exception:
            pass

    def _convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(p)

    def map_droplet_drawing_vals(self, droplet: Droplet):
        tangent_l = tuple(map(lambda x: self.mapFromImage(*x), droplet.line_l))
        tangent_r = tuple(map(lambda x: self.mapFromImage(*x), droplet.line_r))
        center = self.mapFromImage(*droplet.center)
        maj, min = self.mapFromImage(droplet.maj, droplet.min)
        int_l = self.mapFromImage(*droplet.int_l)
        int_r = self.mapFromImage(*droplet.int_r)
        return tangent_l,tangent_r,int_l,int_r,center,maj,min

    def mapToImage(self, x=None, y=None) -> Union[Tuple[int,int],int]:
        """ Convert QLabel coordinates to image pixel coordinates
        :param x: x coordinate to be transformed
        :param y: y coordinate to be transformed
        :returns: x or y or Tuple (x,y) of the transformed coordinates, depending on what parameters where given
        """
        pix_rect = self._pixmap.size()
        res: List[int] = []
        if x is not None:
            scale_x = self._image_size[1] / pix_rect.width()
            tr_x = int(round(x - (abs(pix_rect.width() - self.width())/2) * scale_x))
            res.append(tr_x)
        if y is not None:
            scale_y = self._image_size[0] / pix_rect.height() 
            tr_y = int(round((y - (abs(pix_rect.height() - self.height())/2)) * scale_y))
            res.append(tr_y)
        return tuple(res) if len(res)>1 else res[0]

    def mapFromImage(self, x=None, y=None) -> Union[Tuple[int,int],int]:
        """ Convert Image pixel coordinates to QLabel coordinates
        :param x: x coordinate to be transformed
        :param y: y coordinate to be transformed
        :returns: x or y or Tuple (x,y) of the transformed coordinates, depending on what parameters where given
        """
        scale_x, scale_y, offset_x, offset_y = self.get_from_image_transform()
        res: List[int] = []
        if x is not None:
            tr_x = int(round((x  * scale_x) + offset_x))
            res.append(tr_x)
        if y is not None:
            tr_y = int(round((y * scale_y) + offset_y))
            res.append(tr_y)
        return tuple(res) if len(res)>1 else res[0]

    def get_from_image_transform(self):
        """ Gets the scale and offset for a Image to QLabel coordinate transform """
        pix_rect = self._pixmap.size()
        scale_x = float(pix_rect.width() / self._image_size[1])
        offset_x = abs(pix_rect.width() - self.width())/2
        scale_y = float(pix_rect.height() / self._image_size[0])
        offset_y = abs(pix_rect.height() - self.height())/2
        return scale_x, scale_y, offset_x, offset_y
        
        