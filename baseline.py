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


from PySide2.QtWidgets import QWidget, QHBoxLayout
from PySide2.QtGui import QPainter, QPen
from PySide2.QtCore import Qt, QPoint

class Baseline(QWidget):
    def __init__(self, parent=None):
        super(Baseline, self).__init__(parent)
        #self.setWindowFlags(Qt.SubWindow)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.SizeVerCursor)
        self.origin = QPoint(0,0)
        self._first_show = True
        self._y_level = 0
        self._max_level: int = 10000
        self._min_level: int = 0
        self.show()

    @property
    def y_level(self) -> int:
        # y1 = self.mapToParent(self.pos()).y()
        # y2 = self.height()
        return self._y_level

    @y_level.setter
    def y_level(self, level):
        self._y_level = level
        if level > self._min_level and level < self._max_level:
            self.move(QPoint(self.x(), level - self.height()/2))
        elif level < self._min_level:
            self.move(QPoint(self.x(), self._min_level))
        elif level > self._max_level:
            self.move(QPoint(self.x(), self._max_level))

    @property
    def max_level(self):
        return self._max_level + self.height()/2

    @max_level.setter
    def max_level(self, level):
        self._max_level = level - self.height()/2

    @property
    def min_level(self):
        return self._min_level + self.height()/2

    @min_level.setter
    def min_level(self, level):
        self._min_level = level - self.height()/2

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        #painter.beginNativePainting()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.gray, 1))
        x1,y1,x2,y2 = self.rect().getCoords()
        painter.drawRect(self.rect())
        painter.setPen(QPen(Qt.blue, 2))
        painter.drawLine(QPoint(x1, y1+(y2-y1)/2), QPoint(x2, y1+(y2-y1)/2))
        #painter.endNativePainting()
        painter.end()

    def showEvent(self, event):
        if self._first_show:
            self.setGeometry(0, self.parent().geometry().height() - 10, self.parent().geometry().width(), 20)
            self.max_level = self.parent().geometry().height() - self.height()
            self._first_show = False

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.globalPos() - self.pos()

    def mouseReleaseEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            #new_y = event.globalPos().y() - self.origin.y()
            self.y_level = event.globalPos().y() - self.origin.y() + self.height()/2