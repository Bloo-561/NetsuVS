@echo off
rem Builds and bakes North Ambria in its own background Blender (never touches Blender windows you have open),
rem exports it for Godot and renders the final camera image (north_ambria\renders\final_CAM_mid.png). ~30 min.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
if not exist "%ST%north_ambria\src\cache" mkdir "%ST%north_ambria\src\cache"
echo North Ambria...
%BL% --background --factory-startup --python "%ST%north_ambria\src\run_na.py" -- STEPS=build,bake,preview,export,beauty CAMS=CAM_mid,CAM_far > "%ST%north_ambria\src\cache\_log_storm.txt" 2>&1
echo Done. You can close this window.
pause
