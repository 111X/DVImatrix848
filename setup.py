# ModuleFinder can't handle runtime changes to __path__, but win32com uses them
try:
    # py2exe 0.6.4 introduced a replacement modulefinder.
    # This means we have to add package paths there, not to the built-in
    # one.  If this new modulefinder gets integrated into Python, then
    # we might be able to revert this some day.
    # if this doesn't work, try import modulefinder
    try:
        import py2exe.mf as modulefinder
    except ImportError:
        import modulefinder
    import win32com
    import sys
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]:  # ,"win32com.mapi"
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass

from distutils.core import setup
import os
from glob import glob


def getMSVCfiles():
    # urgh, find the msvcrt redistributable DLLs
    # either it's in the MSVC90 application folder
    # or in some winsxs folder
    import os
    import sys
    from glob import glob
    program_path = os.path.expandvars('%ProgramFiles%')
    winsxs_path = os.path.expandvars('%SystemRoot%\WinSXS')
    msvcrt_paths = [
        (r'%s\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT'
         % program_path)]
    # python2.7 seems to be built against VC90 (9.0.21022), so let's try that
    msvcrt_paths += glob(
        r'%s\x86_microsoft.vc90.crt_*_9.0.21022.8_*_*' "\\" % winsxs_path
        )
    for p in msvcrt_paths:
        if os.path.exists(os.path.join(p, 'msvcp90.dll')):
            sys.path.append(p)
            return glob(r'%s\*.*' % p)
    return None


def getSVGLIBfiles():
    import os
    from glob import glob

    import PySide
    return glob(
        os.path.join(
            os.path.dirname(os.path.realpath(PySide.__file__)),
            'plugins', 'imageformats', '*svg*.dll'))


def getCACERTfiles():
    import os
    from glob import glob
    import requests

    return glob(
        os.path.join(
            os.path.dirname(os.path.realpath(requests.__file__)),
            '*.pem'))
    

if os.name == 'nt':
    data_files = [("", ["about.json"])]

    f = getMSVCfiles()
    if f:
        data_files += [("Microsoft.VC90.CRT", f)]

    f = getSVGLIBfiles()
    if f:
        data_files += [("imageformats", f)]

    f = getCACERTfiles()
    if f:
        data_files += [("", f)]

    data_files += [('media', glob(r'media\*.*'))]

    import py2exe
    setup(windows=[{
        'icon_resources': [(1, "media\DVImatrix848.ico")],
        'script': 'DVImatrix848.py',
        }],
        data_files=data_files,
        options={"py2exe": {
            "includes": ['PySide.QtSvg', 'PySide.QtXml'],
            "bundle_files": 3,
            #            "optimize": 2,
            #            "compressed": True
            }
        },
        zipfile=None,
        )
    #       setup(console=['DVImatrix848.py'])
