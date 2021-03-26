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

from light_widget import LightWidget
from lt_control.lt_control import LT

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

class MagnetControl(QGroupBox):
    """
    A widget to control the motor via the module `lt_control`_.

    .. seealso:: :class:`LightWidget<light_widget.LightWidget>`
    .. _lt_control: https://github.com/rk-exxec/linear_stage_control
    """
    def __init__(self, parent=None) -> None:
        super(MagnetControl, self).__init__(parent)
        self._lt_ctl = LT()
        self.ui: Ui_main = self.window().ui
        self._shown = False
        self._mov_dist: float = 0
        self._mov_unit: str = 'steps'
        self._old_unit: str = 'steps'
        self._invalid = False
        self.wait_movement_thread = CallbackWorker(self.wait_movement, slotOnFinished=self.finished_moving)
        self.update_pos_timer = CustomCallbackTimer(self.update_pos, 250)
        self._calibration_table: pd.DataFrame = None
        self.mag_to_mm_interp: interpolate.interp1d = None
        self.mm_to_mag_interp: interpolate.interp1d = None
        logging.debug("initialized magnet control")

    def __del__(self):
        #self._lt_ctl.close()
        del self._lt_ctl

    def connect_signals(self):
        self.ui.jogUpBtn.pressed.connect(self.jog_up_start)
        self.ui.jogDownBtn.pressed.connect(self.jog_down_start)
        self.ui.jogUpBtn.released.connect(self.motor_stop_soft)
        self.ui.jogDownBtn.released.connect(self.motor_stop_soft)
        self.ui.referenceBtn.clicked.connect(self.reference)
        self.ui.goBtn.clicked.connect(self.move_pos)
        self.ui.stopBtn.clicked.connect(self.motor_stop)
        self.ui.posSpinBox.valueChanged.connect(self.spin_box_val_changed) #lambda pos: self.magnet_ctl.set_mov_dist(int(pos)) or self.ui.posSlider.setValue(int(pos))
        self.ui.unitComboBox.currentTextChanged.connect(self.mag_mov_unit_changed)
        self.ui.posSlider.sliderMoved.connect(self.slider_moved) # only fires with user input lambda pos: self.ui.posLineEdit.setText(str(pos)) or self.ui.posSpinBox.setValue(float(pos))
        self.ui.softRampChk.stateChanged.connect(self.change_ramp_type)

    def OnlyIfPortActive(func):
        """ Decorator that only executes fcn if serial port is open, otherwise it fails silently """
        def null(*args, **kwargs):
            pass

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if args[0]._lt_ctl.has_connection_error():
                logging.warning("magnet control: device not ready")
                return null(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper

    def showEvent(self, event: QShowEvent):
        if not self._shown:
            self.connect_signals()
            self.update_motor_status()
            self.update_pos()
            self.change_ramp_type(self.ui.softRampChk.isChecked())
            try:
                self.load_calib_file('./MagnetCalibration.csv')
                #self.unlock_mag_unit()
            except Exception as ex:
                self.lock_mag_unit()
            self._shown = True

    @OnlyIfPortActive
    def update_pos(self):
        """ update spin box with current pos"""
        try:
            pos = float(self.get_position())
        except Exception as toe:
            pos = 45100
        self.ui.posSpinBox.setValue(pos)

    @OnlyIfPortActive
    def update_motor_status(self):
        """ Get motor status and display it """
        with self._lt_ctl:
            try:
                if not self._lt_ctl.is_referenced():
                    self.ui.lamp.set_yellow()
                    self.set_status_message('Referencing needed!')
                    self.unlock_movement_buttons()
                    self.lock_abs_pos_buttons()
                    logging.info("magnet control: no reference! locking absolute movement")
                else:
                    self.ui.lamp.set_green()
                    self.set_status_message('')
                    self.unlock_movement_buttons()
                    logging.info("magnet control: has reference! unlocking absolute movement")
                return True
            except TimeoutError as te:
                self.ui.lamp.set_red()
                self.set_status_message('Connection Timeout!')
                self.lock_movement_buttons()
                return False

    @Slot(str)
    def mag_mov_unit_changed(self, unit: str):
        """ update slider and spin box if the movement units has changes """
        self._mov_unit = unit.strip()
        if unit == 'mm':
            self.ui.posSlider.setMaximum(3906) #max mm are 39.0625
            self.ui.posSlider.setTickInterval(100)
            self.ui.posSpinBox.setDecimals(2)
            if self._old_unit == 'steps':
                self.ui.posSpinBox.setValue(self._lt_ctl.steps_to_mm(self.ui.posSpinBox.value()))
            elif self._old_unit == 'mT':
                #/1000 bc interpolation works with tesla, while we work with mT
                self.ui.posSpinBox.setValue(self.mag_to_mm_interp(self.ui.posSpinBox.value()/1000))
        elif unit == 'steps':
            self.ui.posSlider.setMaximum(50000)
            self.ui.posSlider.setTickInterval(1000)
            self.ui.posSpinBox.setDecimals(0)
            if self._old_unit == 'mm':
                self.ui.posSpinBox.setValue(self._lt_ctl.mm_to_steps(self.ui.posSpinBox.value()))
            elif self._old_unit == 'mT':
                self.ui.posSpinBox.setValue(self._lt_ctl.mm_to_steps(self.mag_to_mm_interp(self.ui.posSpinBox.value()/1000)))
        elif unit == 'mT':
            self.ui.posSlider.setMaximum(max(self._calibration_table['Field(T)'])*1000)
            self.ui.posSlider.setTickInterval(10)
            self.ui.posSpinBox.setDecimals(0)
            if self._old_unit == 'mm':
                self.ui.posSpinBox.setValue(self.mm_to_mag_interp(self.ui.posSpinBox.value())*1000)
            elif self._old_unit == 'steps':
                self.ui.posSpinBox.setValue(self.mm_to_mag_interp(self._lt_ctl.steps_to_mm(self.ui.posSpinBox.value()))*1000)
        else:
            return
        logging.info(f"magnet control: movement unit changed from {self._old_unit} to {self._mov_unit}")
        self._old_unit = self._mov_unit

    @Slot(float)
    def spin_box_val_changed(self, value: float):
        """ update internal variable and slider if spin box value changed """
        if self.ui.unitComboBox.currentText() == 'steps':
            self._mov_dist = int(value)
            self.ui.posSlider.setValue(int(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self._mov_dist = value
            self.ui.posSlider.setValue(int(value*100))
        elif self.ui.unitComboBox.currentText() == 'mT':
            self._mov_dist = value
            self.ui.posSlider.setValue(int(value))

    @Slot(int)
    def slider_moved(self, value: int):
        """ update spin box if slider moved """
        if self.ui.unitComboBox.currentText() == 'steps':
            self.ui.posSpinBox.setValue(float(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self.ui.posSpinBox.setValue(float(value/100))
        elif self.ui.unitComboBox.currentText() == 'mT':
            self.ui.posSpinBox.setValue(float(value))

    @Slot(int)
    @OnlyIfPortActive
    def change_ramp_type(self, state: Qt.CheckState):
        """ set motor brake and accel ramp on check changed """
        if state == Qt.Checked:
            with self._lt_ctl:
                self._lt_ctl.set_soft_ramp()
            logging.info("magnet control: set soft ramp")
        elif state == Qt.Unchecked:
            with self._lt_ctl:
                self._lt_ctl.set_quick_ramp()
                logging.info("magnet control: set quick ramp")
        else:
            pass


    def do_timeout_dialog(self) -> bool:
        """ display a dialog if the connection timed out """
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

    def get_position(self):
        """ return the motor position in the current unit """
        with self._lt_ctl:
            if self._mov_unit == 'steps':
                return self._lt_ctl.get_position()
            elif self._mov_unit == 'mm':
                return self._lt_ctl.steps_to_mm(self._lt_ctl.get_position())
            elif self._mov_unit == 'mT':
                return self.mm_to_mag_interp(self._lt_ctl.steps_to_mm(self._lt_ctl.get_position()))*1000

    @Slot()
    def jog_up_start(self):
        """ start motor movement away from motor """
        logging.info("magnet control: start jog up")
        with self._lt_ctl:
            self._lt_ctl.move_inf_start(0)
        self.update_pos_timer.start()

    @Slot()
    def jog_down_start(self):
        """ start motor movement towards motor """
        logging.info("magnet control: start jog down")
        with self._lt_ctl:
            self._lt_ctl.move_inf_start(1)
        self.update_pos_timer.start()

    @Slot()
    def move_pos(self):
        """ move motor to specified position """
        with self._lt_ctl:
            if self._mov_unit == 'mm':
                self._lt_ctl.move_absolute_mm(self._mov_dist)
            elif self._mov_unit == 'steps':
                self._lt_ctl.move_absolute(int(self._mov_dist))
            elif self._mov_unit == 'mT':
                self._lt_ctl.move_absolute_mm(self.mag_to_mm_interp(self._mov_dist/1000))
        self.lock_movement_buttons()
        logging.info(f"magnet control: start movement to {self._mov_dist}{self._mov_unit}")
        self.wait_movement_thread.start()

    @Slot()
    def motor_stop(self):
        """ stop motor immediately"""
        with self._lt_ctl:
            self._lt_ctl.stop()
        if self.update_pos_timer.isActive():
            self.update_pos_timer.stop()
        logging.info("magnet control: stop")
        self.update_pos()
        self.update_motor_status()

    @Slot()
    def motor_stop_soft(self):
        """ stops motor with brake ramp """
        with self._lt_ctl:
            self._lt_ctl.stop_soft()
        if self.update_pos_timer.isActive():
            self.update_pos_timer.stop()
        logging.info("magnet control: stop")
        self.lock_movement_buttons()
        self.wait_movement_thread.start()

    def wait_movement(self):
        """ wait unitl movement stops """
        with self._lt_ctl:
            self._lt_ctl.wait_movement()

    def finished_moving(self):
        """ update ui position displays when movement finishes """
        # callback for when the motor stops moving (only absolute and relative, and jogging with soft stop)
        logging.info("magnet control: reached pos")
        self.update_pos()
        self.update_motor_status()

    @Slot()
    def reference(self):
        """ execute referencing process """
        self.ui.lamp.set_yellow()
        logging.info("magnet control: referencing")
        with self._lt_ctl:
            self._lt_ctl.do_referencing()
        self.lock_movement_buttons()
        self.wait_movement_thread.start()

    def is_driver_ready(self) -> bool:
        """ check if the motor drive is ready for movement """
        with self._lt_ctl:
            return self._lt_ctl.test_connection()

    def unlock_mag_unit(self):
        """ mag unit is now available """
        self.ui.unitComboBox.addItem('mT')

    def lock_mag_unit(self):
        """ mag unit is not available """
        self.ui.unitComboBox.clear()
        self.ui.unitComboBox.addItems(['steps','mm'])

    def lock_movement_buttons(self):
        """ lock buttons if movemnt shouldn't be possible """
        self.ui.jogUpBtn.setEnabled(False)
        self.ui.jogDownBtn.setEnabled(False)
        self.ui.jogUpBtn.setEnabled(False)
        self.ui.jogDownBtn.setEnabled(False)
        self.ui.referenceBtn.setEnabled(False)
        self.ui.goBtn.setEnabled(False)
        self.ui.posSpinBox.setEnabled(False)
        self.ui.unitComboBox.setEnabled(False)
        self.ui.posSlider.setEnabled(False)
        self.ui.softRampChk.setEnabled(False)

    def lock_abs_pos_buttons(self):
        self.ui.goBtn.setEnabled(False)

    def unlock_movement_buttons(self):
        self.ui.jogUpBtn.setEnabled(True)
        self.ui.jogDownBtn.setEnabled(True)
        self.ui.jogUpBtn.setEnabled(True)
        self.ui.jogDownBtn.setEnabled(True)
        self.ui.referenceBtn.setEnabled(True)
        self.ui.goBtn.setEnabled(True)
        self.ui.posSpinBox.setEnabled(True)
        self.ui.unitComboBox.setEnabled(True)
        self.ui.posSlider.setEnabled(True)
        self.ui.softRampChk.setEnabled(True)

    def set_status_message(self, text: str = ''):
        """ set the message that is displayed on the motor control label """
        self.ui.statusLabel.setText(text)

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
                self._lt_ctl.move_absolute_mm(i)
                time.sleep(1)
                mult = gaussmeter.query('FIELDM?').strip()
                if len(mult) == 0:
                    mult = 1
                else:
                    mult = _prefix[mult]
                tesla = abs(float(gaussmeter.query('FIELD?'))*mult)
                steps = self._lt_ctl.get_position()
                #df = df.append(pd.DataFrame([[steps, self._lt_ctl.steps_to_mm(steps), tesla]]))
                #df.at[i,'Steps'] = steps
                #df.at[i,'Field(T)'] = tesla
                #df.at[i,'Distance(m)'] = steps*(1.25e-3/1600)
                #print('{0:d}\t{1:.3E} mm\t{2:.3E} T'.format(steps, self._lt_ctl.steps_to_mm(steps), tesla))
                f.write('{0:d}\t{1:.3E}\t{2:.3E}\n'.format(steps, self._lt_ctl.steps_to_mm(steps), tesla))
        self.load_calib_file(path)
        self.unlock_mag_unit()
        #self._lt_ctl.move_absolute(0)
        gaussmeter.close()