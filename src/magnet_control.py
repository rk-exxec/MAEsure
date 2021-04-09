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

# TODO expose more settings of lt_control, reference side, etc.

# TODO maybe do StageControl class and expand it with the magnet stuff??

import functools
import pyvisa
import time
import logging
import numpy as np
import pandas as pd
from scipy import interpolate

from PySide2.QtCore import QTimer, Slot, Qt
from PySide2.QtGui import QShowEvent
from PySide2.QtWidgets import QGroupBox, QMessageBox
from scipy.interpolate.interpolate import interp1d

from lt_control import LinearStageControlGUI

from qthread_worker import CallbackWorker

# import for type hinting not evaluated at runtime to avoid cyclic imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

class CustomCallbackTimer(QTimer):
    """ Timer with custom callback function """
    def __init__(self, target, interval=500):
        super(CustomCallbackTimer, self).__init__()
        self.setInterval(interval)
        self.setSingleShot(False)
        self.timeout.connect(target)

# TODO implement as standalone for Heiko Unold
# TODO calib - test
# TODO retry failed serial port in timer and update motor status once connected again
# TODO test new decorator

class MagnetControl(LinearStageControlGUI):
    """
    A widget to control a magnet with the stage control widget

    .. seealso:: :class:`StageControl<https://github.com/rk-exxec/linear_stage_control/blob/master/stage_control.py#L52>`
    """
    def __init__(self, parent) -> None:
        super().__init__(parent=parent)
        self.ui : Ui_main = None
        self._calibration_table: pd.DataFrame = None
        self.mag_to_mm_interp: interpolate.interp1d = None
        self.mm_to_mag_interp: interpolate.interp1d = None
        logging.debug("initialized magnet control")

    def showEvent(self, event: QShowEvent):
        if super().showEvent(event):
            self.ui = self.window().ui
            try:
                self.load_calib_file('./MagnetCalibration.csv')
                #self.unlock_mag_unit()
            except Exception as ex:
                self.lock_mag_unit()
            

    @Slot(str)
    def mag_mov_unit_changed(self, unit: str):
        """ update slider and spin box if the movement units has changes """
        self._mov_unit = unit.strip()
        if unit == 'mm':
            self.posSlider.setMaximum(3906) #max mm are 39.0625
            self.posSlider.setTickInterval(100)
            self.posSpinBox.setDecimals(2)
            if self._old_unit == 'steps':
                self.posSpinBox.setValue(self.ls_ctl.steps_to_mm(self.posSpinBox.value()))
            elif self._old_unit == 'mT':
                #/1000 bc interpolation works with tesla, while we work with mT
                self.posSpinBox.setValue(self.mag_to_mm_interp(self.posSpinBox.value()/1000))
        elif unit == 'steps':
            self.posSlider.setMaximum(50000)
            self.posSlider.setTickInterval(1000)
            self.posSpinBox.setDecimals(0)
            if self._old_unit == 'mm':
                self.posSpinBox.setValue(self.ls_ctl.mm_to_steps(self.posSpinBox.value()))
            elif self._old_unit == 'mT':
                self.posSpinBox.setValue(self.ls_ctl.mm_to_steps(self.mag_to_mm_interp(self.posSpinBox.value()/1000)))
        elif unit == 'mT':
            self.posSlider.setMaximum(max(self._calibration_table['Field(T)'])*1000)
            self.posSlider.setTickInterval(10)
            self.posSpinBox.setDecimals(0)
            if self._old_unit == 'mm':
                self.posSpinBox.setValue(self.mm_to_mag_interp(self.posSpinBox.value())*1000)
            elif self._old_unit == 'steps':
                self.posSpinBox.setValue(self.mm_to_mag_interp(self.ls_ctl.steps_to_mm(self.posSpinBox.value()))*1000)
        else:
            return
        logging.info(f"magnet control: movement unit changed from {self._old_unit} to {self._mov_unit}")
        self._old_unit = self._mov_unit

    def get_position(self):
        """ return the motor position in the current unit """
        if self._mov_unit == 'mT':
            return self.mm_to_mag_interp(super().get_position())*1000
        else:
            return super().get_position()

    @Slot()
    def move_pos(self):
        """ move motor to specified position """
        with self.ls_ctl:
            if self._mov_unit == 'mm':
                self.ls_ctl.move_absolute_mm(self._mov_dist)
            elif self._mov_unit == 'steps':
                self.ls_ctl.move_absolute(int(self._mov_dist))
            elif self._mov_unit == 'mT':
                self.ls_ctl.move_absolute_mm(self.mag_to_mm_interp(self._mov_dist/1000))
        self.lock_movement_buttons()
        logging.info(f"magnet control: start movement to {self._mov_dist}{self._mov_unit}")
        self.wait_movement_thread.start()

    def wait_movement(self):
        """ wait unitl movement stops """
        with self.ls_ctl:
            self.ls_ctl.wait_movement()

    def unlock_mag_unit(self):
        """ mag unit is now available """
        self.unitComboBox.addItem('mT')

    def lock_mag_unit(self):
        """ mag unit is not available """
        self.unitComboBox.clear()
        self.unitComboBox.addItems(['steps','mm'])

    def load_calib_file(self, file):
        """ load magnet to mm calibration file """
        self._calibration_table = pd.read_csv(file)
        self.mag_to_mm_interp = interp1d(self._calibration_table['Field(T)'], self._calibration_table['Distance(m)'])
        self.mm_to_mag_interp = interp1d(self._calibration_table['Distance(m)'], self._calibration_table['Field(T)'])

    def do_calibration(self):
        """ do a magnet vs mm calibration """
        # TODO test this
        rm = pyvisa.ResourceManager()
        res = rm.list_resources('GPIB?*INSTR')
        gm_addr = res[0]
        gaussmeter = rm.open_resource(gm_addr)
        gaussmeter.query('AUTO 1')
        _prefix = {'y': 1e-24, 'z': 1e-21,'a': 1e-18,'f': 1e-15,'p': 1e-12,'n': 1e-9,'u': 1e-6,'m': 1e-3,
           'c': 1e-2,'d': 1e-1,'k': 1e3,'M': 1e6,'G': 1e9,'T': 1e12,'P': 1e15,'E': 1e18,'Z': 1e21,'Y': 1e24}
        df = pd.DataFrame(columns=['Steps','Field(T)','Distance(m)'])

        csv_sep = '\t'
        path = './MagnetCalibration.csv'

        with open(path, 'w') as f:
            #f.write('SEP=' + csv_sep +'\n')
            #df.to_csv(f, sep = csv_sep)
            f.write('Steps\tDistance(mm)\tField(T)\n')
            #print('Steps\tDistance(mm)\tField(T)')
            for i in np.arange(0, 35, .5):
                self.ls_ctl.move_absolute_mm(i)
                time.sleep(1)
                mult = gaussmeter.query('FIELDM?').strip()
                if len(mult) == 0:
                    mult = 1
                else:
                    mult = _prefix[mult]
                tesla = abs(float(gaussmeter.query('FIELD?'))*mult)
                steps = self.ls_ctl.get_position()
                #df = df.append(pd.DataFrame([[steps, self._lt_ctl.steps_to_mm(steps), tesla]]))
                #df.at[i,'Steps'] = steps
                #df.at[i,'Field(T)'] = tesla
                #df.at[i,'Distance(m)'] = steps*(1.25e-3/1600)
                #print('{0:d}\t{1:.3E} mm\t{2:.3E} T'.format(steps, self._lt_ctl.steps_to_mm(steps), tesla))
                f.write('{0:d}\t{1:.3E}\t{2:.3E}\n'.format(steps, self.ls_ctl.steps_to_mm(steps), tesla))
        self.load_calib_file(path)
        self.unlock_mag_unit()
        #self._lt_ctl.move_absolute(0)
        gaussmeter.close()
