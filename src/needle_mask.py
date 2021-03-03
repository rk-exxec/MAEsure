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
from PySide2.QtGui import QPainter, QPen, QResizeEvent
from PySide2.QtCore import Qt, QPoint, QRect

class DynamicNeedleMask(QWidget):
    """ 
    provides a rectangle with fixed centerline and x-symmetric resizability
    """
    _gripSize = 8
    def __init__(self, parent=None):
        super(DynamicNeedleMask, self).__init__(parent)
        self._first_show = False
        self.setWindowFlag(Qt.SubWindow)
        self.setFocusPolicy(Qt.ClickFocus)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCursor(Qt.SizeAllCursor)
        self.setGeometry(self.parent().width()/2-10, 0, 20, self.parent().height())
        self._old_geo = self.geometry()

        
        self.origin = QPoint(0,0)
        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)

        self.rubberband.move(0, 0)
        self.hide()
        self.rubberband.hide()
        # self.rubberband.show()
        # self.show()
        self.sideGrips = [
            SideGrip(self, Qt.LeftEdge), 
            SideGrip(self, Qt.TopEdge), 
            SideGrip(self, Qt.RightEdge), 
            SideGrip(self, Qt.BottomEdge), 
        ]
        # corner grips should be "on top" of everything, otherwise the side grips
        # will take precedence on mouse events, so we are adding them *after*;
        # alternatively, widget.raise_() can be used
        self.cornerGrips = [QSizeGrip(self) for i in range(4)]

    def showEvent(self, event):
        """
        custom show event

        initializes geometry for first show
        """
        if self._first_show:
            self.setGeometry(self.parent().geometry().width()/4, 0, self.parent().geometry().width()/2, self.parent().geometry().height())
            self._first_show = False

    @property
    def gripSize(self):
        return self._gripSize

    def setGripSize(self, size):
        if size == self._gripSize:
            return
        self._gripSize = max(2, size)
        self.updateGrips()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.beginNativePainting()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setPen(QPen(Qt.green, 1, Qt.DotLine))
        painter.drawRect(self.rubberband.rect())
        painter.setPen(QPen(Qt.green, 1))
        x_begin = self.rubberband.x()
        x_half = self.rubberband.x() + self.rubberband.width()/2
        x_full = self.rubberband.x() + self.rubberband.width()
        y_begin = self.rubberband.y()
        y_half = self.rubberband.y() + self.rubberband.height()/2
        y_full = self.rubberband.y() + self.rubberband.height()
        points = [QPoint(x_half, y_begin),QPoint(x_half,y_full)]
        painter.drawLines(points)
        painter.endNativePainting()
        painter.end()

    def resizeEvent(self, event: QResizeEvent):
        x,y,w,h = self.geometry().normalized().getRect()
        ox,oy,ow,oh = self._old_geo.normalized().getRect()
        if(ox != x):
            # resize left side
            x = ox + round((x - ox)/2)
        else:
            # resize right side
            x = x - round((w - ow)/2) # keep middle line steady
        y = 0
        self.setGeometry(min(x,self.parent().width()), y, min(w, self.parent().width() - x), self.parent().height())
        self.updateGrips()
        self.rubberband.resize(self.size())
        self._old_geo = self.geometry()
        
        
    def updateGrips(self):
        self.setContentsMargins(*[self.gripSize] * 4)

        outRect = self.rect()
        # an "inner" rect used for reference to set the geometries of size grips
        inRect = outRect.adjusted(self.gripSize, self.gripSize,
            -self.gripSize, -self.gripSize)

        # top left
        self.cornerGrips[0].setGeometry(
            QRect(outRect.topLeft(), inRect.topLeft()))
        # top right
        self.cornerGrips[1].setGeometry(
            QRect(outRect.topRight(), inRect.topRight()).normalized())
        # bottom right
        self.cornerGrips[2].setGeometry(
            QRect(inRect.bottomRight(), outRect.bottomRight()))
        # bottom left
        self.cornerGrips[3].setGeometry(
            QRect(outRect.bottomLeft(), inRect.bottomLeft()).normalized())

        # left edge
        self.sideGrips[0].setGeometry(
            0, inRect.top(), self.gripSize, inRect.height())
        # top edge
        self.sideGrips[1].setGeometry(
            inRect.left(), 0, inRect.width(), self.gripSize)
        # right edge
        self.sideGrips[2].setGeometry(
            inRect.left() + inRect.width(), 
            inRect.top(), self.gripSize, inRect.height())
        # bottom edge
        self.sideGrips[3].setGeometry(
            self.gripSize, inRect.top() + inRect.height(), 
            inRect.width(), self.gripSize)

    # def moveEvent(self, event: QMoveEvent):
    #     self.rubberband.move(event.pos())

    def mousePressEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.origin = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos().x() - self.origin.x(),0)


    # def show(self):
    #     self.rubberband.show()
    #     super().show()

# https://stackoverflow.com/questions/62807295/how-to-resize-a-window-from-the-edges-after-adding-the-property-qtcore-qt-framel
class SideGrip(QWidget):
    def __init__(self, parent, edge):
        QWidget.__init__(self, parent)
        if edge == Qt.LeftEdge:
            self.setCursor(Qt.SizeHorCursor)
            self.resizeFunc = self.resizeLeft
        elif edge == Qt.TopEdge:
            self.setCursor(Qt.SizeVerCursor)
            self.resizeFunc = self.resizeTop
        elif edge == Qt.RightEdge:
            self.setCursor(Qt.SizeHorCursor)
            self.resizeFunc = self.resizeRight
        else:
            self.setCursor(Qt.SizeVerCursor)
            self.resizeFunc = self.resizeBottom
        self.mousePos = None

    def resizeLeft(self, delta):
        parent = self.parent()
        width = max(parent.minimumWidth(), parent.width() - delta.x())
        geo = parent.geometry()
        geo.setLeft(geo.right() - width)
        parent.setGeometry(geo)

    def resizeTop(self, delta):
        parent = self.parent()
        height = max(parent.minimumHeight(), parent.height() - delta.y())
        geo = parent.geometry()
        geo.setTop(geo.bottom() - height)
        parent.setGeometry(geo)

    def resizeRight(self, delta):
        parent = self.parent()
        width = max(parent.minimumWidth(), parent.width() + delta.x())
        parent.resize(width, parent.height())

    def resizeBottom(self, delta):
        parent = self.parent()
        height = max(parent.minimumHeight(), parent.height() + delta.y())
        parent.resize(parent.width(), height)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.mousePos = event.pos()

    def mouseMoveEvent(self, event):
        if self.mousePos is not None:
            delta = event.pos() - self.mousePos
            self.resizeFunc(delta)

    def mouseReleaseEvent(self, event):
        self.mousePos = None
