"""Download official covers for all 90 modern games into fotos juegos_new/ and build clean metadata."""
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = ROOT / "tools" / "modern_catalog_raw.json"
PARSED_PATH = ROOT / "tools" / "modern_catalog_parsed.json"
OUT_COVERS = ROOT / "fotos juegos_new"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}

RETROSTIC_THUMBS = {
    1: "https://www.retrostic.com/img/screenshots/Grand-Theft-Auto-San-Andreas-ps3-thumb.jpg",
    2: "https://www.retrostic.com/img/screenshots/fifa-19-ps3-retrostic-thumb.jpg",
    3: "https://www.retrostic.com/img/screenshots/minecraft-ps3-thumb.jpg",
    4: "https://www.retrostic.com/img/screenshots/Pro-Evolution-Soccer-2017-ps3-thumb.jpg",
    5: "https://www.retrostic.com/img/screenshots/The-Amazing-Spider-Man-2-ps3-thumb.jpg",
    6: "https://www.retrostic.com/img/screenshots/Plants-vs-Zombies-Garden-Warfare-ps3-thumb.jpg",
    7: "https://www.retrostic.com/img/screenshots/Assassins-Creed-Rogue-ps3-thumb.jpg",
    8: "https://www.retrostic.com/img/screenshots/sonic-unleashed-ps3-thumb.jpg",
    9: "https://www.retrostic.com/img/screenshots/need-for-speed-rivals-ps3-thumb.jpg",
    10: "https://www.retrostic.com/img/screenshots/WRC-5-FIA-World-Rally-Championship-ps3-thumb.jpg",
    # Fallback via Wikipedia REST API or official boxart for Lego Jurassic World:
    11: "https://www.retrostic.com/img/screenshots/lego-jurassic-park-ps2-thumb.jpg",
}

RETROSTIC_SIZES = {
    1: ("1.83 GB", 1.83),
    2: ("9.37 GB", 9.37),
    3: ("100 MB", 0.10),
    4: ("7.47 GB", 7.47),
    5: ("6.04 GB", 6.04),
    6: ("2.76 GB", 2.76),
    7: ("5.68 GB", 5.68),
    8: ("6.92 GB", 6.92),
    9: ("6.36 GB", 6.36),
    10: ("4.50 GB", 4.50),
    11: ("4.90 GB", 4.90),
}


def find_poster_url(item: dict) -> str:
    idx = item["idx"]
    if idx in RETROSTIC_THUMBS:
        return RETROSTIC_THUMBS[idx]
    cov = item.get("cover", "")
    if cov and ("histats" not in cov and "no-image" not in cov and "logo" not in cov):
        return cov
    url = item["url"].replace("http://romshq.com/", "https://romshq.com/")
    html = urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=15).read().decode("utf-8", errors="ignore")
    posters = re.findall(r"https?://romshq\.com/uploads/[^\s\"'<>]+|/uploads/[^\s\"'<>]+", html, re.I)
    for p in posters:
        if any(p.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
            return ("https://romshq.com" + p) if p.startswith("/") else p
    return cov


def slugify(text: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return t[:52]


def download_cover(item: dict, poster_url: str) -> tuple[int, str, str]:
    ext = Path(urllib.parse.urlparse(poster_url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    fname = f"{item['idx']:02d}_{slugify(item['title'])}{ext}"
    out_path = OUT_COVERS / fname
    req = urllib.request.Request(poster_url, headers={**HEADERS, "Referer": item["url"]})
    data = urllib.request.urlopen(req, timeout=20).read()
    if len(data) < 1000:
        raise ValueError(f"Image too small ({len(data)} bytes) from {poster_url}")
    out_path.write_bytes(data)
    return item["idx"], f"fotos juegos/{fname}", poster_url


def main():
    OUT_COVERS.mkdir(parents=True, exist_ok=True)
    raw = json.load(RAW_PATH.open(encoding="utf-8"))
    parsed = json.load(PARSED_PATH.open(encoding="utf-8"))
    raw_by_idx = {r["idx"]: r for r in raw}

    # First patch missing size/cover on parsed from raw
    for p in parsed:
        idx = p["idx"]
        if idx in RETROSTIC_SIZES:
            p["size_str"], p["size_gb"] = RETROSTIC_SIZES[idx]
        elif not p.get("size_str"):
            sizes = raw_by_idx[idx].get("sizes") or []
            if sizes:
                s = sizes[0]
                p["size_str"] = s
                m = re.search(r"(\d+(?:[.,]\d+)?)\s*(GB|MB)", s, re.I)
                if m:
                    val = float(m.group(1).replace(",", "."))
                    p["size_gb"] = round(val / 1024.0, 3) if "M" in m.group(2).upper() else round(val, 2)
        if not p.get("size_str") and idx == 75:
            p["size_str"] = "2.0 GB"
            p["size_gb"] = 2.0
        elif not p.get("size_str") and idx == 18:
            p["size_str"] = "4.2 GB"
            p["size_gb"] = 4.2

        p["desc"] = raw_by_idx[idx].get("desc", "")
        p["cover_url"] = find_poster_url(p)

    # Try Wikipedia cover for Lego Jurassic World so #11 isn't JP PS2
    try:
        wk = json.loads(
            urllib.request.urlopen(
                urllib.request.Request(
                    "https://en.wikipedia.org/api/rest_v1/page/summary/Lego_Jurassic_World",
                    headers=HEADERS,
                ),
                timeout=10,
            ).read().decode()
        )
        thumb = (wk.get("thumbnail") or {}).get("source")
        if thumb:
            parsed[10]["cover_url"] = thumb
    except Exception:
        pass

    results = {}
    errors = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(download_cover, p, p["cover_url"]): p for p in parsed}
        for f in as_completed(futs):
            p = futs[f]
            try:
                idx, rel, url = f.result()
                results[idx] = rel
            except Exception as e:
                errors.append((p["idx"], p["title"], p.get("cover_url"), str(e)))

    for p in parsed:
        if p["idx"] in results:
            p["cover_rel"] = results[p["idx"]]

    PARSED_PATH.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Downloaded {len(results)}/{len(parsed)} covers cleanly. Errors: {len(errors)}")
    for er in errors:
        print("ERR:", er)


if __name__ == "__main__":
    main()
