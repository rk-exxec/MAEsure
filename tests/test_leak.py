 
from PySide2.QtCore import QObject, QRect, QSize, QTimer, Qt, Signal, Slot
from PySide2 import QtGui
from PySide2.QtGui import QPixmap
from PySide2.QtWidgets import QApplication
import cv2
import numpy as np
import sys
import gc


class Test(QObject):   
    update_signal = Signal(np.ndarray, bool)
    def __init__(self):
        super(Test, self).__init__()
        self.update_signal.connect(self.update_image)
        self._pixmap = None
        self.size = QSize(700,500)

    @Slot(np.ndarray, bool)
    def update_image(self, cv_img: np.ndarray, eval: bool = True):
        #FIXME memory leak in here
        """ Updates the image_label with a new opencv image"""
        #print(np.shape(cv_img))
        try:
            self._pixmap = self._convert_cv_qt(cv_img)
        except Exception as ex:
            print(str(ex))
            input()

    def _convert_cv_qt(self, cv_img: np.ndarray):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        #h, w, ch = rgb_image.shape
        h, w, ch = cv_img.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(cv_img, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return QPixmap.fromImage(p)

if __name__=="__main__":
    app = QApplication(sys.argv)
    test = Test()
    #arr = np.zeros(shape=(2000,1500,3))
    arr:np.ndarray = cv2.imread('untitled1.png')
    _timer = QTimer()
    _timer.setInterval(1)
    _timer.setSingleShot(False)
    _timer.timeout.connect(lambda: test.update_signal.emit(arr,False))
    _timer.start()
    sys.exit(app.exec_())
