@echo off
rem Bakes North Ambria in its own background Blender (never touches open Blender windows). About 1-2 minutes.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
echo Baking North Ambria...
%BL% --background --factory-startup --python "%ST%north_ambria\src\run_na.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%north_ambria\src\cache\_log_bat.txt" 2>&1
echo Done.
