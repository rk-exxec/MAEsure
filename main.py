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

import sys
from PySide2.QtGui import QPixmap, Qt
from PySide2.QtWidgets import QApplication, QSplashScreen

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pic = QPixmap('qt_resources/maesure.png')
    splash = QSplashScreen(pic, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    splash.setMask(pic.mask())
    splash.show()
    app.processEvents()
    from main_window import MainWindow
    widget = MainWindow()
    #widget.show()
    splash.finish(widget)
    sys.exit(app.exec_())
