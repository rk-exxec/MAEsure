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

from enum import Enum, auto
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Signal, Slot, Qt
from PySide2.QtGui import QPaintEvent, QPainter
 
class LightColor(Enum):
    DISCONNECTED = auto() #Qt.red
    CONNECTED = auto() #Qt.green
    ERROR = auto() #Qt.darkRed
    CONNECTING = auto() #Qt.yellow

class LightWidget(QWidget):
    def __init__(self, parent=None):
        super(LightWidget, self).__init__(parent)
        self._color = LightColor.DISCONNECTED

    def set_disconnected(self):
        self._color = LightColor.DISCONNECTED

    def set_connected(self):
        self._color = LightColor.CONNECTED

    def set_error(self):
        self._color = LightColor.ERROR

    def set_connecting(self):
        self._color = LightColor.CONNECTING

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self._color == LightColor.DISCONNECTED:
            painter.setBrush(Qt.red)
        elif self._color == LightColor.CONNECTED:
            painter.setBrush(Qt.green)
        elif self._color == LightColor.ERROR:
            painter.setBrush(Qt.darkRed)
        elif self._color == LightColor.CONNECTING:
            painter.setBrush(Qt.yellow)
        else:
            painter.setBrush(Qt.gray)
        painter.drawEllipse(0,0,self.width(), self.height())
        painter.end()


