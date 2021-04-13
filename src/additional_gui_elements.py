#     MAEsure is a program to measure the surface energy of MAEs via contact angle
#     Copyright (C) 2021  Raphael Kriegl

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

from PySide2.QtCore import QCoreApplication, QObject, QRect
from PySide2.QtGui import Qt
from PySide2.QtWidgets import QDialog, QFrame, QLineEdit, QPlainTextEdit, QPushButton, QVBoxLayout


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)
        self.setupUI()

        # Add button signal to greetings slot
        self.okButton.clicked.connect(self.hide)

        self.show()


    def setupUI(self):
        self.resize(431, 260)
        self.licenseText = QPlainTextEdit(self)
        self.licenseText.setObjectName(u"licenseText")
        self.licenseText.setEnabled(True)
        self.licenseText.setGeometry(QRect(10, 10, 411, 211))
        self.licenseText.setFrameShape(QFrame.StyledPanel)
        self.licenseText.setFrameShadow(QFrame.Sunken)
        self.licenseText.setUndoRedoEnabled(False)
        self.licenseText.setTextInteractionFlags(Qt.NoTextInteraction)
        self.okButton = QPushButton(self)
        self.okButton.setObjectName(u"okButton")
        self.okButton.setGeometry(QRect(350, 230, 75, 23))

        self.retranslateUi()
    # setupUi

    def retranslateUi(self):
        self.setWindowTitle(QCoreApplication.translate("about", u"About MAEsure", None))
        self.licenseText.setPlainText(QCoreApplication.translate("about", u"MAEsure is a program to measure the surface energy of MAEs via contact angle\n"
"Copyright (C) 2021  Raphael Kriegl\n"
"\n"
"This program is free software: you can redistribute it and/or modify\n"
"it under the terms of the GNU General Public License as published by\n"
"the Free Software Foundation, either version 3 of the License, or\n"
"(at your option) any later version.\n"
"\n"
"This program is distributed in the hope that it will be useful,\n"
"but WITHOUT ANY WARRANTY; without even the implied warranty of\n"
"MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the\n"
"GNU General Public License for more details.\n"
"\n"
"You should have received a copy of the GNU General Public License\n"
"along with this program.  If not, see <https://www.gnu.org/licenses/>.", None))
        self.licenseText.setPlaceholderText("")
        self.okButton.setText(QCoreApplication.translate("about", u"OK", None))
    # retranslateUi

    

