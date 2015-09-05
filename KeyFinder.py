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
import xml.etree.ElementTree as ET


class UIData(QObject):
    urlSearch = ""
    pattern = ""
    refreshRate = 100;
    threads = 1

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
        self.comboProfiles.currentIndexChanged[str].connect(self.loadProfile)
        self.setFixedSize(self.size())  # block resizing

        tree = ET.parse('profiles.xml')
        root = tree.getroot()

        self.uiData = UIData()
        self.searchThread = []
        self.codeDataBase = set()
        self.attempts = 0
        self.profiles = {'': UIData()}
        self.comboProfiles.addItem("")

        for profile in root.findall('profile'):
            profileData = UIData()
            self.comboProfiles.addItem(profile.get('name'))
            profileData.urlSearch = profile.find('urlSearch').text
            profileData.pattern = profile.find('pattern').text
            self.profiles[profile.get('name')] = profileData

    def validate(self):
        if not self.lineEditUrlSearch.text():
            self.statusBar().showMessage("URL Search is mandatory")
            return False

        if not self.lineEditRegularExpression.text():
            self.statusBar().showMessage("Regular Expression is mandatory")
            return False

        return True

    def readInput(self):
        self.uiData.urlSearch = self.lineEditUrlSearch.text()
        self.uiData.pattern = self.lineEditRegularExpression.text()
        self.uiData.refreshRate = self.spinBoxRefresh.value() / 1000
        self.uiData.threads = self.spinBoxThreads.value()

    def loadProfile(self, string):
        if self.profiles[string]:
            self.lineEditUrlSearch.setText(self.profiles[string].urlSearch)
            self.lineEditRegularExpression.setText(self.profiles[string].pattern)

    def startCliked(self):
        if self.pushButtonStart.text() == "Start":
            if self.validate():
                self.readInput()
                for threadNumber in range(0, self.uiData.threads):
                    del self.searchThread[:]
                    self.searchThread.append(SearchThread(self.uiData))
                    self.searchThread[threadNumber].c.increaseAttempt.connect(self.updateAttempts)
                    self.searchThread[threadNumber].c.codeFound.connect(self.receiveCode)
                    self.searchThread[threadNumber].start()

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
