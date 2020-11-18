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

from threading import Thread, Event
import cv2
import pydevd
from PySide2.QtCore import QObject, QTimer, Signal, Slot
import numpy as np

try:
    from vimba import Vimba, Frame, Camera, LOG_CONFIG_TRACE_FILE_ONLY
    from vimba.frame import FrameStatus
    HAS_VIMBA = True
except Exception:
    HAS_VIMBA = False

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from vimba import Vimba, Frame, Camera, LOG_CONFIG_TRACE_FILE_ONLY
    from vimba.frame import FrameStatus

class FrameRateCounter:
    """ Framerate counter with rolling average filter """
    def __init__(self, length=5):
        # lenght of filter
        self.length = length
        self.buffer = [50.0]*length
        self.counter = 0
        self.last_timestamp = 0

    def _rotate(self):
        # increase current index by 1 or loop back to 0
        if self.counter == (self.length - 1):
            self.counter = 0
        else:
            self.counter += 1

    def _put(self, value):
        # add value to current line then rotate index
        self.buffer[self.counter] = value
        self._rotate()

    @staticmethod
    def _calc_frametime(timestamp_new, timestamp_old):
        # Calculate frametime from camera timestamps (in ns)
        return (timestamp_new - timestamp_old)*1e-9

    @property
    def average_fps(self) -> float:
        """ Return the averaged fps """
        return sum(self.buffer) / self.length

    def add_new_timesstamp(self, timestamp):
        """ Add new poi to buffer
        Framtime is calculated from timestamp then added to buffer.
        """
        self._put(1 / self._calc_frametime(timestamp, self.last_timestamp))
        self.last_timestamp = timestamp


class AbstractCamera(QObject):
    """ Interface class for implementing camera objects for MAEsure """
    # signal to emit when a new image is available
    new_image_available = Signal(np.ndarray)
    def __init__(self):
        super(AbstractCamera, self).__init__()
        self._is_running = False
        self._image_size_invalid = True

    @property
    def is_running(self):
        return self._is_running

    def snapshot(self):
        """ record a single image and emit signal """
        raise NotImplementedError

    def start_streaming(self):
        """ start streaming """
        raise NotImplementedError

    def stop_streaming(self):
        raise NotImplementedError

    def set_roi(self, x, y, w, h):
        """ set the region of interest on the cam
        :param x,y: x,y of ROI in image coordinates
        :param w,h: width and height of ROI
        """
        raise NotImplementedError

    def reset_roi(self):
        """ Reset ROI to full size """
        raise NotImplementedError

    def get_framerate(self):
        """ return current FPS of camera"""
        pass #raise NotImplementedError

if HAS_VIMBA:
    class VimbaCamera(AbstractCamera):
        def __init__(self):
            super(VimbaCamera, self).__init__()
            self._stream_killswitch: Event = None
            self._frame_producer_thread: Thread = None
            self._cam : Camera = None
            self._cam_id: str = ''
            self._vimba: Vimba = Vimba.get_instance()
            self._frc = FrameRateCounter(10)
            #self._vimba.enable_log(LOG_CONFIG_TRACE_FILE_ONLY)
            self._init_camera()
            self._setup_camera()

        def __del__(self):
            self.stop_streaming()
            del self._cam
            del self._vimba

        def snapshot(self):
            if self._is_running: return
            with self._vimba:
                with self._cam:
                    frame: Frame = self._cam.get_frame()
                    self.new_image_available.emit(frame.as_opencv_image())

        def stop_streaming(self):
            if self._is_running:
                self._stream_killswitch.set() # set the event the producer is waiting on
                self._frame_producer_thread.join() # wait for the thread to actually be done
                self._is_running = False

        def start_streaming(self):
            self._is_running = True
            self._stream_killswitch = Event() # the event that will be used to stop the streaming
            self._frame_producer_thread = Thread(target=self._frame_producer) # create the thread object to run the frame producer
            self._frame_producer_thread.start() # actually start the thread to execute the method given as target

        def reset_roi(self):
            #self.set_roi(0,0, 2064, 1544)
            was_running = self._is_running
            self.stop_streaming()
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
            self.snapshot()
            if was_running: self.start_streaming()

        def set_roi(self, x, y, w, h):
            # x, y, width and height need be multiple of 8
            x = int(8 * round(x/8))
            y = int(8 * round(y/8))
            w = int(8 * round(w/8))
            h = int(8 * round(h/8))
            if h > 1542:
                h = 1542
            was_running = self._is_running
            self.stop_streaming()
            with self._vimba:
                with self._cam:
                    self._cam.Width.set(w)
                    self._cam.Height.set(h)
                    self._cam.OffsetX.set(x)
                    self._cam.OffsetY.set(y)
            self._image_size_invalid = True
            self.snapshot()
            if was_running: self.start_streaming()

        def _frame_producer(self):
            with self._vimba:
                with self._cam:
                    try:
                        self._cam.start_streaming(handler=self._frame_handler, buffer_count=10)
                        self._stream_killswitch.wait()
                    finally:
                        self._cam.stop_streaming()

        def _frame_handler(self, cam: Camera, frame: Frame) -> None:
            #pydevd.settrace(suspend=False)
            self._frc.add_new_timesstamp(frame.get_timestamp())
            if frame.get_status() != FrameStatus.Incomplete:
                img = frame.as_opencv_image()
                self.new_image_available.emit(img)
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

        def get_framerate(self):
            with self._vimba:
                with self._cam:
                    #return round(self._cam.AcquisitionFrameRate.get(),1)
                    return round(self._frc.average_fps,1)

class TestCamera(AbstractCamera):
    def __init__(self):
        super(TestCamera, self).__init__()
        self._timer = QTimer()
        self._timer.setInterval(16)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._timer_callback)
        self._test_image:np.ndarray = cv2.imread('untitled1.png', cv2.IMREAD_GRAYSCALE)
        self._test_image = np.reshape(self._test_image, self._test_image.shape + (1,) )

    def snapshot(self):
        if not self._is_running:
            self.new_image_available.emit(self._test_image.copy())

    def start_streaming(self):
        self._is_running = True
        self._timer.start()

    def stop_streaming(self):
        self._timer.stop()
        self._is_running = False

    def set_roi(self,x,y,w,h):
        pass

    def reset_roi(self):
        pass

    def get_framerate(self):
        return 1000 / self._timer.interval()

    @Slot()
    def _timer_callback(self):
        self.new_image_available.emit(self._test_image.copy())