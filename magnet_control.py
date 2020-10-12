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

from PySide2.QtCore import Signal, Slot, Qt

from serial.tools import list_ports
from lt_control.lt_control import LT

# TODO
# calib
# lamp shows reference status

class MagnetControl:
    def __init__(self, parent=None) -> None:
        #self.portsComboBox: QComboBox = None
        self._lt_ctl = LT(self.find_com_port())
        self._shown = False
        self._mov_dist: float = 0
        self._mov_unit: str = 'steps'


    def __del__(self):
        self._lt_ctl.close()
        del self._lt_ctl

    def find_com_port(self) -> str:
        lst = list_ports.comports()
        for port in lst:
            if port.manufacturer == 'Nanotec':
                return port.device

    def showEvent(self, event):
        if not self._shown:
            self.post_init()
            self._shown = True

    @Slot()
    def jog_up_start(self):
        self._lt_ctl.move_inf_start(0)

    @Slot()
    def jog_down_start(self):
        self._lt_ctl.move_inf_start(1)
        
    def set_mov_dist(self, value: float):
        try:
            self._mov_dist = value   
        except Exception as ex:
            print(ex)

    def set_mov_unit(self, text: str):
        try:
            self._mov_unit = text.strip()
        except Exception as ex:
            print(ex) 
        
    @Slot()
    def move_pos(self):
        # FIXME movement not correct!
        if self._mov_unit == 'mm':
            self._lt_ctl.move_absolute_mm(self._mov_dist)
        elif self._mov_unit == 'steps':
            self._lt_ctl.move_absolute(int(self._mov_dist))
        elif self._mov_unit == 'mT':
            print('Not implemented!')

    @Slot()
    def motor_stop(self):
        self._lt_ctl.stop()

    @Slot()
    def reference(self):
        self._lt_ctl.do_referencing()

    def populate_int_selector(self):
        pass

    @Slot()
    def connect(self):
        pass

