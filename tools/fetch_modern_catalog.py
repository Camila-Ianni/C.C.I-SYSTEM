"""Inspect and extract structured modern game metadata from the 90 user URLs."""
import json
import re
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path

DOCX_PATH = Path(
    "/Users/cami/.gemini/antigravity/brain/1db74365-5846-478f-81f4-d6b7838af88e/"
    ".user_uploaded/media_1794408755201_098226a8.docx"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}


def extract_urls() -> list[str]:
    with zipfile.ZipFile(DOCX_PATH) as z:
        xml_data = z.read("word/document.xml").decode("utf-8", errors="ignore")
        rels = z.read("word/_rels/document.xml.rels").decode("utf-8", errors="ignore")
    urls = re.findall(r"https?://[^\s<\"']+", xml_data + "\n" + rels)
    seen = []
    for u in urls:
        if any(d in u for d in ("retrostic.com", "romsjuegos.com", "romshq.com")) and u not in seen:
            seen.append(u)
    return seen


def parse_size_gb(size_str: str) -> float | None:
    if not size_str:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(GB|MB|GiB|MiB)", size_str, re.I)
    if not m:
        return None
    val = float(m.group(1).replace(",", "."))
    unit = m.group(2).upper()
    if "M" in unit:
        return round(val / 1024.0, 3)
    return round(val, 2)


def inspect_url(idx: int, url: str) -> dict:
    req_url = url.replace("http://romshq.com/", "https://romshq.com/")
    req = urllib.request.Request(req_url, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    host = urllib.parse.urlparse(req_url).netloc.lower()

    if "retrostic.com" in host:
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
        title = unescape(re.sub(r"<[^>]+>", "", h1_m.group(1))).strip() if h1_m else ""
        title = re.sub(r"^Descargar\s+", "", title, flags=re.I)
        title = re.sub(r"\s+ROM$", "", title, flags=re.I).strip()
        kv = {}
        for m in re.finditer(r"<tr>(.*?)</tr>", html, re.S):
            cells = [
                re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", m.group(1), re.S)
            ]
            if len(cells) >= 2:
                kv[cells[0].rstrip(":")] = cells[1]
        img_m = re.search(
            r"""src=["']([^"']*roms[^"']+\.(?:jpg|jpeg|png|webp))["']""",
            html,
            re.I,
        )
        og_img = re.search(
            r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""",
            html,
            re.I,
        )
        cover = img_m.group(1) if img_m else (og_img.group(1) if og_img else "")
        if cover.startswith("/"):
            cover = "https://www.retrostic.com" + cover
        return {
            "idx": idx,
            "url": url,
            "source": "retrostic",
            "title": title,
            "console": "PS3",
            "format": "ZIP/ISO",
            "genre": kv.get("Género(s)", "Action"),
            "size_str": kv.get("Tamaño", "unknown"),
            "size_gb": parse_size_gb(kv.get("Tamaño", "")),
            "cover": cover,
            "year": "—",
            "dl_links": [req_url.rstrip("/") + "/download"],
            "filename": kv.get("Nombre del archivo", ""),
        }

    elif "romsjuegos.com" in host:
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
        title = unescape(re.sub(r"<[^>]+>", "", h1_m.group(1))).strip() if h1_m else ""
        txt = re.sub(r"<[^>]+>", " ", html)
        sz_m = re.search(r"Tamaño[^0-9]*(\d+(?:[.,]\d+)?\s*(?:GB|MB))", txt, re.I)
        if not sz_m:
            sz_m = re.search(r"\b(\d+(?:[.,]\d+)?\s*(?:GB|MB))\b", txt, re.I)
        yr_m = re.search(r"(?:Año|Fecha|Release)[^0-9]*(20\d{2}|19\d{2})", txt, re.I)
        og_img = re.search(
            r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""",
            html,
            re.I,
        )
        dl = re.findall(r"""href=["'](https?://romsforever\.co/[^"']+)["']""", html, re.I)
        s_str = sz_m.group(1) if sz_m else ""
        return {
            "idx": idx,
            "url": url,
            "source": "romsjuegos",
            "title": title,
            "console": "PS4",
            "format": "PKG",
            "genre": "Action / Sports",
            "size_str": s_str,
            "size_gb": parse_size_gb(s_str),
            "cover": og_img.group(1) if og_img else "",
            "year": yr_m.group(1) if yr_m else "—",
            "dl_links": dl[:2],
        }

    else:  # romshq.com
        pos = html.find("<h1")
        chunk = re.sub(r"<[^>]+>", " | ", html[max(0, pos - 300) : pos + 2600])
        parts = [unescape(p).strip() for p in chunk.split("|") if unescape(p).strip()]
        h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.I | re.S)
        title = unescape(re.sub(r"<[^>]+>", "", h1_m.group(1))).strip() if h1_m else ""
        fmt = parts[0] if parts and parts[0] in ("PKG", "NSP", "XCI", "ISO", "ZIP", "RAR") else ""
        rel_date = ""
        console_raw = ""
        for i, p in enumerate(parts):
            if re.match(r"\d{2}\s+[A-Za-z]{3},\s+\d{4}", p):
                rel_date = p
                if i + 1 < len(parts):
                    console_raw = parts[i + 1]
                break
        yr_m = re.search(r"(20\d{2}|19\d{2})", rel_date)
        og_img = re.search(
            r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""",
            html,
            re.I,
        )
        imgs = [
            i
            for i in re.findall(r"""<img[^>]+src=["']([^"']+)["']""", html, re.I)
            if "logo" not in i.lower() and not i.startswith("data:") and "svg" not in i.lower()
        ]
        cover = og_img.group(1) if og_img else (imgs[0] if imgs else "")
        if cover.startswith("/"):
            cover = "https://romshq.com" + cover

        body_txt = re.sub(r"<[^>]+>", " ", html[pos:])
        dl_sec = body_txt[:4500]
        sizes = re.findall(r"\b(\d+(?:[.,]\d+)?\s*(?:GB|MB))\b", dl_sec, re.I)
        s_str = sizes[0] if sizes else ""
        dl = re.findall(
            r"""href=["']([^"']*(?:datanodes|gofile|1fichier|mediafire|mega\.nz|/download/)[^"']*)["']""",
            html[pos:],
            re.I,
        )
        return {
            "idx": idx,
            "url": url,
            "source": "romshq",
            "title": title,
            "console": console_raw or fmt,
            "format": fmt,
            "size_str": s_str,
            "size_gb": parse_size_gb(s_str),
            "cover": cover,
            "year": yr_m.group(1) if yr_m else "—",
            "dl_links": list(dict.fromkeys(dl))[:4],
        }


def main():
    seen = extract_urls()
    items = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(inspect_url, i, u) for i, u in enumerate(seen, 1)]
        for f in as_completed(futs):
            items.append(f.result())
    items.sort(key=lambda x: x["idx"])
    Path("tools/modern_catalog_parsed.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Consoles distribution:", Counter(x["console"] for x in items))
    for x in items:
        sg = x["size_gb"]
        tag = "LOCAL(<4G)" if (sg is not None and sg < 4.0) else ("UNKNOWN" if sg is None else "CLOUD(>=4G)")
        print(f"{x['idx']:02d} | {x['console']:18s} | {tag:11s} | {x['size_str']:9s} | {x['title'][:42]:42s} | img={bool(x['cover'])}")


if __name__ == "__main__":
    main()
