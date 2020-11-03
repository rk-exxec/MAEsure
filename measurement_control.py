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

# TODO meas ctl
#   - werte für magnetschritte und so parse als kommaseparierte liste oder ranges mit start:stop:step oder kombination für ausreißerwerte
#       -> als custom lineedit?
#   - form braucht noch edit feld für anfangs und endwerte der parameter nicht nur intervall

#   - zeit immer vor magnetfeld gemessen falls beide gewählt!
#   - wnn nur magnet, droplet nicht nach jedem punkt wieder neu ausgeben?

from evaluate_droplet import Droplet
import numpy as np
import time

from PySide2 import QtGui
from PySide2.QtWidgets import QGroupBox
from PySide2.QtCore import Signal, Slot, Qt

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class MeasurementControl(QGroupBox):
    new_datapoint_signal = Signal(float, Droplet, int)
    def __init__(self, parent=None) -> None:
        super(MeasurementControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        self._time_interval = 0.0
        self._magnet_interval = 0.0
        self._repeat_after = 0 # 0 is time, 1 is magnet
        self._method = 0 # sessile
        self._cycles = 1
        self.connect_signals()

    def connect_signals(self):
        self.new_datapoint_signal.connect(self.ui.dataControl.new_data_point)

    def measure(self):
        """ Here the measurement process happens
        This fcn will not return until done or aborted
        """
        # TODO execute in thread!!!
        # init vars
        old_t = 0
        self.read_intervals()
        self.ui.dataControl.init_data()



        # TODO not nested but flat with one while loop with custom increments and checks
        # measuring = True
        # mag = next(self._magnet_interval) if self.ui.sweepMagChk else 0
        # tim = next(self._time_interval) if self.ui.sweepTimeChk else 0
        # while measuring:
        #     #dispense if necessary
        #     time.sleep(tim)

        #     # take a measurement

        #     if self.ui.sweepTimeChk:



        #repeat measurement after
        for cycle in self._cycles:
            self.ui.pump_control.infuse()
            self.ui.dataControl.init_time()
            for tim in self._time_interval:
                # FIXME rather use timer and callback fcn?
                time.sleep(tim - old_t)
                old_t = tim
                # get droplet
                drplt = self.ui.camera_prev._droplet
                self.new_datapoint_signal.emit(tim, drplt, cycle)
                #self.ui.dataControl.new_data_point(tim, drplt)

            self.ui.pump_control.withdraw()

    def read_intervals(self):
        self._time_interval = self.parse_intervals(self.ui.timeInt.text())
        self._magnet_interval = self.parse_intervals(self.ui.magInt.text())
        self._repeat_after = self.ui.repWhenCombo.currentIndex()

    # TODO logspace??
    def parse_intervals(self, expr:str):
        """ Parses string of values to float list
        expr can look like '2', '1.0,2.3,3.8', '1.1,3:6' or '1.7,4:6:5,-2.8'
        with 'x:y:z' the values will be passed to numpy.linspace(x, y, num=z, enpoint=True), optional z = 10
        Values won't be sorted
        """
        expr = expr.strip()
        out: List[float] = []
        for s in expr.split(','):
            if ':' in s:
                r = s.split(':')
                r[0] = float(r[0])
                r[1] = float(r[1])
                if len(r) == 2:
                    r[2] = 10
                elif len(r) == 3:
                    r[2] = int(r[2])
                out.append(np.linspace(r[0], r[1], num=r[2], endpoint=True))
            else:
                out.append(float(s))
        return out
