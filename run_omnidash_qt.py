"""run_omnidash_qt.py - Lanzador oficial de OmniDash Frutiger Aero en PySide6.
C.C.I. SYSTEM v2.1.0 — Arquitectura desacoplada de alto rendimiento.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

# Configurar variables de entorno Qt
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from omnidash_qt import OmniDashMainWindow, AERO_STYLE_SHEET


def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setApplicationName("C.C.I. SYSTEM — OmniDash Virtual Console")
    app.setStyleSheet(AERO_STYLE_SHEET)

    window = OmniDashMainWindow()
    window.show()

    print("[C.C.I. SYSTEM] OmniDash Frutiger Aero (PySide6) iniciado exitosamente.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
