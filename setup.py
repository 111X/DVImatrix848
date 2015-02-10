from distutils.core import setup
import os


if os.name == 'nt':
    import py2exe
    setup(windows=['DVImatrix848.py'])
    #setup(console=['DVImatrix848.py'])
