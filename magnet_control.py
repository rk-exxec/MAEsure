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

from PySide2.QtCore import QTimer, Signal, Slot, Qt, QThread
from PySide2.QtGui import QShowEvent
from PySide2.QtWidgets import QGroupBox, QMessageBox, QPushButton

from light_widget import LightWidget
from lt_control.lt_control import LT

class WaitMovementThread(QThread):
    def __init__(self, target, slotOnFinished=None):
        super(WaitMovementThread, self).__init__()
        self.target = target
        if slotOnFinished:
            self.finished.connect(slotOnFinished)
    
    def run(self, *args, **kwargs):
        self.target(*args, **kwargs)

class CustomCallbackTimer(QTimer):
    def __init__(self, target, interval=500):
        super(CustomCallbackTimer, self).__init__()
        self.setInterval(interval)
        self.setSingleShot(False)
        self.timeout.connect(target)

# TODO magnet control
# TODO better cleanup (deleteLater())
# calib

class MagnetControl(QGroupBox):
    """A widget to control the motor via lt_control  

    Use instead of QGroupBox
    """
    def __init__(self, parent=None) -> None:
        #self.portsComboBox: QComboBox = None
        super(MagnetControl, self).__init__(parent)
        self._lt_ctl = LT()
        self.workerThread = QThread(self)
        self.ui = self.window()
        self._shown = False
        self._mov_dist: float = 0
        self._mov_unit: str = 'steps'
        self._invalid = False
        self.wait_movement_thread = WaitMovementThread(self.wait_movement, self.finished_moving)
        self.update_pos_timer = CustomCallbackTimer(self.update_pos, 250)

    def __del__(self):
        #self._lt_ctl.close()
        del self._lt_ctl

    def connect_signals(self):
        self.ui.jogUpBtn.pressed.connect(self.jog_up_start)
        self.ui.jogDownBtn.pressed.connect(self.jog_down_start)
        self.ui.jogUpBtn.released.connect(self.motor_stop)
        self.ui.jogDownBtn.released.connect(self.motor_stop)
        self.ui.referenceBtn.clicked.connect(self.reference)
        self.ui.goBtn.clicked.connect(self.move_pos)
        self.ui.stopBtn.clicked.connect(self.motor_stop)
        self.ui.posSpinBox.valueChanged.connect(self.spin_box_val_changed) #lambda pos: self.magnet_ctl.set_mov_dist(int(pos)) or self.ui.posSlider.setValue(int(pos))
        self.ui.unitComboBox.currentTextChanged.connect(self.mag_mov_unit_changed)
        self.ui.posSlider.sliderMoved.connect(self.slider_moved) # lambda pos: self.ui.posLineEdit.setText(str(pos)) or self.ui.posSpinBox.setValue(float(pos))

    def showEvent(self, event: QShowEvent):
        if not self._shown:
            self.connect_signals()
            self.update_motor_status()
            self.update_pos()
            self._shown = True

    def update_pos(self):
        # update spin box with current pos    
        self.ui.posSpinBox.setValue(float(self.get_position()))

    def update_motor_status(self):
        with self._lt_ctl:
            try:
                if not self._lt_ctl.is_referenced():
                    self.ui.lamp.set_yellow()
                    self.lock_abs_pos_buttons()
                else:
                    self.ui.lamp.set_green()
                    self.unlock_movement_buttons()
            except TimeoutError as te:
                self.ui.lamp.set_red()
    
    @Slot(str)
    def mag_mov_unit_changed(self, unit: str):
        self._mov_unit = unit.strip()
        if unit == 'mm':
            self.ui.posSlider.setMaximum(3906) #max mm are 39.0625
            self.ui.posSlider.setTickInterval(100)
            self.ui.posSpinBox.setDecimals(2)
            self.ui.posSpinBox.setValue(self._lt_ctl.steps_to_mm(self.ui.posSpinBox.value()))
        elif unit == 'steps':
            self.ui.posSlider.setMaximum(50000)
            self.ui.posSlider.setTickInterval(1000)
            self.ui.posSpinBox.setDecimals(0)
            self.ui.posSpinBox.setValue(self._lt_ctl.mm_to_steps(self.ui.posSpinBox.value()))

    @Slot(float)
    def spin_box_val_changed(self, value: float):
        if self.ui.unitComboBox.currentText() == 'steps':
            self._mov_dist = int(value)
            self.ui.posSlider.setValue(int(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self._mov_dist = value
            self.ui.posSlider.setValue(int(value*100))

    @Slot(int)
    def slider_moved(self, value: int):
        if self.ui.unitComboBox.currentText() == 'steps':
            self.ui.posSpinBox.setValue(float(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self.ui.posSpinBox.setValue(float(value/100))

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

    def get_position(self):
        with self._lt_ctl:
            if self._mov_unit == 'steps':
                return self._lt_ctl.get_position()
            else:
                return self._lt_ctl.steps_to_mm(self._lt_ctl.get_position())
    
    @Slot()
    def jog_up_start(self):
        with self._lt_ctl:
            self._lt_ctl.move_inf_start(0)
        self.update_pos_timer.start()

    @Slot()
    def jog_down_start(self):
        with self._lt_ctl:
            self._lt_ctl.move_inf_start(1)
        self.update_pos_timer.start()
        
    @Slot()
    def move_pos(self):
        with self._lt_ctl:
            if self._mov_unit == 'mm':
                self._lt_ctl.move_absolute_mm(self._mov_dist)
            elif self._mov_unit == 'steps':
                self._lt_ctl.move_absolute(int(self._mov_dist))
            elif self._mov_unit == 'mT':
                print('Not implemented!')
        self.lock_movement_buttons()
        self.wait_movement_thread.start()

    @Slot()
    def motor_stop(self):
        with self._lt_ctl:
            self._lt_ctl.stop()
        if self.update_pos_timer.isActive():
            self.update_pos_timer.stop()
        self.update_pos()
        self.update_motor_status()

    def wait_movement(self):
        with self._lt_ctl:
            self._lt_ctl.wait_movement()

    def finished_moving(self):
        # callback for when the motor stops moving (only absolute and relative, not jogging)
        self.update_pos()
        self.update_motor_status()
        self.unlock_movement_buttons()

    @Slot()
    def reference(self):
        with self._lt_ctl:
            self._lt_ctl.do_referencing()
        self.lock_movement_buttons()
        self.wait_movement_thread.start()

    def is_driver_ready(self) -> bool:
        with self._lt_ctl:
            return self._lt_ctl.test_connection()

    def lock_movement_buttons(self):
        self.ui.jogUpBtn.setEnabled(False)
        self.ui.jogDownBtn.setEnabled(False)
        self.ui.jogUpBtn.setEnabled(False)
        self.ui.jogDownBtn.setEnabled(False)
        self.ui.referenceBtn.setEnabled(False)
        self.ui.goBtn.setEnabled(False)
        self.ui.posSpinBox.setEnabled(False)
        self.ui.unitComboBox.setEnabled(False)
        self.ui.posSlider.setEnabled(False)

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