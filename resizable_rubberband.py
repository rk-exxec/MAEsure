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

from PySide2.QtWidgets import QWidget, QHBoxLayout, QSizeGrip, QRubberBand
from PySide2.QtGui import QPalette, QBrush
from PySide2.QtCore import Qt

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super(ResizableRubberBand, self).__init__(parent)

        #self.rubber_band = QRubberBand(QRubberBand.Rectangle, pixmap)
        self.setWindowFlags(Qt.SubWindow)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.grip1 = QSizeGrip(self)
        self.grip2 = QSizeGrip(self)
        self.layout.addWidget(self.grip1, 0, Qt.AlignLeft | Qt.AlignTop)
        self.layout.addWidget(self.grip2, 0, Qt.AlignRight | Qt.AlignBottom)
        	
        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)
        try:
            pal = QPalette()
            pal.setBrush(QPalette.Highlight, QBrush(Qt.red))
            self.rubberband.setPalette(pal)
        except:
            pass
        self.rubberband.move(0, 0)
        self.hide()
        self.rubberband.hide()
        # self.rubberband.show()
        # self.show()

    def resizeEvent(self, event):
        self.rubberband.resize(self.size())

    def show(self):
        self.rubberband.show()
        super().show()