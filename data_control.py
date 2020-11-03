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

from evaluate_droplet import Droplet
import time
import numpy as np
import pandas as pd
from PySide2.QtWidgets import QTableWidget, QTableWidgetItem
from PySide2.QtCore import Signal, Slot, Qt



class DataControl(QTableWidget):
    def __init__(self, parent=None) -> None:
        super(DataControl, self).__init__(parent)
        self._time = 0
        self.data: pd.DataFrame = None
        self._block_painter = False

    def paintEvent(self, event):
        if not self._block_painter:
            super().paintEvent(event)

    @Slot(float, Droplet, int)
    def new_data_point(self, target_time:float, droplet:Droplet, cycle:int):
        self.data.append[time.monotonic() - self._time, cycle, droplet.angle_l, droplet.angle_r, droplet.base_diam, 0.0]
        # auch in thread?
        self.redraw_table()

    def redraw_table(self):
        self._block_painter = True
        self.setHorizontalHeaderLabels(list(self.data.columns.values))
        for r in range(self.data.shape[0]):
            for c in range(self.data.shape[1]):
                self.setItem(r, c, QTableWidgetItem(str(self.data.iloc[r, c])))
        self._block_painter = False

    def export_data_csv(self, filename):
        with open(filename, 'w') as f:
            self.data.to_csv(f, sep='\t', index=False)

    def import_data_csv(self, filename):
        with open(filename, 'r') as f:
            self.data = pd.read_csv(f, sep='\t')
        self.redraw_table()

    def init_time(self):
        self.time = time.monotonic()

    def init_data(self):
        self.data = pd.DataFrame()
        self.data.columns = ['Time', 'Cycle', 'Left_Angle', 'Right_Angle', 'Base_Width', 'Substate_Surface_Energy']