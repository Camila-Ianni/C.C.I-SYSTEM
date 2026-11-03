#!/usr/bin/env python3
"""installer.py - Instalador gráfico 1-clic de C.C.I. SYSTEM (Multiplataforma).
Permite al usuario elegir dónde ubicar la consola (por defecto en el Escritorio)
y lanza automáticamente el emulador con 0 perfiles de fábrica.
Autora: Camila Carolina Ianni.
"""
from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from cci_updater import CURRENT_VERSION

SOURCE_DIR = Path(__file__).resolve().parent


def ask_install_location_macos() -> Path | None:
    """Muestra un cuadro de diálogo nativo de macOS preguntando la ubicación."""
    script = '''
    set dlg to display dialog "Bienvenido al emulador C.C.I. SYSTEM de Camila Carolina Ianni.\n\n¿Dónde deseas instalar la consola?\n(Por defecto se instalará en tu Escritorio para acceso directo inmediato)." with title "C.C.I. SYSTEM — Instalación de Emulador" buttons {"Cancelar", "Elegir otra carpeta...", "Escritorio (Por defecto)"} default button "Escritorio (Por defecto)" with icon note
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
    '''
    try:
        res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        if not out or out == "CANCEL":
            return None
        base_path = Path(out)
        return base_path / "C.C.I SYSTEM"
    except subprocess.CalledProcessError:
        return None


def ask_install_location_windows() -> Path | None:
    """Muestra un diálogo nativo en Windows vía PowerShell Forms."""
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $dlg = [System.Windows.Forms.MessageBox]::Show(
        "Bienvenido a C.C.I. SYSTEM de Camila Carolina Ianni.`n`n¿Deseas instalar el emulador en tu Escritorio (Recomendado)?`n`nPresiona 'Sí' para instalar en Escritorio.`nPresiona 'No' para elegir otra carpeta.",
        "C.C.I. SYSTEM — Instalación de Emulador",
        [System.Windows.Forms.MessageBoxButtons]::YesNoCancel,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    if ($dlg -eq [System.Windows.Forms.DialogResult]::Yes) {
        $desk = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
        Write-Output $desk
    } elseif ($dlg -eq [System.Windows.Forms.DialogResult]::No) {
        $fb = New-Object System.Windows.Forms.FolderBrowserDialog
        $fb.Description = "Selecciona la carpeta donde deseas ubicar C.C.I. SYSTEM"
        if ($fb.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-Output $fb.SelectedPath
        } else {
            Write-Output "CANCEL"
        }
    } else {
        Write-Output "CANCEL"
    }
    """
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        if not out or out == "CANCEL":
            return None
        base_path = Path(out)
        return base_path / "C.C.I SYSTEM"
    except Exception:
        # Fallback a Desktop
        desk = Path.home() / "Desktop"
        return desk / "C.C.I SYSTEM"


def ask_install_location() -> Path | None:
    if sys.platform == "darwin":
        return ask_install_location_macos()
    elif sys.platform == "win32":
        return ask_install_location_windows()
    else:
        # Linux / Unix
        return Path.home() / "Desktop" / "C.C.I SYSTEM"


def notify_macos(title: str, message: str):
    script = f'display notification "{message}" with title "{title}"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True)
    except Exception:
        pass


def create_macos_app_bundle(app_dir: Path, target_dir: Path):
    """Crea una app nativa .app en macOS para lanzar la consola con doble clic."""
    macos_dir = app_dir / "Contents" / "MacOS"
    macos_dir.mkdir(parents=True, exist_ok=True)

    launcher_script = macos_dir / "CCI_System"
    py_exec = sys.executable

    launcher_content = f'''#!/usr/bin/env python3
import os
import sys
from pathlib import Path

APP_TARGET = Path("{target_dir.resolve()}")
sys.path.insert(0, str(APP_TARGET))
os.chdir(str(APP_TARGET))

# Auto-detect virtualenv si existe
venv_py = APP_TARGET / ".venv" / "bin" / "python"
if venv_py.exists() and sys.prefix == sys.base_prefix:
    os.execv(str(venv_py), [str(venv_py), str(APP_TARGET / "main.py")])
else:
    from main import main
    sys.exit(main())
'''
    launcher_script.write_text(launcher_content, encoding="utf-8")
    launcher_script.chmod(launcher_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    plist_path = app_dir / "Contents" / "Info.plist"
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
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
    <string>{CURRENT_VERSION}</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
'''
    plist_path.write_text(plist_content, encoding="utf-8")

    # Registrar en LaunchServices
    lsregister = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
    if os.path.exists(lsregister):
        try:
            subprocess.run([lsregister, "-f", str(app_dir)], capture_output=True)
        except Exception:
            pass


def create_windows_shortcut(target_dir: Path, desktop_dir: Path):
    """Crea acceso directo en el Escritorio de Windows usando PowerShell."""
    shortcut_path = desktop_dir / "C.C.I. SYSTEM.lnk"
    main_py = target_dir / "emulator.py"
    ps_cmd = f"""
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = 'pythonw.exe'
    $Shortcut.Arguments = '"{main_py}"'
    $Shortcut.WorkingDirectory = '{target_dir}'
    $Shortcut.Description = 'C.C.I. SYSTEM — Emulador de Consola Retro (Camila Carolina Ianni)'
    $Shortcut.Save()
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
    except Exception:
        pass


def install_and_launch():
    # 1. Preguntar al usuario dónde ubicar la consola
    target_dir = ask_install_location()
    if target_dir is None:
        # Cancelado por el usuario
        sys.exit(0)

    # 2. Si el directorio destino es distinto del origen, copiar archivos limpios
    source_resolved = SOURCE_DIR.resolve()
    target_resolved = target_dir.resolve()

    if source_resolved != target_resolved:
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in source_resolved.iterdir():
            if item.name in (".git", ".venv", "__pycache__", ".pytest_cache", ".DS_Store"):
                continue
            dest_item = target_dir / item.name
            if item.is_dir():
                if not dest_item.exists():
                    shutil.copytree(item, dest_item, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
            else:
                shutil.copy2(item, dest_item)

    # 3. Asegurar que .cci-user-data/users/ esté 100% limpio (0 perfiles)
    users_dir = target_dir / ".cci-user-data" / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    for u in users_dir.glob("*.json"):
        try:
            u.unlink()
        except OSError:
            pass
    active_u = target_dir / ".cci-user-data" / "active_user.json"
    if active_u.exists():
        try:
            active_u.unlink()
        except OSError:
            pass

    # 4. Crear accesos directos de 1-clic en el Escritorio
    desktop_dir = Path.home() / "Desktop"
    if sys.platform == "darwin":
        desktop_app = desktop_dir / "C.C.I. SYSTEM.app"
        create_macos_app_bundle(desktop_app, target_dir)
        # También crear una copia dentro de la carpeta instalada
        local_app = target_dir / "C.C.I. SYSTEM.app"
        create_macos_app_bundle(local_app, target_dir)
        notify_macos("C.C.I. SYSTEM", "Consola emulada instalada en el Escritorio. ¡Iniciando!")
    elif sys.platform == "win32":
        create_windows_shortcut(target_dir, desktop_dir)

    # 5. Lanzar el emulador inmediatamente (como cualquier consola instalada)
    main_script = target_dir / "emulator.py"
    if not main_script.exists():
        main_script = target_dir / "main.py"

    venv_py = target_dir / ".venv" / ("bin/python" if sys.platform != "win32" else "Scripts/python.exe")
    launcher_python = str(venv_py) if venv_py.exists() else sys.executable

    subprocess.Popen([launcher_python, str(main_script)], cwd=str(target_dir))


if __name__ == "__main__":
    install_and_launch()
