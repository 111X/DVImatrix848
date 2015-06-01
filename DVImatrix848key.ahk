; DVImatrix848-hotkey

;     ScrollLock-ScrollLock

; this authotkey script creates a global shortcut
; that will load a default ("emergency") routing matrix into DVImatrix848
; (e.g. if you accidentally switched off the monitor that shows the
;  DVImatrix848 window)
; If DVImatrix848 is running, it will simply send a "restore emergency matrix" command
; if DVImatrix848 is not running, it is started (and emergency matrix is loaded)

#NoEnv  ; Recommended for performance and compatibility with future AutoHotkey releases.
; #Warn  ; Enable warnings to assist with detecting common errors.
SendMode Input  ; Recommended for new scripts due to its superior speed and reliability.
SetWorkingDir %A_ScriptDir%  ; Ensures a consistent starting directory.




#IfWinExist ahk_exe DVImatrix848.exe
; case#1: DVImatrix848 is already running

; we use double-press ScrollLock as hotkey
ScrollLock::
if (A_PriorHotkey <> "ScrollLock" or A_TimeSincePriorHotkey > 400)
{
  ; not a double-press, discard
  KeyWait, ScrollLock
  Return
}
 ; activate the DVImatrix
 WinActivate
 Send, ^+r
Return

; for testing::
; ^j::
; MsgBox, window found



#IfWinExist
; case#2: DVImatrix848 is NOTrunning

ScrollLock::
if (A_PriorHotkey <> "ScrollLock" or A_TimeSincePriorHotkey > 400)
{
  ; not a double-press, discard
  KeyWait, ScrollLock
  Return
}
; not running, so start (with '-r' to automatically load the matrix)
run, DVImatrix848.exe -r
Return

; for testing::
; ^j::
; MsgBox, window not found

