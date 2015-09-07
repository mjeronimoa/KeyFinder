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
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions


class UIData(QObject):
    urlSearch = ""
    pattern = ""
    urlOutput = ""
    outputRemove = ""
    outputField = ""
    failWord = ""
    refreshRate = 100
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
            profileData.urlOutput = profile.find('urlOutput').text
            profileData.threads = profile.find('threads').text
            profileData.refreshRate = profile.find('refreshRate').text
            profileData.outputRemove = profile.find('outputRemove').text
            profileData.outputField = profile.find('outputField').text
            profileData.failWord = profile.find('failWord').text

            self.profiles[profile.get('name')] = profileData

    def validate(self):
        if not self.lineEditUrlSearch.text():
            self.statusBar().showMessage("URL Search is mandatory")
            return False

        if not self.lineEditRegularExpression.text():
            self.statusBar().showMessage("Regular Expression is mandatory")
            return False

        if not self.lineEditUrlOutput.text():
            self.statusBar().showMessage("Url Output is mandatory")
            return False

        if not self.lineEditOutpuField.text():
            self.statusBar().showMessage("Output field is mandatory")
            return False

        return True

    def readInput(self):
        self.uiData.urlSearch = self.lineEditUrlSearch.text()
        self.uiData.pattern = self.lineEditRegularExpression.text()
        self.uiData.urlOutput = self.lineEditUrlOutput.text()
        self.uiData.outputRemove = self.lineEditOutputRemove.text()
        self.uiData.outputField = self.lineEditOutpuField.text()
        self.uiData.failWord = self.lineEditFailWord.text()
        self.uiData.refreshRate = self.spinBoxRefresh.value() / 1000
        self.uiData.threads = self.spinBoxThreads.value()

    def loadProfile(self, string):
        if self.profiles[string]:
            self.lineEditUrlSearch.setText(self.profiles[string].urlSearch)
            self.lineEditRegularExpression.setText(self.profiles[string].pattern)
            self.lineEditUrlOutput.setText(self.profiles[string].urlOutput)
            self.lineEditOutputRemove.setText(self.profiles[string].outputRemove)
            self.lineEditOutpuField.setText(self.profiles[string].outputField)
            self.lineEditFailWord.setText(self.profiles[string].failWord)
            self.spinBoxRefresh.setValue(int(self.profiles[string].refreshRate))
            self.spinBoxThreads.setValue(int(self.profiles[string].threads))

    def startCliked(self):
        if self.pushButtonStart.text() == "Start":
            if self.validate():
                self.readInput()
                self.openExplorer()
                del self.searchThread[:]
                for threadNumber in range(0, self.uiData.threads):
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
            self.validateCode(code)

    def validateCode(self, code):
        if self.uiData.outputRemove:
            code = code.replace(self.uiData.outputRemove, '')

        self.browser.find_element_by_id(self.uiData.outputField).send_keys(code)
        self.browser.find_element_by_id(self.uiData.outputField).send_keys(Keys.RETURN)
        self.writeTrace("Code: " + code + " introduced in output web")
        if self.uiData.failWord:
            old_page = self.browser.find_element_by_tag_name('html')
            WebDriverWait(self.browser, 3).until(expected_conditions.staleness_of(old_page))
            src = self.browser.page_source
            text_found = re.search(self.uiData.failWord, src)
            if text_found:
                self.writeTrace("Code: " + code + " FAILED")
            else:
                self.writeTrace("Code: " + code + " ACCEPTED")

    def writeTrace(self, text):
        ts = time.time()
        textTime = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        trace = textTime + " - " + text
        item = QtWidgets.QListWidgetItem(trace)
        self.listLog.addItem(item)
        return

    def openExplorer(self):
        path_to_chromedriver = './chromedriver' # change path as needed
        self.browser = webdriver.Chrome(executable_path = path_to_chromedriver)
        self.browser.get(self.uiData.urlOutput)


#Main Program

app = QtWidgets.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
