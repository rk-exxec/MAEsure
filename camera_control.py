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
from typing import List, Tuple, Union
from VimbaPython.vimba.shared import filter_affected_features
from threading import Thread, Event
import time
import cv2
import numpy as np
import pydevd

from PySide2 import QtGui
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import Signal, Slot, Qt, QPoint, QRect, QSize
from PySide2.QtGui import QBrush, QPaintEvent, QPainter, QPen, QPixmap, QTransform
from vimba import Vimba, Frame, Camera, LOG_CONFIG_TRACE_FILE_ONLY
from vimba.frame import FrameStatus

from resizable_rubberband import ResizableRubberBand
from baseline import Baseline
from evaluate_droplet import Droplet, evaluate_droplet


# TODO camera control
#   pause running while setting roi - needs testing
#   escape not removing rubberband

# TODO cleanup functions


class CameraControl(QLabel):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.roi_origin = QPoint()
        self._stream_killswitch: Event = None
        self._frame_producer_thread: Thread = None
        self._double_buffer: QPixmap = None
        self._first_show = True # whether form is shown for the first time
        self._is_running = False
        self._image_size = 0
        self._image_size_invalid = True
        self._droplet = Droplet()
        self.change_pixmap_signal.connect(self.update_image)
        self._cam : Camera = None
        self._cam_id: str = ''
        self._vimba: Vimba = Vimba.get_instance()
        #self._vimba.enable_log(LOG_CONFIG_TRACE_FILE_ONLY)
        self._init_camera()
        self._setup_camera()
        self.update()
        self._roi_rubber_band = ResizableRubberBand(self)
        self._baseline = Baseline(self)
        self._use_test_image = True
        self._test_image: np.ndarray = None
        

    def __del__(self):
        self.stop_preview()
        del self._cam
        del self._vimba

    def closeEvent(self, event: QtGui.QCloseEvent):
        self.stop_preview()

    def showEvent(self, event):
        if self._first_show:
            if self._use_test_image:
                self._set_image('./untitled1.png')
            else:
                self.display_snapshot()
            self._baseline.y_level= self.mapFromImage(y=250)
            self._first_show = False

    @Slot()
    def stop_preview(self):
        if self._is_running:
            self._stream_killswitch.set() # set the event the producer is waiting on
            self._frame_producer_thread.join() # wait for the thread to actually be done
            self._is_running = False

    @Slot()
    def start_preview(self):
        self._stream_killswitch = Event() # the event that will be used to stop the streaming
        self._frame_producer_thread = Thread(target=self._frame_producer) # create the thread object to run the frame producer
        self._frame_producer_thread.start() # actually start the thread to execute the method given as target
        self.is_running = True

    def _frame_producer(self):
        with self._vimba:
            with self._cam:
                try:
                    self._cam.start_streaming(handler=self._frame_handler, buffer_count=10)
                    self._stream_killswitch.wait()
                finally:
                    self._cam.stop_streaming()

    def _frame_handler(self, cam: Camera, frame: Frame) -> None:
        pydevd.settrace(suspend=False)
        if frame.get_status() != FrameStatus.Incomplete:
            img = frame.as_opencv_image() if not self._use_test_image else np.copy(self._test_image)
            self._droplet = Droplet()
            try:
                drplt = evaluate_droplet(img, self.get_baseline_y())
                self._droplet = drplt
            except Exception as ex:
                print(ex.with_traceback(None))
            self.change_pixmap_signal.emit(img)        
        cam.queue_frame(frame)

    def _init_camera(self):
        with self._vimba:
            cams = self._vimba.get_all_cameras()
            self._cam = cams[0]
            with self._cam:
                self._cam.AcquisitionStatusSelector.set('AcquisitionActive')
                if self._cam.AcquisitionStatus.get():
                    self._cam.AcquisitionStop.run()
                    # fetch broken frame
                    self._cam.get_frame()

    def _reset_camera(self):
        with self._cam:
            self._cam.DeviceReset.run()

    def _setup_camera(self):
        #self.reset_camera()
        with self._vimba:
            with self._cam:
                self._cam.ExposureTime.set(1000.0)
                self._cam.ReverseY.set(True)
    
    def display_snapshot(self):
        if self._is_running: return
        with self._vimba:
            with self._cam:
                frame: Frame = self._cam.get_frame()
                self.change_pixmap_signal.emit(frame.as_opencv_image())

    def show_baseline(self):
        self._baseline.show()

    def hide_baseline(self):
        self._baseline.hide()

    def get_baseline_y(self) -> int:
        y_base = self._baseline.y_level
        y = self.mapToImage(y=y_base)
        return y

    def set_new_baseline_constraints(self):
        pix_size = self.pixmap().size()
        offset_y = int(abs(pix_size.height() - self.height())/2)
        self._baseline.max_level = pix_size.height() + offset_y
        self._baseline.min_level = offset_y

    def paintEvent(self, event: QPaintEvent):
        # FIXME white border around pixmap!!
        # completely override super.paintEvent() to use double buffering
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.Antialiasing)
        self.drawFrame(painter)
        # using a pixmap and separate painter for content do avoid flicker
        if self._double_buffer is None:
            self._double_buffer = QPixmap(self.width(), self.height())
        self._double_buffer.fill(Qt.black)
        db_painter = QPainter(self._double_buffer)
        db_painter.setRenderHint(QPainter.Antialiasing)
        # calculate offset and scale of droplet image pixmap
        scale_x, scale_y, offset_x, offset_y = self.get_from_image_transform()
        db_painter.setBackground(QBrush(Qt.black))
        db_painter.setPen(QPen(Qt.black,0))
        db_painter.drawPixmap(offset_x, offset_y, self.pixmap())
        # draw drolet outline and tangent only if evaluate_droplet was successful
        if self._droplet.is_valid:
            try:           
                db_painter.setPen(QPen(Qt.magenta,2))
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

        # painting the buffer pixmap to screen
        painter.drawPixmap(0, 0, self._double_buffer)
        db_painter.end()
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

    def reset_roi(self):
        #self.set_roi(0,0, 2064, 1544)
        was_running = self._is_running
        self.stop_preview()
        with self._vimba:
            with self._cam:
                h = self._cam.SensorHeight.get()
                w = self._cam.SensorWidth.get()
                w = int(8 * round(w/8))
                h = int(8 * round(h/8))
                if h > 1542:
                    h = 1542
                with self._vimba:
                    with self._cam:
                        self._cam.OffsetX.set(0)
                        self._cam.OffsetY.set(0)
                        self._cam.Width.set(w)
                        self._cam.Height.set(h)
        self._image_size_invalid = True           
        self.display_snapshot()
        if was_running: self.start_preview()
        

    def set_roi(self, x, y, w, h):
        # x, y, width and height need be multiple of 8
        x = int(8 * round(x/8))
        y = int(8 * round(y/8))
        w = int(8 * round(w/8))
        h = int(8 * round(h/8))
        if h > 1542:
            h = 1542
        was_running = self._is_running
        self.stop_preview()
        with self._vimba:
            with self._cam:
                self._cam.Width.set(w)
                self._cam.Height.set(h)
                self._cam.OffsetX.set(x)
                self._cam.OffsetY.set(y)
        self._image_size_invalid = True
        self.display_snapshot()
        if was_running: self.start_preview()

    def _set_image(self, file):
        img = cv2.imread(file)
        if self._use_test_image:
            self._test_image = img
        self.change_pixmap_signal.emit(img)

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            qt_img = self._convert_cv_qt(cv_img)
            self.setPixmap(qt_img)
            if self._image_size_invalid:
                self._image_size = np.shape(cv_img)
                self.set_new_baseline_constraints()
                self._image_size_invalid = False
        except Exception:
            pass

    def _convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size(), Qt.KeepAspectRatio)
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
        pix_rect = self.pixmap().size()
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
        pix_rect = self.pixmap().size()
        scale_x = float(pix_rect.width() / self._image_size[1])
        offset_x = abs(pix_rect.width() - self.width())/2
        scale_y = float(pix_rect.height() / self._image_size[0])
        offset_y = abs(pix_rect.height() - self.height())/2
        return scale_x, scale_y, offset_x, offset_y
        
        