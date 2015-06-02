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


class autostarter_base(object):
    def __init__(self, name, executable):
        super(autostarter_base, self).__init__()
        self.name = name
        self.executable = executable

    def exists(self):
        """returns True if there is already an autostarter called <name>"""
        raise NotImplementedError('autostarter::exists')

    def create(self):
        """creates a new autostarter <name>
        On success returns True, else False
        """
        raise NotImplementedError('autostarter::create')

    def delete(self):
        """deletes an existing autostarter <name>
        On success returns True, else False
        """
        raise NotImplementedError('autostarter::delete')

    def toggle(self):
        """creates a new autostarter if non exists; else it deletes it!
        returns True if an autostarter exists after this call, else False
        """
        if self.exists():
            return not self.delete()
        else:
            return self.create()
