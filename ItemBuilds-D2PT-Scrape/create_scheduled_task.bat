@REM This didn't quite work... Need more research.

@echo off
setlocal

set taskname=D2UpdateBuilds
set scriptpath=%~dp0main.py

schtasks /delete /tn %taskname% /f >nul 2>&1
schtasks /Create /TN %taskname% /TR "pythonw.exe %scriptpath%" /SC WEEKLY /F

if %errorlevel% equ 0 (
    echo Task "%taskname%" created successfully.
) else (
    echo Failed to create task "%taskname%".
    exit /b %errorlevel%
)

schtasks /Run /TN %taskname%
endlocal
pause