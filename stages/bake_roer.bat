@echo off
rem Bakes Roer in its own background Blender. It never opens or touches any Blender window you have open.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
if not exist "%ST%roer\src\cache" mkdir "%ST%roer\src\cache"
echo Roer...
%BL% --background --factory-startup --python "%ST%roer\src\run_rr.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid,CAM_far > "%ST%roer\src\cache\_log_dusk.txt" 2>&1
echo Done. You can close this window.
pause
