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

import time
from datetime import datetime
from math import degrees
import numpy as np
import pandas as pd
from PySide2.QtWidgets import QFileDialog, QGroupBox, QMessageBox
from PySide2.QtCore import Signal, Slot

from evaluate_droplet import Droplet
from qthread_worker import Worker

from typing import Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class DataControl(QGroupBox):
    """ class for data and file control """
    update_plot_signal = Signal(float,float)
    def __init__(self, parent=None) -> None:
        super(DataControl, self).__init__(parent)
        self.ui: Ui_main = None # set post init bc of parent relationship not automatically applied on creation in generated script
        self._time = 0   
        self.thr = None
        self._block_painter = False
        """this represents the header for the table and the csv file

        .. note::
            - **Time**: actual point in time the dataset was aquired
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
        self.header = ['Time', 'Cycle', 'Left_Angle', 'Right_Angle', 'Base_Width', 'Substate_Surface_Energy', 'Magn_Pos', 'Magn_Unit', 'Fe_Vol_P', 'ID', 'DateTime']
        self.data = pd.DataFrame(columns=self.header)

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
            self.ui = self.window().ui
            self.ui.tableControl.setHorizontalHeaderLabels(self.header)
            # self.thr = Worker(self.ui.tableControl.redraw_table)
            # self.thr.start()
            self.ui.tableControl.redraw_table_signal.emit()
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
        

    @Slot(Droplet, int)
    def new_data_point(self, droplet:Droplet, cycle:int):
        """ 
        add new datapoint to dataframe and invoke redrawing of table
        
        :param target_time: unused
        :param droplet: droplet data
        :param cycle: current cycle in case of repeated measurements
        """
        if self._is_time_invalid: self.init_time()
        id = self.ui.idCombo.currentText() if self.ui.idCombo.currentText() != "" else "-"
        percent = self.ui.ironContentEdit.text()
        curtime = time.monotonic() - self._time
        self.data = self.data.append(
            pd.DataFrame([[
                curtime, 
                cycle, 
                droplet.angle_l, 
                droplet.angle_r, 
                droplet.base_diam, 
                "-", 
                self.ui.magnetControl.posSpinBox.value(),
                self.ui.magnetControl.unitComboBox.currentText(),
                percent, 
                id, 
                self._meas_start_datetime
            ]], columns=self.header)
        )
        #logging.debug("starte thread zum redrawing vom table")
        # self.thr = Worker(self.ui.tableControl.redraw_table)
        # self.thr.start()
        self.ui.tableControl.redraw_table_signal.emit()
        self.update_plot_signal.emit(curtime,(droplet.angle_l + droplet.angle_r)/2)

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
        self._cur_filename = self._cur_filename.replace('!pos!', f'{self.ui.magnetControl.posSpinBox.value()}')
        self._cur_filename = self._cur_filename.replace('!ID!', f'{self.ui.idCombo.currentText()}')
        open(self._cur_filename, 'w').close()

    def save_data(self):
        """ Saves all the stored data.

        Overwrites everything.
        """
        self.export_data_csv(self._cur_filename)
        logging.info(f"saved data {self._cur_filename}")
        self.ui.statusbar.showMessage(f"saved data {self._cur_filename}")

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

    def invalidate_time(self):
        self._is_time_invalid = True

    def init_data(self):
        """ Initialize the date before measurement.

        Create new dataframe with column headers and create new file with current filename.
        Invalidate time variable.
        """
        self.data = pd.DataFrame(columns=self.header)
        self.create_file()
        self._is_time_invalid = True