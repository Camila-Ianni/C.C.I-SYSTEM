"""tools/download_modern_local.py - Descargador seguro y reanudable para las ROMs PS3 < 4 GB."""
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "roms" / "ps3"
TARGETS = [
    ("Minecraft: PlayStation 3 Edition (100 MB)", "https://www.retrostic.com/es/roms/ps-3/minecraft-83919"),
    ("Grand Theft Auto: San Andreas (1.83 GB)", "https://www.retrostic.com/es/roms/ps-3/grand-theft-auto-san-andreas-83910"),
    ("Plants vs. Zombies: Garden Warfare (2.76 GB)", "https://www.retrostic.com/es/roms/ps-3/plants-vs-zombies-garden-warfare-83911"),
]


def download_all():
    DEST.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"

    for label, url in TARGETS:
        print(f"\n[DL] {label}")
        r1 = s.get(url, timeout=15)
        fm = re.search(r'<form[^>]*id=["\']dl["\'][^>]*>(.*?)</form>', r1.text, re.S)
        if not fm:
            print("  [ERR] No se encontró formulario de descarga.")
            continue
        pdata = {
            m.group(1): m.group(2)
            for m in re.finditer(r'<input[^>]*name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']', fm.group(1))
        }
        r2 = s.post(url.rstrip("/") + "/download", data=pdata, headers={"Referer": url}, timeout=15)
        m_dl = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]*downloads\.retrostic[^'\"]*)['\"]", r2.text)
        if not m_dl:
            print("  [ERR] No se obtuvo enlace directo.")
            continue
        dl_url = m_dl.group(1)
        fname = requests.utils.unquote(dl_url.split("/")[-1])
        final_path = DEST / fname
        if final_path.exists() and final_path.stat().st_size > 1024 * 1024:
            print(f"  [OK] Ya descargado: {fname}")
            continue
        part_path = DEST / f"{fname}.part"
        existing = part_path.stat().st_size if part_path.exists() else 0
        headers = {"Range": f"bytes={existing}-"} if existing > 0 else {}
        with s.get(dl_url, headers=headers, stream=True, timeout=60) as resp:
            if resp.status_code == 416:
                part_path.rename(final_path)
                continue
            resp.raise_for_status()
            mode = "ab" if (existing > 0 and resp.status_code == 206) else "wb"
            with open(part_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
        part_path.rename(final_path)
        print(f"  [OK] Completado: {final_path}")


if __name__ == "__main__":
    download_all()
