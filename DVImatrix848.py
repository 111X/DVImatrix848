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
from QtSingleApplication import QtSingleApplication

import os, sys, time, re, random

import serial
import serial.tools.list_ports

import json

def _makeRandomRoutes():
    routes={}
    for i in range(8):
        routes[i]=random.randint(1,8)
    return routes

def _getRoutingMatrixUnparsed(routes):
    S=['m']
    S+=['**** MATRIX STATUS ****']
    for o in routes:
        i=routes[o]
        o_=chr(o+65)
        S+=["Mon%s: {DviIn=%d , Hpd=0 , DviOutEn=0 , InDDC=%d , DDC-Master=0 PreEmphasis=0 [db]}" % (o_, i+1, i+1)]
    return '\r'.join(S)
def _parseRoutingMatrixString(s):
    routes={}
    if not s:
        return routes
    pat = r"^Mon(?P<output>[A-Z]+): {DviIn=(?P<input>[0-9]+) ,.*}$"
    for x in s.split('\r'):
        match=re.search(pat, x)
        if match:
            d=match.groupdict()
            try:
                routes[ord(d['output'])-65]=int(d['input'])-1
            except (KeyError, TypeError, ValueError):
                pass
    return routes

def _testRoutingParser():
    r0=_makeRandomRoutes()
    rs=_getRoutingMatrixUnparsed(r0)
    r1=_parseRoutingMatrixString(rs)
    if r0 == r1:
        print("%d bytes match: %s" % (len(rs), r0))

def getConfigFile():
    if os.name == "nt":
        from win32com.shell import shellcon, shell
        appdatadir=os.path.join(shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0),
                                "DVImatrix848")
    else:
        appdatadir = os.path.join(os.path.expanduser("~"), ".config", "DVImatrix848")
    if not os.path.isdir(appdatadir):
        os.mkdir(appdatadir)
    return os.path.join(appdatadir, "setup.json")

class communicator(object):
    def __init__(self):
        super(communicator, self).__init__()
        self.serial=None
        self.connectTime=None

    def send(self, data, readback=None):
        ## 'readback' controls a subsequent 'read' operation
        ## - positive ints:
        print("TODO: write '%s'" % (data))
        #return

        ## send data to the device
        ## will block if we have just opened the device

        if not self.serial or not self.connectTime:
                return None
        ser=self.serial
        sleeptime=self.connectTime + 1 - time.time()
        if sleeptime > 0:
                time.sleep(sleeptime)
        ser.write(data)
        ser.flush() ## untested
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
        print("connecting to '%s' instead of '%s'" % (device, self.getConnection()))
        if device == self.getConnection():
            return
        self.connectTime=None
        self.serial=serial.Serial(port=device,
                                  baudrate=19200, bytesize=8, parity='N', stopbits=1,
                                  timeout=1 ## untested
                                  )
        #self.serial.flowControl(False)
        self.connectTime=time.time()
        print("connected to '%s'" % self.getConnection())
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
        command='m\r'
        res=self.send(command, 673)
        d=_parseRoutingMatrixString(res)
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
        self.serialport=None

        self.serialSelections= QtGui.QActionGroup(self)
        self.serialSelections.triggered.connect(self.selectSerialByMenu)

        self.setupStaticUI()

        self.rescanSerial()
        self.readConfig(configfile)

        self.setupDynamicUI()
        if self.serialport:
            self.selectSerial(self.serialport)

        self.getMatrix()

    def setupStaticUI(self):
        self.resize(320, 240)
        self.centralwidget = QtGui.QWidget(self)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.gridLayout = QtGui.QGridLayout(self.groupBox)

        self.label = QtGui.QLabel(self.groupBox)
        self.label.setText("")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1, QtCore.Qt.AlignCenter)
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
        self.actionQuit.setStatusTip("Quit the application")

        self.actionQuit.setShortcut("Ctrl+Q")
        self.actionQuit.activated.connect(self.exit)

        self.actionRescanSerial = QtGui.QAction(self)
        self.actionRescanSerial.setText("Rescan")
        self.actionRescanSerial.setStatusTip("Rescan for serial devices")

        self.actionRescanSerial.activated.connect(self.rescanSerial)

        self.actionEditLabels = QtGui.QAction(self)
        self.actionEditLabels.setText("Edit Labels")
        self.actionEditLabels.setStatusTip("Edit the input/output labels")
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
        #self.matrixButton.setEnabled(False)
        self.matrixButton.clicked.connect(self.getMatrix)
        self.gridLayout.addWidget(self.matrixButton, 0,0,1,1, QtCore.Qt.AlignCenter)

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
                self.gridLayout.addWidget(butn, 1+innum, 1+outnum, 1, 1, QtCore.Qt.AlignCenter
                                          )
                outgroup.addButton(butn)
                outgroup.setId(butn, innum)
                outgroup.buttonClicked.connect(self.clickedRouting)
        self._updateTooltips()
    def _updateTooltips(self):
        inputs=self.inputs
        outputs=self.outputs
        for outnum, output in enumerate(outputs):
            for innum, input in enumerate(inputs):
                itm=self.gridLayout.itemAtPosition(innum+1, outnum+1)
                if itm:
                    wdg=itm.widget()
                    wdg.setToolTip(u"%s → %s" % (input, output))
                    wdg.setStatusTip(u"%s → %s" % (input, output))

    def _replaceWidget(self, wdg, row, col):
        oldwdgitm=self.gridLayout.itemAtPosition(row, col)
        if oldwdgitm:
            oldwdg=oldwdgitm.widget()
            self.gridLayout.removeWidget(oldwdg)
            oldwdg.deleteLater()
        self.gridLayout.addWidget(wdg, row, col, 1, 1, QtCore.Qt.AlignCenter)

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
        if not enable:
            self._updateTooltips()

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
        self.setRouting(routes, False)
    def setRouting(self, routes, apply=True):
        print("setRouting: %s" % (routes))
        for og in self.outgroup:
            btn = og.checkedButton()
            if btn:
                og.setExclusive(False);
                btn.setChecked(False)
                og.setExclusive(True);
        if not routes:
            return
        print("routes=%s" % (routes))
        print("outgroups=%s" % (len(self.outgroup)))
        if apply:
            d=self.out4in
            for o in d:
                self.routeInput2Output(d[o], o)
            self.getMatrix()
        else:
            self.showRouting(routes)
    def showRouting(self, routes):
        for o in routes:
            try:
                i=routes[o]
                #print("input[%s] -> output[%s]" % (i,o))
                buttons=self.outgroup[o].buttons()
                buttons[i].setChecked(True)
            except IndexError:
                pass
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

    def selectSerial(self, portname=None, fetchMatrix=True):
        print("selecting %s in %s" % (portname, [x for (x,y) in self.serialPorts]))
        for (name,action) in self.serialPorts:
            if portname is None:
                selected=action.isChecked()
            else:
                selected=(portname == name)
            if selected:
                print("selected serial port: %s" % (name))
                try:
                    self.comm.connect(name)
                    action.setChecked(True)
                    self.status("serial port connected to %s" % (name))

                except serial.serialutil.SerialException as e:
                    self.status("ERROR: %s" % (e))
                    action.setChecked(False)
                    fetchMatrix=False
                break
        if fetchMatrix:
            self.getMatrix()

    def selectSerialByMenu(self):
        return self.selectSerial()

    def exit(self):
        self.writeConfig()
        sys.exit()
    def readConfig(self, configfile=None):
        if not configfile:
            configfile=self.configfile
        if not configfile:
            configfile='DVImatrix848.json'

        config=None
        try:
            with open(configfile, 'rb') as cf:
                config=json.load(cf)
        except (IOError, ValueError) as e:
            self.status("WARNING: configfile error: %s" % (e))
        if not config:
            config={}
        if not isinstance(config, dict):
            self.status("ERROR: illegal configfile '%s'" % (configfile))

        try:
            x=config['INPUTS']
            if isinstance(x, list):
                self.inputs=x
        except KeyError:
            self.status("WARNING: no 'INPUTS' in configuration %s" % (configfile))
            self.inputs=[ 'IN#%s' % x for x in range(8) ]
        try:
            x=config['OUTPUTS']
            if isinstance(x, list):
                self.outputs=x
        except KeyError:
            self.status("WARNING: no 'OUTPUTS' in configuration %s" % (configfile))
            self.outputs=[ 'OUT#%s' % x for x in range(8) ]

        try:
            d=config['serial']
            self.serialport=d['port']
        except (KeyError, TypeError) as e:
            self.status("WARNING: no 'serial' configuration %s" % (configfile))

        try:
            d=config['matrix']
            if d:
                routes={}
                ## fix the keys: we want int, not strings
                for k in d:
                    try:
                        routes[int(k)]=d[k]
                    except (ValueError):
                        pass
                self.out4in=routes
                print("configmatrix: %s" % (routes))
        except (KeyError, TypeError) as e:
            self.status("WARNING: no 'serial' configuration %s" % (configfile))

        self.configfile=configfile
    def writeConfig(self, configfile=None):
        if not configfile:
            configfile=self.configfile
        if not configfile:
            configfile='DVImatrix848.json'


        serialconf={}
        d={}
        portname=self.comm.getConnection()
        if portname:
            serialconf['port']=portname
        if serialconf:
            d['serial']=serialconf
        print("portname='%s'\nserialconf=%s\nconf=%s" % (portname, serialconf, d))

        if self.inputs:
            d['INPUTS']=self.inputs
        if self.outputs:
            d['OUTPUTS']=self.outputs
        if self.out4in:
            d['matrix']=self.out4in

        with open(configfile, 'wb') as cf:
            json.dump(d, cf,
                      indent=4,
                      ensure_ascii=True,
            )
    def status(self, text):
        self.statusBar().showMessage(text)
        print("STATE: %s" % text)
if __name__ == '__main__':
    ## the following is a pre-calculated type5 UUID
    ## appGuid=str(uuid.uuid5(uuid.NAMESPACE_DNS, 'github.com/iem-projects/DVImatrix848'))
    appGuid='78cf6144-49c4-5a01-ade8-db93316aff6c'



    app = QtSingleApplication(appGuid, sys.argv)
    if app.isRunning(): sys.exit(0)

    window = DVImatrix848()
    app.setActivationWindow(window)
    window.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
