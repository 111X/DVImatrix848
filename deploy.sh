#!/bin/sh

cd "${0%/*}"

## cleanup old stuff
rm -rf dist
rm -rf DVImatrix848

## build python script into an exe
python2.7 ./setup.py py2exe

## build autohotkey script into an exe
AHKSCRIP=DVImatrix848key
"${PROGRAMFILES}/AutoHotkey/Compiler/Ahk2Exe.exe" /in "${AHKSCRIPT}.ahk" /out "dist/${AHKSCRIPT}.exe" /icon "media/${AHKSCRIPT}.ico"

## rename dist folder
mv dist DVImatrix848

## and zip it
zip -r DVImatrix848.zip DVImatrix848


