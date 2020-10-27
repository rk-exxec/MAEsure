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

import functools
from PySide2.QtWidgets import QGroupBox
import serial
import time

from serial.tools.list_ports_windows import comports

from typing import TYPE_CHECKING, ValuesView
if TYPE_CHECKING:
    from ui_form import Ui_main

# TODO Pump control https://www.hugo-sachs.de/media/manuals/Product%20Manuals/702220,%202225%20Microliter%20Manual.pdf
# TODO see about serial port timout handling, lock self up til reset?
class PumpControl(QGroupBox):
    def __init__(self, parent=None) -> None:
        super(PumpControl, self).__init__(parent)
        self.ui: Ui_main = self.window().ui
        self._serial_port = serial.Serial()
        try:
            self._serial_port.port = self.find_com_port()
        except ConnectionError as ce:
            self._serial_port.port = 'COM6'

        self._serial_port.baudrate = 9600
        self._serial_port.timeout = 0.2
        self._serial_port.bytesize = 8
        self._serial_port.stopbits = 2
        self._serial_port.parity = 'N'
        self._context_depth = 0

    def __enter__(self):
        try:
            if self._context_depth == 0 and self._serial_port.port is not None:
                self._serial_port.open()
        except Exception as ex:
            raise  
        self._context_depth += 1
        return self

    def __exit__(self, type, value, traceback):
        self._context_depth -= 1
        if self._context_depth == 0:
            self._serial_port.close()

    def query_num(self, query: str):
        # TODO query dict with response lengths
        # TODO possible to only send CR to get status?
        # TODO use pumpy?
        queries = ['DIA', 'RAT', 'RAT W', 'VOL', 'VOL W', 'VER', 'TAR', 'TAR W', 'FRC']
        if not query in queries:
            raise ValueError('Unknown query command')
        resp_length = queries[query]
        if self._serial_port.is_open:
            msg: str = query + '\r'
            self._serial_port.write(msg.encode())
            # TODO this does not get the PROMPT bc that starts with CRLF?
            ans = self._serial_port.read(resp_length).decode('utf-8')

            if len(ans) == 0:
                raise TimeoutError('Port Timeout!')
            else:
                return ans.strip()
        else: return 0

    def is_port_alive(self):
        pass

    @staticmethod
    def find_com_port() -> str:
        lst = comports()
        for port in lst:
            if port.manufacturer == 'Nanotec':
                return port.device
        else:
            raise ConnectionError('No Pump found!')