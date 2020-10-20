import random, sys
from PySide2.QtCore import QPoint, QRect, QSize, Qt
from PySide2.QtWidgets import *
from PySide2.QtGui import *

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
        self.rubberband.move(0, 0)
        self.rubberband.show()
        self.show()

    def resizeEvent(self, event):
        self.rubberband.resize(self.size())

class Window(QLabel):

    def __init__(self, parent = None):
    
        QLabel.__init__(self, parent)
        self.rubberBand = ResizableRubberBand(self)
        self.origin = QPoint()
    
    def mousePressEvent(self, event):
    
        if event.button() == Qt.LeftButton:
        
            self.origin = QPoint(event.pos())
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
    
    def mouseMoveEvent(self, event):
    
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter:
            print(str(self.rubberBand.pos()))
            print(str(self.rubberBand.size()))
            self.rubberBand.hide()


def create_pixmap():

    def color():
        r = random.randrange(0, 255)
        g = random.randrange(0, 255)
        b = random.randrange(0, 255)
        return QColor(r, g, b)
    
    def point():
        return QPoint(random.randrange(0, 400), random.randrange(0, 300))
    
    pixmap = QPixmap(400, 300)
    pixmap.fill(color())
    painter = QPainter()
    painter.begin(pixmap)
    i = 0
    while i < 1000:
        painter.setBrush(color())
        painter.drawPolygon(QPolygon([point(), point(), point()]))
        i += 1
    
    painter.end()
    return pixmap


if __name__ == "__main__":

    app = QApplication(sys.argv)
    random.seed()
    
    window = Window()
    window.setPixmap(create_pixmap())
    window.resize(400, 300)
    window.show()
    
    sys.exit(app.exec_())