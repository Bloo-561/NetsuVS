@echo off
rem Bakes Roer and the Septian Chapel, each in its own background Blender, one after the other.
rem It never opens or touches any Blender window you have open. A few minutes in total.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
if not exist "%ST%roer\src\cache" mkdir "%ST%roer\src\cache"
if not exist "%ST%septian_chapel\src\cache" mkdir "%ST%septian_chapel\src\cache"
echo [1/2] Roer...
%BL% --background --factory-startup --python "%ST%roer\src\run_rr.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid,CAM_far > "%ST%roer\src\cache\_log_dusk.txt" 2>&1
echo [2/2] Septian Chapel...
%BL% --background --factory-startup --python "%ST%septian_chapel\src\run_ch.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid,CAM_far > "%ST%septian_chapel\src\cache\_log_afternoon.txt" 2>&1
echo Done. You can close this window.
pause
