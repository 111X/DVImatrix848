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
import _winreg as wr
from autostarter import autostarter_base


class autostarter(autostarter_base):
    def __init__(self, name, executable):
        super(autostarter, self).__init__(name, executable)
        path=r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        self._registry=wr.ConnectRegistry(None, wr.HKEY_CURRENT_USER)
        self._key=wr.OpenKey(self._registry, path, 0, KEY_WRITE)

    def exists(self):
        """returns True if there is already an autostarter called <name>"""
        try:
            v=wr.QueryValueEx(self._key, self.name)
        except WindowsError:
            return False
        return True

    def create(self):
        """creates a new autostarter <name>
        On success returns True, else False
        """
        try:
            wr.SetValueEx(self._key, self.name, 0, REG_SZ, self.executable)
        except EnvironmentError as e:
            print("OOPS[%s] regwriting '%s' failed: %s"
                  % (type(e), self.name, e))
            return False
        return True

    def delete(self):
        """deletes an existing autostarter <name>
        On success returns True, else False
        """
        try:
            wr.DeleteValue(self._key, self.name)
        except Exception as e:
            print("OOPS[%s] regremoving '%s' failed: %s"
                  % (type(e), self.name, e))
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

if __name__ == '__main__':
    import sys

    def runtest(starter):
        print("autostart: %s -> %s" % (starter.name, starter.executable))
        if starter.exists():
            print("autostarter '%s' already exists. STOPPING" % (starter.name))
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
    runtest(starter)
