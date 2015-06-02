#!/usr/bin/python
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

import os.path
from autostarter import autostarter_base


class autostarter(autostarter_base):
    def __init__(self, name, executable, workingDir=None, icon=None):
        super(autostarter, self).__init__(name, executable)
        self._shortcut = self.getShortcutPath(name)
        self.workingDir = workingDir
        self.icon = icon

    def exists(self):
        """returns True if there is already an autostarter called <name>"""
        return os.path.exists(self._shortcut)

    def create(self):
        """creates a new autostarter <name>
        On success returns True, else False
        """
        return self.makeShortcut(
            self._shortcut,
            self.executable,
            workingDir=self.workingDir,
            icon=self.icon)

    def delete(self):
        """deletes an existing autostarter <name>
        On success returns True, else False
        """
        try:
            os.remove(self._shortcut)
        except Exception as e:
            print("OOPS[%s] removing %s failed: %s"
                  % (type(e), self._shortcut, e))
            return False
        return True

    def toggle(self):
        """creates a new autostarter if non exists; else it deletes it!
        returns True if an autostarter exists after this call, else False
        """
        if self.exists():
            return not self.delete()
        else:
            return self.create()

    @staticmethod
    def _getAppDataDir():
        from win32com.shell import shellcon, shell
        appdatadir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        if os.path.exists(appdatadir):
            return appdatadir
        return None

    @staticmethod
    def makeShortcut(destination, source, workingDir=None, icon=None):
        # destination: r'C:\tmp\test.lnk'
        # source     : r'C:\Program Files\Application\app.exe'
        # workingDir : r'C:\Program Files\Application'
        # icon       : r'C:\Program Files\Application\app.ico'
        import os
        from win32com.client import Dispatch
        from pythoncom import com_error
        shell = Dispatch('WScript.Shell')
        try:
            shortcut = shell.CreateShortCut(destination)
        except com_error as e:
            print("unable to create shortcut '%s': %s" % (destination, e))
            return False
        shortcut.Targetpath = source
        if workingDir:
            shortcut.WorkingDirectory = workingDir
        if icon:
            shortcut.IconLocation = icon
        try:
            shortcut.save()
        except com_error as e:
            print("unable to save shortcut '%s': %s" % (destination, e))
            return False
        return True

    @staticmethod
    def getShortcutPath(name):
        # calculate autostartdir
        appdatadir = autostarter._getAppDataDir()
        ext = '.lnk'
        if not name.endswith(ext):
            name = name+ext

        autostartdir = os.path.join(
            appdatadir,
            'Microsoft',
            'Windows',
            'Start Menu',
            'Programs',
            'Startup',
            )
        if not os.path.isdir(autostartdir):
            return None
        targetpath = os.path.join(
            autostartdir,
            name
            )
        return targetpath


if __name__ == '__main__':
    import sys

    def runtest(starter):
        print("autostart: %s -> %s" % (starter.name, starter.executable))
        if starter.exists():
            print("autostarter '%s' already exists. aborting test"
                  % (starter.name))
            return
        r = starter.create()
        x = starter.exists()
        print("created: %s\t = > exists: %s" % (r, x))
        r = starter.delete()
        x = starter.exists()
        print("deleted: %s\t = > exists: %s" % (r, x))

    name = 'autostart test'
    script = os.path.abspath(sys.argv[0])
    starter = autostarter(name, script)
    starter.workingDir = os.path.dirname(script)
    starter.icon = os.path.join(
        starter.workingDir,
        'media',
        'DVImatrix848key.ico')
    runtest(starter)
