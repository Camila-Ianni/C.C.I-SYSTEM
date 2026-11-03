#!/usr/bin/env python3
"""web/app.py - Landing Page Oficial en Flask de C.C.I. SYSTEM Virtual Console."""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path
from flask import Flask, Response, abort, jsonify, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cci_console import CATALOG, CATEGORIES
from web.landing_page import build_landing_page, CYBER_CSS, CLIENT_JS

app = Flask(__name__)

DOWNLOADS_DIR = ROOT / "web" / "static" / "downloads"
CARDS_DIR = ROOT / "assets_cards"
UI_DIR = ROOT / "assets_ui"
PANTALLAS_DIR = ROOT / "pantallas"
FOTOS_WEB_DIR = ROOT / "fotos web"

WEB_CARDS_MAP = {
    "davinci": "Street_Fighter_old_logo.png",
    "asteroids": "asteroids.jpg",
    "mario": "super mario.jpg",
    "zelda": "The_Legend_of_Zelda_film_logo.jpg",
    "pacman": "pac man.jpg",
    "tetris": "tetris logo .jpg",
    "space_invaders": "space nvaders.jpg",
    "metalslug": "metal slug.jpg",
    "doom": "Doom_logo.png",
    "flappy": "Flappy_Bird_icon.png",
    "dino": "dino.jpg",
    "ghostbusters": "ghostbusters.webp",
    "cyberpunk": "ciberpunk.ico",
    "pokemon": "pokemon.webp",
    "megaman": "megaman.jpg" if (FOTOS_WEB_DIR / "megaman.jpg").exists() else "megaman}",
    "castlevania": "castlevania.webp",
    "bubblebobble": "MV5BNDk1NzI2YmEtZGJiNi00Mzc5LTkxMzktMWI4MmQ2YTZmNGQzXkEyXkFqcGc@._V1_.jpg",
    "plantsvszombies": "pvzr-key-art.png.adapt.crop1x1.767p.png",
    "donkeykong": "donkeykong.jpg",
}


def _format_games():
    """Enriquece el catálogo oficial con las imágenes de 'fotos web' para la landing."""
    formatted = []
    for g in CATALOG:
        gid = g["id"]
        web_file = WEB_CARDS_MAP.get(gid)
        if web_file and (FOTOS_WEB_DIR / web_file).exists():
            card_url = f"/assets/fotos_web/{urllib.parse.quote(web_file)}"
        else:
            card_img = f"{gid}_clean.png" if (CARDS_DIR / f"{gid}_clean.png").exists() else f"{gid}.png"
            card_url = f"/assets/cards/{card_img}"

        formatted.append({
            "id": gid,
            "title": g["title"],
            "subtitle": g.get("subtitle", ""),
            "developer": g.get("developer", "C.C.I. System"),
            "year": g.get("year", "2026"),
            "genre": g.get("genre", "Arcade"),
            "players": g.get("players", "1"),
            "tags": [t.strip() for t in g.get("tags", "").split("·") if t.strip()],
            "categories": sorted(list(g.get("categories", {"ARCADE"}))),
            "card_url": card_url,
            "slot": g.get("slot", 0),
        })
    return formatted


@app.route("/")
def index():
    games = _format_games()
    author_info = {
        "name": "Camila Carolina Ianni",
        "title": "Desarrolladora & Arquitecta de C.C.I. SYSTEM",
        "bio": (
            "Estudiante de Analista de Sistemas apasionada por la arquitectura de software, "
            "emulación y desarrollo de sistemas interactivos en Python. C.C.I. SYSTEM nace como un proyecto "
            "integral que transforma una suite de 19 clásicos arcade en una consola virtual moderna con "
            "interfaz Cyberpunk / PS5, sistema multiusuario con gestión de estadísticas independiente, "
            "grabador de capturas y mapeo universal de gamepads."
        ),
        "institution": "Escuela Da Vinci — Analista de Sistemas",
        "year": "2026",
    }
    stats = {
        "total_games": len(games),
        "architecture": "100% Python (Pygame-CE)",
        "resolution": "1280 x 720 Nativa (Escalable / Fullscreen)",
        "audio": "Sintetizador Estéreo en Tiempo Real & BGM Ambiental",
        "profiles": "0 Perfiles de fábrica (Arranque limpio para nuevos usuarios)",
        "gamepad": "Soporte Plug & Play (PS4, PS5, Xbox, Mandos Genéricos USB)",
    }
    html_content = build_landing_page(
        games=games,
        categories=CATEGORIES,
        author=author_info,
        stats=stats
    )
    return Response(html_content, mimetype="text/html")


@app.route("/api/games")
def api_games():
    return jsonify({
        "status": "success",
        "count": len(CATALOG),
        "games": _format_games()
    })


@app.route("/download/mac")
def download_mac():
    dmg_path = DOWNLOADS_DIR / "CCI_System_macOS.dmg"
    if dmg_path.exists():
        return send_from_directory(
            DOWNLOADS_DIR,
            "CCI_System_macOS.dmg",
            as_attachment=True,
            download_name="CCI_System_macOS.dmg"
        )
    zip_path = DOWNLOADS_DIR / "CCI_System_macOS.zip"
    if zip_path.exists():
        return send_from_directory(
            DOWNLOADS_DIR,
            "CCI_System_macOS.zip",
            as_attachment=True,
            download_name="CCI_System_macOS.zip"
        )
    abort(404, description="Paquete para macOS aún no generado.")


@app.route("/download/windows")
def download_windows():
    exe_path = DOWNLOADS_DIR / "CCI_System_Windows_Installer.exe"
    if exe_path.exists():
        return send_from_directory(
            DOWNLOADS_DIR,
            "CCI_System_Windows_Installer.exe",
            as_attachment=True,
            download_name="CCI_System_Windows_Installer.exe"
        )
    zip_path = DOWNLOADS_DIR / "CCI_System_Windows.zip"
    if zip_path.exists():
        return send_from_directory(
            DOWNLOADS_DIR,
            "CCI_System_Windows.zip",
            as_attachment=True,
            download_name="CCI_System_Windows.zip"
        )
    abort(404, description="Paquete para Windows aún no generado.")


@app.route("/assets/fotos_web/<path:filename>")
def serve_fotos_web(filename):
    return send_from_directory(FOTOS_WEB_DIR, filename)


@app.route("/assets/cards/<path:filename>")
def serve_card(filename):
    return send_from_directory(CARDS_DIR, filename)


@app.route("/assets/ui/<path:filename>")
def serve_ui(filename):
    return send_from_directory(UI_DIR, filename)


@app.route("/assets/pantallas/<path:filename>")
def serve_pantallas(filename):
    return send_from_directory(PANTALLAS_DIR, filename)


@app.route("/static/css/style.css")
@app.route("/style.css")
def serve_css():
    return Response(CYBER_CSS, mimetype="text/css")


@app.route("/static/js/main.js")
@app.route("/main.js")
def serve_js():
    return Response(CLIENT_JS, mimetype="application/javascript")


@app.route("/assets/welcome.png")
def serve_welcome():
    return send_from_directory(ROOT, "Bienvenida al sistema C.C.I.png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f"  C.C.I. SYSTEM LANDING PAGE — FLASK SERVER")
    print(f"  Servidor iniciado en: http://127.0.0.1:{port}")
    print(f"  Autora: Camila Carolina Ianni")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=True)
