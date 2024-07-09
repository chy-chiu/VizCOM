@echo off
echo Building application...
pyinstaller CardiacMap.py
echo Zipping CardiacMap application...
powershell -Command "Compress-Archive -Path 'dist\CardiacMap' -DestinationPath 'cardiacmap.zip'"
echo Built CardiacMap v0.0.6
pause