#MaxHotkeysPerInterval 200
#NoTrayIcon
;#InstallKeybdHook

#IfWinActive ahk_exe dota2.exe

!SC029::F8
F6::Esc

LWin::F6
SC056::F9
Esc::F10
CapsLock::F11

NumpadAdd::
send {Enter}
Sleep, 10
SendInput, ^v
Sleep,  990
send {Esc}
return

; FOR SELECT ALLIES THING

!1::
send !1
sleep 10
send !1
return

!2::
send !2
sleep 10
send !2
return

!3::
send !3
sleep 10
send !3
return

!4::
send !4
sleep 10
send !4
return

!5::
send !5
sleep 10
send !5
return

; FOR SCRENSHOTS

#If Getkeystate("LShift","p")
LWin & S::Run, explorer ms-screenclip:

#If Getkeystate("LWin","p")
LShift & S::Run, explorer ms-screenclip:

; LEAGUE TERRITORY 

#IfWinActive ahk_exe `League of Legends.exe

; WheelUp:: ; we cant have WheelUp set up because league zooms in on my champ with that thing anyway

WheelDown::
send {F3}
return

SC029::F9
LWin::F10
CapsLock::F11

<#D:: ComObjCreate("Shell.Application").ToggleDesktop()

#If Getkeystate("CapsLock","p")
A::
send !a
return

#IfWinActive ahk_exe `VALORANT-Win64-Shipping.exe

LWin::F10
CapsLock::F9
SC029::F8 ; it's tilda key

#If