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

from math import degrees
from PySide2.QtCore import QSettings
import logging

from typing import Tuple

from numpy.lib.function_base import angle

class Singleton(object):
    """ singleton base class """
    _instance = None
    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
        return class_._instance

# TODO make length always be a fixed fraction of a second and change with framerate

# TODO comments

class Droplet(Singleton):
    """
    provides a singleton storage structure for droplet information and conversion functions  

    saves droplet scale with QSettings

    Has the following attributes:

    - **is_valid**: whether contained data is valid
    - **_angle_l**, **_angle_r**: the unfiltered left and right tangent angles
    - **_angle_l_avg**, **_angle_r_avg**: the rolling averager filter object for the angles
    - **center**: center point of fitted ellipse (x,y)
    - **maj**: length of major ellipse axis
    - **min**: lenght of minor ellipse axis
    - **phi**: tilt of ellipse in rad
    - **tilt_deg**: tilt of ellipse in deg
    - **foc_pt1**, foc_pt2**: focal points of ellipse (x,y)
    - **tan_l_m**, **tan_r_m**: slope of left and right tangent
    - **int_l**, **int_r**: left and right intersections of ellipse with baseline
    - **line_l**, **line_r**: left and right tangent as 4-Tuple (x1,y1,x2,y2)
    - **base_diam**: diameter of the contact surface of droplet
    - **_area**: unfiltered area of droplet silouette
    - **_area_avg**: rolling average filter for area
    - **_height**: unfiltered droplet height in px
    - **_height_avg**: rolling average filter for height
    - **scale_px_to_mm**: scale to convert between px and mm, is loaded from storage on startup
    """
    def __init__(self):
        settings                                    = QSettings()
        self.is_valid       : bool                  = False
        self._angle_l       : float                 = 0.0
        self._angle_l_avg                           = RollingAverager()
        self._angle_r       : float                 = 0.0
        self._angle_r_avg                           = RollingAverager()
        self.center         : Tuple[int,int]        = (0,0)
        self.maj            : int                   = 0
        self.min            : int                   = 0
        self.phi            : float                 = 0.0
        self.tilt_deg       : float                 = 0.0
        self.foc_pt1        : Tuple[int,int]        = (0,0)
        self.foc_pt2        : Tuple[int,int]        = (0,0)
        self.tan_l_m        : int                   = 0
        self.int_l          : Tuple[int,int]        = (0,0)
        self.line_l         : Tuple[int,int,int,int] = (0,0,0,0)
        self.tan_r_m        : int                   = 0
        self.int_r          : Tuple[int,int]        = (0,0)
        self.line_r         : Tuple[int,int,int,int] = (0,0,0,0)
        self.base_diam      : int                   = 0
        self._area          : float                 = 0.0
        self._area_avg                              = RollingAverager()
        self._height        : float                 = 0.0
        self._height_avg                            = RollingAverager()
        self.scale_px_to_mm : float                 = float(settings.value("droplet/scale_px_to_mm", 0.0)) # try to load from persistent storage

    def __str__(self) -> str:
        if self.is_valid:
            # if scalefactor is present, display in metric, else in pixles
            if self.scale_px_to_mm is None or self.scale_px_to_mm <= 0:
                return 'Angle Left:\n{:.2f}°\nAngle Right:\n{:.2f}°\nSurface Diam:\n{:.2f} px\nArea:\n{:.2f} px2\nHeight:\n{:.2f} px'.format(
                    round(degrees(self.angle_l),2), round(degrees(self.angle_r),2), round(self.base_diam), round(self.area,2), round(self.height,2)
                )
            else:
                return 'Angle Left:\n{:.2f}°\nAngle Right:\n{:.2f}°\nSurface Diam:\n{:.2f} mm\nArea:\n{:.2f} mm2\nHeight:\n{:.2f} mm'.format(
                    round(degrees(self.angle_l),2), round(degrees(self.angle_r),2), round(self.base_diam_mm,2), round(self.area_mm,2), round(self.height_mm,2)
                )
        else:
            return 'No droplet!'

    # properties section, get returns the average, set feeds the rolling averager
    @property
    def angle_l(self):
        """ average of left tangent angle """
        return self._angle_l_avg.average

    @angle_l.setter
    def angle_l(self, value):
        self._angle_l_avg._put(value)
        self._angle_l = value

    @property
    def angle_r(self):
        """ average of right tangent angle """
        return self._angle_r_avg.average

    @angle_r.setter
    def angle_r(self, value):
        self._angle_r_avg._put(value)
        self._angle_r = value

    @property
    def height(self):
        """ height of droplet in px """
        return self._height_avg.average

    @height.setter
    def height(self, value):
        self._height_avg._put(value)
        self._height = value

    @property
    def area(self):
        """ approx area of droplet silouette in px^2 """
        return self._area_avg.average

    @area.setter
    def area(self, value):
        self._area_avg._put(value)
        self._area = value

    # return values after converting to metric
    @property
    def height_mm(self):
        """ droplet height in mm 
        
        .. seealso:: :meth:`set_scale` 
        """
        return self._height_avg.average * self.scale_px_to_mm

    @property
    def base_diam_mm(self):
        """ droplet contact surface width in mm

        .. seealso:: :meth:`set_scale` 
        """
        return self.base_diam * self.scale_px_to_mm

    @property
    def area_mm(self):
        return self._area_avg.average * self.scale_px_to_mm**2

    def set_scale(self, scale):
        """ set and store a scalefactor to calculate mm from pixels

        :param scale: the scalefactor to calculate mm from px
        
        .. seealso:: :meth:`camera_control.CameraControl.calib_size` 
        """
        logging.info(f"droplet: set scale to {scale}")
        self.scale_px_to_mm = scale
        # save in persistent storage
        settings = QSettings()
        settings.setValue("droplet/scale_px_to_mm", scale)

    def set_filter_length(self, value):
        """ adjust the filter length for the rolling average
        
        :param value: new filter length
        """
        self._angle_l_avg.set_length(value)
        self._angle_r_avg.set_length(value)
        self._height_avg.set_length(value)
        self._area_avg.set_length(value)



class RollingAverager:
    """ 
    rolling average filter of variable length
    
    :param length: length of the filter
    """
    def __init__(self, length=300):
        # lenght of filter
        self.length = length
        self.buffer = [0.0]*length
        self.counter = 0
        self.first_number = True

    def _rotate(self):
        """
        shift  internal index to next position
        """
        # increase current index by 1 or loop back to 0
        if self.counter == (self.length - 1):
            self.counter = 0
        else:
            self.counter += 1

    def _put(self, value):
        """ set value at current index

        :param float value: the new value to set
        """ 
        if self.first_number:
            # initialize buffer with first value
            self.buffer = [value]*self.length
            self.first_number = False
        else:
            # add value to current line then rotate index
            self.buffer[self.counter] = value
        self._rotate()

    @property
    def average(self) -> float:
        """ Return the averaged value """
        return sum(self.buffer) / self.length

    def set_length(self, value):
        """
        set the length of the filter, if new length is smaller the already exisitng values are cut off, if it is longer the current average is used to fille the ne spots

        :param int value: the new filter length
        """
        if value > self.length:
            # append delta len to exisiting buffer, fill w/ current average
            self.buffer = self.buffer + [self.average]*(value - self.length)
        else:
            # keep last numbers
            self.buffer = self.buffer[-value:]
            # roll counter over if too large
            if self.counter > (value -1 ): self.counter = 0
        self.length = value
        logging.info(f"set filter length to {value}")
