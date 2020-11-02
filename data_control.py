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

import numpy as np
import pandas as pd
from PySide2.QtWidgets import QTableWidget
from PySide2.QtCore import Signal, Slot, Qt



class DataControl(QTableWidget):
    def __init__(self, parent=None) -> None:
        super(DataControl, self).__init__(parent)

    @Slot(np.ndarray)
    def new_data_point(self, data:np.ndarray):
        pass