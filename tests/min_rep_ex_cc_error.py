import sys
from types import FrameType
import cv2
import numpy as np

from PySide2 import QtGui, QtWidgets
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

class CameraControl(QLabel):
    change_pixmap_signal = Signal(np.ndarray)
    def __init__(self, parent=None):
        super(CameraControl, self).__init__(parent)
        self._double_buffer: QPixmap = None
        self._first_show = True # whether form is shown for the first time
        self._is_running = False
        self._image_size = 0
        self.change_pixmap_signal.connect(self.update_image)
        self.update()
        self._use_test_image = True
        self._test_image: np.ndarray = None
        
    def __del__(self):
        del self._double_buffer

    def showEvent(self, event):
        if self._first_show:
            if self._use_test_image:
                self._set_image('./untitled1.png')
            self._first_show = False

    def paintEvent(self, event: QPaintEvent):
        # completely override super.paintEvent() to use double buffering
        painter = QPainter(self)
        #painter.setRenderHint(QPainter.Antialiasing)
        self.drawFrame(painter)
        # using a pixmap and separate painter for content do avoid flicker
        if self._double_buffer is None:
            self._double_buffer = QPixmap(self.width(), self.height())
        self._double_buffer.fill(Qt.black)
        db_painter = QPainter(self._double_buffer)
        db_painter.setRenderHint(QPainter.Antialiasing)
        # calculate offset and scale of droplet image pixmap
        scale_x, scale_y, offset_x, offset_y = self.getFromImageScaling()
        db_painter.setBackground(QBrush(Qt.black))
        db_painter.setPen(QPen(Qt.black,0))
        db_painter.drawPixmap(offset_x, offset_y, self.pixmap())

        # painting the buffer pixmap to screen
        painter.drawPixmap(0, 0, self._double_buffer)
        db_painter.end()
        painter.end()

    def _set_image(self, file):
        img = cv2.imread(file)
        if self._use_test_image:
            self._test_image = img
        self.change_pixmap_signal.emit(img)

    @Slot(np.ndarray)
    def update_image(self, cv_img: np.ndarray):
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            qt_img = self._convert_cv_qt(cv_img)
            self.setPixmap(qt_img)
            self._image_size = np.shape(cv_img)
        except Exception:
            pass

    def _convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size(), Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def getFromImageScaling(self):
        """ Gets the scale and offset for a Image to QLabel coordinate transform """
        pix_rect = self.pixmap().size()
        scale_x = float(pix_rect.width() / self._image_size[1])
        offset_x = int(abs(pix_rect.width() - self.width())/2)
        scale_y = float(pix_rect.height() / self._image_size[0])
        offset_y = int(abs(pix_rect.height() - self.height())/2)
        return scale_x, scale_y, offset_x, offset_y

class Ui_main(QMainWindow):
    def setupUi(self, main):
        if not main.objectName():
            main.setObjectName(u"main")
        main.resize(500, 380)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(main.sizePolicy().hasHeightForWidth())
        main.setSizePolicy(sizePolicy)
        self.centralwidget = QWidget(main)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.camera_prev = CameraControl(self.centralwidget)
        self.camera_prev.setObjectName(u"camera_prev")
        self.camera_prev.setGeometry(QRect(10, 10, 480, 360))
        self.camera_prev.setMinimumSize(QSize(0, 0))
        self.camera_prev.setBaseSize(QSize(640, 480))
        self.camera_prev.setMouseTracking(True)
        self.camera_prev.setAutoFillBackground(True)
        self.camera_prev.setFrameShape(QFrame.Panel)
        self.camera_prev.setPixmap(QPixmap(u"untitled1.png"))
        self.camera_prev.setScaledContents(False)
        self.camera_prev.setAlignment(Qt.AlignCenter)
        main.setCentralWidget(self.centralwidget)
        self.retranslateUi(main)

        QMetaObject.connectSlotsByName(main)
    # setupUi

    def retranslateUi(self, main):
        main.setWindowTitle(QCoreApplication.translate("main", u"main", None))
        self.camera_prev.setText("")
    # retranslateUi


if __name__=='__main__':
    app = QApplication()
    widget = QMainWindow()
    widget.ui = Ui_main()
    widget.ui.setupUi(widget)
    widget.show()
    sys.exit(app.exec_())

