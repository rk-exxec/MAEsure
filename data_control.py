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

import logging
import os
from evaluate_droplet import Droplet
import time
from datetime import datetime
import numpy as np
import pandas as pd
from PySide2.QtWidgets import QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem
from PySide2.QtCore import Signal, Slot, Qt

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class DataControl(QTableWidget):
    def __init__(self, parent=None) -> None:
        super(DataControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        self._time = 0
        self.data: pd.DataFrame = None
        self._block_painter = False
        self._header = ['Time', 'Cycle', 'Left_Angle', 'Right_Angle', 'Base_Width', 'Substate_Surface_Energy']
        self.setHorizontalHeaderLabels(self._header)
        self._is_time_invalid = False
        self._first_show = True
        self._default_dir = '%USERDATA%'
        self._cur_filename = ''
        self._seps = ['\t',',']

    def showEvent(self, event):
        #super().showEvent()
        if self._first_show:
            self.connect_signals()
            self._first_show = False

    def connect_signals(self):
        self.ui.saveFileAsBtn.clicked.connect(self.select_filename)

    @Slot(float, Droplet, int)
    def new_data_point(self, target_time:float, droplet:Droplet, cycle:int):
        if self._is_time_invalid: self.init_time()
        self.data = self.data.append(pd.DataFrame([[time.monotonic() - self._time, cycle, droplet.angle_l, droplet.angle_r, droplet.base_diam, 0.0]], columns=self._header))
        # TODO auch in thread?
        self.redraw_table()

    def redraw_table(self):
        self._block_painter = True
        self.setHorizontalHeaderLabels(self._header)
        self.setRowCount(self.data.shape[0])
        self.setColumnCount(self.data.shape[1])
        for r in range(self.data.shape[0]):
            for c in range(self.data.shape[1]):
                val = self.data.iloc[r, c]
                #if type(val) is np.float64:
                if isinstance(val ,float):
                    val = f'{val:g}'
                else:
                    val = str(val)
                self.setItem(r, c, QTableWidgetItem(val))
        self._block_painter = False
        #self.viewport().update()

    def export_data_csv(self, filename):
        sep = self._seps[self.ui.sepComb.currentIndex()]
        with open(filename, 'w', newline='') as f:
            if self.data is not None:
                self.data.to_csv(f, sep=sep, index=False)
                logging.info(f'data_ctl:Saved data as {filename}')
            else:
                QMessageBox.information(self, 'MAEsure Information', 'No data to be saved!', QMessageBox.Ok)
                logging.warning('data_ctl:cannot convert empty dataframe to csv')

    def select_filename(self):
        file, filter = QFileDialog.getSaveFileName(self, 'Save Measurement Data', f'{self._default_dir}/!now!.dat' ,'Data Files (*.dat *.csv)')
        if file == '': return
        self._default_dir = os.path.dirname(file)
        #self.export_data_csv(file)
        self.ui.fileNameEdit.setText(file)

    def create_file(self):
        """ Create the file, where all the data will be written to.
        Will be called at start of measurement.
        Fiolename is picked from LineEdit.
        Relaces \'!now!\' in filename with current datetime.
        """
        date = datetime.now().strftime('%Y%m%d_%H-%M-%S')
        self._cur_filename = self.ui.fileNameEdit.text().replace('!now!', f'{date}')
        open(self._cur_filename, 'w').close()

    def save_data(self):
        """ Saves all the stored data.
        Can be called as often as wanted, rewrites everything.
        """
        self.export_data_csv(self._cur_filename)

    def import_data_csv(self, filename):
        with open(filename, 'r') as f:
            self.data = pd.read_csv(f, sep='\t')
        self.redraw_table()

    def init_time(self):
        self._time = time.monotonic()
        self._is_time_invalid = False

    def init_data(self):
        self.data = pd.DataFrame(columns=self._header)
        self.create_file()
        self._is_time_invalid = True