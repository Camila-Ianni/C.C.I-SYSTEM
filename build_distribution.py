#!/usr/bin/env python3
"""build_distribution.py - Genera los paquetes ZIP limpios (0 perfiles) para Mac y Windows."""
from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS_DIR = ROOT / "web" / "static" / "downloads"

EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".gemini", "brain",
    "capturas", "node_modules", "web/static/downloads"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".DS_Store"}


def _should_include(file_path: Path, rel_str: str) -> bool:
    parts = rel_str.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return False
    if file_path.suffix in EXCLUDE_EXTS:
        return False
    # Excluir perfiles de usuario locales para que la descarga sea 100% limpia (0 perfiles)
    if ".cci-user-data" in parts:
        if file_path.name in ("active_user.json", "system.json"):
            return False
        if "users" in parts and file_path.suffix == ".json":
            return False
    # Excluir zips previos generados
    if file_path.suffix == ".zip":
        return False
    return True


def create_release_zip(target_platform: str, out_zip: Path):
    print(f"[Build] Empaquetando C.C.I. SYSTEM para {target_platform}...")
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    temp_zip = out_zip.with_suffix(".tmp")
    if temp_zip.exists():
        temp_zip.unlink()

    included_count = 0
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # Añadir estructura limpia de .cci-user-data/users/ vacía
        zf.writestr("CCI_System/.cci-user-data/users/.gitkeep", "")

        for root_dir, dirs, files in os.walk(ROOT):
            r_path = Path(root_dir)
            # Evitar explorar carpetas excluidas grandes
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp")]

            for fname in files:
                fpath = r_path / fname
                rel = fpath.relative_to(ROOT)
                rel_str = str(rel)

                if _should_include(fpath, rel_str):
                    arcname = f"CCI_System/{rel_str}"
                    zinfo = zipfile.ZipInfo.from_file(fpath, arcname=arcname)
                    zf.writestr(zinfo, fpath.read_bytes())
                    included_count += 1

    if out_zip.exists():
        out_zip.unlink()
    temp_zip.rename(out_zip)
    size_mb = out_zip.stat().st_size / (1024 * 1024)
    print(f"[Build] {target_platform} listo: {out_zip.name} ({size_mb:.1f} MB, {included_count} archivos incluidos)")


def build_all():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    mac_zip = DOWNLOADS_DIR / "CCI_System_macOS.zip"
    win_zip = DOWNLOADS_DIR / "CCI_System_Windows.zip"

    create_release_zip("macOS", mac_zip)
    create_release_zip("Windows", win_zip)
    print("[Build] ¡Empaquetado de ambos emuladores completado con éxito!")


if __name__ == "__main__":
    build_all()
