#!/usr/bin/env python3
"""Instalar_CCI_System.pyw - Instalador gráfico de 1-clic para Windows.
Se ejecuta de forma nativa sin abrir ventana de comandos (consola negra).
Autora: Camila Carolina Ianni
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import installer

if __name__ == "__main__":
    installer.install_and_launch()
