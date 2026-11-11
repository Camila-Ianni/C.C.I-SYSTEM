#!/usr/bin/env python3
"""tools/download_3d_playstation_pack.py - Descarga y extracción automática de ISOs 3D PlayStation (PSP y PS1) para C.C.I. SYSTEM."""
from __future__ import annotations

import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PSP_DIR = ROOT / "assets_omnidash" / "playable_roms" / "psp"
PS1_DIR = ROOT / "assets_omnidash" / "playable_roms" / "ps1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
    "Referer": "https://www.retrostic.com/",
}

PSP_TARGETS: list[tuple[str, str]] = [
    ("sonic_rivals_2.iso", "https://www.retrostic.com/es/roms/psp/sonic-rivals-2-84049"),
    ("the_sims_2.iso", "https://www.retrostic.com/es/roms/psp/the-sims-2-83868"),
    ("call_of_duty.iso", "https://www.retrostic.com/es/roms/psp/call-of-duty-roads-to-victory-83731"),
    ("gta_liberty_city.iso", "https://www.retrostic.com/es/roms/psp/grand-theft-auto-liberty-city-stories-83751"),
    ("crash_of_the_titans.iso", "https://www.retrostic.com/es/roms/psp/crash-of-the-titans-83842"),
    ("assassins_creed.iso", "https://www.retrostic.com/es/roms/psp/assassins-creed-bloodlines-83744"),
]

PS1_TARGETS: list[tuple[str, str]] = [
    ("Resident Evil 3 - Nemesis", "https://www.retrostic.com/es/roms/ps-1/resident-evil-3-nemesis-iso-sles-02529-81187"),
    ("Crash Team Racing", "https://www.retrostic.com/es/roms/ps-1/ctr-crash-team-racing-iso-sces-02105-81966"),
    ("Gran Turismo 2", "https://www.retrostic.com/es/roms/ps-1/gran-turismo-2-simulation-mode-ntsc-u-iso-scus-94488-81606"),
    ("Spider-Man 3D", "https://www.retrostic.com/es/roms/ps-1/spider-man-ntsc-u-iso-slus-00875-81598"),
    ("Silent Hill 3D", "https://www.retrostic.com/es/roms/ps-1/silent-hill-ntsc-u-iso-slus-00707-81619"),
    ("ISS Pro Evolution 2", "https://www.retrostic.com/es/roms/ps-1/iss-pro-evolution-2-iso-sles-03321-81649"),
    ("MediEvil 3D", "https://www.retrostic.com/es/roms/ps-1/medievil-iso-sces-00311-82094"),
]


def _resolve_retrostic_dl_url(url: str) -> str | None:
    req = urllib.request.Request(url, headers=HEADERS)
    page_html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    fm = re.search(r'<form[^>]*id=["\']dl["\'][^>]*>(.*?)</form>', page_html, re.S)
    if not fm:
        return None
    post_data = {
        m.group(1): m.group(2)
        for m in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', fm.group(1))
    }
    req_post = urllib.request.Request(
        f"{url}/download",
        data=urllib.parse.urlencode(post_data).encode(),
        headers=HEADERS,
    )
    dl_page = urllib.request.urlopen(req_post, timeout=20).read().decode("utf-8", "ignore")
    loc = re.search(r'window\.location\.href\s*=\s*["\'](https://downloads\.retrostic\.com/[^"\']+)["\']', dl_page)
    return loc.group(1) if loc else None


def fetch_psp_iso(target_iso_name: str, url: str) -> str:
    PSP_DIR.mkdir(parents=True, exist_ok=True)
    final_iso = PSP_DIR / target_iso_name
    if final_iso.exists() and final_iso.stat().st_size > 50 * 1024 * 1024:
        return f"[SKIP PSP] {target_iso_name} ({final_iso.stat().st_size // (1024 * 1024)} MB)"

    stem = target_iso_name.replace(".iso", "")
    work_dir = PSP_DIR / f"_tmp_{stem}"
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_url = _resolve_retrostic_dl_url(url)
        if not file_url:
            return f"[ERR PSP] No dl link for {target_iso_name}"
        fname = urllib.parse.unquote(file_url.split("/")[-1])
        arc_path = work_dir / fname
        with urllib.request.urlopen(urllib.request.Request(file_url, headers=HEADERS), timeout=240) as r, open(arc_path, "wb") as f:
            shutil.copyfileobj(r, f, length=262144)

        unar_bin = shutil.which("unar") or "/opt/homebrew/bin/unar"
        subprocess.run([unar_bin, "-f", "-o", str(work_dir), str(arc_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        arc_path.unlink(missing_ok=True)

        for sub_rar in list(work_dir.rglob("*.rar")):
            subprocess.run([unar_bin, "-f", "-o", str(work_dir), str(sub_rar)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        isos = [
            p for p in work_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".iso", ".cso") and p.stat().st_size > 50 * 1024 * 1024
        ]
        isos.sort(key=lambda p: p.stat().st_size, reverse=True)
        if isos:
            shutil.move(str(isos[0]), str(final_iso))
            shutil.rmtree(work_dir, ignore_errors=True)
            return f"[OK PSP] {target_iso_name} ({final_iso.stat().st_size // (1024 * 1024)} MB)"
        shutil.rmtree(work_dir, ignore_errors=True)
        return f"[ERR PSP] No ISO found for {target_iso_name}"
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        return f"[ERR PSP] {target_iso_name}: {e}"


def fetch_ps1_game(label: str, url: str) -> str:
    PS1_DIR.mkdir(parents=True, exist_ok=True)
    marker_cue = PS1_DIR / f"{label}.cue"
    if marker_cue.exists() and marker_cue.stat().st_size > 0:
        return f"[SKIP PS1] {label}"

    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", label)
    work_dir = PS1_DIR / f"_tmp_{safe_stem}"
    shutil.rmtree(work_dir, ignore_errors=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_url = _resolve_retrostic_dl_url(url)
        if not file_url:
            return f"[ERR PS1] No dl link for {label}"
        fname = urllib.parse.unquote(file_url.split("/")[-1])
        arc_path = work_dir / fname
        with urllib.request.urlopen(urllib.request.Request(file_url, headers=HEADERS), timeout=240) as r, open(arc_path, "wb") as f:
            shutil.copyfileobj(r, f, length=262144)

        unar_bin = shutil.which("unar") or "/opt/homebrew/bin/unar"
        subprocess.run([unar_bin, "-f", "-o", str(work_dir), str(arc_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        arc_path.unlink(missing_ok=True)

        # Descomprimir cualquier .ecm o sub-archivo si existiera
        bins = [
            p for p in work_dir.rglob("*")
            if p.is_file() and p.suffix.lower() in (".bin", ".img", ".iso") and p.stat().st_size > 20 * 1024 * 1024
        ]
        bins.sort(key=lambda p: p.stat().st_size, reverse=True)
        if not bins:
            shutil.rmtree(work_dir, ignore_errors=True)
            return f"[ERR PS1] No BIN/ISO found for {label}"

        main_bin = bins[0]
        dest_bin = PS1_DIR / f"{label}{main_bin.suffix.lower()}"
        shutil.move(str(main_bin), str(dest_bin))
        # Generar .cue limpio apuntando a dest_bin.name
        cue_content = f'FILE "{dest_bin.name}" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n'
        marker_cue.write_text(cue_content, encoding="utf-8")
        shutil.rmtree(work_dir, ignore_errors=True)
        return f"[OK PS1] {label} -> {marker_cue.name} ({dest_bin.stat().st_size // (1024 * 1024)} MB)"
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        return f"[ERR PS1] {label}: {e}"


def main():
    print(f"Descargando {len(PSP_TARGETS)} ISOs 3D PSP y {len(PS1_TARGETS)} ISOs 3D PS1...")
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(fetch_psp_iso, name, u) for name, u in PSP_TARGETS]
        futs += [ex.submit(fetch_ps1_game, name, u) for name, u in PS1_TARGETS]
        for f in as_completed(futs):
            print(f.result(), flush=True)


if __name__ == "__main__":
    main()
