#!/usr/bin/env python3
"""web/app.py - Landing Page Oficial en Flask de C.C.I. SYSTEM Virtual Console."""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path
from flask import Flask, Response, abort, jsonify, make_response, redirect, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cci_database
from catalog_data import CATALOG, CATEGORIES
from web.landing_page import build_landing_page, CYBER_CSS, CLIENT_JS

app = Flask(__name__)

# Inicializar base de datos SQLite relacional
try:
    cci_database.init_db()
except Exception as _e:
    print(f"[web/app.py] Aviso inicialización DB: {_e}")

MAC_DOWNLOAD_URL = os.environ.get(
    "MAC_DOWNLOAD_URL",
    "https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg"
)
WIN_DOWNLOAD_URL = os.environ.get(
    "WIN_DOWNLOAD_URL",
    "https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe"
)

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
        "avatar_url": "/assets/fotos_web/Cami.jpg",
        "github_url": "https://github.com/Camila-Ianni/C.C.I-SYSTEM",
        "github_profile": "https://github.com/Camila-Ianni",
        "bio": (
            "Estudiante de la carrera de Analista de Sistemas en Escuela Da Vinci. "
            "C.C.I. SYSTEM fue concebido como un proyecto académico para el Parcial 2, "
            "con el propósito de demostrar la capacidad de Python para sostener una plataforma interactiva "
            "de alto rendimiento a 60 FPS. El proyecto aborda la orquestación determinista de 19 clásicos arcade, "
            "aislamiento estricto de memoria entre motores independientes, traducción universal de mandos con respuesta háptica "
            "y una experiencia de usuario limpia con 0 perfiles de fábrica."
        ),
        "institution": "Escuela Da Vinci — Analista de Sistemas · Parcial 2",
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


# ==============================================================================
# REST API v1 (Fase 2: Arquitectura de Base de Datos y Servicios REST)
# ==============================================================================

@app.route("/api/games")
@app.route("/api/v1/games")
def api_games():
    """Retorna el catálogo completo de títulos (desde SQLite con fallback)."""
    try:
        games = cci_database.get_all_games()
        if not games:
            games = _format_games()
    except Exception:
        games = _format_games()
    return jsonify({
        "status": "success",
        "count": len(games),
        "games": games
    })


@app.route("/api/v1/games/<game_id>")
def api_game_detail(game_id: str):
    """Retorna información detallada de un juego y su podio de récords."""
    game = cci_database.get_game_by_id(game_id)
    if not game:
        match = next((g for g in CATALOG if g["id"] == game_id), None)
        if not match:
            abort(404, description=f"Juego con id '{game_id}' no encontrado.")
        game = match

    scores = cci_database.get_leaderboard(game_id=game_id, limit=5)
    return jsonify({
        "status": "success",
        "game": game,
        "highscores": scores
    })


@app.route("/api/v1/health")
def api_health():
    """Estado de salud del backend, base de datos SQLite y telemetría."""
    return jsonify(cci_database.get_telemetry_summary())


@app.route("/api/v1/version")
def api_version():
    """Retorna la versión oficial liberada y metadata para el auto-updater."""
    from cci_updater import load_local_version
    ver_data = load_local_version()
    return jsonify({
        "status": "success",
        **ver_data
    })


@app.route("/api/v1/stats")
def api_stats():
    """Telemetría global y métricas de uso del ecosistema."""
    return jsonify({
        "status": "success",
        "telemetry": cci_database.get_telemetry_summary()
    })


@app.route("/api/v1/leaderboards", methods=["GET", "POST"])
def api_leaderboards():
    """
    GET: Retorna el ranking global o filtrado por ?game_id=...&limit=...
    POST: Registra un nuevo récord arcade con validación de datos.
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        game_id = str(payload.get("game_id", "")).strip()
        player_name = str(payload.get("player_name", "")).strip().upper()
        try:
            score = int(payload.get("score", 0))
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "El campo 'score' debe ser un entero válido."}), 400

        level = int(payload.get("level", 1))
        profile_id = payload.get("profile_id")

        if not game_id or not player_name or score <= 0:
            return jsonify({
                "status": "error",
                "message": "Parámetros inválidos. Requiere 'game_id', 'player_name' y 'score' > 0."
            }), 400

        try:
            rec_id = cci_database.record_highscore(
                game_id=game_id,
                player_name=player_name,
                score=score,
                level=level,
                profile_id=profile_id
            )
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        return jsonify({
            "status": "success",
            "message": "Récord guardado exitosamente en el salón de la fama.",
            "record_id": rec_id,
            "data": {
                "game_id": game_id,
                "player_name": player_name,
                "score": score,
                "level": level,
            }
        }), 201

    # GET
    game_id = request.args.get("game_id")
    try:
        limit = int(request.args.get("limit", 15))
    except (ValueError, TypeError):
        limit = 15

    scores = cci_database.get_leaderboard(game_id=game_id, limit=limit)
    return jsonify({
        "status": "success",
        "filter_game": game_id,
        "count": len(scores),
        "leaderboard": scores
    })


@app.route("/api/v1/leaderboards/<game_id>")
def api_leaderboards_game(game_id: str):
    """Atajo para el podio de un juego específico."""
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10
    scores = cci_database.get_leaderboard(game_id=game_id, limit=limit)
    return jsonify({
        "status": "success",
        "game_id": game_id,
        "count": len(scores),
        "leaderboard": scores
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
    if MAC_DOWNLOAD_URL:
        return redirect(MAC_DOWNLOAD_URL)
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
    if WIN_DOWNLOAD_URL:
        return redirect(WIN_DOWNLOAD_URL)
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


@app.route("/assets/video/<path:filename>")
def serve_video(filename):
    return send_from_directory(ROOT, filename, mimetype="video/mp4")


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
