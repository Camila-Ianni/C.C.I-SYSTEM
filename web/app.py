#!/usr/bin/env python3
"""web/app.py - Landing Page Oficial en Flask de C.C.I. SYSTEM — OmniDash Virtual Console (Frutiger Aero)."""
from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path
from flask import Flask, Response, abort, jsonify, redirect, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cci_database
from catalog_data import CATALOG
from backend.games.modern_catalog import MODERN_GAMES_CATALOG
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
FOTOS_JUEGOS_DIR = ROOT / "fotos juegos"
OMNIDASH_ASSETS_DIR = ROOT / "assets_omnidash"

MODERN_WEB_CATEGORIES = [
    "TODOS",
    "PS5",
    "PS4",
    "SWITCH",
    "SWITCH 2",
    "PS3",
    "PS1 / PS2",
    "ACCIÓN",
    "AVENTURA",
    "DEPORTES / CARRERAS",
    "LUCHA",
    "SANDBOX / RPG",
]


def _infer_web_categories(entry: dict) -> list[str]:
    badge = str(entry.get("badge") or "PS5").upper()
    genre = str(entry.get("genre") or "").upper()
    cats = ["TODOS", badge]
    if badge in ("PS1", "PS2"):
        cats.append("PS1 / PS2")
    if any(k in genre for k in ("ACCIÓN", "SHOOTER", "SURVIVAL", " SIGILO", "PLATAFORMAS")):
        cats.append("ACCIÓN")
    if any(k in genre for k in ("AVENTURA", "METROIDVANIA", "PUZLES")):
        cats.append("AVENTURA")
    if any(k in genre for k in ("DEPORTES", "FÚTBOL", "CARRERAS", "KARTS", "BAILE", "RITMO")):
        cats.append("DEPORTES / CARRERAS")
    if "LUCHA" in genre:
        cats.append("LUCHA")
    if any(k in genre for k in ("SANDBOX", "RPG", "SIMULACIÓN", "MUNDO ABIERTO")):
        cats.append("SANDBOX / RPG")
    return cats


def _format_games() -> list[dict]:
    """Formatea los 90 títulos modernos del catálogo oficial con sus carátulas de 'fotos juegos/'."""
    formatted = []
    for idx, g in enumerate(MODERN_GAMES_CATALOG, start=1):
        gid = g["id"]
        cov_rel = str(g.get("cover") or "")
        cov_name = Path(cov_rel).name if cov_rel else ""
        if cov_name and (FOTOS_JUEGOS_DIR / cov_name).exists():
            card_url = f"/assets/fotos_juegos/{urllib.parse.quote(cov_name)}"
        else:
            card_url = "/assets/welcome.png"

        badge = str(g.get("badge") or "PS5")
        fmt = str(g.get("format") or "PKG")
        sz = str(g.get("size") or "—")
        console_name = str(g.get("console") or "Consola Moderna")
        genre = str(g.get("genre") or "Acción / Aventura")

        formatted.append({
            "id": gid,
            "title": g["title"],
            "subtitle": g.get("desc", ""),
            "developer": g.get("developer", "Official Studio"),
            "year": str(g.get("year", "2025")),
            "genre": genre,
            "players": g.get("players", "1-4 Jugadores"),
            "console": console_name,
            "badge": badge,
            "format": fmt,
            "size": sz,
            "tags": [badge, f"{fmt} · {sz}", genre],
            "categories": _infer_web_categories(g),
            "card_url": card_url,
            "slot": idx,
        })
    return formatted


@app.route("/")
def index():
    games = _format_games()
    author_info = {
        "name": "Camila Carolina Ianni",
        "title": "Desarrolladora & Arquitecta de Software — C.C.I. SYSTEM",
        "avatar_url": "/assets/fotos_web/Cami.jpg",
        "github_url": "https://github.com/Camila-Ianni/C.C.I-SYSTEM",
        "github_profile": "https://github.com/Camila-Ianni",
        "bio": (
            "Estudiante de la carrera de Analista de Sistemas en Escuela Da Vinci. "
            "C.C.I. SYSTEM evolucionó hacia una consola virtual de nueva generación con interfaz acelerada por hardware "
            "en PySide6 (Qt6) bajo estética Frutiger Aero (cristal acrílico traslúcido, iluminación cian-aguamarina y desenfoque óptico). "
            "Integra una biblioteca de 90 títulos modernos (PlayStation 5, PlayStation 4, Nintendo Switch, Switch 2, PS3, PS2 y PS1) "
            "con instalación directa en consola para macOS y Windows, gestión inteligente de almacenamiento estilo PS5 que permite "
            "desinstalar juegos para liberar espacio sin perder jamás tu progreso ni tus partidas guardadas, y el ecosistema social "
            "C.C.I. Communities con voz/streaming WebRTC en tiempo real (LiveKit SFU), Soundboard RTC, detección automática de juegos "
            "y vinculación segura OAuth 2.0 con Spotify."
        ),
        "institution": "Escuela Da Vinci — Analista de Sistemas · Arquitectura de Software",
        "year": "2026",
    }
    stats = {
        "total_games": len(games),
        "architecture": "PySide6 (Qt6 Frutiger Aero) + Runtime Multi-OS 60 FPS + LiveKit WebRTC",
        "resolution": "1280 x 720 / 1080p Acelerado por Hardware (Metal / DirectX / OpenGL)",
        "audio": "Voz & Streaming LiveKit RTC + Soundboard Mixer + Spotify OAuth 2.0",
        "profiles": "Gestión de Almacenamiento estilo PS5 (Desinstalación sin perder progreso)",
        "gamepad": "Soporte Plug & Play (DualSense PS5, DualShock 4, Switch Pro, Xbox, Teclado)",
    }
    html_content = build_landing_page(
        games=games,
        categories=MODERN_WEB_CATEGORIES,
        author=author_info,
        stats=stats,
    )
    return Response(html_content, mimetype="text/html")


# ==============================================================================
# REST API v1 (Persistencia SQLite + Catálogo Moderno)
# ==============================================================================

@app.route("/api/games")
@app.route("/api/v1/games")
def api_games():
    """Retorna el catálogo completo de títulos."""
    try:
        games = cci_database.get_all_games()
        if not games:
            games = _format_games()
    except Exception:
        games = _format_games()
    return jsonify({
        "status": "success",
        "count": len(games),
        "games": games,
    })


@app.route("/api/v1/games/<game_id>")
def api_game_detail(game_id: str):
    """Retorna información detallada de un juego y su podio de récords."""
    game = cci_database.get_game_by_id(game_id)
    if not game:
        match = next((g for g in _format_games() if g["id"] == game_id), None)
        if not match:
            match = next((g for g in CATALOG if g["id"] == game_id), None)
        if not match:
            abort(404, description=f"Juego con id '{game_id}' no encontrado.")
        game = match

    scores = cci_database.get_leaderboard(game_id=game_id, limit=5)
    return jsonify({
        "status": "success",
        "game": game,
        "highscores": scores,
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
        **ver_data,
    })


@app.route("/api/v1/stats")
def api_stats():
    """Telemetría global y métricas de uso del ecosistema."""
    return jsonify({
        "status": "success",
        "telemetry": cci_database.get_telemetry_summary(),
    })


@app.route("/api/v1/leaderboards", methods=["GET", "POST"])
def api_leaderboards():
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
                "message": "Parámetros inválidos. Requiere 'game_id', 'player_name' y 'score' > 0.",
            }), 400

        try:
            rec_id = cci_database.record_highscore(
                game_id=game_id,
                player_name=player_name,
                score=score,
                level=level,
                profile_id=profile_id,
            )
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        return jsonify({
            "status": "success",
            "message": "Récord guardado exitosamente.",
            "record_id": rec_id,
            "data": {
                "game_id": game_id,
                "player_name": player_name,
                "score": score,
                "level": level,
            },
        }), 201

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
        "leaderboard": scores,
    })


@app.route("/api/v1/leaderboards/<game_id>")
def api_leaderboards_game(game_id: str):
    try:
        limit = int(request.args.get("limit", 10))
    except (ValueError, TypeError):
        limit = 10
    scores = cci_database.get_leaderboard(game_id=game_id, limit=limit)
    return jsonify({
        "status": "success",
        "game_id": game_id,
        "count": len(scores),
        "leaderboard": scores,
    })


@app.route("/download/mac")
def download_mac():
    dmg_path = DOWNLOADS_DIR / "CCI_System_macOS.dmg"
    if dmg_path.exists():
        return send_from_directory(
            DOWNLOADS_DIR,
            "CCI_System_macOS.dmg",
            as_attachment=True,
            download_name="CCI_System_macOS.dmg",
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
            download_name="CCI_System_Windows_Installer.exe",
        )
    if WIN_DOWNLOAD_URL:
        return redirect(WIN_DOWNLOAD_URL)
    abort(404, description="Paquete para Windows aún no generado.")


@app.route("/assets/fotos_juegos/<path:filename>")
def serve_fotos_juegos(filename):
    return send_from_directory(FOTOS_JUEGOS_DIR, filename)


@app.route("/assets/fotos_web/<path:filename>")
def serve_fotos_web(filename):
    return send_from_directory(FOTOS_WEB_DIR, filename)


@app.route("/assets/omnidash/<path:filename>")
def serve_omnidash_assets(filename):
    return send_from_directory(OMNIDASH_ASSETS_DIR, filename)


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
@app.route("/static/cyber.css")
@app.route("/style.css")
def serve_css():
    return Response(CYBER_CSS, mimetype="text/css")


@app.route("/static/js/main.js")
@app.route("/static/client.js")
@app.route("/main.js")
def serve_js():
    return Response(CLIENT_JS, mimetype="application/javascript")


@app.route("/assets/welcome.png")
def serve_welcome():
    if (ROOT / "background.jpg").exists():
        return send_from_directory(ROOT, "background.jpg")
    return send_from_directory(ROOT, "Bienvenida al sistema C.C.I.png")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f"  C.C.I. SYSTEM — OMNIDASH FRUTIGER AERO WEB SERVER")
    print(f"  Servidor iniciado en: http://127.0.0.1:{port}")
    print(f"  Autora: Camila Carolina Ianni")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
