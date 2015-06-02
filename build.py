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

# what this script does:
# - remove leftovers from previous runs
# - build DVImatrix848 into w32 executable
# - build hotkey scripts into w32 executable
# - store current (git) version
# - zip it
# - cleanup


import os.path
import sys
_SCRIPTDIR = os.path.dirname(os.path.abspath(sys.argv[0]))
_VERSION = ''
BASENAME = 'DVImatrix848'


def getVersion(force=False):
    global _VERSION
    if not force and _VERSION:
        return _VERSION
    import subprocess
    # the following gives us: <tagname>-<ticks>-<committish>
    try:
        longtag = subprocess.check_output(
            ['git', 'describe', '--long', '--tags'])
    except subprocess.CalledProcessError:
        # unable to determine version, giving up
        _VERSION = ''
        return _VERSION
    modified = False
    try:
        modified = subprocess.check_output(
            ['git', 'status', '--untracked-files=normal', '--porcelain'])
        if modified:
            modified = True
        else:
            modified = False
    except subprocess.CalledProcessError:
        modified = True
    longtag = longtag.split()[-1].split('-')
    tagname = '-'.join(longtag[0:-2])
    tick = longtag[-2]
    _VERSION = '+'.join([tagname, tick])
    if modified:
        _VERSION += '*'
    return _VERSION


def cleanup():
    # delete dist/ and DVImatrix848/ folders
    import shutil
    for d in ['dist', BASENAME]:
        d = os.path.join(_SCRIPTDIR, d)
        if os.path.exists(d):
            shutil.rmtree(d)


def build_exe():
    # run py2exe
    # mv dist/ to DVImatrix848 folder
    import distutils.core
    import shutil
    import os

    distutils.core.run_setup('setup.py', ['py2exe'])
    # FIXXME: check whether DVImatrix848 exists
    shutil.move('dist', BASENAME)


def build_ahk():
    # run ahk2exe
    import subprocess

    ProgramFiles = os.path.expandvars('%ProgramFiles%')
    ahk2exe = os.path.join(
        ProgramFiles,
        'AutoHotkey',
        'Compiler',
        'Ahk2Exe.exe'
        )
    ahk = 'DVImatrix848key'
    infile = ('%s.ahk' % (ahk))
    outfile = os.path.join(BASENAME, ('%s.exe' % (ahk)))
    iconfile = os.path.join('media', ('%s.ico' % (ahk)))

    subprocess.check_call([ahk2exe,
                           '/in', infile,
                           '/out', outfile,
                           '/icon', iconfile])


def store_version():
    # run git to get current version, and put it into a file
    v = getVersion()
    if v:
        outfile = os.path.join(BASENAME, 'version.txt')
        with open(outfile, 'w') as f:
            f.write(v+'\n')


def zipit():
    # store the folder contents in a zip file
    import shutil
    v = getVersion()
    basename = BASENAME
    if v:
        filename = '_'.join(basename, v)
    else:
        filename = basename
    shutil.make_archive(filename, 'zip', base_dir=basename)


if __name__ == '__main__':
    cleanup()
    build_exe()
    build_ahk()
    store_version()
    zipit()
    cleanup()
