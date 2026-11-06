#!/usr/bin/env python3
"""
ios/build_ios.py - Validador y preparador de empaquetado iOS para C.C.I. SYSTEM.

Comprueba:
1. Validez sintáctica y claves mandatorias en `ios/Info.plist` (incluyendo permiso de micrófono).
2. Detección de herramientas de desarrollo Apple (Xcode, xcrun, simctl, codesign).
3. Entorno de empaquetado para distribución vía TestFlight / App Store.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys


def validate_info_plist(plist_path: Path) -> dict:
    """Lee y comprueba los campos obligatorios de Info.plist para iOS."""
    if not plist_path.is_file():
        raise FileNotFoundError(f"Info.plist no encontrado en {plist_path}")

    with open(plist_path, "rb") as fp:
        data = plistlib.load(fp)

    required_keys = [
        "CFBundleIdentifier",
        "CFBundleDisplayName",
        "CFBundleShortVersionString",
        "NSMicrophoneUsageDescription",
        "UISupportedInterfaceOrientations",
    ]

    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Faltan claves requeridas en Info.plist: {missing}")

    # Verificar que el permiso de micrófono no esté vacío
    if not data["NSMicrophoneUsageDescription"].strip():
        raise ValueError("NSMicrophoneUsageDescription no puede estar vacío (requerido para WebRTC).")

    # Verificar orientación Landscape
    orientations = data.get("UISupportedInterfaceOrientations", [])
    if not any("Landscape" in o for o in orientations):
        raise ValueError("UISupportedInterfaceOrientations debe incluir al menos una orientación Landscape.")

    return data


def check_apple_toolchain() -> dict[str, bool]:
    """Verifica si el entorno macOS cuenta con las herramientas de compilación de iOS."""
    results = {
        "is_macos": sys.platform == "darwin",
        "has_xcode_select": shutil.which("xcode-select") is not None,
        "has_xcrun": shutil.which("xcrun") is not None,
        "has_codesign": shutil.which("codesign") is not None,
        "has_kivy_ios": shutil.which("toolchain") is not None,
        "has_briefcase": shutil.which("briefcase") is not None,
    }
    return results


def run_ios_preflight(root_dir: Path) -> bool:
    """Ejecuta chequeos previos de preparación para iOS."""
    print("=== C.C.I. SYSTEM — iOS Pre-flight Check ===")

    plist_path = root_dir / "ios" / "Info.plist"
    try:
        plist_data = validate_info_plist(plist_path)
        print(f" [OK] ios/Info.plist válido.")
        print(f"      App: {plist_data.get('CFBundleDisplayName')} ({plist_data.get('CFBundleIdentifier')})")
        print(f"      Version: {plist_data.get('CFBundleShortVersionString')}")
        print(f"      Mic Description: {plist_data.get('NSMicrophoneUsageDescription')[:40]}...")
    except Exception as e:
        print(f" [FAIL] Error en ios/Info.plist: {e}")
        return False

    # Entitlements
    entitlements_path = root_dir / "ios" / "Entitlements.plist"
    if not entitlements_path.is_file():
        print(" [FAIL] ios/Entitlements.plist no encontrado.")
        return False
    print(" [OK] ios/Entitlements.plist encontrado.")

    # Proyecto nativo Xcode
    xcode_proj = root_dir / "ios" / "CCI_System.xcodeproj"
    if not xcode_proj.exists():
        print(" [FAIL] ios/CCI_System.xcodeproj no encontrado.")
        return False
    print(" [OK] ios/CCI_System.xcodeproj encontrado.")

    # Módulo mobile/ios_adapter.py
    adapter_path = root_dir / "mobile" / "ios_adapter.py"
    if not adapter_path.is_file():
        print(" [FAIL] mobile/ios_adapter.py no encontrado.")
        return False
    print(" [OK] mobile/ios_adapter.py encontrado.")

    # Toolchain
    status = check_apple_toolchain()
    print("--- Estado de la Toolchain Apple / iOS ---")
    for tool, ok in status.items():
        sym = "[OK]" if ok else "[INFO/MISSING]"
        print(f"  {sym} {tool}: {ok}")

    return True


def execute_ios_build(root_dir: Path, configuration: str = "Release") -> int:
    """Compila el proyecto Xcode usando xcodebuild."""
    proj_path = root_dir / "ios" / "CCI_System.xcodeproj"
    cmd = [
        "xcodebuild",
        "-project", str(proj_path),
        "-scheme", "CCISystem",
        "-configuration", configuration,
        "CODE_SIGNING_ALLOWED=NO",
        "build"
    ]
    print(f"\nEjecutando: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True)
        return res.returncode
    except subprocess.CalledProcessError as e:
        print(f"xcodebuild falló con código {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("xcodebuild no encontrado. Asegúrese de tener Xcode instalado.")
        return 127


def main():
    parser = argparse.ArgumentParser(description="Verificador y empaquetador iOS para C.C.I. SYSTEM")
    parser.add_argument("--dry-run", action="store_true", help="Solo validar plist y entorno")
    parser.add_argument("--build", action="store_true", help="Compilar proyecto Xcode nativo")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    ok = run_ios_preflight(root_dir)

    if not ok:
        sys.exit(1)

    if args.build:
        code = execute_ios_build(root_dir)
        sys.exit(code)

    print("\nPre-flight check de iOS completado con éxito.")
    sys.exit(0)


if __name__ == "__main__":
    main()
