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


from PySide2.QtWidgets import QGroupBox
import pumpy

from serial.tools.list_ports_windows import comports

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

# TODO Pump control https://www.hugo-sachs.de/media/manuals/Product%20Manuals/702220,%202225%20Microliter%20Manual.pdf
class PumpControl(QGroupBox):
    def __init__(self, parent=None) -> None:
        super(PumpControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        port = self.find_com_port()
        self._context_depth = 0
        chain = pumpy.Chain(port)
        self._pump = pumpy.PHD2000(chain, name='Drplt_Pump')
        # FIXME syringe properties
        self._pump.setdiameter(1)
        self._pump.setflowrate(120) # 2ul / s

    def connect_signals(self):
        self.ui.dispenseBtn.clicked.connect(self.infuse)
        self.ui.collectBtn.clicked.connect(self.withdraw)
        self.ui.fillBtn.clicked.connect(self.fill)
        self.ui.emptyBtn.clicked.connect(self.empty)
        self.ui.stopPumpBtn.clicked.connect(self.stop)

    def fill(self):
        # caution! only use if limitswitches are properly setup to avoid damage to syringe
        self._pump.settargetvolume(1000)
        self._pump.withdraw()

    def empty(self):
        # caution! only use if limitswitches are properly setup to avoid damage to syringe
        self._pump.settargetvolume(1000)
        self._pump.infuse()

    def infuse(self):
        amount = self.ui.amountSpinBox.value()
        self._pump.settargetvolume(amount)
        self._pump.infuse()

    def withdraw(self):
        amount = self.ui.amountSpinBox.value()
        self._pump.settargetvolume(amount)
        self._pump.withdraw()

    def stop(self):
        self._pump.stop()

    @staticmethod
    def find_com_port() -> str:
        lst = comports()
        for port in lst:
            # FIXME apply proper name when pump arrives
            if port.manufacturer == 'Nanotec':
                return port.device
        else:
            raise ConnectionError('No Pump found!')