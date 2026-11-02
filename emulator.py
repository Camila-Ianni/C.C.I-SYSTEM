#!/usr/bin/env python3
"""emulator.py - Lanzador universal multiplataforma 100% Python de C.C.I. SYSTEM.
Funciona idénticamente en macOS, Windows y Linux sin depender de scripts bash o batch.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

REQUIRED_PACKAGES = {
    "pygame": "pygame-ce>=2.5.0",
    "cv2": "opencv-python>=4.8.0",
    "numpy": "numpy>=1.24.0",
    "pymunk": "pymunk>=6.5.0",
}


def print_banner():
    os_name = platform.system()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print("\n" + "=" * 64)
    print("      C.C.I. SYSTEM — VIRTUAL CONSOLE & RETRO EMULATOR")
    print("      Arquitectura: 100% Python (Multiplataforma)")
    print(f"      Sistema Operativo: {os_name} | Python: {py_ver}")
    print("      Autora: Camila Carolina Ianni")
    print("=" * 64 + "\n")


def check_and_install_dependencies():
    missing = []
    for module_name, pkg_req in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pkg_req)

    if missing:
        print(f"[C.C.I. System] Dependencias faltantes detectadas: {', '.join(missing)}")
        print("[C.C.I. System] Instalando automáticamente vía pip en Python...")
        try:
            req_file = ROOT / "requirements.txt"
            if req_file.exists():
                cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
            else:
                cmd = [sys.executable, "-m", "pip", "install"] + missing
            subprocess.check_call(cmd)
            print("[C.C.I. System] Dependencias instaladas con éxito.\n")
        except Exception as exc:
            print(f"[C.C.I. System] Error al instalar dependencias: {exc}")
            print("Por favor ejecuta manualmente: pip install -r requirements.txt")
            sys.exit(1)
    else:
        print("[C.C.I. System] Todas las dependencias Python están listas y verificadas.")


def run():
    print_banner()
    check_and_install_dependencies()

    # Lanzar la consola virtual principal
    print("[C.C.I. System] Iniciando consola virtual C.C.I. SYSTEM...\n")
    try:
        from main import main as console_main
        sys.exit(console_main())
    except Exception as exc:
        print(f"\n[C.C.I. System] Error durante la ejecución del emulador: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    run()
