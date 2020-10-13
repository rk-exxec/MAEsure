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
from threading import Thread, Event
import time
import cv2
import numpy as np

from PySide2 import QtGui
from PySide2.QtWidgets import QLabel
from PySide2.QtCore import Signal, Slot, Qt, QPoint, QRect, QSize
from PySide2.QtGui import QPixmap
from vimba import Vimba, Frame, Camera, LOG_CONFIG_TRACE_FILE_ONLY
from vimba.frame import FrameStatus

from resizable_rubberband import ResizableRubberBand
from baseline import Baseline
from evaluate_droplet import evaluate_droplet


# TODO camera control
#   droplet detection
#   pause running while setting roi
#   
#


class CameraControl(QLabel):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self.roi_origin = QPoint()
        self._frame_producer_thread: Thread = None
        self._stream_killswitch: Event = None
        self._first_show = True # whether form is shown for the first time
        self._is_running = False
        self._original_image_size = 0
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
        #self.set_image('./untitled1.png')

    def __del__(self):
        self._stream_killswitch.set()
        self._frame_producer_thread.join()
        del self._cam
        del self._vimba

    def closeEvent(self, event: QtGui.QCloseEvent):
        self._stream_killswitch.set()
        self._frame_producer_thread.join()

    @Slot()
    def stop_preview(self):
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
        if frame.get_status() != FrameStatus.Incomplete:
            img = frame.as_opencv_image()
            try:
                drplt, img = evaluate_droplet(img, self.get_baseline_y())
            except Exception as ex:
                #print(ex)
                pass
            self.change_pixmap_signal.emit(img)        
            #self.change_frametime_signal.emit()
            #print(frame.get_timestamp())
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
        with self._vimba:
            with self._cam:
                frame: Frame = self._cam.get_frame()
                self.change_pixmap_signal.emit(frame.as_opencv_image())

    def show_baseline(self):
        self._baseline.show()

    def hide_baseline(self):
        self._baseline.hide()

    def get_baseline_y(self) -> int:
        y_base = self._baseline.get_y_level()
        y = self._convert_to_image_coordinates(y=y_base)
        return y

    def showEvent(self, event):
        if self._first_show:
            self.display_snapshot()
            self._first_show = False

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
        x,y = self._convert_to_image_coordinates(x=x, y=y)
        w,h = self._convert_to_image_coordinates(x=w, y=h)
        self.set_roi(x,y,w,h)

    def _abort_roi(self):
        self._roi_rubber_band.hide()

    def _start_roi_sel(self):
        pass

    def reset_roi(self):
        #self.set_roi(0,0, 2064, 1544)
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
                        
        self.display_snapshot()

    def set_roi(self, x, y, w, h):
        # x, y, width and height need be multiple of 8
        x = int(8 * round(x/8))
        y = int(8 * round(y/8))
        w = int(8 * round(w/8))
        h = int(8 * round(h/8))
        if h > 1542:
            h = 1542
        with self._vimba:
            with self._cam:
                self._cam.Width.set(w)
                self._cam.Height.set(h)
                self._cam.OffsetX.set(x)
                self._cam.OffsetY.set(y)
        self.display_snapshot()

    def _set_image(self, file):
        img = QPixmap(file)
        self.setPixmap(img.scaled(self.size(), Qt.KeepAspectRatio))

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            self._original_image_size = np.shape(cv_img)
            qt_img = self._convert_cv_qt(cv_img)
            self.setPixmap(qt_img)
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

    def _convert_to_image_coordinates(self, x=-1, y=-1):
        """ Convert QLabel coordinates to image pixel coordinates
        :param x: x coordinate to be transformed
        :param y: y coordinate to be transformed
        :returns: x or y or Tuple (x,y) of the transformed coordinates, depending on what parameters where given
        """
        pix_rect = self.pixmap().rect()
        scale_x = self._original_image_size[1] / self.width()
        scale_y = self._original_image_size[0] / self.height()
        tr_x = int((x - pix_rect.x()) * scale_x)
        tr_y = int((y - pix_rect.y()) * scale_y)
        if x >= 0 and y >= 0:
            return tr_x, tr_y
        elif x >= 0:
            return tr_x
        elif y >= 0:
            return tr_y
            
        
        