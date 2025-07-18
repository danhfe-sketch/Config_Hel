@echo off
echo Building LT32Pro Configurator...

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Run PyInstaller with the fixed spec file
python -m PyInstaller LT32Pro_Configurator_v1_fixed.spec

echo Build complete. Check the dist folder for the executable.
pause