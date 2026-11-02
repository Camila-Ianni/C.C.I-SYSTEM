#!/usr/bin/env bash
# ==============================================================================
# C.C.I. SYSTEM — VIRTUAL CONSOLE EMULATOR (macOS Launcher)
# Autora: Camila Carolina Ianni
# ==============================================================================
set -e
cd "$(dirname "$0")"

echo ""
echo "  ================================================================"
echo "      ██████╗     ██████╗    ██╗     ███████╗██╗   ██╗███████╗    "
echo "     ██╔════╝    ██╔════╝    ██║     ██╔════╝╚██╗ ██╔╝██╔════╝    "
echo "     ██║         ██║         ██║     ███████╗ ╚████╔╝ ███████╗    "
echo "     ██║         ██║         ██║     ╚════██║  ╚██╔╝  ╚════██║    "
echo "     ╚██████╗    ╚██████╗    ██║     ███████║   ██║   ███████║    "
echo "      ╚═════╝     ╚═════╝    ╚═╝     ╚══════╝   ╚═╝   ╚══════╝    "
echo "                  C.C.I. VIRTUAL CONSOLE v2.0                     "
echo "                  Autora: Camila Carolina Ianni                   "
echo "  ================================================================"
echo ""

# 1. Detectar Python 3
PY_CMD=""
for cmd in python3 python; do
    if command -v $cmd >/dev/null 2>&1; then
        VER=$($cmd -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$VER" -eq 3 ]; then
            PY_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PY_CMD" ]; then
    echo "[!] ERROR: No se encontró Python 3 instalado en tu Mac."
    echo "    Por favor descarga e instala Python 3 desde: https://www.python.org/downloads/"
    echo "    O usando Homebrew: brew install python"
    echo ""
    read -p "Presiona ENTER para cerrar..." _
    exit 1
fi

echo "[1/3] Python detectado: $($PY_CMD --version)"

# 2. Configurar entorno virtual local si no existe
if [ ! -d ".venv" ]; then
    echo "[2/3] Configurando entorno virtual local (.venv)..."
    $PY_CMD -m venv .venv
fi

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    PY_RUN=".venv/bin/python"
    PIP_RUN=".venv/bin/pip"
else
    PY_RUN="$PY_CMD"
    PIP_RUN="$PY_CMD -m pip"
fi

# 3. Comprobar e instalar dependencias esenciales
if ! $PY_RUN -c "import pygame, cv2, numpy, pymunk" >/dev/null 2>&1; then
    echo "[2/3] Instalando dependencias de C.C.I. System (Pygame-CE, OpenCV, NumPy, PyMunk)..."
    $PIP_RUN install --upgrade pip >/dev/null 2>&1 || true
    $PIP_RUN install -r requirements.txt
else
    echo "[2/3] Dependencias verificadas correctamente."
fi

# 4. Lanzar consola virtual
echo "[3/3] Iniciando C.C.I. SYSTEM Virtual Console..."
echo ""
$PY_RUN main.py
