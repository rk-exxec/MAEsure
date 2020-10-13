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
from PySide2.QtWidgets import QMessageBox, QPushButton

from lt_control.lt_control import LT

# TODO magnet control
# calib
# lamp shows reference status
# vllt doch als custom widget, problem war ja falsche form.ui datei

class MagnetControl:
    def __init__(self, parent=None) -> None:
        #self.portsComboBox: QComboBox = None
        self._lt_ctl = LT()
        self.parent = parent
        self._shown = False
        self._mov_dist: float = 0
        self._mov_unit: str = 'steps'
        self._invalid = False

    def __del__(self):
        #self._lt_ctl.close()
        del self._lt_ctl

    def do_timeout_dialog(self) -> bool:
        msgBox = QMessageBox()
        msgBox.setText("The connection timed out")
        msgBox.setInformativeText("Could not connect ot the stepper driver!")
        msgBox.setStandardButtons(QMessageBox.Retry | QMessageBox.Abort | QMessageBox.Close)
        msgBox.setDefaultButton(QMessageBox.Retry)
        ret = msgBox.exec_()
        if ret == QMessageBox.Retry:
            return True
        elif ret == QMessageBox.Abort:
            return False
        elif ret == QMessageBox.Close:
            return False

    @Slot()
    def jog_up_start(self):
        with self._lt_ctl:
            self._lt_ctl.move_inf_start(0)

    @Slot()
    def jog_down_start(self):
        with self._lt_ctl:
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

    def get_position(self):
        with self._lt_ctl:
            if self._mov_unit == 'steps':
                return self._lt_ctl.get_position()
            else:
                return self._lt_ctl.steps_to_mm(self._lt_ctl.get_position())
        
    @Slot()
    def move_pos(self, sender: QPushButton):
        # FIXME movement not correct!
        sender.setEnabled(False)
        with self._lt_ctl:
            if self._mov_unit == 'mm':
                self._lt_ctl.move_absolute_mm(self._mov_dist)
            elif self._mov_unit == 'steps':
                self._lt_ctl.move_absolute(int(self._mov_dist))
            elif self._mov_unit == 'mT':
                print('Not implemented!')
        sender.setEnabled(True)


    @Slot()
    def motor_stop(self):
        with self._lt_ctl:
            self._lt_ctl.stop()

    @Slot()
    def reference(self, sender: QPushButton):
        sender.setEnabled(False)
        with self._lt_ctl:
            self._lt_ctl.do_referencing()
        sender.setEnabled(True)

    def is_driver_ready(self) -> bool:
        with self._lt_ctl:
            return self._lt_ctl.test_connection()

    @Slot()
    def connect(self):
        pass

