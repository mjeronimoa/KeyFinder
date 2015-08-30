from pip.utils import ui

__author__ = 'Miguel'

# !/usr/bin/python
import sys
from PyQt5 import QtCore, QtGui, QtWidgets, uic  # works for pyqt5
from PyQt5.QtCore import QObject, pyqtSignal
import time
import datetime
import urllib.request
import re


class UIData(QObject):
    urlSearch = ""
    pattern = ""
    refreshRate = 100;

    stopSearch = pyqtSignal()


class Communicate(QObject):
    increaseAttempt = pyqtSignal()
    codeFound = pyqtSignal(str)


class SearchThread(QtCore.QThread):
    def __init__(self, UIData):
        QtCore.QThread.__init__(self)
        self.c = Communicate()
        self.hasToStop = False
        self.uiData = UIData
        self.uiData.stopSearch.connect(self.stop)
        self.codeLocalDataBase = set()

    def __del__(self):
        self.wait()

    def stop(self):
        self.hasToStop = True

    def run(self):
        while not self.hasToStop:
            req = urllib.request.Request(self.uiData.urlSearch)
            resp = urllib.request.urlopen(req)
            respData = resp.read()

            results = re.findall(self.uiData.pattern, str(respData))

            for result in results:
                if result not in self.codeLocalDataBase:
                    self.codeLocalDataBase.add(result)
                    self.c.codeFound.emit(result)



            self.c.increaseAttempt.emit()
            time.sleep(self.uiData.refreshRate)


form_class = uic.loadUiType("mainwindow.ui")[0]  # Load the UI


class MyWindowClass(QtWidgets.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.pushButtonStart.clicked.connect(self.startCliked)  # Bind the event handlers
        self.setFixedSize(self.size())  # block resizing

        self.uiData = UIData()
        self.codeDataBase = set()
        self.attempts = 0
        self.lineEditUrlSearch.setText("http://www.wepaste.com/m_jero/")
        self.lineEditRegularExpression.setText("([A-Z|0-9]{4}-[A-Z|0-9]{4}-[A-Z|0-9]{4}-[A-Z|0-9]{4})")

    def startCliked(self):
        if self.pushButtonStart.text() == "Start":
            self.uiData.urlSearch = self.lineEditUrlSearch.text()
            self.uiData.pattern = self.lineEditRegularExpression.text()
            self.uiData.refreshRate = self.spinBoxRefresh.value() / 1000

            self.searchThread = SearchThread(self.uiData)
            self.searchThread.c.increaseAttempt.connect(self.updateAttempts)
            self.searchThread.c.codeFound.connect(self.receiveCode)
            self.searchThread.start()
            self.pushButtonStart.setText("Stop")
        else:
            self.uiData.stopSearch.emit()
            self.pushButtonStart.setText("Start")

    def updateAttempts(self):
        self.attempts += 1
        self.statusBar().showMessage('Attempts: ' + str(self.attempts))

    def receiveCode(self, code):
        if code not in self.codeDataBase:
            self.codeDataBase.add(code)
            self.writeTrace("Code: " + code + " found")

    def writeTrace(self, text):
        ts = time.time()
        textTime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        trace = textTime + " - " + text
        item = QtWidgets.QListWidgetItem(trace)
        self.listLog.addItem(item)
        return


app = QtWidgets.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
