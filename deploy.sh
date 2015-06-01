#!/bin/sh


cd "${0%/*}"

getrevision() {
    local REV
    local SHORTREV
    local TICK
    REV=$(git describe --long --tags 2>/dev/null | sed -e 's|-[^-]*$||')
    if [  -x "${REV}" ]; then
        SHORTREV=$(git rev-parse --short HEAD 2>/dev/null)
        TICK=$(git rev-list --count HEAD 2>/dev/null)
        if [ "${TICK}" -gt 0 ]; then
          REV="${SHORTREV}+${TICK}"
        fi
    else
        TICK=${REV##*-}
        TICK=$((TICK+0))
        if [ ${TICK} -lt 1 ]; then
          REV="${REV%-*}"
        else
          REV="${REV%-*}+${TICK}"
        fi
    fi
    test -z "$(git status --untracked-files=normal --porcelain 2>/dev/null)" || REV="${REV}*"
    echo "${REV}"
}

## cleanup old stuff
rm -rf dist
rm -rf DVImatrix848

## build python script into an exe
python ./setup.py py2exe

## build autohotkey script into an exe
AHKSCRIPT=DVImatrix848key
"${PROGRAMFILES}/AutoHotkey/Compiler/Ahk2Exe.exe" //in "${AHKSCRIPT}.ahk" //out "dist/${AHKSCRIPT}.exe" //icon "media/${AHKSCRIPT}.ico"

## create version-file
getrevision > dist/version.txt

## rename dist folder
mv dist DVImatrix848

## and zip it
zip -r DVImatrix848.zip DVImatrix848


