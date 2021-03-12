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


from PySide2.QtWidgets import QGroupBox
import pumpy
import logging
from pump import Microliter
from serial.tools.list_ports_windows import comports

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ui_form import Ui_main

# TODO Pump control https://www.hugo-sachs.de/media/manuals/Product%20Manuals/702220,%202225%20Microliter%20Manual.pdf
# TODO error handling when no pump available!
# TODO put settings in extra dialog?

class PumpControl(QGroupBox):
    """
    provides a grupbox with UI to control the pump 
    """
    def __init__(self, parent=None) -> None:
        super(PumpControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        port = self.find_com_port()
        self._context_depth = 0
        logging.debug("initialize pump")
        try:
            chain = pumpy.Chain(port)
            self._pump = pumpy.Microliter(chain, name='Pump')
        except Exception as ex:
           self._pump = None
           logging.warning('Pump Error:' + str(ex))

    def showEvent(self, event):
        self._pump.stop()
        self._pump.setdiameter(self.ui.diamSpinBox.value())
        self._pump.setflowrate(self.ui.flowSpinBox.value()) # 2ul / s
        self.connect_signals()

    def connect_signals(self):
        self.ui.dispenseBtn.clicked.connect(self.infuse)
        self.ui.collectBtn.clicked.connect(self.withdraw)
        self.ui.fillBtn.clicked.connect(self.fill)
        self.ui.emptyBtn.clicked.connect(self.empty)
        self.ui.stopPumpBtn.clicked.connect(self.stop)
        self.ui.syringeApplyBtn.clicked.connect(self.apply_settings)

    def fill(self):
        """ Pump will fill the current syringe to max level

        **Caution!** only use if limitswitches are properly setup to avoid damage to syringe
        """
        logging.info("filling syringe")
        self._pump.settargetvolume(1000)
        self._pump.withdraw()

    def empty(self):
        """ Pump will empty syringe completely  

        **Caution!** only use if limitswitches are properly setup to avoid damage to syringe
        """
        logging.info("emptying syringe")
        self._pump.settargetvolume(1000)
        self._pump.infuse()

    def infuse(self):
        """ Pump will move plunger down until specified volume is displaced """
        amount = self.ui.amountSpinBox.value()
        logging.info(f"pump: infusing {amount} ul")
        self._pump.settargetvolume(amount)
        self._pump.infuse()

    def withdraw(self):
        """ Pump will move plunge up until specified volume is gained """
        amount = self.ui.amountSpinBox.value()
        logging.info(f"pump: withdrawing {amount} ul")
        self._pump.settargetvolume(amount)
        self._pump.withdraw()

    def apply_settings(self):
        """ read the values from the ui and apply them to the pump """
        self._pump.setdiameter(self.ui.diamSpinBox.value())
        self._pump.setflowrate(self.ui.flowSpinBox.value())
        logging.info(f"set syringe diameter to {self.ui.diamSpinBox.value()} mm, flowrate to {self.ui.flowSpinBox.value()} ul/m")

    def stop(self):
        """ Immediately stop the pump """
        self._pump.stop()

    @staticmethod
    def find_com_port() -> str:
        """ find the comport the pump is connected to """
        lst = comports()
        for port in lst:
            if port.manufacturer == 'Prolific':
                return port.device
        # else:
        #     raise ConnectionError('No Pump found!')