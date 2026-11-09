#!/usr/bin/env python3
"""tools/download_batch2.py - Descarga automática de la segunda tanda de ROMs (PS1, N64, NDS, Neo-Geo, Wii)."""
import os
import re
import sys
import time
import zipfile
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import py7zr
except ImportError:
    py7zr = None

ROOT = Path(__file__).resolve().parent.parent

LINKS = [
    # Neo-Geo
    ("neogeo", "https://www.retrostic.com/es/roms/neo-geo/puzzle-bobble-bust-a-move-10958"),
    ("neogeo", "https://www.retrostic.com/es/roms/neo-geo/snow-bros-2-83409"),
    ("neogeo", "https://www.retrostic.com/es/roms/neo-geo/super-sidekicks-2-the-world-championship-tokuten-ou-2-real-fight-football-11018"),
    # Nintendo 64
    ("n64", "https://www.retrostic.com/es/roms/n64/super-mario-64-83299"),
    ("n64", "https://www.retrostic.com/es/roms/n64/mario-kart-64-v1-1-e-83296"),
    ("n64", "https://www.retrostic.com/es/roms/n64/super-smash-bros-83298"),
    ("n64", "https://www.retrostic.com/es/roms/n64/legend-of-zelda-the-ocarina-of-time-v12-2-83297"),
    ("n64", "https://www.retrostic.com/es/roms/n64/donkey-kong-64-83302"),
    # Nintendo DS
    ("nds", "https://www.retrostic.com/es/roms/nds/new-super-mario-bros-g-82246"),
    ("nds", "https://www.retrostic.com/es/roms/nds/mario-kart-ds-original-82977"),
    ("nds", "https://www.retrostic.com/es/roms/nds/pokemon-black-version-eur-82976"),
    ("nds", "https://www.retrostic.com/es/roms/nds/animal-crossing-wild-world-g-74733"),
    ("nds", "https://www.retrostic.com/es/roms/nds/pokemon-white-2-v01-jp-82980"),
    ("nds", "https://www.retrostic.com/es/roms/nds/kirby-super-stars-ultra2-82983"),
    ("nds", "https://www.retrostic.com/es/roms/nds/lego-marvel-super-heroes-universe-in-peril-74994"),
    # PlayStation 1
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/crash-bandicoot-u-iso-scus-94900-81197"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/resident-evil-3-nemesis-iso-sles-02529-81187"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/crash-bandicoot-3-warped-u-iso-scus-94244-81206"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/metal-slug-x-ntsc-u-iso-slus-01212-81639"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/resident-evil-u-iso-slus-00170-81628"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/yu-gi-oh-forbidden-memories-iso-slus-014-11-81210"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/castlevania-symphony-of-the-night-plus-music-cd-u-iso-slu-00067-81655"),
    ("ps1", "https://www.retrostic.com/es/roms/ps-1/resident-evil-2-cd2-u-iso-slus-00592-81651"),
    # Nintendo Wii
    ("wii", "https://www.retrostic.com/es/roms/wii/wii-sports-84147"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.retrostic.com/",
}


def download_rom(console: str, url: str):
    out_dir = ROOT / "roms" / console
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = url.rstrip("/").split("/")[-1]
    print(f"\n[GET] Procesando: {slug} ({console})...")

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [ERROR] Falló al cargar página: {e}")
        return

    form_match = re.search(r'<form[^>]*id=["\']dl["\'][^>]*>(.*?)</form>', page_html, re.DOTALL)
    if not form_match:
        print("  [ERROR] No se encontró form #dl")
        return

    form_body = form_match.group(1)
    post_data = {}
    for inp in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', form_body):
        post_data[inp.group(1)] = inp.group(2)

    dl_endpoint = f"{url}/download"
    data_encoded = urllib.parse.urlencode(post_data).encode("utf-8")
    req_post = urllib.request.Request(dl_endpoint, data=data_encoded, headers=HEADERS)
    try:
        with urllib.request.urlopen(req_post, timeout=15) as resp:
            dl_page = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [ERROR] Falló POST download: {e}")
        return

    loc_match = re.search(r'window\.location\.href\s*=\s*["\'](https://downloads\.retrostic\.com/[^"\']+)["\']', dl_page)
    if not loc_match:
        print("  [WARN] No se encontró link directo")
        return

    file_url = loc_match.group(1)
    file_name = urllib.parse.unquote(file_url.split("/")[-1])
    print(f"  [URL] {file_name}")

    archive_dest = out_dir / file_name
    stem = Path(file_name).stem
    if archive_dest.exists() or any(out_dir.glob(f"{stem}.*")):
        print(f"  [OK] Ya existe: {file_name}")
        return

    print(f"  [DOWNLOADING] Guardando {archive_dest.name}...")
    req_file = urllib.request.Request(file_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req_file, timeout=180) as resp, open(archive_dest, "wb") as f:
            chunk = resp.read(131072)
            while chunk:
                f.write(chunk)
                chunk = resp.read(131072)
        print(f"  [DOWNLOAD OK] {archive_dest.stat().st_size // 1024} KB")

        # Descomprimir según tipo de consola
        if console in ("n64", "nds", "ps1", "wii"):
            if file_name.endswith(".zip") and zipfile.is_zipfile(archive_dest):
                with zipfile.ZipFile(archive_dest, "r") as z:
                    z.extractall(out_dir)
                print(f"  [UNZIPPED] Extraído en {out_dir}")
                archive_dest.unlink()
            elif file_name.endswith(".7z") and py7zr and py7zr.is_7zfile(archive_dest):
                with py7zr.SevenZipFile(archive_dest, mode="r") as z:
                    z.extractall(path=out_dir)
                print(f"  [UNPACKED 7Z] Extraído en {out_dir}")
                archive_dest.unlink()
        elif console == "neogeo":
            print(f"  [NEOGEO ZIP READY] {file_name} preservado para MAME/FBNeo")
    except Exception as e:
        print(f"  [ERROR] Falló descarga: {e}")


def main():
    print(f"=== INICIANDO BATCH 2 ({len(LINKS)} JUEGOS) ===")
    for console, link in LINKS:
        download_rom(console, link)
        time.sleep(1.0)
    print("\n=== BATCH 2 FINALIZADO ===")


if __name__ == "__main__":
    main()
