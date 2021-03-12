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

import logging
import os
import threading
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
    """ class for data and file control """
    def __init__(self, parent=None) -> None:
        super(DataControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        self._time = 0
        self.data: pd.DataFrame = None
        self._block_painter = False
        """this represents the header for the table and the csv file

        .. note::
            - **Time**: actual point in time the dataset was aquired
            - **T_Time**: point in time, where the dataset should have been aquired (target time)
            - **Cycle**: if measurement is repeated, current number of repeats
            - **Left_Angle**: angle of left droplet side
            - **Right_Angle**: angle of right droplet side
            - **Base_Width**: Width of the droplet
            - **Substrate_Surface_Energy**: calculated surface energy of substrate from angles
            - **Magn_Pos**: position of magnet
            - **Magn_Unit**: unit of magnet pos (mm or steps or Tesla)
            - **Fe_Vol_P**: iron content in sample in Vol.% 
            - **ID**: ID of sample
            - **DateTime**: date and time at begin of measurement
        
        """
        self._header = ['Time', 'T_Time', 'Cycle', 'Left_Angle', 'Right_Angle', 'Base_Width', 'Substate_Surface_Energy', 'Magn_Pos', 'Magn_Unit', 'Fe_Vol_P', 'ID', 'DateTime']
        self.setHorizontalHeaderLabels(self._header)
        self._is_time_invalid = False
        self._first_show = True
        self._default_dir = '%USERDATA%'
        self._initial_filename = '!now!_!ID!_!pos!'
        self._meas_start_datetime = ''
        self._cur_filename = ''
        self._seps = ['\t',',']

    def showEvent(self, event):
        #super().showEvent()
        if self._first_show:
            # try to use Home drive, if not, use Documents folder
            if os.path.exists("G:/Messungen/Angle_Measurements"):
                self.ui.fileNameEdit.setText(os.path.expanduser(f'G:/Messungen/Angle_Measurements/{self._initial_filename}.dat'))
                self._default_dir = 'G:/Messungen/Angle_Measurements'
            else:
                self.ui.fileNameEdit.setText(os.path.expanduser(f'~/Documents/{self._initial_filename}.dat'))
                self._default_dir = '~/Documents'
            self.connect_signals()
            self._first_show = False

    def connect_signals(self):
        self.ui.saveFileAsBtn.clicked.connect(self.select_filename)

    @Slot(float, Droplet, int)
    def new_data_point(self, target_time:float, droplet:Droplet, cycle:int):
        """ 
        add new datapoint to dataframe and invoke redrawing of table
        
        :param target_time: unused
        :param droplet: droplet data
        :param cycle: current cycle in case of repeated measurements
        """
        if self._is_time_invalid: self.init_time()
        id = self.ui.materialIDEdit.text() if self.ui.materialIDEdit.text() != "" else "-"
        percent = self.ui.ironContentEdit.text()
        self.data = self.data.append(
            pd.DataFrame([[
                time.monotonic() - self._time, 
                target_time,
                cycle, 
                droplet.angle_l, 
                droplet.angle_r, 
                droplet.base_diam, 
                "-", 
                self.ui.posSpinBox.value(),
                self.ui.unitComboBox.currentText(),
                percent, 
                id, 
                self._meas_start_datetime
            ]], columns=self._header)
        )
        thr = threading.Thread(target=self.redraw_table)
        thr.start()
        # self.redraw_table()

    def redraw_table(self):
        """ Redraw table with contents of dataframe """
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
        self.scrollToBottom()
        #self.viewport().update()

    def export_data_csv(self, filename):
        """ Export data as csv with selected separator

        :param filename: name of file to create and write data to
        """
        sep = self._seps[self.ui.sepComb.currentIndex()]
        with open(filename, 'w', newline='') as f:
            if self.data is not None:
                self.data.to_csv(f, sep=sep, index=False)
                logging.info(f'data_ctl: Saved data as {filename}')
            else:
                QMessageBox.information(self, 'MAEsure Information', 'No data to be saved!', QMessageBox.Ok)
                logging.warning('data_ctl: cannot convert empty dataframe to csv')

    def select_filename(self):
        """ Opens `Save As...` dialog to determine file save location.
        Displays filename in line edit
        """
        file, filter = QFileDialog.getSaveFileName(self, 'Save Measurement Data', f'{self._default_dir}/{self._initial_filename}' ,'Data Files (*.dat *.csv)')
        if file == '': return
        self._default_dir = os.path.dirname(file)
        #self.export_data_csv(file)
        self.ui.fileNameEdit.setText(file)

    def create_file(self):
        """ Create the file, where all the data will be written to.
        Will be called at start of measurement.
        Filename is picked from LineEdit.

        - Replaces \'!now!\' in filename with current datetime.
        - Replaces \'!pos!\' in filename with current magnet pos.
        - Replaces \'!ID!\' in filename with current material ID.
        """
        self._meas_start_datetime = datetime.now().strftime('%y_%m_%d_%H-%M')
        if self.ui.fileNameEdit.text() == "": raise ValueError("No File specified!")
        self._cur_filename = self.ui.fileNameEdit.text().replace('!now!', f'{ self._meas_start_datetime}')
        self._cur_filename = self._cur_filename.replace('!pos!', f'{self.ui.posSpinBox.value()}')
        self._cur_filename = self._cur_filename.replace('!ID!', f'{self.ui.materialIDEdit.text()}')
        open(self._cur_filename, 'w').close()

    def save_data(self):
        """ Saves all the stored data.

        Overwrites everything.
        """
        self.export_data_csv(self._cur_filename)
        logging.info(f"saved data {self._cur_filename}")

    def import_data_csv(self, filename):
        """ Import data and display it.

        Can be used to append measurement to exiting data
        """
        with open(filename, 'r') as f:
            self.data = pd.read_csv(f, sep='\t')
        self.redraw_table()

    def init_time(self):
        """ Initialize time variable to current time if invalid.
        """
        self._time = time.monotonic()
        self._is_time_invalid = False

    def init_data(self):
        """ Initialize the date before measurement.

        Create new dataframe with column headers and create new file with current filename.
        Invalidate time variable.
        """
        self.data = pd.DataFrame(columns=self._header)
        self.create_file()
        self._is_time_invalid = True