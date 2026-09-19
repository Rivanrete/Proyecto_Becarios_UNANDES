@echo off
REM Genera dist\BecariosUNANDES.exe (doble clic, sin consola).
REM Reejecutar este script tras cada cambio. Requiere: pip install pyinstaller pillow
python -m PyInstaller --noconfirm --clean --name BecariosUNANDES --onefile --windowed --icon app\assets\icono-unandes.ico --add-data "app\assets;assets" BecariosUNANDES.py
echo.
echo Ejecutable en: dist\BecariosUNANDES.exe
