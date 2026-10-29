@echo off
rem Bakes the Depths of the Old Schoolhouse stage in a background Blender (about 3 minutes).
rem It never touches any Blender window you have open.
echo Baking Depths of the Old Schoolhouse... this window closes by itself when it is done.
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --background --factory-startup --python "%~dp0run_sd.py" -- STEPS=build,bake,pv,export TAG=v1 CAMS=CAM_mid > "%~dp0cache\_log.txt" 2>&1
echo Done.
