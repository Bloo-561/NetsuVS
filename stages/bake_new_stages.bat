@echo off
rem Bakes the stages waiting for a bake, each in its own background Blender, one after another.
rem It never opens or touches any Blender window you have open. About 10-15 minutes in total.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
echo [1/5] North Ambria...
%BL% --background --factory-startup --python "%ST%north_ambria\src\run_na.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%north_ambria\src\cache\_log_bat.txt" 2>&1
echo [2/5] Ordis Royal Manor - Day...
%BL% --background --factory-startup --python "%ST%ordis_manor\src\run_om.py" -- VARIANT=day STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%ordis_manor\src\cache\_log_day.txt" 2>&1
echo [3/5] Ordis Royal Manor - Ruined...
%BL% --background --factory-startup --python "%ST%ordis_manor\src\run_om.py" -- VARIANT=ruined STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%ordis_manor\src\cache\_log_ruined.txt" 2>&1
echo [4/5] Old Schoolhouse -Entrance-...
%BL% --background --factory-startup --python "%ST%schoolhouse_entrance\src\run_se.py" -- STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%schoolhouse_entrance\src\cache\_log_night.txt" 2>&1
echo [5/5] The GeoFront (new vault version)...
%BL% --background --factory-startup --python "%ST%geofront\src\run_gf.py" -- VARIANT=vault STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%geofront\src\cache\_log_vault.txt" 2>&1
echo Done. You can close this window.
pause
