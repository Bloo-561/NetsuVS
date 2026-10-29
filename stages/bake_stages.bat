@echo off
rem Bakes the 3D stages that are waiting for a bake, each in its own background Blender.
rem It never opens or touches any Blender window you have open. Takes about 5-8 minutes in total.
set BL="C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
set ST=%~dp0
echo [1/3] Depths of the Old Schoolhouse...
%BL% --background --factory-startup --python "%ST%schoolhouse_depths\src\run_sd.py" -- STEPS=build,bake,pv,export TAG=v2 CAMS=CAM_mid > "%ST%schoolhouse_depths\src\cache\_log.txt" 2>&1
echo [2/3] Celdic - Day...
%BL% --background --factory-startup --python "%ST%celdic\src\run_ce.py" -- VARIANT=day STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%celdic\src\cache\_log_day.txt" 2>&1
echo [3/3] Celdic - Burning...
%BL% --background --factory-startup --python "%ST%celdic\src\run_ce.py" -- VARIANT=burning STEPS=build,bake,preview,export CAMS=CAM_mid > "%ST%celdic\src\cache\_log_burning.txt" 2>&1
echo Done. You can close this window.
pause
