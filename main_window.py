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

# This Python file uses the following encoding: utf-8
import os
import atexit

from PySide2.QtWidgets import QComboBox, QMainWindow
from PySide2.QtCore import QFile, Signal, Slot
from PySide2.QtUiTools import QUiLoader
#from ui_main import Ui_main

from camera_control import CameraControl
from magnet_control import MagnetControl
from pump_control import PumpControl
from data_control import DataControl
from measurement_control import MeasurementControl
from light_widget import LightWidget

class MainWindow(QMainWindow):
    start_acquisition_signal = Signal()
    stop_acquisition_signal = Signal()
    def __init__(self):
        super(MainWindow, self).__init__()
        #cctl = CameraControl() # test for syntax errors
        #del cctl
        loader = QUiLoader(self)
        file = QFile("./form.ui")
        file.open(QFile.ReadOnly)
        loader.registerCustomWidget(CameraControl)
        loader.registerCustomWidget(DataControl)
        loader.registerCustomWidget(LightWidget)
        self.ui = loader.load(file)
        file.close()
        self.setCentralWidget(self.ui)
        self.resize(self.ui.size())
        # self.ui = Ui_main()
        # self.ui.setupUi(self)
        atexit.register(self.cleanup)
        self.magnet_ctl = MagnetControl()
        self.meas_ctl = MeasurementControl()
        self.pump_ctl = PumpControl()

        self.connect_signals()
        
        self.show()
        

    def __del__(self):
        del self.ui.camera_prev

    def cleanup(self):
        del self

    def connect_signals(self):
        # Camera
        self.ui.btn_prev_st.clicked.connect(self.prev_start_pushed)
        self.ui.btn_set_roi.clicked.connect(self.ui.camera_prev.apply_roi)
        self.ui.btn_reset_roi.clicked.connect(self.ui.camera_prev.reset_roi)
        self.start_acquisition_signal.connect(self.ui.camera_prev.start_preview)
        self.stop_acquisition_signal.connect(self.ui.camera_prev.stop_preview)

        # Magnet
        self.ui.jogUpBtn.pressed.connect(self.magnet_ctl.jog_up_start)
        self.ui.jogDownBtn.pressed.connect(self.magnet_ctl.jog_down_start)
        self.ui.jogUpBtn.released.connect(self.magnet_ctl.motor_stop)
        self.ui.jogDownBtn.released.connect(self.magnet_ctl.motor_stop)
        self.ui.referenceBtn.clicked.connect(self.magnet_ctl.reference)
        self.ui.goBtn.clicked.connect(self.magnet_ctl.move_pos)
        self.ui.posSpinBox.valueChanged.connect(self.spin_box_val_changed) #lambda pos: self.magnet_ctl.set_mov_dist(int(pos)) or self.ui.posSlider.setValue(int(pos))
        self.ui.unitComboBox.currentTextChanged.connect(self.mag_mov_unit_changed)
        self.ui.posSlider.sliderMoved.connect(self.slider_moved) # lambda pos: self.ui.posLineEdit.setText(str(pos)) or self.ui.posSpinBox.setValue(float(pos))

    def load_ui(self):
        loader = QUiLoader()
        path = os.path.join(os.path.dirname(__file__), "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        loader.load(ui_file, self)
        ui_file.close()
    
    @Slot(str)
    def mag_mov_unit_changed(self, unit: str):
        self.magnet_ctl.set_mov_unit(unit)
        if unit == 'mm':
            self.ui.posSlider.setMaximum(3906) #max mm are 39.0625
            self.ui.posSlider.setTickInterval(100)
            self.ui.posSpinBox.setDecimals(2)
            self.ui.posSpinBox.setValue(self.magnet_ctl._lt_ctl.steps_to_mm(self.ui.posSpinBox.value()))
        elif unit == 'steps':
            self.ui.posSlider.setMaximum(50000)
            self.ui.posSlider.setTickInterval(1000)
            self.ui.posSpinBox.setDecimals(0)
            self.ui.posSpinBox.setValue(self.magnet_ctl._lt_ctl.mm_to_steps(self.ui.posSpinBox.value()))

    @Slot(float)
    def spin_box_val_changed(self, value: float):
        if self.ui.unitComboBox.currentText() == 'steps':
            self.magnet_ctl.set_mov_dist(int(value))
            self.ui.posSlider.setValue(int(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self.magnet_ctl.set_mov_dist(value)
            self.ui.posSlider.setValue(int(value*100))

    @Slot(int)
    def slider_moved(self, value: int):
        if self.ui.unitComboBox.currentText() == 'steps':
            self.ui.posSpinBox.setValue(float(value))
        elif self.ui.unitComboBox.currentText() == 'mm':
            self.ui.posSpinBox.setValue(float(value/100))

    @Slot()
    def prev_start_pushed(self, event):
        if self.ui.btn_prev_st.text() != 'Stop':
            self.start_acquisition_signal.emit()
            #self.ui.camera_prev.start_preview()
            self.ui.btn_prev_st.setText('Stop')
        else:
            #self.ui.camera_prev.stop_preview()
            self.stop_acquisition_signal.emit()
            self.ui.btn_prev_st.setText('Start')
