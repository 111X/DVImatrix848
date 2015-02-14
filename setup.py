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
    import win32com, sys
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    for extra in ["win32com.shell"]: #,"win32com.mapi"
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
    ## urgh, find the msvcrt redistributable DLLs
    ## either it's in the MSVC90 application folder
    ## or in some winsxs folder
    program_path=os.path.expandvars('%ProgramFiles%')
    winsxs_path=os.path.expandvars('%SystemRoot%\WinSXS')
    msvcrt_paths=[(r'%s\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT' % program_path)]
    ## python2.7 seems to be built against VC90 (9.0.21022), so let's try that
    msvcrt_paths+=glob(r'%s\x86_microsoft.vc90.crt_*_9.0.21022.8_*_*' "\\" % winsxs_path)
    for p in msvcrt_paths:
        if os.path.exists(os.path.join(p, 'msvcp90.dll')):
            sys.path.append(p)
            return glob(r'%s\*.*' % p)
    return None
if os.name == 'nt':
    data_files=[]
    f=getMSVCfiles()
    if f:
        data_files += [("Microsoft.VC90.CRT", f)]

    data_files += [('media', glob(r'media\*.*'))]

    import py2exe
    setup(windows=[{
        'script': 'DVImatrix848.py',
        'icon_resources': [(1, "media\DVImatrix848.ico")]
        }],
        data_files=data_files,
        )
    #setup(console=['DVImatrix848.py'])
