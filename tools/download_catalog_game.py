#!/usr/bin/env python3
"""tools/download_catalog_game.py - Descargador e instalador verificado de paquetes reales para C.C.I. SYSTEM.

Utiliza el registro exacto de 90 URLs de CATALOG_SOURCE_URLS (RomsHQ / Retrostic / RomsJuegos) para:
1. Descargar el archivo binario real (.nsp, .xci, .pkg, .iso, .cue/.bin, .rar, .zip) del game_id indicado.
2. Extraer automáticamente contenedores comprimidos (.rar, .zip, .7z) con unar en roms/<platform_key>/.
3. Validar la identidad estricta del paquete con ROMPackageIdentityValidator antes de darlo por instalado.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.games.package_validator import CATALOG_SOURCE_URLS, ROMPackageIdentityValidator
from backend.games.scanner_service import GameLibraryScannerService

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"


def _resolve_direct_stream(source_url: str) -> tuple[urllib.request.OpenerDirector, str, dict[str, str]]:
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    headers = {"User-Agent": UA, "Referer": source_url}

    if "romshq.com/game/" in source_url:
        html = opener.open(urllib.request.Request(source_url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "ignore")
        m_csrf = re.search(r"const CSRF = ['\"]([^'\"]+)['\"]", html)
        m_vid = re.search(r"data-video-id=['\"](\d+)['\"]", html)
        if not m_csrf or not m_vid:
            raise RuntimeError(f"No se encontraron tokens de descarga en {source_url}")
        sign_req = urllib.request.Request(
            f"https://romshq.com/api/download/sign/{m_vid.group(1)}",
            data=b"",
            headers={
                "User-Agent": UA,
                "Accept": "application/json",
                "X-CSRF-TOKEN": m_csrf.group(1),
                "X-Requested-With": "XMLHttpRequest",
                "Referer": source_url,
            },
            method="POST",
        )
        res = json.loads(opener.open(sign_req, timeout=20).read().decode("utf-8"))
        if not res.get("success") or not res.get("download_url"):
            raise RuntimeError(f"Error al firmar descarga en RomsHQ: {res}")
        return opener, res["download_url"], headers

    if "retrostic.com/" in source_url:
        html = opener.open(urllib.request.Request(source_url, headers=headers), timeout=20).read().decode("utf-8", "ignore")
        fm = re.search(r'<form[^>]*id=["\']dl["\'][^>]*>(.*?)</form>', html, re.S)
        if not fm:
            raise RuntimeError(f"No se encontró formulario de descarga en {source_url}")
        post_data = {
            m.group(1): m.group(2)
            for m in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', fm.group(1))
        }
        dl_req = urllib.request.Request(
            f"{source_url}/download",
            data=urllib.parse.urlencode(post_data).encode("utf-8"),
            headers=headers,
        )
        dl_html = opener.open(dl_req, timeout=20).read().decode("utf-8", "ignore")
        loc = re.search(r'window\.location\.href\s*=\s*["\'](https://downloads\.retrostic\.com/[^"\']+)["\']', dl_html)
        if not loc:
            raise RuntimeError(f"No se encontró enlace directo en {source_url}/download")
        return opener, loc.group(1), headers

    raise RuntimeError(f"Proveedor requiere descarga manual desde navegador: {source_url}")


def download_and_install_game(
    game_id: str,
    root_dir: Path | None = None,
) -> tuple[bool, str]:
    base_root = (root_dir or ROOT).resolve()
    scanner = GameLibraryScannerService(root_dir=base_root)
    game = scanner.get_game_by_id(game_id)
    if not game:
        return False, f"Juego no encontrado en el catálogo: {game_id}"

    source_url = CATALOG_SOURCE_URLS.get(game_id)
    if not source_url:
        return False, f"No hay URL de origen registrada para {game_id}"

    plat_key = str(game.get("platform_key") or "ps3")
    dest_dir = base_root / "roms" / plat_key
    dest_dir.mkdir(parents=True, exist_ok=True)

    part_path: Path | None = None
    try:
        opener, dl_url, headers = _resolve_direct_stream(source_url)
        with opener.open(urllib.request.Request(dl_url, headers=headers), timeout=300) as resp:
            cd = resp.headers.get("Content-Disposition", "")
            m_fn = re.search(r'filename="([^"]+)"', cd)
            fname = m_fn.group(1) if m_fn else urllib.parse.unquote(dl_url.split("/")[-1].split("?")[0])
            if "." not in fname:
                fname = f"{game_id}.zip"
            fname = Path(fname).name

            expected_length = int(resp.headers.get("Content-Length", 0) or 0)
            part_path = dest_dir / f".{fname}.part"
            print(f"[C.C.I. Downloader] Descargando '{game['title']}' -> {dest_dir / fname}")
            with open(part_path, "wb") as fh:
                shutil.copyfileobj(resp, fh, length=524288)
            if part_path.stat().st_size == 0 or (
                expected_length and part_path.stat().st_size != expected_length
            ):
                raise RuntimeError(
                    f"Descarga incompleta: recibidos {part_path.stat().st_size} B, "
                    f"esperados {expected_length} B."
                )

        # La instalación centralizada valida contenido, estructura, identidad,
        # espacio y unicidad antes de mover el paquete a roms/.
        from backend.games.storage_manager import GameStorageManager

        storage = GameStorageManager(root_dir=base_root)
        ok, msg, _entry = storage.install_local_package(
            game_id,
            part_path,
            scanner=scanner,
        )
        return ok, msg
    except (OSError, RuntimeError, urllib.error.URLError, ValueError) as exc:
        return False, f"Descarga/instalación rechazada: {exc}"
    finally:
        if part_path is not None:
            part_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Descargador oficial verificado para C.C.I. SYSTEM")
    parser.add_argument("game_id", nargs="?", help="ID del juego en MODERN_GAMES_CATALOG")
    parser.add_argument("--list", action="store_true", help="Listar todos los IDs y sus URLs de origen")
    args = parser.parse_args()

    if args.list or not args.game_id:
        for gid, url in CATALOG_SOURCE_URLS.items():
            print(f"{gid:56s} -> {url}")
        return 0

    try:
        ok, msg = download_and_install_game(args.game_id)
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
        return 0 if ok else 1
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
