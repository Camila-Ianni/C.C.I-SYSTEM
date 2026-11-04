"""
web/dashboard_views.py - Vistas HTML en Python puro para Autenticación y Dashboard Privado.
Diseñado con la estética oficial Cyberpunk / Virtual Console de C.C.I. SYSTEM.
100% Python sin plantillas externas.
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional

from web.landing_page import CYBER_CSS


def _auth_head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} — C.C.I. SYSTEM</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/style.css">
  <style>
{CYBER_CSS}
  .auth-stage {{
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 30px 20px;
    position: relative;
    z-index: 10;
  }}
  .auth-card {{
    background: var(--cci-bg-surface);
    border: 1px solid var(--cci-cyan);
    box-shadow: 0 0 40px var(--cci-cyan-dim);
    max-width: 480px;
    width: 100%;
    padding: 36px 32px;
    clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px));
  }}
  .auth-header {{
    text-align: center;
    margin-bottom: 28px;
  }}
  .auth-logo {{
    font-family: var(--font-display);
    font-size: 1.6rem;
    font-weight: 700;
    letter-spacing: 2px;
    color: #fff;
  }}
  .auth-logo span {{
    color: var(--cci-cyan);
  }}
  .auth-tagline {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--cci-muted);
    letter-spacing: 1px;
    margin-top: 6px;
  }}
  .auth-error {{
    background: rgba(255, 0, 85, 0.12);
    border: 1px solid #ff0055;
    color: #ff6b8b;
    padding: 10px 14px;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .form-group {{
    margin-bottom: 18px;
  }}
  .form-group label {{
    display: block;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--cci-cyan);
    margin-bottom: 6px;
    letter-spacing: 1px;
  }}
  .form-control {{
    width: 100%;
    padding: 12px 14px;
    background: #06080c;
    border: 1px solid var(--cci-border-panel);
    color: #fff;
    font-family: var(--font-display);
    font-size: 0.95rem;
    box-sizing: border-box;
    transition: all 0.2s;
  }}
  .form-control:focus {{
    outline: none;
    border-color: var(--cci-cyan);
    box-shadow: 0 0 12px var(--cci-cyan-dim);
  }}
  .btn-auth {{
    width: 100%;
    padding: 14px;
    background: var(--cci-cyan);
    color: #000;
    border: none;
    font-family: var(--font-display);
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.2s;
    margin-top: 10px;
    clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px));
  }}
  .btn-auth:hover {{
    background: #fff;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.8);
    transform: translateY(-1px);
  }}
  .auth-footer {{
    margin-top: 24px;
    text-align: center;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--cci-muted);
  }}
  .auth-footer a {{
    color: var(--cci-cyan);
    text-decoration: none;
    font-weight: 700;
  }}
  .auth-footer a:hover {{
    text-decoration: underline;
  }}

  /* Dashboard específico */
  .dash-container {{
    max-width: 1100px;
    margin: 100px auto 60px;
    padding: 0 20px;
    position: relative;
    z-index: 10;
  }}
  .dash-header-card {{
    background: var(--cci-bg-surface);
    border: 1px solid var(--cci-border-panel);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    padding: 24px 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 25px;
    clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px));
  }}
  .dash-pilot-info h1 {{
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.8rem;
    color: #fff;
    letter-spacing: 2px;
  }}
  .dash-pilot-info p {{
    margin: 4px 0 0;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--cci-muted);
  }}
  .dash-kpis-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 25px;
  }}
  .kpi-card {{
    background: var(--cci-bg-surface);
    border: 1px solid var(--cci-border-panel);
    padding: 20px;
    position: relative;
  }}
  .kpi-label {{
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--cci-muted);
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
  .kpi-value {{
    font-family: var(--font-display);
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--cci-cyan);
    margin-top: 6px;
  }}
  .dash-panel {{
    background: var(--cci-bg-surface);
    border: 1px solid var(--cci-border-panel);
    margin-bottom: 25px;
    overflow: hidden;
  }}
  .dash-panel-header {{
    padding: 14px 20px;
    background: #07090d;
    border-bottom: 1px solid var(--cci-border-panel);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--cci-cyan);
    font-weight: 700;
    letter-spacing: 1px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .token-box {{
    padding: 12px 16px;
    background: #06080c;
    border: 1px dashed var(--cci-cyan);
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--cci-gold);
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 16px 20px;
  }}
  .dash-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  .dash-table th {{
    padding: 12px 16px;
    text-align: left;
    background: #080a0e;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--cci-muted);
    border-bottom: 1px solid var(--cci-border-panel);
  }}
  .dash-table td {{
    padding: 12px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: #ddd;
  }}
  .btn-logout {{
    padding: 8px 16px;
    background: rgba(255, 0, 85, 0.15);
    border: 1px solid #ff0055;
    color: #ff6b8b;
    text-decoration: none;
    font-family: var(--font-display);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 1px;
    transition: all 0.2s;
  }}
  .btn-logout:hover {{
    background: #ff0055;
    color: #fff;
  }}
  </style>
</head>
<body>
  <div class="crt-overlay"></div>
  <div class="tech-grid-bg"></div>
"""


def render_login_page(error: Optional[str] = None) -> str:
    err_html = f'<div class="auth-error"><span>⚠️</span> {html.escape(error)}</div>' if error else ""
    return _auth_head("Iniciar Sesión") + f"""
  <div class="auth-stage">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-logo">C.C.I. <span>SYSTEM</span></div>
        <div class="auth-tagline">// ACCESO AL ECOSISTEMA CLOUD V2.1</div>
      </div>

      {err_html}

      <form action="/login" method="POST">
        <div class="form-group">
          <label>CORREO ELECTRÓNICO (EMAIL)</label>
          <input type="email" name="email" class="form-control" placeholder="piloto@arcade.com" required autofocus>
        </div>
        <div class="form-group">
          <label>CONTRASEÑA</label>
          <input type="password" name="password" class="form-control" placeholder="••••••••" required>
        </div>
        <button type="submit" class="btn-auth">[ ⌧ A ] AUTENTICAR EN EL NÚCLEO</button>
      </form>

      <div class="auth-footer">
        ¿Aún no tienes cuenta de piloto? <a href="/register">Crear cuenta gratuita</a>
        <br><br>
        <a href="/">← Volver a la Consola Principal</a>
      </div>
    </div>
  </div>
</body>
</html>"""


def render_register_page(error: Optional[str] = None) -> str:
    err_html = f'<div class="auth-error"><span>⚠️</span> {html.escape(error)}</div>' if error else ""
    return _auth_head("Crear Cuenta") + f"""
  <div class="auth-stage">
    <div class="auth-card">
      <div class="auth-header">
        <div class="auth-logo">C.C.I. <span>SYSTEM</span></div>
        <div class="auth-tagline">// REGISTRO DE PILOTO ARCADE CLOUD</div>
      </div>

      {err_html}

      <form action="/register" method="POST">
        <div class="form-group">
          <label>CALLSIGN / NOMBRE DE JUGADOR</label>
          <input type="text" name="username" class="form-control" placeholder="CAMI_PILOT" required autofocus>
        </div>
        <div class="form-group">
          <label>CORREO ELECTRÓNICO (EMAIL)</label>
          <input type="email" name="email" class="form-control" placeholder="piloto@arcade.com" required>
        </div>
        <div class="form-group">
          <label>CONTRASEÑA (MÍNIMO 6 CARACTERES)</label>
          <input type="password" name="password" class="form-control" placeholder="••••••••" minlength="6" required>
        </div>
        <button type="submit" class="btn-auth">[ ⌧ A ] REGISTRAR PILOTO</button>
      </form>

      <div class="auth-footer">
        ¿Ya tienes cuenta activa? <a href="/login">Iniciar sesión</a>
        <br><br>
        <a href="/">← Volver a la Consola Principal</a>
      </div>
    </div>
  </div>
</body>
</html>"""


def render_dashboard_page(account: Dict[str, Any]) -> str:
    username = html.escape(str(account.get("username", "PILOTO")))
    email = html.escape(str(account.get("email", "")))
    token = html.escape(str(account.get("token", "")))
    total_time = html.escape(str(account.get("playtime_formatted", "0h 00m")))
    launches = account.get("total_launches", 0)
    trophies = account.get("total_trophies", 0)
    profiles = account.get("profiles", [])
    game_stats = account.get("game_stats", [])
    scores = account.get("highscores", [])

    profiles_count = len(profiles)

    # Filas de juegos
    if game_stats:
        stats_rows = "".join(f"""
          <tr>
            <td><strong>{html.escape(s.get('game_title') or s.get('game_id','').upper())}</strong></td>
            <td>{html.escape(s.get('genre','Arcade'))}</td>
            <td>{s.get('seconds', 0) // 60} min</td>
            <td>{s.get('launches', 0)}</td>
            <td><span style="color: var(--cci-cyan);">{s.get('progress', 0)}%</span></td>
          </tr>
        """ for s in game_stats)
    else:
        stats_rows = '<tr><td colspan="5" style="text-align: center; color: var(--cci-muted); padding: 20px;">Sin partidas sincronizadas todavía. ¡Inicia el emulador y juega un clásico!</td></tr>'

    # Filas de récords
    if scores:
        scores_rows = "".join(f"""
          <tr>
            <td><strong>{html.escape(sc.get('game_title') or sc.get('game_id','').upper())}</strong></td>
            <td><span style="color: var(--cci-gold); font-weight: 700;">{sc.get('score', 0):,} PTS</span></td>
            <td>LVL {sc.get('level', 1)}</td>
            <td>{html.escape(str(sc.get('recorded_at','')))}</td>
          </tr>
        """ for sc in scores)
    else:
        scores_rows = '<tr><td colspan="4" style="text-align: center; color: var(--cci-muted); padding: 20px;">No has registrado puntuaciones en el Salón de la Fama aún.</td></tr>'

    return _auth_head(f"Dashboard · {username}") + f"""
  <header class="top-hud">
    <div class="container hud-container">
      <a href="/" class="hud-brand">
        <div class="brand-badge">C.C.I. <span>SYSTEM</span></div>
        <div class="hud-sys-status">
          <span class="led-indicator"></span>
          <span>PILOTO: {username}</span>
        </div>
      </a>
      <nav class="hud-nav">
        <a href="/" class="hud-tab">← Volver al Sitio</a>
        <a href="/#catalogo" class="hud-tab">Catálogo</a>
        <a href="/logout" class="btn-logout">CERRAR SESIÓN</a>
      </nav>
    </div>
  </header>

  <div class="dash-container">
    <div class="dash-header-card">
      <div class="dash-pilot-info">
        <h1>PANEL DE PILOTO ARCADE // PILOTO: {username}</h1>
        <p>IDENTIFICADOR CLOUD: {email} · ESTADO: AUTENTICADO</p>
      </div>
      <div>
        <a href="/logout" class="btn-logout">DESCONECTAR</a>
      </div>
    </div>

    <!-- KPIs -->
    <div class="dash-kpis-grid">
      <div class="kpi-card">
        <div class="kpi-label">TIEMPO TOTAL EN CABINA</div>
        <div class="kpi-value">{total_time}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">LANZAMIENTOS DE TÍTULOS</div>
        <div class="kpi-value">{launches}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">TROFEOS DESBLOQUEADOS</div>
        <div class="kpi-value">{trophies}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">PERFILES DE CONSOLA VINCULADOS</div>
        <div class="kpi-value">{profiles_count}</div>
      </div>
    </div>

    <!-- Token de vinculación con la consola física -->
    <div class="dash-panel">
      <div class="dash-panel-header">
        <span>// TOKEN PRIVADO DE SINCRONIZACIÓN DE LA CONSOLA (EMULADOR)</span>
        <span>STATUS: ACTIVO</span>
      </div>
      <div class="token-box">
        <div>
          <span style="color: var(--cci-muted); font-size: 0.72rem; display: block;">TOKEN DE VINCULACIÓN:</span>
          <code>{token}</code>
        </div>
        <span style="font-size: 0.75rem; color: var(--cci-cyan);">USA ESTE TOKEN PARA ENLAZAR TU APP DESKTOP</span>
      </div>
      <p style="margin: 0 20px 16px; font-size: 0.78rem; font-family: var(--font-mono); color: var(--cci-muted);">
        Para sincronizar automáticamente tus récords y horas de juego desde la consola de escritorio hacia este panel web,
        puedes configurar este token en tu emulador local mediante la variable <code>CCI_AUTH_TOKEN</code> o en Ajustes.
      </p>
    </div>

    <!-- Estadísticas por juego -->
    <div class="dash-panel">
      <div class="dash-panel-header">
        <span>// DESGLOSE DE PARTIDAS Y ACTIVIDAD POR TÍTULO</span>
      </div>
      <table class="dash-table">
        <thead>
          <tr>
            <th>JUEGO ARCADE</th>
            <th>GÉNERO</th>
            <th>TIEMPO</th>
            <th>LANZAMIENTOS</th>
            <th>PROGRESO</th>
          </tr>
        </thead>
        <tbody>
          {stats_rows}
        </tbody>
      </table>
    </div>

    <!-- Récords Personales -->
    <div class="dash-panel">
      <div class="dash-panel-header">
        <span>// TUS PUNTUACIONES EN EL SALÓN DE LA FAMA</span>
      </div>
      <table class="dash-table">
        <thead>
          <tr>
            <th>TÍTULO</th>
            <th>PUNTUACIÓN</th>
            <th>NIVEL</th>
            <th>FECHA DE REGISTRO</th>
          </tr>
        </thead>
        <tbody>
          {scores_rows}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
