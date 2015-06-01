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

from distutils.version import LooseVersion


def _stripVersionString(version_string):
    if version_string.startswith('v'):
        version_string = version_string[1:]
    return version_string.strip()


def _getLatestVersion(j):
    v = None
    # print("latest: %s" % (j))
    for k in j:
        try:
            version_string = _stripVersionString(k['tag_name'])
        except TypeError:
            continue
        vnew = LooseVersion(version_string)
        if not v:
            v = vnew
        else:

            if vnew > v:
                v = vnew
    if v:
        return str(v)
    return None


def getGithubVersion(project):
    import requests
    url = ("https://api.github.com/repos/%s/releases" % project)
    try:
        r = requests.get(url)
    except requests.exceptions.ConnectionError:
        return None
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        return None
    try:
        j = r.json()
    except ValueError:
        return None
    return _getLatestVersion(j)


def getCurrentVersion():
    data = None
    try:
        with open('version.txt') as f:
            data = f.read()
    except IOError:
        return None
    if not data:
        return None
    return _stripVersionString(data.split()[-1])


def isNewer(newversion, oldversion):
    """
    returns True if newversion is newer than oldversion,
    None if they are the same,
    and False otherwise"""
    if not oldversion:
        return None
    if not newversion:
        return None
    if oldversion == newversion:
        return None
    try:
        return LooseVersion(oldversion) < LooseVersion(newversion)
    except (TypeError, AttributeError):
        return None


if __name__ == '__main__':
    current_version = getCurrentVersion()
    github_version = getGithubVersion("iem-projects/DVImatrix848")
    if github_version:
        if current_version:
            if LooseVersion(current_version) < LooseVersion(github_version):
                print("new version available: '%s' (deprecating '%s')"
                      % (github_version, current_version))
            else:
                print("congrats: version '%s' is up-to-date (>=%s)"
                      % (current_version, github_version))
        else:
            print("unable to determine current version."
                  "last released version is '%s'" % github_version)
    else:
        if current_version:
            print("unable to determine last release."
                  "current version is '%s'" % current_version)
        else:
            print("unable to determine version")
