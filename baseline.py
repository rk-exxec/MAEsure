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

# TODO baseline set max and min according to image
class Baseline(QWidget):
    def __init__(self, parent=None):
        super(Baseline, self).__init__(parent)
        #self.setWindowFlags(Qt.SubWindow)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.SizeVerCursor)
        self.origin = QPoint(0,0)
        self.setGeometry(0, parent.geometry().height() - 10, parent.geometry().width(), 20)
        self.show()

    def get_y_level(self):
        x1,y1 = self.mapToParent(self.pos()).toTuple()
        y2 = self.height()
        return int(y1+(y2-y1)/2)

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
        self.resize(self.parent().geometry().width(), 20)

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.globalPos() - self.pos()

    def mouseReleaseEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            new_y = event.globalPos().y() - self.origin.y()
            if new_y > 0 and new_y < (self.parent().geometry().height() - self.height()):
                self.move(QPoint(self.x(), new_y))