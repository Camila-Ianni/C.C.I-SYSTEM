#!/usr/bin/env python3
"""build_distribution.py - Genera los instaladores oficiales de C.C.I. SYSTEM.
- macOS: Imagen de disco nativa Apple Disk Image (.dmg) con C.C.I. SYSTEM.app
  y asistente de instalación interactivo con destino en el Escritorio.
- Windows: Paquete de instalación con instalador gráfico de 1-clic sin terminal.
- 0 perfiles de fábrica en ambas versiones.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS_DIR = ROOT / "web" / "static" / "downloads"

EXCLUDE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".gemini", "brain",
    "capturas", "node_modules", "web/static/downloads", ".tmp_dmg_staging",
    ".tmp_win_staging", "test_output", "scratch", "tests copy",
    "Archive_Other_Versions", "fotos web"
}
EXCLUDE_EXTS = {".pyc", ".pyo", ".DS_Store", ".raw", ".tmp"}


def _should_include(file_path: Path, rel_str: str, target_platform: str) -> bool:
    parts = rel_str.split(os.sep)
    for p in parts:
        if p in EXCLUDE_DIRS:
            return False
    if file_path.suffix in EXCLUDE_EXTS:
        return False

    # Excluir videos pesados de gameplay raw y caches binarios (>1GB)
    if file_path.name in ("No Commentary].mp4", ".cached_320x224.raw"):
        return False

    # Excluir perfiles de usuario locales para que la descarga sea 100% limpia (0 perfiles)
    if ".cci-user-data" in parts:
        if file_path.name in ("active_user.json", "system.json"):
            return False
        if "users" in parts and file_path.suffix == ".json":
            return False

    # Excluir instaladores previos generados
    if file_path.suffix in (".zip", ".dmg", ".exe"):
        return False

    return True


def create_release_dmg(out_dmg: Path):
    if sys.platform != "darwin":
        print("[Build] Saltando DMG (solo disponible en macOS)")
        return

    print("[Build] Generando imagen de disco nativa macOS (.dmg)...")
    out_dmg.parent.mkdir(parents=True, exist_ok=True)
    temp_dmg = out_dmg.with_suffix(".tmp.dmg")
    if temp_dmg.exists():
        temp_dmg.unlink()

    staging_dir = ROOT / ".tmp_dmg_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    app_dir = staging_dir / "C.C.I. SYSTEM.app"
    macos_dir = app_dir / "Contents" / "MacOS"
    resources_dir = app_dir / "Contents" / "Resources"
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # 1. Launcher nativo en Python para la .app
    exec_script = macos_dir / "CCI_System"
    exec_content = '''#!/usr/bin/env python3
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

APP_BUNDLE = Path(__file__).resolve().parent.parent.parent
RESOURCES_DIR = APP_BUNDLE / "Contents" / "Resources"

# Detectar si estamos ejecutando desde el volumen DMG montado (read-only)
is_mounted_volume = "/Volumes/" in str(APP_BUNDLE)

if is_mounted_volume:
    script = """
    set dlg to display dialog "Bienvenido al emulador C.C.I. SYSTEM de Camila Carolina Ianni.\\n\\n¿Dónde deseas instalar la consola?\\n(Por defecto se instalará en tu Escritorio para acceso directo inmediato)." with title "C.C.I. SYSTEM — Instalación de Emulador" buttons {"Cancelar", "Elegir otra carpeta...", "Escritorio (Por defecto)"} default button "Escritorio (Por defecto)" with icon note
    set btn to button returned of dlg
    if btn is "Escritorio (Por defecto)" then
        set userDesk to POSIX path of (path to desktop folder)
        return userDesk
    else if btn is "Elegir otra carpeta..." then
        set selFolder to choose folder with prompt "Selecciona la carpeta donde deseas ubicar C.C.I. SYSTEM:" default location (path to desktop folder)
        return POSIX path of selFolder
    else
        return "CANCEL"
    end if
    """
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        choice = res.stdout.strip()
    except Exception:
        choice = "CANCEL"

    if not choice or choice == "CANCEL":
        sys.exit(0)

    target_parent = Path(choice)
    target_app = target_parent / "C.C.I. SYSTEM.app"
    desktop_app = Path.home() / "Desktop" / "C.C.I. SYSTEM.app"

    # Copiar .app al destino elegido
    if target_app.exists():
        shutil.rmtree(target_app)
    shutil.copytree(APP_BUNDLE, target_app)
    try:
        subprocess.run(["xattr", "-cr", str(target_app)], capture_output=True)
    except Exception:
        pass

    # Si el destino no fue el Escritorio, crear acceso directo en el Escritorio
    if target_app.resolve() != desktop_app.resolve():
        if desktop_app.exists() or desktop_app.is_symlink():
            try:
                if desktop_app.is_dir() and not desktop_app.is_symlink():
                    shutil.rmtree(desktop_app)
                else:
                    desktop_app.unlink()
            except OSError:
                pass
        try:
            desktop_app.symlink_to(target_app)
        except OSError:
            pass

    # Registrar en LaunchServices
    lsregister = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
    if os.path.exists(lsregister):
        try:
            subprocess.run([lsregister, "-f", str(target_app)], capture_output=True)
        except Exception:
            pass

    try:
        subprocess.run(["osascript", "-e", 'display notification "C.C.I. SYSTEM instalado correctamente en tu Escritorio. ¡Iniciando consola!" with title "C.C.I. SYSTEM"'], capture_output=True)
    except Exception:
        pass

    try:
        subprocess.Popen(["open", str(target_app)])
    except Exception:
        pass
    sys.exit(0)

# Ejecución normal de la consola emulada
CORE_DIR = RESOURCES_DIR if (RESOURCES_DIR / "main.py").exists() else APP_BUNDLE.parent
sys.path.insert(0, str(CORE_DIR))
os.chdir(str(CORE_DIR))

# Auto-detectar entorno virtual
venv_py = CORE_DIR / ".venv" / "bin" / "python"
if venv_py.exists() and sys.prefix == sys.base_prefix:
    os.execv(str(venv_py), [str(venv_py), str(CORE_DIR / "main.py")])
else:
    from main import main
    sys.exit(main())
'''
    exec_script.write_text(exec_content, encoding="utf-8")
    exec_script.chmod(exec_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # 2. Info.plist
    plist = app_dir / "Contents" / "Info.plist"
    plist.write_text('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CCI_System</string>
    <key>CFBundleIdentifier</key>
    <string>com.cci.system.emulator</string>
    <key>CFBundleName</key>
    <string>C.C.I. SYSTEM</string>
    <key>CFBundleDisplayName</key>
    <string>C.C.I. SYSTEM</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
''', encoding="utf-8")

    # 3. Copiar archivos del emulador dentro de resources_dir con 0 perfiles
    (resources_dir / ".cci-user-data" / "users").mkdir(parents=True, exist_ok=True)
    (resources_dir / ".cci-user-data" / "users" / ".gitkeep").touch()

    copied_count = 0
    for root_dir, dirs, files in os.walk(ROOT):
        r_path = Path(root_dir)
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp")]
        for fname in files:
            fpath = r_path / fname
            rel = fpath.relative_to(ROOT)
            rel_str = str(rel)
            if _should_include(fpath, rel_str, "macOS"):
                dest = resources_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fpath, dest)
                copied_count += 1

    # 4. PkgInfo, limpieza xattr y firma ad-hoc
    pkginfo = app_dir / "Contents" / "PkgInfo"
    pkginfo.write_text("APPL????", encoding="utf-8")
    try:
        subprocess.run(["xattr", "-cr", str(app_dir)], check=False)
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(app_dir)], check=False)
    except Exception:
        pass

    # 5. Enlace a Applications en staging
    apps_link = staging_dir / "Applications"
    try:
        apps_link.symlink_to("/Applications")
    except OSError:
        pass

    # 6. Generar DMG con hdiutil
    cmd = ["hdiutil", "create", "-volname", "C.C.I. SYSTEM", "-srcfolder", str(staging_dir), "-ov", "-format", "UDZO", str(temp_dmg)]
    subprocess.run(cmd, check=True)

    if out_dmg.exists():
        out_dmg.unlink()
    temp_dmg.rename(out_dmg)
    shutil.rmtree(staging_dir, ignore_errors=True)
    size_mb = out_dmg.stat().st_size / (1024 * 1024)
    print(f"[Build] macOS DMG listo: {out_dmg.name} ({size_mb:.1f} MB, {copied_count} archivos en .app)")


def create_release_zip(target_platform: str, out_zip: Path):
    print(f"[Build] Empaquetando C.C.I. SYSTEM para {target_platform}...")
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    temp_zip = out_zip.with_suffix(".tmp")
    if temp_zip.exists():
        temp_zip.unlink()

    included_count = 0
    with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        zf.writestr("CCI_System/.cci-user-data/users/.gitkeep", "")

        for root_dir, dirs, files in os.walk(ROOT):
            r_path = Path(root_dir)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp")]

            for fname in files:
                fpath = r_path / fname
                rel = fpath.relative_to(ROOT)
                rel_str = str(rel)

                if _should_include(fpath, rel_str, target_platform):
                    arcname = f"CCI_System/{rel_str}"
                    zinfo = zipfile.ZipInfo.from_file(fpath, arcname=arcname)
                    file_mode = fpath.stat().st_mode
                    if file_mode & stat.S_IXUSR or fpath.suffix in (".py", ".pyw") or "MacOS" in rel_str:
                        zinfo.external_attr = (file_mode | 0o755) << 16
                    else:
                        zinfo.external_attr = (file_mode | 0o644) << 16

                    zf.writestr(zinfo, fpath.read_bytes())
                    included_count += 1

    if out_zip.exists():
        out_zip.unlink()
    temp_zip.rename(out_zip)
    size_mb = out_zip.stat().st_size / (1024 * 1024)
    print(f"[Build] {target_platform} listo: {out_zip.name} ({size_mb:.1f} MB, {included_count} archivos incluidos)")


def create_release_exe(out_exe: Path):
    print("[Build] Generando instalador ejecutable nativo para Windows (.exe)...")
    out_exe.parent.mkdir(parents=True, exist_ok=True)
    temp_exe = out_exe.with_suffix(".tmp.exe")
    if temp_exe.exists():
        temp_exe.unlink()

    has_nsis = shutil.which("makensis") is not None
    staging_dir = ROOT / ".tmp_win_staging"
    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=True)

    if has_nsis:
        print("[Build] Detectado NSIS (makensis). Generando instalador profesional con runtime embebido y accesos directos...")
        runtime_src = Path("/tmp/win_runtime")
        if runtime_src.exists():
            shutil.copytree(runtime_src, staging_dir / "runtime")

        launcher_src = Path("/tmp/CCI_System_Launcher.exe")
        if launcher_src.exists():
            shutil.copy2(launcher_src, staging_dir / "C.C.I. SYSTEM.exe")

        copied_count = 0
        for root_dir, dirs, files in os.walk(ROOT):
            r_path = Path(root_dir)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp")]
            for fname in files:
                fpath = r_path / fname
                rel = fpath.relative_to(ROOT)
                rel_str = str(rel)
                if _should_include(fpath, rel_str, "Windows"):
                    dest = staging_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fpath, dest)
                    copied_count += 1

        (staging_dir / ".cci-user-data" / "users").mkdir(parents=True, exist_ok=True)
        (staging_dir / ".cci-user-data" / "users" / ".gitkeep").touch()

        icon_path = ROOT / "fotos web" / "ciberpunk.ico"
        nsi_script = f"""
Unicode true
RequestExecutionLevel user
SetCompressor /SOLID lzma

Name "C.C.I. SYSTEM"
OutFile "{temp_exe}"
InstallDir "$LOCALAPPDATA\\Programs\\CCI_System"
Icon "{icon_path}"
UninstallIcon "{icon_path}"

Page directory
Page instfiles

Section "C.C.I. SYSTEM" SecMain
  SetOutPath "$INSTDIR"
  File /r "{staging_dir}\\*"

  CreateShortcut "$DESKTOP\\C.C.I. SYSTEM.lnk" "$INSTDIR\\C.C.I. SYSTEM.exe" "" "$INSTDIR\\fotos web\\ciberpunk.ico" 0 SW_SHOWNORMAL "" "C.C.I. SYSTEM — Emulador de Consola Retro"
  CreateDirectory "$SMPROGRAMS\\C.C.I. SYSTEM"
  CreateShortcut "$SMPROGRAMS\\C.C.I. SYSTEM\\C.C.I. SYSTEM.lnk" "$INSTDIR\\C.C.I. SYSTEM.exe" "" "$INSTDIR\\fotos web\\ciberpunk.ico" 0 SW_SHOWNORMAL "" "C.C.I. SYSTEM — Emulador de Consola Retro"
  CreateShortcut "$SMPROGRAMS\\C.C.I. SYSTEM\\Desinstalar.lnk" "$INSTDIR\\Uninstall.exe"

  WriteUninstaller "$INSTDIR\\Uninstall.exe"
SectionEnd

Function .onInstSuccess
  Exec '"$INSTDIR\\C.C.I. SYSTEM.exe"'
FunctionEnd

Section "Uninstall"
  Delete "$DESKTOP\\C.C.I. SYSTEM.lnk"
  RMDir /r "$SMPROGRAMS\\C.C.I. SYSTEM"
  RMDir /r "$INSTDIR"
SectionEnd
"""
        nsi_file = ROOT / ".tmp_installer.nsi"
        nsi_file.write_text(nsi_script, encoding="utf-8")
        subprocess.run(["makensis", str(nsi_file)], check=True)
        nsi_file.unlink(missing_ok=True)
    else:
        # Fallback a 7z.sfx si no está makensis
        sfx_path = ROOT / "tools" / "7z.sfx"
        package_root = staging_dir / "CCI_System"
        package_root.mkdir(parents=True, exist_ok=True)
        (package_root / ".cci-user-data" / "users").mkdir(parents=True, exist_ok=True)
        (package_root / ".cci-user-data" / "users" / ".gitkeep").touch()
        copied_count = 0
        for root_dir, dirs, files in os.walk(ROOT):
            r_path = Path(root_dir)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".tmp")]
            for fname in files:
                fpath = r_path / fname
                rel = fpath.relative_to(ROOT)
                if _should_include(fpath, str(rel), "Windows"):
                    dest = package_root / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fpath, dest)
                    copied_count += 1
        payload_7z = ROOT / ".tmp_win_payload.7z"
        if payload_7z.exists():
            payload_7z.unlink()
        subprocess.run(["7zz", "a", "-m0=BCJ", "-m1=LZMA2:d=32m", "-mx=5", "-y", str(payload_7z), str(package_root)], check=True)
        temp_exe.write_bytes(sfx_path.read_bytes() + payload_7z.read_bytes())
        if payload_7z.exists():
            payload_7z.unlink()

    if out_exe.exists():
        out_exe.unlink()
    temp_exe.rename(out_exe)
    shutil.rmtree(staging_dir, ignore_errors=True)

    size_mb = out_exe.stat().st_size / (1024 * 1024)
    print(f"[Build] Windows EXE listo: {out_exe.name} ({size_mb:.1f} MB, {copied_count} archivos incluidos)")


def build_all():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    mac_dmg = DOWNLOADS_DIR / "CCI_System_macOS.dmg"
    win_exe = DOWNLOADS_DIR / "CCI_System_Windows_Installer.exe"
    win_zip = DOWNLOADS_DIR / "CCI_System_Windows.zip"

    # 1. Generar instalador nativo DMG para Mac
    create_release_dmg(mac_dmg)

    # 2. Generar instalador ejecutable nativo para Windows (.exe)
    create_release_exe(win_exe)

    # 3. Generar respaldo ZIP para Windows
    create_release_zip("Windows", win_zip)

    print("[Build] ¡Empaquetado oficial completado con éxito!")


if __name__ == "__main__":
    build_all()
