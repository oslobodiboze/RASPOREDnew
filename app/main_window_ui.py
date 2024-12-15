# Form implementation generated from reading ui file 'main_window.ui'
#
# Created by: PyQt6 UI code generator 6.7.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt6 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 400)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.centralLayout.setObjectName("centralLayout")
        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.buttonLayout.setObjectName("buttonLayout")
        self.loadButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.loadButton.setObjectName("loadButton")
        self.buttonLayout.addWidget(self.loadButton)
        self.saveButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.saveButton.setEnabled(False)
        self.saveButton.setObjectName("saveButton")
        self.buttonLayout.addWidget(self.saveButton)
        self.editButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.editButton.setEnabled(False)
        self.editButton.setObjectName("editButton")
        self.buttonLayout.addWidget(self.editButton)
        self.uploadButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.uploadButton.setEnabled(False)
        self.uploadButton.setObjectName("uploadButton")
        self.buttonLayout.addWidget(self.uploadButton)
        self.closeButton = QtWidgets.QPushButton(parent=self.centralwidget)
        self.closeButton.setObjectName("closeButton")
        self.buttonLayout.addWidget(self.closeButton)
        self.centralLayout.addLayout(self.buttonLayout)
        self.messageLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.messageLabel.setText("")
        self.messageLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.messageLabel.setObjectName("messageLabel")
        self.centralLayout.addWidget(self.messageLabel)
        self.fileListLayout = QtWidgets.QVBoxLayout()
        self.fileListLayout.setObjectName("fileListLayout")
        self.fileListLabel = QtWidgets.QLabel(parent=self.centralwidget)
        self.fileListLabel.setObjectName("fileListLabel")
        self.fileListLayout.addWidget(self.fileListLabel)
        self.excelListWidget = QtWidgets.QListWidget(parent=self.centralwidget)
        self.excelListWidget.setObjectName("excelListWidget")
        self.fileListLayout.addWidget(self.excelListWidget)
        self.centralLayout.addLayout(self.fileListLayout)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusBar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusBar.setObjectName("statusBar")
        MainWindow.setStatusBar(self.statusBar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Excel to XMLTV Converter/Editor - DIADORA TV"))
        self.loadButton.setText(_translate("MainWindow", "Učitaj Excel datoteku"))
        self.saveButton.setText(_translate("MainWindow", "Spremi kao XMLTV datoteku"))
        self.editButton.setText(_translate("MainWindow", "Uredi Excel datoteku"))
        self.uploadButton.setText(_translate("MainWindow", "Pošalji na FTP"))
        self.closeButton.setText(_translate("MainWindow", "Izlaz"))
        self.fileListLabel.setText(_translate("MainWindow", "Spremljene Excel datoteke:"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
