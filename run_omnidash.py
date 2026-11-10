"""run_omnidash.py - Lanzador oficial de OmniDash en PySide6 (C.C.I. SYSTEM).
C.C.I. SYSTEM v2.1.0 — Arquitectura desacoplada de alto rendimiento.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import sys
import os

# Configurar variables de entorno Qt
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from omnidash_qt import OmniDashMainWindow, AERO_STYLE_SHEET, run_qt_app


def main():
    return run_qt_app()


if __name__ == "__main__":
    sys.exit(main())

