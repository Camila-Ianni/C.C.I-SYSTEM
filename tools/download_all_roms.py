#!/usr/bin/env python3
"""tools/download_all_roms.py - Descarga automática y segura de ROMs desde Retrostic."""
import os
import re
import sys
import time
import zipfile
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LINKS = [
    ("mame", "https://www.retrostic.com/es/roms/mame/metal-slug-2-super-vehicle-001-ii-40817"),
    ("mame", "https://www.retrostic.com/es/roms/mame/marvel-vs-capcom-clash-of-super-heroes-40814"),
    ("mame", "https://www.retrostic.com/es/roms/mame/pac-man-40808"),
    ("mame", "https://www.retrostic.com/es/roms/mame/metal-slug-6-40797"),
    ("mame", "https://www.retrostic.com/es/roms/mame/final-fight-41558"),
    ("mame", "https://www.retrostic.com/es/roms/mame/cruis-n-usa-40995"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-mario-kart-full-g-81982"),
    ("snes", "https://www.retrostic.com/es/roms/snes/donkey-kong-country-v3-2-81984"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-mario-all-stars-super-mario-world-game-81978"),
    ("snes", "https://www.retrostic.com/es/roms/snes/street-fighter-ii-the-world-warrior-2887"),
    ("snes", "https://www.retrostic.com/es/roms/snes/legend-of-zelda-the-a-link-to-the-past1-81981"),
    ("snes", "https://www.retrostic.com/es/roms/snes/donkey-kong-country-2-diddys-kong-quest12-1-81979"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-mario-world-2-yoshis-island-v1-2-81980"),
    ("snes", "https://www.retrostic.com/es/roms/snes/bs-mario-collection-3-82128"),
    ("snes", "https://www.retrostic.com/es/roms/snes/ultimate-mortal-kombat-3-2808"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-metroid-jug-81991"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-mario-all-stars-online-81983"),
    ("snes", "https://www.retrostic.com/es/roms/snes/aladdin-2810"),
    ("snes", "https://www.retrostic.com/es/roms/snes/super-bomberman-4-2829"),
    ("snes", "https://www.retrostic.com/es/roms/snes/sonic-the-hedgehog-4-2882"),
    ("snes", "https://www.retrostic.com/es/roms/snes/donkey-kong-country-3-dixie-ko-double-trouble-81993"),
    ("snes", "https://www.retrostic.com/es/roms/snes/mortal-kombat-2821"),
    ("snes", "https://www.retrostic.com/es/roms/snes/sunset-riders-2824"),
    ("snes", "https://www.retrostic.com/es/roms/snes/megaman-x3-2817"),
    ("snes", "https://www.retrostic.com/es/roms/snes/doom-2818"),
    ("snes", "https://www.retrostic.com/es/roms/snes/kirby-super-star-game-81992"),
    ("snes", "https://www.retrostic.com/es/roms/snes/street-fighter-ii-turbo-hyper-fighting-2813"),
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

    # 1. Obtener la página del juego para extraer campos del form
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [ERROR] Falló al cargar página: {e}")
        return

    # Buscar form #dl
    form_match = re.search(r'<form[^>]*id=["\']dl["\'][^>]*>(.*?)</form>', page_html, re.DOTALL)
    if not form_match:
        print("  [ERROR] No se encontró form #dl")
        return

    form_body = form_match.group(1)
    post_data = {}
    for inp in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', form_body):
        post_data[inp.group(1)] = inp.group(2)

    if not post_data:
        print("  [ERROR] No se pudieron extraer campos de formulario")
        return

    # 2. Enviar POST al endpoint de descarga
    dl_endpoint = f"{url}/download"
    data_encoded = urllib.parse.urlencode(post_data).encode("utf-8")
    req_post = urllib.request.Request(dl_endpoint, data=data_encoded, headers=HEADERS)
    try:
        with urllib.request.urlopen(req_post, timeout=15) as resp:
            dl_page = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  [ERROR] Falló POST download: {e}")
        return

    # 3. Buscar window.location.href en la respuesta
    loc_match = re.search(r'window\.location\.href\s*=\s*["\'](https://downloads\.retrostic\.com/[^"\']+)["\']', dl_page)
    if not loc_match:
        print("  [WARN] No se encontró link directo en window.location.href")
        return

    file_url = loc_match.group(1)
    file_name = urllib.parse.unquote(file_url.split("/")[-1])
    print(f"  [URL] {file_name}")

    # 4. Descargar archivo
    zip_dest = out_dir / file_name
    if zip_dest.exists() or any(out_dir.glob(f"{Path(file_name).stem}.*")):
        print(f"  [OK] Ya existe: {file_name}")
        return

    print(f"  [DOWNLOADING] Guardando en {zip_dest.name}...")
    req_file = urllib.request.Request(file_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req_file, timeout=60) as resp, open(zip_dest, "wb") as f:
            chunk = resp.read(65536)
            while chunk:
                f.write(chunk)
                chunk = resp.read(65536)
        print(f"  [DOWNLOAD OK] {zip_dest.stat().st_size // 1024} KB")

        # Para SNES descomprimir; para MAME mantener zip (MAME necesita zip intacto con sus roms)
        if console == "snes" and zipfile.is_zipfile(zip_dest):
            with zipfile.ZipFile(zip_dest, 'r') as z:
                z.extractall(out_dir)
            print(f"  [UNZIPPED] Contenido extraído en {out_dir}")
            zip_dest.unlink()
    except Exception as e:
        print(f"  [ERROR] Falló descarga: {e}")


def main():
    print(f"=== INICIANDO DESCARGA DE {len(LINKS)} ROMS ===")
    seen = set()
    for console, link in LINKS:
        if link in seen:
            continue
        seen.add(link)
        download_rom(console, link)
        time.sleep(1.0)
    print("\n=== DESCARGAS FINALIZADAS ===")


if __name__ == "__main__":
    main()
