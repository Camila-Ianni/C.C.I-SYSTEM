@echo off
rem ==============================================================================
rem C.C.I. SYSTEM — VIRTUAL CONSOLE EMULATOR (Windows Launcher)
rem Autora: Camila Carolina Ianni
rem ==============================================================================
title C.C.I. SYSTEM — Virtual Console Emulator
cd /d "%~dp0"

echo.
echo  ================================================================
echo      C.C.I. SYSTEM — VIRTUAL CONSOLE EMULATOR v2.0               
echo      Autora: Camila Carolina Ianni                               
echo      Iniciando emulador en Windows...                            
echo  ================================================================
echo.

rem 1. Verificar Python
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=py -3
    goto :PYTHON_FOUND
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=python
    goto :PYTHON_FOUND
)

echo [!] ERROR: No se encontro Python 3 instalado en Windows.
echo     Por favor descarga e instala Python 3.10 o superior desde:
echo     https://www.python.org/downloads/windows/
echo     (IMPORTANTE: marca la casilla "Add Python to PATH" durante la instalacion)
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [1/3] Python detectado correctamente.

rem 2. Crear entorno virtual local si no existe
if not exist ".venv" (
    echo [2/3] Configurando entorno virtual local (.venv)...
    %PY_CMD% -m venv .venv
)

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set PY_RUN=.venv\Scripts\python.exe
    set PIP_RUN=.venv\Scripts\pip.exe
) else (
    set PY_RUN=%PY_CMD%
    set PIP_RUN=%PY_CMD% -m pip
)

rem 3. Comprobar e instalar dependencias
%PY_RUN% -c "import pygame, cv2, numpy, pymunk" >nul 2>nul
if %errorlevel% neq 0 (
    echo [2/3] Instalando dependencias de C.C.I. System (Pygame-CE, OpenCV, NumPy, PyMunk)...
    %PIP_RUN% install --upgrade pip >nul 2>nul
    %PIP_RUN% install -r requirements.txt
) else (
    echo [2/3] Dependencias verificadas correctamente.
)

rem 4. Lanzar consola virtual
echo [3/3] Iniciando C.C.I. SYSTEM Virtual Console...
echo.
%PY_RUN% main.py
if %errorlevel% neq 0 (
    echo.
    echo [!] La aplicacion cerro con una advertencia o codigo de error.
    pause
)
