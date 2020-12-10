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
from PySide2.QtGui import QPainter, QPen
from PySide2.QtCore import Qt, QPoint

# FIXME broken handles

class ResizableRubberBand(QWidget):
    def __init__(self, parent=None):
        super(ResizableRubberBand, self).__init__(parent)
        self.setWindowFlag(Qt.SubWindow)
        self.setFocusPolicy(Qt.ClickFocus)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.SizeAllCursor)
        self.origin = QPoint()

        self.grip1 = QSizeGrip(self)
        self.grip2 = QSizeGrip(self)
        self.layout.addWidget(self.grip1, 0, Qt.AlignLeft | Qt.AlignTop)
        self.layout.addWidget(self.grip2, 0, Qt.AlignRight | Qt.AlignBottom)
        	
        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)

        self.rubberband.move(0, 0)
        self.hide()
        self.rubberband.hide()
        # self.rubberband.show()
        # self.show()

    def resizeEvent(self, event):
        self.rubberband.resize(self.size())

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.beginNativePainting()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(QPen(Qt.red, 3))
        painter.drawRect(self.rubberband.rect())
        painter.setPen(QPen(Qt.red, 1))
        x_begin = self.rubberband.x()
        x_half = self.rubberband.x() + self.rubberband.width()/2
        x_full = self.rubberband.x() + self.rubberband.width()
        y_begin = self.rubberband.y()
        y_half = self.rubberband.y() + self.rubberband.height()/2
        y_full = self.rubberband.y() + self.rubberband.height()
        points = [QPoint(x_half, y_begin),QPoint(x_half,y_full),QPoint(x_begin,y_half),QPoint(x_full,y_half)]
        painter.drawLines(points)
        painter.endNativePainting()
        painter.end()
        

    # def moveEvent(self, event: QMoveEvent):
    #     self.rubberband.move(event.pos())

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.origin)

    # def show(self):
    #     self.rubberband.show()
    #     super().show()