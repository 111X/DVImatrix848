#! /usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright © 2014-2015, IOhannes m zmölnig, IEM

# This file is part of DVImatrix848
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
import versions

import os
import sys
import time
import re
import random

import serial
import serial.tools.list_ports

import json
import logging

FETCHMATRIX_NEVER = 0x0
FETCHMATRIX_AUTOMATIC = 0x1
FETCHMATRIX_INTERACTIVE = 0x2
FETCHMATRIX_ALWAYS = FETCHMATRIX_AUTOMATIC | FETCHMATRIX_INTERACTIVE

_SCRIPTDIR = os.path.dirname(os.path.abspath(sys.argv[0]))


def _makeRandomRoutes():
    routes = {}
    for i in range(8):
        routes[i] = random.randint(1, 8)
    return routes


def _getRoutingMatrixUnparsed(routes):
    S = ['m']
    S += ['**** MATRIX STATUS ****']
    for o in routes:
        i = routes[o]
        o_ = chr(o+65)
        s = ("Mon%s: {" % (o_))
        s += ("DviIn=%d" % (i+1))
        s += " , Hpd=0 , DviOutEn=0 , "
        s += ("InDDC=%d" % (i+1))
        s += " , DDC-Master=0 PreEmphasis=0 [db]}"
        S += [s]
    return '\r'.join(S)


def _parseRoutingMatrixString(s):
    routes = {}
    if not s:
        return routes
    pat = r"^Mon(?P<output>[A-Z]+): {DviIn=(?P<input>[0-9]+) ,.*}$"
    for x in s.split('\r'):
        match = re.search(pat, x)
        if match:
            d = match.groupdict()
            try:
                routes[ord(d['output'])-65] = int(d['input'])-1
            except (KeyError, TypeError, ValueError):
                pass
    return routes


def _testRoutingParser():
    r0 = _makeRandomRoutes()
    rs = _getRoutingMatrixUnparsed(r0)
    r1 = _parseRoutingMatrixString(rs)
    if r0 == r1:
        logging.debug("%d bytes match: %s" % (len(rs), r0))


def _getAppDataDir():
    appdatadir = []
    if os.name == 'nt':
        from win32com.shell import shellcon, shell
        appdatadir += [shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)]
    appdatadir += [
        os.path.join(os.path.expanduser("~"), ".config")
        ]
    for ad in appdatadir:
        if os.path.exists(ad):
            ad = os.path.join(ad, "DVImatrix848")
            try:
                os.makedirs(ad)
            except OSError:
                pass
            if os.path.isdir(ad):
                return ad
    return None


def getConfigFile():
    appdatadir = _getAppDataDir()
    if not appdatadir:
        return
    return os.path.join(appdatadir, "setup.json")


def getAutostarter(name):
    try:
        from autostarterW32registry import autostarter
    except ImportError:
        return None

    exe = os.path.join(_SCRIPTDIR, 'DVImatrix848key.exe')
    if not os.path.exists(exe):
        return None

    try:
        ast = autostarter(name, exe)
    except ImportError:
        return None

    icon = os.path.join(
        _SCRIPTDIR,
        'media',
        'DVImatrix848key.ico')
    if not os.path.exists(icon):
        icon = None
    try:
        ast.icon = icon
    except AttributeError:
        pass
    try:
        ast.workingDir = _SCRIPTDIR
    except AttributeError:
        pass
    return ast


class communicator(object):
    def __init__(self, sleepTime=0):
        super(communicator, self).__init__()
        self.serial = None
        self._lastTime = None
        self.sleepTime = sleepTime

    def send(self, data, readback=None):
        # 'readback' controls a subsequent 'read' operation
        # - positive ints:
        logging.info("TODO: write '%s'" % (data))

        # send data to the device
        # will block if we have just opened the device

        if not self.serial or not self._lastTime:
                return None
        ser = self.serial

        # make sure there are no left-overs in the input buffers
        # (important for parsing readback)
        ser.flushInput()

        # wait until the device has settled
        now = time.time()
        sleeptime = self._lastTime + self.sleepTime - now
        logging.debug("sleeping %s seconds (%s-%s+%s)"
                      % (sleeptime, self._lastTime, now, self.sleepTime))
        if sleeptime > 0:
                time.sleep(sleeptime)
        ser.write(data)

        ser.flush()
        self._lastTime = time.time()

        if readback is None:
            return None
        if readback is True:
            return ser.readline()
        if int(readback) > 0:
            return ser.read(int(readback))
        return None

    def connect(self, device):
        # connects to another device
        # if we cannot connect, this throws an exception
        logging.info("connecting to '%s' instead of '%s'"
                     % (device, self.getConnection()))
        if device == self.getConnection():
            return
        self._lastTime = None
        self.serial = serial.Serial(
            port=device,
            baudrate=19200, bytesize=8, parity='N', stopbits=1,
            timeout=1  # untested
            )
        # need to wait for at least 1sec until the device is usable
        self._lastTime = time.time() + 1
        logging.info("connected to '%s'" % self.getConnection())

    def getConnection(self):
        # gets the name of the current connection
        # returns None if there is no open connection
        if self.serial and self.serial.portstr:
            return self.serial.portstr
        return None

    def route(self, input, output):
        # tells the matrix to choose 'input' as an input for 'output'
        # might block
        if not self.serial:
                return None
        command = chr(65+output)
        command += ('%s' % (1+input))
        command += '\r'
        self.send(command)

    def getRoutes(self):
        # gets all outputs with their selected inputs (as a dictionary)
        # might block
        if not self.serial:
            return None
        command = 'm\r'
        res = self.send(command, 673)
        d = _parseRoutingMatrixString(res)
        return d


class DVImatrix848(QtGui.QMainWindow):
    def __init__(self,
                 configfile=None,
                 fetchMatrix=FETCHMATRIX_ALWAYS,
                 restore=False
                 ):
        super(DVImatrix848, self).__init__()
        self.whenFetchMatrix = FETCHMATRIX_NEVER
        self.inputs = []
        self.outputs = []
        self.configfile = None
        self.allow_emergency_store = True

        self.outgroup = []
        self.out4in = {}
        self.default_out4in = {}
        self.serialPorts = []  # array of name/menuitem pais
        self.serialport = None

        self.comm = communicator(sleepTime=0.250)

        if configfile is None:
            configfile = getConfigFile()
        self.whenFetchMatrix = fetchMatrix
        self.readConfig(configfile)

        self.serialSelections = QtGui.QActionGroup(self)
        self.serialSelections.triggered.connect(self.selectSerialByMenu)

        self.setupStaticUI()

        self.rescanSerial()

        self.setupDynamicUI()
        if self.serialport:
            self.selectSerial(self.serialport, False)

        if self.whenFetchMatrix & FETCHMATRIX_AUTOMATIC:
            self.getMatrix()
        else:
            logging.info("using config-matrix: %s" % (self.out4in))
            self.setRouting(self.out4in)
            self.showRouting(self.out4in)
        logging.info("when: %s" % self.whenFetchMatrix)
        if restore:
            self.restore()

    def setupStaticUI(self):
        self.resize(320, 240)
        self.centralwidget = QtGui.QWidget(self)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.gridLayout = QtGui.QGridLayout(self.groupBox)

        self.label = QtGui.QLabel(self.groupBox)
        self.label.setText("")
        self.gridLayout.addWidget(
            self.label,
            0, 0,
            1, 1,
            QtCore.Qt.AlignCenter)
        self.verticalLayout.addWidget(self.groupBox)
        self.setCentralWidget(self.centralwidget)

        self.menubar = QtGui.QMenuBar(self)
        # self.menubar.setGeometry(QtCore.QRect(0, 0, 168, 19))
        self.setMenuBar(self.menubar)

        self.menuFile = QtGui.QMenu(self.menubar)

        self.menuConfiguration = QtGui.QMenu(self.menubar)
        self.menuSerial_Ports = QtGui.QMenu(self.menuConfiguration)

        self.actionStore = QtGui.QAction(self)
        self.actionStore.setText("Store")
        self.actionStore.setStatusTip("Store an emergency routing")
        # self.actionStore.setShortcut("Ctrl+Shift+S")
        if not self.allow_emergency_store:
            self.actionStore.setEnabled(False)
        self.actionStore.activated.connect(self.store)
        self.actionRestore = QtGui.QAction(self)
        self.actionRestore.setText("Restore")
        self.actionRestore.setStatusTip("Restore emergency routing")
        self.actionRestore.setShortcut("Ctrl+Shift+R")
        self.actionRestore.activated.connect(self.restore)

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

        self.menuFile.addAction(self.actionStore)
        self.menuFile.addAction(self.actionRestore)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionQuit)
        self.menuSerial_Ports.addAction(self.actionRescanSerial)
        self.menuSerial_Ports.addSeparator()

        self.menuConfiguration.addAction(self.actionEditLabels)
        self.menuConfiguration.addAction(self.menuSerial_Ports.menuAction())

        self.actionInstallHotkey = None
        self.autostarter = getAutostarter('DVImatrix848 hotkey')
        if self.autostarter:
            self.actionInstallHotkey = QtGui.QAction(self)
            self.actionInstallHotkey.activated.connect(
                self.installHotkeyAutostart)
            self.menuConfiguration.addAction(self.actionInstallHotkey)
        self.configureHotkeyMenu()

        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuConfiguration.menuAction())

        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setTitle("Help")
        self.actionHelp = QtGui.QAction(self)
        self.actionHelp.setText("Online Help")
        self.actionHelp.setStatusTip("Read online help")
        self.actionHelp.activated.connect(self.openHelp)
        self.menuHelp.addAction(self.actionHelp)
        self.menubar.addAction(self.menuHelp.menuAction())

        self.aboutBox = None
        try:
            self.aboutBox = aboutBox()
        except (IOError, ValueError, KeyError) as e:
            # couldn't initialize aboutBox, continue without
            logging.warn("disabling ABOUT: %s" % e)
        if self.aboutBox:
            self.actionAbout = QtGui.QAction(self)
            self.actionAbout.setText("Check for updates")
            self.actionAbout.setStatusTip("Check for newer versions")
            self.actionAbout.activated.connect(self.about)
            self.menuHelp.addAction(self.actionAbout)

        self.statusbar = QtGui.QStatusBar(self)
        self.setStatusBar(self.statusbar)

        self.setWindowTitle("DVImatrix848")
        self.setWindowIcon(QtGui.QIcon("media/DVImatrix848.svg"))
        self.groupBox.setTitle("Routing matrix")
        self.menuFile.setTitle("File")
        self.menuConfiguration.setTitle("Configuration")
        self.menuSerial_Ports.setTitle("Serial Ports")

        self.matrixButton = QtGui.QPushButton("Get State")
        logging.info("fetchmatrix: %s" % (self.whenFetchMatrix))
        if self.whenFetchMatrix & FETCHMATRIX_INTERACTIVE:
            logging.info("interactive")
            self.matrixButton.setEnabled(True)
        else:
            self.matrixButton.setEnabled(False)
        self.matrixButton.clicked.connect(self.getMatrix)
        self.gridLayout.addWidget(
            self.matrixButton,
            0, 0,
            1, 1,
            QtCore.Qt.AlignCenter)

    def setupDynamicUI(self):
        inputs = self.inputs
        outputs = self.outputs
        self.outgroup = []

        self.enableLabelEditing(False)

        for outnum, output in enumerate(outputs):
            outgroup = QtGui.QButtonGroup(self.groupBox)
            self.outgroup += [outgroup]

            for innum, input in enumerate(inputs):
                butn = QtGui.QRadioButton(self.groupBox)
                butn.setText("")
                self.gridLayout.addWidget(
                    butn,
                    1+innum, 1+outnum,
                    1, 1,
                    QtCore.Qt.AlignCenter
                    )
                outgroup.addButton(butn)
                outgroup.setId(butn, innum)
                outgroup.buttonClicked.connect(self.clickedRouting)
        self._updateTooltips()

    def configureHotkeyMenu(self, enable=None):
        if not self.autostarter or not self.actionInstallHotkey:
            return

        if enable is None:
            enable = not self.autostarter.exists()

        if enable:
            self.actionInstallHotkey.setText(
                "Install global Hotkey")
            self.actionInstallHotkey.setStatusTip(
                "Enable global emergency hotkey permanently")
        else:
            self.actionInstallHotkey.setText(
                "Uninstall global Hotkey")
            self.actionInstallHotkey.setStatusTip(
                "Disable global emergency hotkey permanently")

    def installHotkeyAutostart(self):
        self.autostarter.toggle()
        self.configureHotkeyMenu()

    def about(self):
        if self.aboutBox:
            self.aboutBox.showAbout()

    def _updateTooltips(self):
        inputs = self.inputs
        outputs = self.outputs
        for outnum, output in enumerate(outputs):
            for innum, input in enumerate(inputs):
                itm = self.gridLayout.itemAtPosition(innum+1, outnum+1)
                if itm:
                    wdg = itm.widget()
                    wdg.setToolTip(u"%s → %s" % (input, output))
                    wdg.setStatusTip(u"%s → %s" % (input, output))

    def _replaceWidget(self, wdg, row, col):
        oldwdgitm = self.gridLayout.itemAtPosition(row, col)
        if oldwdgitm:
            oldwdg = oldwdgitm.widget()
            self.gridLayout.removeWidget(oldwdg)
            oldwdg.deleteLater()
        self.gridLayout.addWidget(wdg, row, col, 1, 1, QtCore.Qt.AlignCenter)

    def enableLabelEditing(self, enable=True):
        inputs = self.inputs
        outputs = self.outputs
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
        state = self.actionEditLabels.isChecked()
        if not state:
            newouts = []
            for idx, _ in enumerate(self.outputs):
                itm = self.gridLayout.itemAtPosition(0, idx+1)
                if itm and itm.widget():
                    wdg = itm.widget()
                    newouts += [wdg.text()]
            newins = []
            for idx, _ in enumerate(self.inputs):
                itm = self.gridLayout.itemAtPosition(idx+1, 0)
                if itm and itm.widget():
                    wdg = itm.widget()
                    newins += [wdg.text()]
            self.inputs = newins
            self.outputs = newouts

        self.enableLabelEditing(state)

    def getMatrix(self):
        routes = self.comm.getRoutes()
        logging.debug("got matrix: %s" % (routes))
        self.setRouting(routes, False)

    def setRouting(self, routes, apply=True):
        logging.debug("setRouting: %s" % (routes))
        for og in self.outgroup:
            btn = og.checkedButton()
            if btn:
                og.setExclusive(False)
                btn.setChecked(False)
                og.setExclusive(True)
        if not routes:
            return
        if apply:
            d = routes
            for o in d:
                self.routeInput2Output(d[o], o)
            if self.whenFetchMatrix & FETCHMATRIX_AUTOMATIC:
                self.getMatrix()
        else:
            self.showRouting(routes)

    def showRouting(self, routes):
        for o in routes:
            try:
                i = routes[o]
                # logging.debug("input[%s] -> output[%s]" % (i, o))
                buttons = self.outgroup[o].buttons()
                buttons[i].setChecked(True)
            except IndexError:
                pass

    def clickedRouting(self, btn):
        btngrp = btn.group()
        innum = btngrp.checkedId()
        outnum = -1
        # logging.debug("outgroup: %s" % (self.outgroup))
        for on, og in enumerate(self.outgroup):
            # logging.debug("out[%s]=%s" % (on, og))
            if og is btngrp:
                outnum = on
                break
        if (outnum not in self.out4in) or (self.out4in[outnum] != innum):
            self.routeInput2Output(innum, outnum)

    def routeInput2Output(self, innum, outnum):
        logging.info("%s -> %s [%s]" % (outnum, innum, self.out4in))
        self.out4in[outnum] = innum
        self.comm.route(innum, outnum)
        # logging.info("TODO: connect: %s -> %s" % (innum, outnum))

    def rescanSerial(self):
        lastselected = ""
        for (name, action) in self.serialPorts:
            if action.isChecked():
                lastselected = name
            self.menuSerial_Ports.removeAction(action)
            self.serialSelections.removeAction(action)
        self.serialPorts = []
        for (port_name, port_desc, _) in serial.tools.list_ports.comports():
            action = QtGui.QAction(self)
            action.setText(port_name)
            action.setToolTip(port_desc)
            action.setStatusTip("Use serial port: %s" % (port_desc))
            action.setCheckable(True)
            action.setActionGroup(self.serialSelections)

            if lastselected and lastselected == port_name:
                action.setChecked(True)
                lastselected = None

            self.menuSerial_Ports.addAction(action)
            self.serialPorts += [(port_name, action)]

        # finally activate the correct selection
        if lastselected is not None:
            # this means that we were not able to continue
            # with the old selection, so just choose the
            # first one available
            acts = self.serialSelections.actions()
            if acts:
                acts[0].setChecked(True)
                self.selectSerial()

    def selectSerial(self, portname=None, fetchMatrix=True):
        logging.info("selectSerial: fetch=%s" % (fetchMatrix))
        logging.info("selecting %s in %s"
                     % (portname, [x for (x, y) in self.serialPorts]))
        for (name, action) in self.serialPorts:
            if portname is None:
                selected = action.isChecked()
            else:
                selected = (portname == name)
            if selected:
                logging.info("selected serial port: %s" % (name))
                try:
                    self.comm.connect(name)
                    action.setChecked(True)
                    self.status("serial port connected to %s" % (name))
                    self.groupBox.setEnabled(True)
                except serial.serialutil.SerialException as e:
                    self.status("ERROR: %s" % (e))
                    action.setChecked(False)
                    self.groupBox.setEnabled(False)
                    fetchMatrix = False
                break
        if fetchMatrix:
            self.getMatrix()

    def selectSerialByMenu(self):
        shouldselect = bool(self.whenFetchMatrix & FETCHMATRIX_AUTOMATIC)
        logging.info("selectSerial: %s = %s&%s"
                     % (shouldselect,
                        self.whenFetchMatrix,
                        FETCHMATRIX_AUTOMATIC))
        return self.selectSerial(fetchMatrix=shouldselect)

    def exit(self):
        logging.info("Bye")
        self.writeConfig()
        logging.info("ByeBye")
        sys.exit()

    def closeEvent(self, event):
        logging.info("closeEvent")
        event.ignore()
        self.exit()

    def store(self):
        d = {}
        for out in self.out4in:
            d[out] = self.out4in[out]
        self.default_out4in = d
        logging.info("stored default routing matrix: %s"
                     % (self.default_out4in))

    def restore(self):
        self.setRouting(self.default_out4in)
        self.showRouting(self.default_out4in)
        logging.info("restored default routing matrix: %s"
                     % (self.default_out4in))

    def readConfig(self, configfile=None):
        if not configfile:
            configfile = self.configfile
        if not configfile:
            configfile = 'DVImatrix848.json'

        def warn(section):
            self.status("WARNING: no '%s' in configuration %s"
                        % (section, configfile))

        config = None
        try:
            with open(configfile, 'rb') as cf:
                config = json.load(cf)
        except (IOError, ValueError) as e:
            self.status("WARNING: configfile error: %s" % (e))
        if not config:
            config = {}
        if not isinstance(config, dict):
            self.status("ERROR: illegal configfile '%s'"
                        % (configfile))

        try:
            x = config['INPUTS']
            if isinstance(x, list):
                self.inputs = x
        except KeyError:
            warn('INPUTS')
            self.inputs = ['IN#%s' % x for x in range(8)]
        try:
            x = config['OUTPUTS']
            if isinstance(x, list):
                self.outputs = x
        except KeyError:
            warn('OUTPUTS')
            self.outputs = ['OUT#%s' % x for x in range(8)]

        try:
            d = config['serial']
            self.serialport = d.get('port', self.serialport)
            self.comm.sleepTime = d.get('sleep', self.comm.sleepTime)
        except (KeyError, TypeError) as e:
            warn('serial')

        wf = FETCHMATRIX_ALWAYS
        try:
            d = config['generic']
            if 'fetchstate' in d:
                whenfetch = str(d['fetchstate']).lower()
                if whenfetch.startswith('never'):
                    wf = FETCHMATRIX_NEVER
                if whenfetch.startswith('auto'):
                    wf = FETCHMATRIX_AUTOMATIC
                if whenfetch.startswith('inter'):
                    wf = FETCHMATRIX_INTERACTIVE
            else:
                self.status("WARNING: no 'generic/fetchstate' configuration %s"
                            % (configfile))
            if 'emergencystore' in d:
                if d['emergencystore']:
                    self.allow_emergency_store = True
                else:
                    self.allow_emergency_store = False
            else:
                warn('generic:fetchstate')

        except (KeyError, TypeError) as e:
            warn('generic')
        self.whenFetchMatrix = wf

        try:
            d = config['matrix']
            if d:
                routes = {}
                # fix the keys: we want int, not strings
                for k in d:
                    try:
                        routes[int(k)] = d[k]
                    except (ValueError):
                        pass
                self.out4in = routes
                logging.info("configmatrix: %s" % (routes))
        except (KeyError, TypeError) as e:
            warn('matrix')

        try:
            d = config['defaultmatrix']
            if d:
                routes = {}
                # fix the keys: we want int, not strings
                for k in d:
                    try:
                        routes[int(k)] = d[k]
                    except (ValueError):
                        pass
                self.default_out4in = routes
                logging.info("defaultmatrix: %s" % (routes))
        except (KeyError, TypeError) as e:
            warn('defaultmatrix')

        self.configfile = configfile

    def writeConfig(self, configfile=None):
        if not configfile:
            configfile = self.configfile
        if not configfile:
            configfile = 'DVImatrix848.json'

        d = {}

        d_generic = {}
        whenfetch = 'always'
        if self.whenFetchMatrix == FETCHMATRIX_NEVER:
            whenfetch = 'never'
        elif self.whenFetchMatrix == FETCHMATRIX_AUTOMATIC:
            whenfetch = 'auto'
        elif self.whenFetchMatrix == FETCHMATRIX_INTERACTIVE:
            whenfetch = 'interactive'
        d_generic['fetchstate'] = whenfetch
        d_generic['emergencystore'] = self.allow_emergency_store

        d['generic'] = d_generic

        serialconf = {}
        portname = self.comm.getConnection()
        if portname:
            serialconf['port'] = portname
        if self.comm.sleepTime:
                serialconf['sleep'] = self.comm.sleepTime
        if serialconf:
            d['serial'] = serialconf
        logging.info("portname = '%s'\nserialconf = %s\nconf = %s"
                     % (portname, serialconf, d))

        if self.inputs:
            d['INPUTS'] = self.inputs
        if self.outputs:
            d['OUTPUTS'] = self.outputs
        if self.out4in:
            d['matrix'] = self.out4in
        if self.default_out4in:
            d['defaultmatrix'] = self.default_out4in

        with open(configfile, 'wb') as cf:
            json.dump(d, cf,
                      indent=4,
                      ensure_ascii=True
                      )

    def openHelp(self):
        QtGui.QDesktopServices.openUrl(
            'https://github.com/iem-projects/DVImatrix848/wiki')

    def status(self, text):
        self.statusBar().showMessage(text)
        logging.warn("STATE: %s" % text)


class aboutBox(QtGui.QDialog):
    def __init__(self):
        super(aboutBox, self).__init__()

        jsonfile = os.path.join(_SCRIPTDIR, 'about.json')
        j = None
        with open(jsonfile) as f:
            j = json.load(f)
            self.text = j['about']
            self.newrelease = j['newrelease']
            self.no_newrelease = j['no_newrelease']

        self.resize(465, 281)
        self.setModal(True)
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.textBrowser = QtGui.QTextBrowser(self)
        self.textBrowser.setOpenExternalLinks(True)
        self.verticalLayout.addWidget(self.textBrowser)
        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Ok)
        self.verticalLayout.addWidget(self.buttonBox)

        self.set()
        QtCore.QObject.connect(
            self.buttonBox,
            QtCore.SIGNAL("accepted()"),
            self.accept)
        QtCore.QObject.connect(
            self.buttonBox,
            QtCore.SIGNAL("rejected()"),
            self.reject)
        QtCore.QMetaObject.connectSlotsByName(self)

    def set(self, current_version=None, github_version=None):
        self.setWindowTitle("About DVImatrix848")
        self.textBrowser.setHtml(self._text(current_version, github_version))

    def _text(self, current_version=None, github_version=None):
        upstream = ''
        if not github_version:
            upstream = self.no_newrelease
        elif ((not current_version
               or versions.isNewer(github_version, current_version))):
            upstream = self.newrelease.replace(
                '@UPSTREAM_VERSION@',
                github_version)
        if not current_version:
            current_version = '<em>unknown</em>'
        return (self.text
                .replace('@VERSION@', current_version)
                .replace('@UPSTREAM@', upstream)
                )

    def showAbout(self):
        current_version = versions.getCurrentVersion()
        github_version = versions.getGithubVersion("iem-projects/DVImatrix848")
        print("version: %s [%s]" % (current_version, github_version))
        self.set(current_version, github_version)
        self.show()


def printVersion(name):
    current_version = versions.getCurrentVersion()
    github_version = versions.getGithubVersion("iem-projects/DVImatrix848")
    versionstring = ''
    if current_version:
        versionstring += (" %s" % (current_version))
    if github_version and github_version != current_version:
        versionstring += (" [%s]" % (github_version))
    if versionstring:
        print("%s:%s" % (name, versionstring))
    else:
        print("%s: unknown version")


# cmdline arguments
def parseCmdlineArgs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=str,
                        help="Configuration file to read")
    parser.add_argument('-r', '--restore', action='store_true',
                        help="Restore emergency routing at startup")
    parser.add_argument('-V', '--version', action='store_true',
                        help="print program version and exit")
    parser.add_argument('-L', '--logfile', type=str,
                        help="Logfile to write to",
                        default=None)
    parser.add_argument('-v', '--verbose', action='count',
                        help="raise verbosity", default=0)
    parser.add_argument('-q', '--quiet', action='count',
                        help="lower verbosity", default=0)

    args = parser.parse_args()
    return args


if __name__ == '__main__':
    # the following is a pre-calculated type5 UUID
    # appGuid = str(
    #     uuid.uuid5(
    #         uuid.NAMESPACE_DNS,
    #         'github.com/iem-projects/DVImatrix848'))
    appGuid = '78cf6144-49c4-5a01-ade8-db93316aff6c'

    app = QtSingleApplication(appGuid, sys.argv)
    if app.isRunning():
        sys.exit(0)

    # make sure that all messages go to stderr
    # (on w32, stderr is caught automatically, whereas stdout is discarded)
    sys.stdout = sys.stderr

    def is_frozen():
        import imp
        return (os.name == 'nt')   # assume always frozen on W32
        return (hasattr(sys, "frozen") or      # new py2exe
                hasattr(sys, "importers")      # old py2exe
                or imp.is_frozen("__main__"))  # tools/freeze

    args = parseCmdlineArgs()
    if args.logfile is None:
        if is_frozen:
            appdatadir = _getAppDataDir()
            if appdatadir:
                logdir = os.path.join(appdatadir, "Logs")
                try:
                    os.makedirs(logdir)
                except (OSError):
                    pass
                if os.path.exists(logdir):
                    args.logfile = os.path.join(logdir, "DVImatrix.log")
    loglevel = max(0,
                   min(logging.FATAL,
                       logging.WARNING+(args.quiet-args.verbose)*10))
    if args.logfile:
        logging.basicConfig(
            filename=args.logfile,
            level=loglevel,
            filemode='w')
    else:
        logging.basicConfig(level=loglevel, filemode='w')
    if args.version:
        printVersion(sys.argv[0])
        sys.exit(0)

    window = DVImatrix848(
        fetchMatrix=FETCHMATRIX_NEVER,
        configfile=args.config,
        restore=args.restore)
    app.setActivationWindow(window)
    window.show()
    # Run the main Qt loop
    sys.exit(app.exec_())
