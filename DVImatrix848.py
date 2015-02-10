#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright © 2014, IOhannes m zmölnig, IEM

# This file is part of HDMIports
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with DVImatrix848.  If not, see <http://www.gnu.org/licenses/>.
from PySide import QtGui, QtCore

import serial
import time

import ConfigParser


def getConfigFile():
    import os
    if os.name == "nt":
        from win32com.shell import shellcon, shell
        appdatadir=os.path.join(shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0),
                                "DVImatrix848")
    else:
        appdatadir = os.path.join(os.path.expanduser("~"), ".config", "DVImatrix848")
    if not os.path.isdir(appdatadir):
        os.mkdir(appdatadir)
    return os.path.join(appdatadir, "setup.ini")

class communicator(object):
    def __init__(self):
        super(communicator, self).__init__()
        self.serial=None
        self.connectTime=None

    def send(self, data, readback=None):
        ## 'readback' controls a subsequent 'read' operation
        ## - positive ints:
        print("TODO: write '%s'" % (data))
        return

        ## send data to the device
        ## will block if we have just opened the device

        if not self.serial or not self.connectTime:
                return None
        sleeptime=time.time() + 1 - self.connectTime
        if sleeptime > 0:
                time.sleep(sleeptime)
        self.serial.write(data)
        self.serial.flush() ## untested
        if readback is None:
            return None
        if readback is True:
            return ser.readline()
        if int(readback) > 0:
            return ser.read(int(readback))
        return None

    def connect(self, device):
        ## connects to another device
        ## if we cannot connect, this throws an exception
        self.connectTime=None
        self.serial=serial.Serial(port=device,
                                  baudrate=19200, bytesize=8, parity='N', stopbits=1,
                                  timeout=10 ## untested
                                  )
        self.serial.flowControl(False)
        self.connectTime=time.time()
    def getConnection(self):
        ## gets the name of the current connection
        ## returns None if there is no open connection
        if self.serial and self.serial.portstr:
            return self.serial.portstr
        return None
    def route(self, input, output):
        ## tells the matrix to choose 'input' as an input for 'output'
        ## might block
        if not self.serial:
                return None
        command=chr(65+output)
        command+=('%s' % (1+input))
        command+='\r'
        self.send(command)
    def getRoutes(self):
        ## gets all outputs with their selected inputs (as a dictionary)
        ## might block
        if not self.serial:
                return None
        command='#PRRS\r'
        res=self.send(command)
        d=dict()
        return d


class DVImatrix848(QtGui.QMainWindow):
    def __init__(self,
                 configfile=None
                 ):
        super(DVImatrix848, self).__init__()
        if configfile is None:
            configfile=getConfigFile()
        self.comm=communicator()

        self.inputs=[]
        self.outputs=[]
        self.configfile=None

        self.outgroup=[]
        self.out4in={}
        self.serialPorts=[] # array of name/menuitem pais

        self.serialSelections= QtGui.QActionGroup(self)
        self.serialSelections.triggered.connect(self.selectSerial)

        self.readConfig(configfile)

        self.setupUI()
        self.rescanSerial()

    def setupUI(self):
        self.resize(320, 240)
        self.centralwidget = QtGui.QWidget(self)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.gridLayout = QtGui.QGridLayout(self.groupBox)
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setText("")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.setCentralWidget(self.centralwidget)

        self.menubar = QtGui.QMenuBar(self)
        #self.menubar.setGeometry(QtCore.QRect(0, 0, 168, 19))
        self.setMenuBar(self.menubar)

        self.menuFile = QtGui.QMenu(self.menubar)

        self.menuConfiguration = QtGui.QMenu(self.menubar)
        self.menuSerial_Ports = QtGui.QMenu(self.menuConfiguration)

        self.actionQuit = QtGui.QAction(self)
        self.actionQuit.setText("Quit")
        self.actionQuit.setShortcut("Ctrl+Q")
        self.actionQuit.activated.connect(self.exit)

        self.actionRescanSerial = QtGui.QAction(self)
        self.actionRescanSerial.setText("Rescan")
        self.actionRescanSerial.activated.connect(self.rescanSerial)

        self.actionEditLabels = QtGui.QAction(self)
        self.actionEditLabels.setText("Edit Labels")
        self.actionEditLabels.setShortcut("Ctrl+E")
        self.actionEditLabels.setEnabled(True)
        self.actionEditLabels.setCheckable(True)
        self.actionEditLabels.activated.connect(self.editLabels)

        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuSerial_Ports.addAction(self.actionRescanSerial)
        self.menuSerial_Ports.addSeparator()

        self.menuConfiguration.addAction(self.actionEditLabels)
        self.menuConfiguration.addAction(self.menuSerial_Ports.menuAction())

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuConfiguration.menuAction())

        self.statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.setWindowTitle("MainWindow")
        self.groupBox.setTitle("DVImatrix848")
        self.menuFile.setTitle("File")
        self.menuConfiguration.setTitle("Configuration")
        self.menuSerial_Ports.setTitle("Serial Ports")

        self.matrixButton = QtGui.QPushButton("Get State")
        self.matrixButton.clicked.connect(self.getMatrix)
        self.gridLayout.addWidget(self.matrixButton, 0,0,1,1)

        self.setupDynamicUI()
    def setupDynamicUI(self):
        inputs=self.inputs
        outputs=self.outputs
        self.outgroup=[]

        self.enableLabelEditing(False)

        for outnum, output in enumerate(outputs):
            outgroup=QtGui.QButtonGroup(self.groupBox)
            self.outgroup+=[outgroup]

            for innum, input in enumerate(inputs):
                butn=QtGui.QRadioButton(self.groupBox)
                butn.setText("")
                self.gridLayout.addWidget(butn, 1+innum, 1+outnum, 1, 1)
                outgroup.addButton(butn)
                outgroup.setId(butn, innum)
                butn.setToolTip("%s -> %s" % (input, output))
                outgroup.buttonClicked.connect(self.clickedRouting)
                #print("connected %s for %s" % (outgroup, butn))
    def _replaceWidget(self, wdg, row, col):
        oldwdgitm=self.gridLayout.itemAtPosition(row, col)
        if oldwdgitm:
            oldwdg=oldwdgitm.widget()
            self.gridLayout.removeWidget(oldwdg)
            oldwdg.deleteLater()
        self.gridLayout.addWidget(wdg, row, col, 1, 1)

    def enableLabelEditing(self, enable=True):
        inputs=self.inputs
        outputs=self.outputs
        for innum, input in enumerate(inputs):
            if not enable:
                inlabel = QtGui.QLabel(self.groupBox)
            else:
                inlabel = QtGui.QLineEdit(self.groupBox)
            self._replaceWidget(inlabel, 1+innum, 0)
            inlabel.setText(input)

        for outnum, output in enumerate(outputs):
            if not enable:
                outlabel = QtGui.QLabel(self.groupBox)
            else:
                outlabel = QtGui.QLineEdit(self.groupBox)
            self._replaceWidget(outlabel, 0, 1+outnum)
            outlabel.setText(output)
    def editLabels(self):
        state=self.actionEditLabels.isChecked()
        if not state:
            newouts=[]
            for idx, _ in enumerate(self.outputs):
                itm=self.gridLayout.itemAtPosition(0, idx+1)
                if itm and itm.widget():
                    wdg=itm.widget()
                    newouts+=[wdg.text()]
            newins=[]
            for idx, _ in enumerate(self.inputs):
                itm=self.gridLayout.itemAtPosition(idx+1, 0)
                if itm and itm.widget():
                    wdg=itm.widget()
                    newins+=[wdg.text()]
            self.inputs=newins
            self.outputs=newouts

        self.enableLabelEditing(state)
    def getMatrix(self):
        routes=self.comm.getRoutes()
        #print("got matrix: %s" % (routes))
        for og in self.outgroup:
            btn = og.checkedButton()
            if btn:
                og.setExclusive(False);
                btn.setChecked(False)
                og.setExclusive(True);
        for o in routes:
            i=routes[o]
            print("input[%s] -> output[%s]" % (i,o))
            buttons=self.outgroup[o].buttons()
            buttons[i].setChecked(True)

    def clickedRouting(self, btn):
        btngrp=btn.group()
        innum=btngrp.checkedId()
        outnum=-1
        #print("outgroup: %s" % (self.outgroup))
        for on,og in enumerate(self.outgroup):
            #print("out[%s]=%s" % (on, og))
            if og is btngrp:
                outnum=on
                break
        if (not outnum in self.out4in) or (self.out4in[outnum] != innum):
            self.routeInput2Output(innum, outnum)

    def routeInput2Output(self, innum, outnum):
        self.out4in[outnum]=innum
        self.comm.route(innum, outnum)
        #print("TODO: connect: %s -> %s" % (innum, outnum))

    def rescanSerial(self):
        lastselected=""
        for (name, action) in self.serialPorts:
            if action.isChecked():
                lastselected=name
            self.menuSerial_Ports.removeAction(action)
            self.serialSelections.removeAction(action)
        self.serialPorts=[]
        import serial.tools.list_ports
        for (port_name,port_desc,_) in serial.tools.list_ports.comports():
            action=QtGui.QAction(self)
            action.setText(port_name)
            action.setToolTip(port_desc)
            action.setStatusTip("Use serial port: %s" % (port_desc))
            action.setCheckable(True);
            action.setActionGroup(self.serialSelections);

            if lastselected and lastselected == port_name:
                action.setChecked(True)
                lastselected=None

            self.menuSerial_Ports.addAction(action)
            self.serialPorts+=[(port_name, action)]

        # finally activate the correct selection
        if lastselected is not None:
            ## this means that we were not able to continue with the old selection
            ## so just choose the first one available
            acts=self.serialSelections.actions()
            if acts:
                acts[0].setChecked(True)
                self.selectSerial()

    def selectSerial(self):
        for (name,action) in self.serialPorts:
            if action.isChecked():
                print("selected serial port: %s" % (name))
                try:
                    self.comm.connect(name)
                except serial.serialutil.SerialException as e:
                    self.statusBar().showMessage("ERROR: %s" % (e))
                    action.setChecked(False)
                break


    def exit(self):
        self.writeConfig()
        import sys
        sys.exit()
    def readConfig(self, configfile=None):
        if not configfile:
            configfile=self.configfile
        if not configfile:
            configfile='DVImatrix848.ini'
        config = ConfigParser.SafeConfigParser(allow_no_value=True)
        config.read(configfile)
        if not config.has_section('INPUTS'):
            self.statusBar().showMessage("WARNING: no 'INPUTS' section in configuration %s" % (configfile))
            config.add_section('INPUTS')
        if not config.options('INPUTS'):
            self.statusBar().showMessage("WARNING: no inputs in 'INPUTS' section in configuration %s" % (configfile))
            for i in range(4):
                config.set('INPUTS', ('in#%d' % (i+1)), None)
        self.inputs=config.options('INPUTS')
        if not config.has_section('OUTPUTS'):
            self.statusBar().showMessage("WARNING: no 'OUTPUTS' section in configuration %s" % (configfile))
            config.add_section('OUTPUTS')
        if not config.options('OUTPUTS'):
            self.statusBar().showMessage("WARNING: no outputs in 'OUTPUTS' section in configuration %s" % (configfile))
            for i in range(4):
                config.set('OUTPUTS', ('out#%d' % (i+1)), None)
        self.outputs=config.options('OUTPUTS')

        self.config=config
        self.configfile=configfile
    def writeConfig(self, configfile=None):
        if not configfile:
            configfile=self.configfile
        if not configfile:
            configfile='DVImatrix848.ini'
        self.configfile=configfile
        config = ConfigParser.SafeConfigParser(allow_no_value=True)

        config.add_section('serial')
        config.set('serial', '# serial-port settings')
        portname=self.comm.getConnection()
        if portname:
            config.set('serial', 'port', portname)
        config.add_section('INPUTS')
        config.set('INPUTS', '# list of inputs (one per line)')
        config.set('INPUTS', '#   MUST NOT contain "=" (equal sign)')
        for i in self.inputs:
            config.set('INPUTS', i, None)
        config.add_section('OUTPUTS')
        config.set('OUTPUTS', '# list of outputs (one per line)')
        config.set('OUTPUTS', '#   MUST NOT contain "=" (equal sign)')
        for o in self.outputs:
            config.set('OUTPUTS', o, None)

        with open(configfile, 'wb') as cf:
            config.write(cf)

if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    window = DVImatrix848()
    window.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
