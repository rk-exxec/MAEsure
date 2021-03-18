#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2021  Raphael Kriegl

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


from PySide2.QtCore import Signal
from PySide2.QtWidgets import QTableWidget, QTableWidgetItem

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class TableControl(QTableWidget):
    redraw_table_signal = Signal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui: Ui_main = None  
        self._first_show = True

    def showEvent(self, event):
        if self._first_show:
            self.ui = self.window().ui
            self.setHorizontalHeaderLabels(self.ui.dataControl.header)
            self._first_show = False
            self.redraw_table_signal.connect(self.redraw_table)
        return super().showEvent(event)

    def redraw_table(self):
        """ Redraw table with contents of dataframe """
        data = self.ui.dataControl.data
        self._block_painter = True
        #self.setHorizontalHeaderLabels(self._header)
        self.setRowCount(data.shape[0])
        self.setColumnCount(data.shape[1])
        for r in range(data.shape[0]):
            for c in range(data.shape[1]):
                val = data.iloc[r, c]
                #if type(val) is np.float64:
                if isinstance(val ,float):
                    val = f'{val:g}'
                else:
                    val = str(val)
                self.setItem(r, c, QTableWidgetItem(val))
        self._block_painter = False
        self.scrollToBottom()