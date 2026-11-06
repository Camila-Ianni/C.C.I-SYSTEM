#!/usr/bin/env python3
"""
mobile/build_apk.py - Script de automatización y validación del empaquetado APK para Android con Buildozer.

Permite:
1. Validar la configuración de `buildozer.spec` y dependencias (SDK, NDK, Java).
2. Verificar compatibilidad del árbol de archivos antes de compilar.
3. Ejecutar `buildozer android debug` o `release` con diagnóstico detallado.
"""
from __future__ import annotations

import argparse
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys


def validate_spec(spec_path: Path) -> dict[str, str]:
    """Lee y valida buildozer.spec asegurando directivas esenciales."""
    if not spec_path.is_file():
        raise FileNotFoundError(f"buildozer.spec no encontrado en {spec_path}")

    config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
    config.read(spec_path)

    if not config.has_section("app"):
        raise ValueError("Sección [app] no encontrada en buildozer.spec")

    app_sec = config["app"]
    required_keys = ["title", "package.name", "package.domain", "requirements", "orientation", "android.permissions"]
    missing = [k for k in required_keys if k not in app_sec]
    if missing:
        raise ValueError(f"Faltan claves requeridas en buildozer.spec: {missing}")

    return dict(app_sec)


def check_toolchain_environment() -> dict[str, bool]:
    """Comprueba herramientas y variables de entorno para compilar en Android."""
    results = {
        "buildozer_installed": shutil.which("buildozer") is not None,
        "java_installed": shutil.which("java") is not None,
        "javac_installed": shutil.which("javac") is not None,
        "adb_installed": shutil.which("adb") is not None,
        "has_android_sdk": bool(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")),
        "has_android_ndk": bool(os.environ.get("ANDROID_NDK_HOME") or os.environ.get("NDK_HOME")),
        "has_java_home": bool(os.environ.get("JAVA_HOME")),
    }
    return results


def run_preflight_checks(root_dir: Path) -> bool:
    """Ejecuta chequeos previos para garantizar que el proyecto es apto para Android."""
    print("=== C.C.I. SYSTEM — Android Pre-flight Check ===")

    spec_path = root_dir / "buildozer.spec"
    try:
        spec_info = validate_spec(spec_path)
        print(f" [OK] buildozer.spec válido.")
        print(f"      App: {spec_info.get('title')} ({spec_info.get('package.name')})")
        print(f"      Requirements: {spec_info.get('requirements')}")
        print(f"      Orientation: {spec_info.get('orientation')}")
    except Exception as e:
        print(f" [FAIL] Error en buildozer.spec: {e}")
        return False

    # Chequeo de archivos principales
    main_py = root_dir / "main.py"
    if not main_py.is_file():
        print(" [FAIL] main.py no encontrado en la raíz.")
        return False
    print(" [OK] main.py encontrado.")

    # Chequeo de módulo mobile
    mobile_adapter = root_dir / "mobile" / "mobile_adapter.py"
    touch_controls = root_dir / "mobile" / "touch_controls.py"
    if not mobile_adapter.is_file() or not touch_controls.is_file():
        print(" [FAIL] Módulos móviles no encontrados en mobile/.")
        return False
    print(" [OK] mobile/mobile_adapter.py y mobile/touch_controls.py presentes.")

    # Chequeo de entorno
    env_status = check_toolchain_environment()
    print("--- Estado de la Toolchain Android ---")
    for tool, ok in env_status.items():
        status_sym = "[OK]" if ok else "[INFO/MISSING]"
        print(f"  {status_sym} {tool}: {ok}")

    return True


def execute_build(mode: str = "debug") -> int:
    """Invoca buildozer para compilar el APK."""
    cmd = ["buildozer", "android", mode]
    print(f"\nEjecutando: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, check=True)
        return res.returncode
    except subprocess.CalledProcessError as e:
        print(f"Buildozer falló con código {e.returncode}")
        return e.returncode
    except FileNotFoundError:
        print("Buildozer no está instalado en este sistema. Instalar con: pip install buildozer")
        return 127


def main():
    parser = argparse.ArgumentParser(description="Empaquetador y verificador APK para C.C.I. SYSTEM")
    parser.add_argument("--dry-run", action="store_true", help="Solo validar entorno y spec")
    parser.add_argument("--build", choices=["debug", "release"], help="Compilar APK")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parent.parent
    ok = run_preflight_checks(root_dir)

    if not ok:
        sys.exit(1)

    if args.build:
        code = execute_build(args.build)
        sys.exit(code)
    else:
        print("\nPre-flight check completado con éxito. Usa --build debug para iniciar compilación.")
        sys.exit(0)


if __name__ == "__main__":
    main()
