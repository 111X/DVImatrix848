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


if os.name == 'nt':
    from glob import glob
    ## urgh, find the msvcrt redistributable DLLs
    ## either it's in the MSVC90 application folder
    ## or in some winsxs folder
    program_path=os.path.expandvars('%ProgramFiles%')
    winsxs_path=os.path.expandvars('%SystemRoot%\WinSXS')
    msvcrt_paths=[(r'%s\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT' % program_path)]
    ## python2.7 seems to be built against VC90 (9.0.21022), so let's try that
    msvcrt_paths+=glob(r'%s\x86_microsoft.vc90.crt_*_9.0.21022.8_*_*' "\\" % winsxs_path)
    data_files=None
    for p in msvcrt_paths:
        if os.path.exists(os.path.join(p, 'msvcp90.dll')):
            data_files = [("Microsoft.VC90.CRT",
                           glob(r'%s\*.*' % p))]
            sys.path.append(p)
            break
    import py2exe
    setup(windows=['DVImatrix848.py'],
          data_files=data_files,
          dll_excludes='MSVCP90.dll',
          )
    #setup(console=['DVImatrix848.py'])
