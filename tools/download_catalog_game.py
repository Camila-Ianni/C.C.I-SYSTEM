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


def download_and_install_game(game_id: str) -> tuple[bool, str]:
    scanner = GameLibraryScannerService.get_instance(ROOT)
    game = scanner.get_game_by_id(game_id)
    if not game:
        return False, f"Juego no encontrado en el catálogo: {game_id}"

    source_url = CATALOG_SOURCE_URLS.get(game_id)
    if not source_url:
        return False, f"No hay URL de origen registrada para {game_id}"

    plat_key = str(game.get("platform_key") or "ps3")
    dest_dir = ROOT / "roms" / plat_key
    dest_dir.mkdir(parents=True, exist_ok=True)

    opener, dl_url, headers = _resolve_direct_stream(source_url)
    with opener.open(urllib.request.Request(dl_url, headers=headers), timeout=300) as resp:
        cd = resp.headers.get("Content-Disposition", "")
        m_fn = re.search(r'filename="([^"]+)"', cd)
        if m_fn:
            fname = m_fn.group(1)
        else:
            fname = urllib.parse.unquote(dl_url.split("/")[-1].split("?")[0])
            if "." not in fname:
                fname = f"{game_id}.zip"

        total_mb = int(resp.headers.get("Content-Length", 0)) // (1024 * 1024)
        part_path = dest_dir / f".{fname}.part"
        final_arc = dest_dir / fname
        print(f"[C.C.I. Downloader] Descargando '{game['title']}' ({total_mb} MB) -> {final_arc.relative_to(ROOT)}...")
        with open(part_path, "wb") as fh:
            shutil.copyfileobj(resp, fh, length=524288)
        part_path.replace(final_arc)

    unar_bin = shutil.which("unar") or "/opt/homebrew/bin/unar"
    if final_arc.suffix.lower() in (".rar", ".zip", ".7z") and unar_bin and Path(unar_bin).exists():
        print(f"[C.C.I. Downloader] Extrayendo paquete {final_arc.name}...")
        subprocess.run([unar_bin, "-f", "-o", str(dest_dir), str(final_arc)], check=False)
        for sub in list(dest_dir.rglob("*")):
            if sub.is_file() and sub.parent != dest_dir and not any(p.startswith(".") for p in sub.relative_to(dest_dir).parts):
                target = dest_dir / sub.name
                if not target.exists():
                    shutil.move(str(sub), str(target))

    scanner.refresh()
    ok, msg = scanner.verify_game_file(game_id)
    return ok, msg


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
