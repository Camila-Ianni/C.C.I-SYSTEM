"""
C.C.I. SYSTEM — Landing Page Web (Frutiger Aero / Cristal Acrílico Cian-Aguamarina)
Sincronizada con la consola virtual OmniDash (PySide6 Qt6), los 90 juegos modernos
(PS5, PS4, Nintendo Switch, Switch 2, PS3, PS2, PS1), gestión de almacenamiento
estilo PS5 sin perder progreso y C.C.I. Communities en tiempo real.
"""

from html import escape
import json

CYBER_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg-deep: #05111d;
  --bg-ocean: #091d30;
  --bg-panel: rgba(13, 31, 49, 0.72);
  --bg-panel-strong: rgba(10, 25, 41, 0.86);
  --bg-glass-light: rgba(34, 82, 118, 0.28);
  --border-glass: rgba(86, 201, 233, 0.34);
  --border-glass-bright: rgba(126, 238, 255, 0.68);
  --specular-top: rgba(255, 255, 255, 0.24);
  --cyan-aero: #27bde7;
  --cyan-bright: #5ce6ff;
  --aqua-mint: #56f0c8;
  --azure-glow: #1b88ca;
  --text-main: #f0faff;
  --text-soft: #b8dceebb;
  --text-muted: #7ea8c4;
  --radius-xl: 26px;
  --radius-lg: 20px;
  --radius-md: 14px;
  --radius-pill: 999px;
  --shadow-aero: 0 20px 50px rgba(2, 10, 20, 0.65), inset 0 1px 1px rgba(255, 255, 255, 0.22);
  --shadow-glow: 0 0 28px rgba(39, 189, 231, 0.32);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  scroll-behavior: smooth;
  background-color: var(--bg-deep);
  color: var(--text-main);
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
  min-height: 100vh;
  background:
    radial-gradient(circle at 18% 12%, rgba(39, 189, 231, 0.24), transparent 38%),
    radial-gradient(circle at 84% 18%, rgba(86, 240, 200, 0.18), transparent 40%),
    radial-gradient(circle at 50% 85%, rgba(27, 136, 202, 0.22), transparent 48%),
    linear-gradient(180deg, #061423 0%, #081b2e 45%, #05101c 100%);
  color: var(--text-main);
  overflow-x: hidden;
  line-height: 1.6;
  position: relative;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  background: url('/assets/welcome.png') center center / cover no-repeat;
  opacity: 0.18;
  filter: saturate(1.2) blur(4px);
  pointer-events: none;
  z-index: -2;
}

body::after {
  content: "";
  position: fixed;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(5, 17, 29, 0.55) 0%, rgba(7, 22, 37, 0.82) 60%, rgba(5, 16, 28, 0.94) 100%);
  pointer-events: none;
  z-index: -1;
}

a {
  color: inherit;
  text-decoration: none;
}

/* ── NAVBAR CÁPSULA FRUTIGER AERO ── */
.aero-nav-wrap {
  position: sticky;
  top: 16px;
  z-index: 100;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 22px;
}

.aero-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 22px;
  background: rgba(11, 29, 46, 0.76);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid var(--border-glass);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-aero);
}

.brand-pill {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: 'Outfit', sans-serif;
}

.brand-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(145deg, rgba(39, 189, 231, 0.35), rgba(86, 240, 200, 0.18));
  border: 1px solid var(--border-glass-bright);
  display: grid;
  place-items: center;
  font-size: 18px;
  box-shadow: var(--shadow-glow);
}

.brand-title {
  font-weight: 800;
  font-size: 1.05rem;
  letter-spacing: 0.06em;
  color: #ffffff;
  line-height: 1.1;
}

.brand-sub {
  display: block;
  font-size: 0.68rem;
  font-family: 'JetBrains Mono', monospace;
  color: var(--cyan-bright);
  letter-spacing: 0.12em;
}

.nav-pills {
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(6, 19, 32, 0.62);
  padding: 5px;
  border-radius: var(--radius-pill);
  border: 1px solid rgba(86, 201, 233, 0.22);
  flex-wrap: wrap;
}

.nav-link {
  padding: 8px 16px;
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-soft);
  transition: all 0.22s ease;
}

.nav-link:hover,
.nav-link.active {
  color: #ffffff;
  background: linear-gradient(135deg, rgba(39, 189, 231, 0.34), rgba(27, 136, 202, 0.22));
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.3), 0 0 16px rgba(39, 189, 231, 0.28);
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  background: rgba(14, 38, 59, 0.72);
  border: 1px solid rgba(86, 240, 200, 0.35);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.74rem;
  color: var(--aqua-mint);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--aqua-mint);
  box-shadow: 0 0 10px var(--aqua-mint);
}

/* ── CONTENEDOR GENERAL ── */
.container {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 24px;
}

section {
  padding: 68px 0;
}

/* ── PANELES DE CRISTAL ACRÍLICO ── */
.glass-panel {
  background: var(--bg-panel);
  backdrop-filter: blur(22px) saturate(155%);
  -webkit-backdrop-filter: blur(22px) saturate(155%);
  border: 1px solid var(--border-glass);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-aero);
  position: relative;
  overflow: hidden;
}

.glass-panel::before {
  content: "";
  position: absolute;
  top: 0;
  left: 16px;
  right: 16px;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--specular-top), transparent);
  pointer-events: none;
}

/* ── HERO SECTION ── */
.hero-section {
  padding-top: 44px;
  padding-bottom: 56px;
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 28px;
  align-items: stretch;
}

.hero-main {
  padding: 46px 44px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background:
    radial-gradient(circle at 88% 14%, rgba(39, 189, 231, 0.25), transparent 45%),
    linear-gradient(155deg, rgba(14, 36, 58, 0.84), rgba(8, 22, 37, 0.88));
}

.aero-badge {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  align-self: flex-start;
  padding: 7px 16px;
  border-radius: var(--radius-pill);
  background: rgba(39, 189, 231, 0.16);
  border: 1px solid var(--border-glass-bright);
  color: var(--cyan-bright);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  margin-bottom: 22px;
}

.hero-title {
  font-family: 'Outfit', sans-serif;
  font-size: clamp(2.4rem, 4.4vw, 3.85rem);
  font-weight: 900;
  line-height: 1.06;
  letter-spacing: -0.02em;
  color: #ffffff;
  margin-bottom: 18px;
}

.hero-title span {
  background: linear-gradient(95deg, #ffffff 0%, var(--cyan-bright) 52%, var(--aqua-mint) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-lead {
  font-size: 1.06rem;
  color: var(--text-soft);
  max-width: 64ch;
  margin-bottom: 28px;
}

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 30px;
}

.spec-chip {
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  background: rgba(16, 43, 67, 0.72);
  border: 1px solid rgba(86, 201, 233, 0.28);
  font-size: 0.8rem;
  font-weight: 600;
  color: #d9f4ff;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
}

.btn-aero-primary {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 28px;
  border-radius: var(--radius-pill);
  background: linear-gradient(135deg, #29c4ee 0%, #1789cb 55%, #24d9b5 100%);
  color: #031320;
  font-weight: 800;
  font-size: 0.94rem;
  letter-spacing: 0.03em;
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: 0 10px 28px rgba(39, 189, 231, 0.42), inset 0 1px 1px rgba(255, 255, 255, 0.65);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  cursor: pointer;
}

.btn-aero-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 34px rgba(39, 189, 231, 0.58), inset 0 1px 2px rgba(255, 255, 255, 0.8);
}

.btn-aero-glass {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 24px;
  border-radius: var(--radius-pill);
  background: rgba(17, 45, 70, 0.68);
  color: #e8f8ff;
  font-weight: 700;
  font-size: 0.92rem;
  border: 1px solid var(--border-glass-bright);
  box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.22);
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-aero-glass:hover {
  background: rgba(39, 189, 231, 0.25);
  transform: translateY(-2px);
}

/* ── HERO SIDE: CONSOLE PREVIEW & METRICS ── */
.hero-showcase {
  padding: 28px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
}

.console-preview-window {
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-glass-bright);
  background: rgba(6, 17, 29, 0.9);
  box-shadow: 0 16px 38px rgba(0, 0, 0, 0.55);
  position: relative;
}

.console-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(12, 33, 52, 0.92);
  border-bottom: 1px solid rgba(86, 201, 233, 0.25);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--cyan-bright);
}

.window-dots {
  display: flex;
  gap: 6px;
}

.window-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(86, 201, 233, 0.45);
}

.window-dots span:nth-child(1) { background: #ff6b81; }
.window-dots span:nth-child(2) { background: #ffd166; }
.window-dots span:nth-child(3) { background: #56f0c8; }

.console-preview-body {
  padding: 20px;
  background:
    radial-gradient(circle at 80% 20%, rgba(39, 189, 231, 0.28), transparent 55%),
    url('/assets/welcome.png') center center / cover no-repeat;
  min-height: 225px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  position: relative;
}

.console-preview-body::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(6, 18, 31, 0.25) 0%, rgba(6, 18, 31, 0.88) 100%);
}

.console-overlay-card {
  position: relative;
  z-index: 1;
  background: rgba(10, 28, 45, 0.82);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border-glass-bright);
  border-radius: 16px;
  padding: 16px 18px;
}

.console-overlay-title {
  font-family: 'Outfit', sans-serif;
  font-weight: 800;
  font-size: 1.08rem;
  color: #ffffff;
  margin-bottom: 4px;
}

.console-overlay-sub {
  font-size: 0.82rem;
  color: var(--text-soft);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-box {
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(11, 29, 47, 0.76);
  border: 1px solid rgba(86, 201, 233, 0.26);
}

.metric-val {
  font-family: 'Outfit', sans-serif;
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--cyan-bright);
  line-height: 1.1;
}

.metric-lbl {
  font-size: 0.76rem;
  color: var(--text-muted);
  margin-top: 4px;
  font-weight: 600;
}

/* ── ENCABEZADOS DE SECCIÓN ── */
.section-header {
  margin-bottom: 36px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--aqua-mint);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 5px 13px;
  border-radius: var(--radius-pill);
  background: rgba(86, 240, 200, 0.12);
  border: 1px solid rgba(86, 240, 200, 0.32);
}

.section-title {
  font-family: 'Outfit', sans-serif;
  font-size: clamp(1.85rem, 3vw, 2.55rem);
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.01em;
}

.section-desc {
  color: var(--text-soft);
  max-width: 74ch;
  font-size: 1rem;
}

/* ── PROYECTO & EVOLUCIÓN + ALMACENAMIENTO PS5 ── */
.project-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 26px;
}

.project-card {
  padding: 34px;
}

.project-card h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.38rem;
  margin-bottom: 14px;
  color: #ffffff;
}

.project-card p {
  color: var(--text-soft);
  margin-bottom: 16px;
  font-size: 0.96rem;
}

.feature-list {
  list-style: none;
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 15px;
  border-radius: 14px;
  background: rgba(9, 25, 41, 0.66);
  border: 1px solid rgba(86, 201, 233, 0.22);
  font-size: 0.9rem;
  color: #e4f6ff;
}

.feature-list li strong {
  color: var(--cyan-bright);
}

.author-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-top: 20px;
}

.meta-tile {
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(8, 22, 36, 0.72);
  border: 1px solid rgba(86, 201, 233, 0.22);
}

.meta-tile span {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 4px;
}

.meta-tile strong {
  font-size: 0.92rem;
  color: #ffffff;
}

/* ── COMUNIDADES & TIEMPO REAL ── */
.communities-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.comm-card {
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform 0.22s ease, border-color 0.22s ease;
}

.comm-card:hover {
  transform: translateY(-4px);
  border-color: var(--border-glass-bright);
}

.comm-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  font-size: 1.35rem;
  background: linear-gradient(135deg, rgba(39, 189, 231, 0.28), rgba(86, 240, 200, 0.16));
  border: 1px solid var(--border-glass-bright);
}

.comm-card h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.15rem;
  color: #ffffff;
}

.comm-card p {
  font-size: 0.88rem;
  color: var(--text-soft);
  flex: 1;
}

.comm-tag {
  align-self: flex-start;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--aqua-mint);
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: rgba(86, 240, 200, 0.12);
  border: 1px solid rgba(86, 240, 200, 0.28);
}

/* ── ARQUITECTURA DE SOFTWARE 100% PYTHON ── */
.arch-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 22px;
}

.arch-card {
  padding: 30px;
}

.arch-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem;
  color: var(--cyan-bright);
  letter-spacing: 0.08em;
  margin-bottom: 8px;
  display: block;
}

.arch-card h3 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.28rem;
  color: #ffffff;
  margin-bottom: 10px;
}

.arch-card p {
  color: var(--text-soft);
  font-size: 0.92rem;
  margin-bottom: 16px;
}

.arch-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.arch-tags span {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.73rem;
  padding: 5px 11px;
  border-radius: 8px;
  background: rgba(6, 19, 32, 0.78);
  border: 1px solid rgba(86, 201, 233, 0.26);
  color: #bfeaff;
}

/* ── BIBLIOTECA DE 90 VIDEOJUEGOS MODERNOS ── */
.catalog-controls {
  padding: 22px 26px;
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.search-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-input-wrap {
  flex: 1;
  min-width: 260px;
  position: relative;
}

.search-input {
  width: 100%;
  padding: 13px 18px 13px 44px;
  border-radius: var(--radius-pill);
  background: rgba(6, 18, 30, 0.82);
  border: 1px solid var(--border-glass);
  color: #ffffff;
  font-size: 0.94rem;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-input:focus {
  border-color: var(--cyan-bright);
  box-shadow: 0 0 0 3px rgba(39, 189, 231, 0.22);
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--cyan-bright);
  font-size: 0.95rem;
  pointer-events: none;
}

.catalog-counter {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  color: var(--aqua-mint);
  padding: 10px 16px;
  border-radius: var(--radius-pill);
  background: rgba(8, 24, 39, 0.76);
  border: 1px solid rgba(86, 240, 200, 0.3);
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-btn {
  padding: 8px 16px;
  border-radius: var(--radius-pill);
  background: rgba(9, 25, 41, 0.72);
  border: 1px solid rgba(86, 201, 233, 0.25);
  color: var(--text-soft);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.filter-btn:hover,
.filter-btn.active {
  background: linear-gradient(135deg, rgba(39, 189, 231, 0.38), rgba(86, 240, 200, 0.22));
  color: #ffffff;
  border-color: var(--border-glass-bright);
  box-shadow: 0 0 18px rgba(39, 189, 231, 0.32);
}

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(235px, 1fr));
  gap: 20px;
}

.game-card {
  border-radius: 20px;
  background: rgba(11, 28, 45, 0.76);
  border: 1px solid rgba(86, 201, 233, 0.28);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: transform 0.24s ease, border-color 0.24s ease, box-shadow 0.24s ease;
  cursor: pointer;
  position: relative;
}

.game-card:hover {
  transform: translateY(-6px);
  border-color: var(--border-glass-bright);
  box-shadow: 0 18px 40px rgba(2, 12, 24, 0.75), 0 0 24px rgba(39, 189, 231, 0.28);
}

.game-cover-wrap {
  position: relative;
  aspect-ratio: 3 / 4;
  width: 100%;
  background: linear-gradient(145deg, #0b2238, #071524);
  overflow: hidden;
}

.game-cover-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
}

.game-card:hover .game-cover-wrap img {
  transform: scale(1.05);
}

.platform-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  padding: 5px 11px;
  border-radius: var(--radius-pill);
  background: rgba(7, 20, 34, 0.86);
  backdrop-filter: blur(10px);
  border: 1px solid var(--border-glass-bright);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--cyan-bright);
  letter-spacing: 0.05em;
}

.size-badge {
  position: absolute;
  bottom: 10px;
  right: 10px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: rgba(6, 18, 30, 0.88);
  border: 1px solid rgba(86, 240, 200, 0.38);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--aqua-mint);
}

.game-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

.game-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.02rem;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.25;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.game-genre {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.game-footer {
  margin-top: auto;
  padding-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid rgba(86, 201, 233, 0.16);
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.72rem;
  color: var(--cyan-bright);
}

/* ── DESCARGA DEL EMULADOR ── */
.download-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 26px;
}

.download-card {
  padding: 38px 34px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 22px;
  background:
    radial-gradient(circle at 90% 12%, rgba(39, 189, 231, 0.2), transparent 48%),
    var(--bg-panel);
}

.os-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.os-badge-icon {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 1.65rem;
  background: linear-gradient(145deg, rgba(39, 189, 231, 0.3), rgba(86, 240, 200, 0.16));
  border: 1px solid var(--border-glass-bright);
  box-shadow: var(--shadow-glow);
}

.os-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.5rem;
  font-weight: 800;
  color: #ffffff;
}

.os-sub {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.76rem;
  color: var(--cyan-bright);
}

.download-specs {
  list-style: none;
  display: grid;
  gap: 10px;
}

.download-specs li {
  font-size: 0.9rem;
  color: var(--text-soft);
  display: flex;
  align-items: center;
  gap: 10px;
}

.download-specs li::before {
  content: "✦";
  color: var(--aqua-mint);
}

/* ── MODAL DE FICHA TÉCNICA DE JUEGO ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(3, 10, 18, 0.82);
  backdrop-filter: blur(16px);
  z-index: 250;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.modal-backdrop.open {
  display: flex;
}

.modal-window {
  max-width: 820px;
  width: 100%;
  padding: 32px;
  border-radius: var(--radius-xl);
  background: rgba(10, 26, 43, 0.94);
  border: 1px solid var(--border-glass-bright);
  box-shadow: var(--shadow-aero);
  position: relative;
}

.modal-close {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 1px solid var(--border-glass);
  background: rgba(16, 42, 66, 0.8);
  color: #ffffff;
  font-size: 1.1rem;
  cursor: pointer;
}

.modal-content-grid {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 28px;
  align-items: start;
}

.modal-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 16px;
  border: 1px solid var(--border-glass-bright);
}

.modal-meta-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin: 18px 0;
}

.modal-meta-item {
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(6, 18, 30, 0.78);
  border: 1px solid rgba(86, 201, 233, 0.24);
}

.modal-meta-item span {
  display: block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.68rem;
  color: var(--text-muted);
}

.modal-meta-item strong {
  font-size: 0.88rem;
  color: #ffffff;
}

/* ── FOOTER ── */
.aero-footer {
  padding: 42px 0 56px;
  border-top: 1px solid rgba(86, 201, 233, 0.2);
  margin-top: 40px;
  color: var(--text-muted);
  font-size: 0.86rem;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
}

@media (max-width: 1024px) {
  .hero-grid,
  .project-grid,
  .arch-grid,
  .download-grid {
    grid-template-columns: 1fr;
  }
  .communities-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 680px) {
  .communities-grid,
  .modal-content-grid {
    grid-template-columns: 1fr;
  }
  .hero-main {
    padding: 30px 24px;
  }
  .aero-nav {
    flex-direction: column;
    border-radius: 22px;
  }
}
"""


CLIENT_JS = """
(function() {
  const cards = Array.from(document.querySelectorAll('.game-card'));
  const filterBtns = Array.from(document.querySelectorAll('.filter-btn'));
  const searchInput = document.getElementById('catalogSearch');
  const counterEl = document.getElementById('catalogCounter');
  const modal = document.getElementById('gameModal');
  const modalClose = document.getElementById('modalCloseBtn');

  let activeCategory = 'TODOS';
  let searchQuery = '';

  function normalizeText(str) {
    return (str || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\\u0300-\\u036f]/g, '');
  }

  function applyFilters() {
    let visibleCount = 0;
    const q = normalizeText(searchQuery);

    cards.forEach((card) => {
      const cat = (card.getAttribute('data-category') || '').toUpperCase();
      const catsList = (card.getAttribute('data-categories') || '').toUpperCase().split('|');
      const plat = (card.getAttribute('data-platform') || '').toUpperCase();
      const title = normalizeText(card.getAttribute('data-title') || '');
      const genre = normalizeText(card.getAttribute('data-genre') || '');
      const dev = normalizeText(card.getAttribute('data-developer') || '');

      let matchesCat = false;
      if (activeCategory === 'TODOS') {
        matchesCat = true;
      } else if (catsList.includes(activeCategory)) {
        matchesCat = true;
      } else if (activeCategory === 'PS1 / PS2') {
        matchesCat = (plat === 'PS1' || plat === 'PS2' || cat === 'PS1 / PS2');
      } else {
        matchesCat = (cat === activeCategory || plat === activeCategory);
      }

      const matchesSearch = !q || title.includes(q) || genre.includes(q) || dev.includes(q) || normalizeText(plat).includes(q);

      if (matchesCat && matchesSearch) {
        card.style.display = '';
        visibleCount++;
      } else {
        card.style.display = 'none';
      }
    });

    if (counterEl) {
      counterEl.textContent = visibleCount + ' / ' + cards.length + ' JUEGOS';
    }
  }

  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterBtns.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = (btn.getAttribute('data-filter') || 'TODOS').toUpperCase();
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value || '';
      applyFilters();
    });
  }

  function openGameModal(card) {
    if (!modal) return;
    const title = card.getAttribute('data-title') || '';
    const platform = card.getAttribute('data-platform-label') || card.getAttribute('data-platform') || '';
    const genre = card.getAttribute('data-genre') || '';
    const developer = card.getAttribute('data-developer') || '';
    const release = card.getAttribute('data-release') || '';
    const players = card.getAttribute('data-players') || '';
    const format = card.getAttribute('data-format') || '';
    const sizeLabel = card.getAttribute('data-size') || '';
    const desc = card.getAttribute('data-description') || '';
    const cover = card.getAttribute('data-cover') || '';

    const elTitle = document.getElementById('modalTitle');
    const elPlat = document.getElementById('modalPlatform');
    const elDesc = document.getElementById('modalDesc');
    const elGenre = document.getElementById('modalGenre');
    const elDev = document.getElementById('modalDeveloper');
    const elRelease = document.getElementById('modalRelease');
    const elPlayers = document.getElementById('modalPlayers');
    const elFormat = document.getElementById('modalFormat');
    const elCover = document.getElementById('modalCover');

    if (elTitle) elTitle.textContent = title;
    if (elPlat) elPlat.textContent = platform + ' · ' + format + ' (' + sizeLabel + ')';
    if (elDesc) elDesc.textContent = desc;
    if (elGenre) elGenre.textContent = genre;
    if (elDev) elDev.textContent = developer;
    if (elRelease) elRelease.textContent = release;
    if (elPlayers) elPlayers.textContent = players;
    if (elFormat) elFormat.textContent = format + ' · ' + sizeLabel;
    if (elCover) elCover.src = cover;

    modal.classList.add('open');
  }

  cards.forEach((card) => {
    card.addEventListener('click', () => openGameModal(card));
  });

  if (modalClose && modal) {
    modalClose.addEventListener('click', () => modal.classList.remove('open'));
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.classList.remove('open');
    });
  }
})();
"""


def _render_game_cards(games: list[dict]) -> str:
    cards_html = []
    for g in games:
        gid = escape(str(g.get("id", "")))
        title = escape(str(g.get("title", "Juego")))
        platform = escape(str(g.get("badge") or g.get("platform") or g.get("category") or "PS5").upper())
        category = escape(str(g.get("category") or platform).upper())
        cats_list = g.get("categories") or [category, platform]
        cats_pipe = escape("|".join(str(c).upper() for c in cats_list))
        platform_label = escape(str(g.get("console") or g.get("platform_label") or platform))
        genre = escape(str(g.get("genre") or category))
        developer = escape(str(g.get("developer") or "Official Studio"))
        release = escape(str(g.get("year") or g.get("release") or "2024"))
        players = escape(str(g.get("players") or "1-4 Jugadores"))
        pkg_format = escape(str(g.get("format") or "PKG"))
        size_label = escape(str(g.get("size") or g.get("size_label") or "Cloud"))
        desc = escape(str(g.get("subtitle") or g.get("description") or ""))
        cover = escape(str(g.get("card_url") or g.get("image_url") or "/assets/welcome.png"))

        cards_html.append(
            f"""
            <article class="game-card"
                     data-id="{gid}"
                     data-title="{title}"
                     data-category="{category}"
                     data-categories="{cats_pipe}"
                     data-platform="{platform}"
                     data-platform-label="{platform_label}"
                     data-genre="{genre}"
                     data-developer="{developer}"
                     data-release="{release}"
                     data-players="{players}"
                     data-format="{pkg_format}"
                     data-size="{size_label}"
                     data-description="{desc}"
                     data-cover="{cover}">
              <div class="game-cover-wrap">
                <img src="{cover}" alt="{title}" loading="lazy" />
                <span class="platform-badge">{platform}</span>
                <span class="size-badge">{pkg_format} · {size_label}</span>
              </div>
              <div class="game-body">
                <h3 class="game-title">{title}</h3>
                <p class="game-genre">{genre} · {developer}</p>
                <div class="game-footer">
                  <span>{platform_label}</span>
                  <span>INSTALACIÓN DIRECTA →</span>
                </div>
              </div>
            </article>
            """
        )
    return "\n".join(cards_html)


def _render_filter_buttons(categories: list[str]) -> str:
    btns = []
    for idx, cat in enumerate(categories):
        cat_esc = escape(str(cat).upper())
        active_cls = "active" if idx == 0 else ""
        btns.append(
            f'<button type="button" class="filter-btn {active_cls}" data-filter="{cat_esc}">{cat_esc}</button>'
        )
    return "\n".join(btns)


def build_landing_page(
    author_info: dict | None = None,
    stats: dict | None = None,
    games: list[dict] | None = None,
    categories: list[str] | None = None,
    leaderboards: dict | None = None,
    author: dict | None = None,
) -> str:
    info = author or author_info or {}
    stats = stats or {}
    games = games or []
    categories = categories or ["TODOS", "PS5", "PS4", "SWITCH", "SWITCH 2", "PS3", "PS1 / PS2"]

    total_games = int(stats.get("total_games", len(games) or 90))
    version = escape(str(stats.get("version", "4.0.0")))
    fps_target = int(stats.get("fps_target", 60))

    author_name = escape(str(info.get("name", "Camila Carolina Ianni")))
    author_title = escape(str(info.get("title", "Desarrolladora & Arquitecta de Software — C.C.I. SYSTEM")))
    author_inst = escape(str(info.get("institution", "Escuela Da Vinci — Analista de Sistemas · Arquitectura de Software")))
    author_year = escape(str(info.get("year", "2026")))
    author_stack = escape(
        str(
            info.get(
                "stack",
                stats.get(
                    "architecture",
                    "Python 3 · PySide6 (Qt6 Frutiger Aero) · LiveKit WebRTC · Flask-SocketIO · SQLite · Keyring",
                ),
            )
        )
    )
    author_bio = escape(str(info.get("bio", "")))
    author_motiv = escape(
        str(
            info.get(
                "motivation",
                "Arquitectura enfocada en ofrecer una experiencia de consola moderna multiplataforma (macOS y Windows) con estética Frutiger Aero, gestión inteligente de almacenamiento en la nube y comunidades de voz/streaming en tiempo real.",
            )
        )
    )

    filter_buttons_html = _render_filter_buttons(categories)
    game_cards_html = _render_game_cards(games)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>C.C.I. SYSTEM — OmniDash Virtual Console (Frutiger Aero)</title>
  <link rel="stylesheet" href="/static/css/style.css" />
</head>
<body>

  <!-- BARRA DE NAVEGACIÓN CÁPSULA FRUTIGER AERO -->
  <div class="aero-nav-wrap">
    <nav class="aero-nav">
      <a href="#inicio" class="brand-pill">
        <div class="brand-icon">🎮</div>
        <div>
          <span class="brand-title">C.C.I. SYSTEM</span>
          <span class="brand-sub">OMNIDASH FRUTIGER AERO · v{version}</span>
        </div>
      </a>

      <div class="nav-pills">
        <a href="#inicio" class="nav-link active">Inicio</a>
        <a href="#proyecto" class="nav-link">Consola &amp; Almacenamiento</a>
        <a href="#comunidades" class="nav-link">Comunidades WebRTC</a>
        <a href="#arquitectura" class="nav-link">Arquitectura</a>
        <a href="#catalogo" class="nav-link">Biblioteca ({total_games})</a>
        <a href="#descarga" class="nav-link">Descargar</a>
      </div>

      <div class="nav-status">
        <span class="status-dot"></span>
        <span>QT6 PYSIDE6 · {total_games} JUEGOS</span>
      </div>
    </nav>
  </div>

  <main class="container">

    <!-- HERO SECTION -->
    <section id="inicio" class="hero-section">
      <div class="hero-grid">
        <div class="glass-panel hero-main">
          <div>
            <div class="aero-badge">
              <span>✦</span>
              <span>CONSOLA VIRTUAL MULTIMEDIA · ESTÉTICA FRUTIGER AERO</span>
            </div>
            <h1 class="hero-title">
              OmniDash Virtual Console:<br />
              <span>{total_games} Juegos Modernos &amp; Comunidades en Vivo</span>
            </h1>
            <p class="hero-lead">
              Diseñada sobre <strong>PySide6 (Qt6)</strong> con paneles de cristal acrílico cian-aguamarina,
              catálogo moderno de <strong>{total_games} títulos de PS5, PS4, Nintendo Switch, Switch 2, PS3, PS2 y PS1</strong>,
              instalación directa en consola para <strong>macOS y Windows</strong>, gestión de espacio estilo PlayStation 5
              sin perder tu progreso y canales de voz/streaming <strong>LiveKit WebRTC</strong> en tiempo real.
            </p>
            <div class="hero-pills">
              <span class="spec-chip">✦ {total_games} Juegos (PS5 · PS4 · Switch · Switch 2 · PS3)</span>
              <span class="spec-chip">✦ Desinstalación sin perder Save Data</span>
              <span class="spec-chip">✦ Voz &amp; Streaming 60 FPS (LiveKit WebRTC)</span>
              <span class="spec-chip">✦ Soundboard RTC &amp; Spotify OAuth 2.0</span>
            </div>
          </div>

          <div class="hero-actions">
            <a href="#descarga" class="btn-aero-primary">
              <span>⬇</span>
              <span>DESCARGAR CONSOLA (macOS / Windows)</span>
            </a>
            <a href="#catalogo" class="btn-aero-glass">
              <span>EXPLORAR BIBLIOTECA ({total_games} JUEGOS)</span>
            </a>
          </div>
        </div>

        <div class="glass-panel hero-showcase">
          <div class="console-preview-window">
            <div class="console-topbar">
              <div class="window-dots">
                <span></span><span></span><span></span>
              </div>
              <span>C.C.I. SYSTEM — OmniDash (Frutiger Aero)</span>
              <span>{fps_target} FPS</span>
            </div>
            <div class="console-preview-body">
              <div class="console-overlay-card">
                <div class="console-overlay-title">Interfaz Acrílica Translúcida &amp; Motor Híbrido</div>
                <div class="console-overlay-sub">
                  Instalación directa según tu sistema operativo, conservación perpetua de partidas en
                  <code>saves/games/</code> y presencia automática de juego en tiempo real.
                </div>
              </div>
            </div>
          </div>

          <div class="metrics-grid">
            <div class="metric-box">
              <div class="metric-val">{total_games}</div>
              <div class="metric-lbl">Juegos Modernos (PS5 / Switch / PS4 / PS3)</div>
            </div>
            <div class="metric-box">
              <div class="metric-val">100%</div>
              <div class="metric-lbl">Progreso Protegido al Desinstalar</div>
            </div>
            <div class="metric-box">
              <div class="metric-val">{fps_target} FPS</div>
              <div class="metric-lbl">Runner Nativo + Streaming WebRTC</div>
            </div>
            <div class="metric-box">
              <div class="metric-val">macOS &amp; Win</div>
              <div class="metric-lbl">Instaladores Oficiales Auto-Actualizados</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- SOBRE EL PROYECTO & GESTIÓN DE ALMACENAMIENTO ESTILO PS5 -->
    <section id="proyecto">
      <div class="section-header">
        <span class="section-eyebrow">EVOLUCIÓN DEL ECOSISTEMA</span>
        <h2 class="section-title">Estética Frutiger Aero &amp; Gestión Inteligente estilo PlayStation 5</h2>
        <p class="section-desc">
          OmniDash evoluciona hacia una consola de escritorio de última generación en PySide6 (Qt6),
          reemplazando los antiguos minijuegos arcade por un catálogo completo de {total_games} entregas modernas
          con administración de almacenamiento en la nube y preservación total de partidas.
        </p>
      </div>

      <div class="project-grid">
        <div class="glass-panel project-card">
          <h3>Almacenamiento inteligente sin perder tu progreso</h3>
          <p>{author_bio}</p>
          <p>{author_motiv}</p>
          <ul class="feature-list">
            <li>
              <span>💾</span>
              <div>
                <strong>Desinstalación limpia estilo PS5 (`GameStorageManager`):</strong>
                Puedes liberar gigabytes eliminando los paquetes pesados de <code>roms/</code> cuando necesites espacio,
                mientras tus partidas guardadas en <code>saves/games/&lt;game_id&gt;/</code> y tu historial en SQLite
                permanecen 100% intactos para cuando vuelvas a instalar el título.
              </div>
            </li>
            <li>
              <span>⚡</span>
              <div>
                <strong>Instalación directa según tu Sistema Operativo:</strong>
                Al pulsar <em>Instalar en Consola</em> dentro de OmniDash, el sistema aprovisiona automáticamente el paquete
                optimizado para <strong>macOS</strong> o <strong>Windows</strong> sin abrir selectores manuales de archivos.
              </div>
            </li>
            <li>
              <span>🎮</span>
              <div>
                <strong>Ejecución a {fps_target} FPS &amp; Emuladores Nativos:</strong>
                Compatible con el motor interactivo integrado multiplataforma y con emuladores externos instalados en el equipo
                (Ryujinx, ShadPS4, RPCS3, PCSX2 y DuckStation).
              </div>
            </li>
          </ul>
        </div>

        <div class="glass-panel project-card">
          <h3>Ficha Técnica &amp; Autoría</h3>
          <p>
            Desarrollo integral de ingeniería de software combinando interfaz gráfica acelerada por hardware,
            comunicaciones WebRTC de baja latencia, persistencia transaccional y seguridad criptográfica en el llavero del SO.
          </p>
          <div class="author-meta-grid">
            <div class="meta-tile">
              <span>AUTORA</span>
              <strong>{author_name}</strong>
            </div>
            <div class="meta-tile">
              <span>PROYECTO</span>
              <strong>{author_inst} ({author_year})</strong>
            </div>
            <div class="meta-tile">
              <span>INTERFAZ GRÁFICA</span>
              <strong>PySide6 (Qt6) Frutiger Aero</strong>
            </div>
            <div class="meta-tile">
              <span>PLATAFORMAS DEL CATÁLOGO</span>
              <strong>PS5 · PS4 · Switch · Switch 2 · PS3 · PS2 · PS1</strong>
            </div>
          </div>
          <div class="meta-tile" style="margin-top: 12px;">
            <span>STACK TECNOLÓGICO</span>
            <strong>{author_stack}</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- COMUNIDADES & TIEMPO REAL -->
    <section id="comunidades">
      <div class="section-header">
        <span class="section-eyebrow">C.C.I. COMMUNITIES · REAL-TIME</span>
        <h2 class="section-title">Comunidades, Voz WebRTC, Soundboard &amp; Presencia Automática</h2>
        <p class="section-desc">
          Integrado directamente en la consola OmniDash: conéctate con tus amigos en salas de voz de baja latencia,
          transmite tu partida en vivo y comparte tu actividad de juego y música en tiempo real.
        </p>
      </div>

      <div class="communities-grid">
        <div class="glass-panel comm-card">
          <div class="comm-icon">🎙️</div>
          <span class="comm-tag">LIVEKIT WEBRTC SFU</span>
          <h3>Voz &amp; Streaming 60 FPS</h3>
          <p>
            Canales de voz full-duplex con cancelación de eco, supresión de ruido y transmisión de pantalla o ventana de juego
            en alta definición mediante LiveKit WebRTC.
          </p>
        </div>

        <div class="glass-panel comm-card">
          <div class="comm-icon">🔊</div>
          <span class="comm-tag">RTC AUDIO MIXER</span>
          <h3>Soundboard en el Canal</h3>
          <p>
            Mezclador PCM en tiempo real (`SoundboardMixer`) que inyecta efectos de sonido directamente sobre el track de audio
            WebRTC saliente para que todos los participantes del canal lo escuchen al instante.
          </p>
        </div>

        <div class="glass-panel comm-card">
          <div class="comm-icon">🛰️</div>
          <span class="comm-tag">GAME PROCESS WATCHER</span>
          <h3>Detección Automática</h3>
          <p>
            Monitor en segundo plano (`GameProcessWatcher`) que detecta la apertura y cierre real de procesos de juegos en el SO
            y publica eventos <code>started / stopped</code> automáticamente a tus amigos.
          </p>
        </div>

        <div class="glass-panel comm-card">
          <div class="comm-icon">🎵</div>
          <span class="comm-tag">OAUTH 2.0 + KEYRING</span>
          <h3>Spotify &amp; Tokens Seguros</h3>
          <p>
            Vinculación Spotify OAuth 2.0 con PKCE opt-in/revocable y almacenamiento seguro de credenciales JWT/OAuth en el
            Keychain de macOS o Credential Locker de Windows.
          </p>
        </div>
      </div>
    </section>

    <!-- ARQUITECTURA DE SOFTWARE 100% PYTHON -->
    <section id="arquitectura">
      <div class="section-header">
        <span class="section-eyebrow">INGENIERÍA DE SISTEMAS</span>
        <h2 class="section-title">ARQUITECTURA DE SOFTWARE 100% PYTHON</h2>
        <p class="section-desc">
          Diseño modular distribuido en cuatro subsistemas principales que articulan la interfaz Frutiger Aero en Qt6,
          el gestor de almacenamiento de los {total_games} juegos modernos y la infraestructura de red en tiempo real.
        </p>
      </div>

      <div class="arch-grid">
        <div class="glass-panel arch-card">
          <span class="arch-code">KERNEL_01 // OMNIDASH QT6 FRUTIGER AERO</span>
          <h3>Motor Visual Acrílico en PySide6 (Qt6)</h3>
          <p>
            Interfaz de consola con paneles translúcidos, iluminación especular cian-aguamarina, navegación fluida por pestañas
            (Inicio, Biblioteca, Comunidades, Amigos y Ajustes), reproductor de música integrado y soporte de mandos Bluetooth/USB.
          </p>
          <div class="arch-tags">
            <span>omnidash_qt.py</span>
            <span>PySide6 / Qt6</span>
            <span>Frutiger Aero UI</span>
            <span>60 FPS Hardware Accel</span>
          </div>
        </div>

        <div class="glass-panel arch-card">
          <span class="arch-code">SUBSYSTEM_02 // STORAGE MANAGER &amp; CATÁLOGO MODERNO</span>
          <h3>Catálogo de {total_games} Juegos &amp; Persistencia de Partidas</h3>
          <p>
            Separación estricta entre binarios de instalación (`roms/`) y datos de progreso del jugador (`saves/games/` + tabla
            SQLite `game_progress`). Permite instalar directamente según el SO y desinstalar juegos pesados sin perder avances.
          </p>
          <div class="arch-tags">
            <span>modern_catalog.py</span>
            <span>storage_manager.py</span>
            <span>modern_game_runner.py</span>
            <span>PS5 / PS4 / Switch / PS3</span>
          </div>
        </div>

        <div class="glass-panel arch-card">
          <span class="arch-code">SUBSYSTEM_03 // LIVEKIT WEBRTC &amp; SOUNDBOARD MIXER</span>
          <h3>Canales de Voz, Video-Streaming &amp; Mezcla PCM</h3>
          <p>
            Cliente nativo WebRTC (`media_client.py`) conectado a LiveKit SFU con captura de micrófono a 48 kHz, mezcla aditiva
            con `SoundboardMixer` y publicación de frames de pantalla/juego (`ScreenStreamer`) en tiempo real.
          </p>
          <div class="arch-tags">
            <span>media_client.py</span>
            <span>LiveKit WebRTC</span>
            <span>SoundboardMixer</span>
            <span>ScreenStreamer</span>
          </div>
        </div>

        <div class="glass-panel arch-card">
          <span class="arch-code">SUBSYSTEM_04 // GAME WATCHER, SPOTIFY OAUTH &amp; KEYRING</span>
          <h3>Presencia Real, Seguridad Criptográfica &amp; API</h3>
          <p>
            Backend Flask + Socket.IO con salas por comunidad y usuario, monitor automático de procesos de juegos (`game_watcher.py`),
            flujo Spotify OAuth 2.0 PKCE revocable y resguardo de tokens en el llavero nativo del sistema operativo (`secret_store.py`).
          </p>
          <div class="arch-tags">
            <span>game_watcher.py</span>
            <span>spotify_oauth.py</span>
            <span>secret_store.py</span>
            <span>Flask-SocketIO</span>
          </div>
        </div>
      </div>
    </section>

    <!-- BIBLIOTECA DE 90 VIDEOJUEGOS MODERNOS -->
    <section id="catalogo">
      <div class="section-header">
        <span class="section-eyebrow">CATÁLOGO OFICIAL SINCRONIZADO CON OMNIDASH</span>
        <h2 class="section-title">BIBLIOTECA ({total_games} JUEGOS)</h2>
        <p class="section-desc">
          Explora las {total_games} entregas modernas disponibles en la consola: títulos de PlayStation 5, PlayStation 4,
          Nintendo Switch, Nintendo Switch 2, PlayStation 3, PlayStation 2 y PlayStation 1 con carátulas originales,
          instalación directa en consola y guardado persistente.
        </p>
      </div>

      <div class="glass-panel catalog-controls">
        <div class="search-row">
          <div class="search-input-wrap">
            <span class="search-icon">🔍</span>
            <input type="search"
                   id="catalogSearch"
                   class="search-input"
                   placeholder="Buscar por título, consola (PS5, Switch, PS4, PS3) o estudio..." />
          </div>
          <div id="catalogCounter" class="catalog-counter">
            {len(games)} / {len(games)} JUEGOS
          </div>
        </div>

        <div class="filter-bar">
          {filter_buttons_html}
        </div>
      </div>

      <div class="games-grid" id="gamesGrid">
        {game_cards_html}
      </div>
    </section>

    <!-- DESCARGA DEL EMULADOR -->
    <section id="descarga">
      <div class="section-header">
        <span class="section-eyebrow">INSTALADORES OFICIALES AUTO-ACTUALIZADOS</span>
        <h2 class="section-title">DESCARGA DEL EMULADOR</h2>
        <p class="section-desc">
          Descarga la consola virtual C.C.I. SYSTEM (OmniDash Frutiger Aero) lista para ejecutar en tu sistema operativo.
          Ambos instaladores incluyen la biblioteca de {total_games} juegos modernos, instalación directa desde la interfaz,
          gestión de almacenamiento sin perder progreso y C.C.I. Communities integrado.
        </p>
      </div>

      <div class="download-grid">
        <div class="glass-panel download-card">
          <div>
            <div class="os-header">
              <div class="os-badge-icon">🍎</div>
              <div>
                <h3 class="os-title">macOS Universal (.DMG)</h3>
                <span class="os-sub">Apple Silicon (M1 / M2 / M3 / M4) &amp; Intel · macOS 12+</span>
              </div>
            </div>
            <ul class="download-specs" style="margin-top: 20px;">
              <li>Interfaz nativa <strong>OmniDash Frutiger Aero (PySide6 Qt6)</strong> acelerada por Metal.</li>
              <li>Catálogo completo de <strong>{total_games} juegos modernos</strong> con instalación directa para macOS.</li>
              <li>Desinstalación inteligente de paquetes pesados conservando el 100% de tus partidas en <code>saves/games/</code>.</li>
              <li>Canales de voz LiveKit WebRTC, Soundboard RTC y Keychain nativo de macOS.</li>
            </ul>
          </div>
          <div>
            <a href="/download/mac" class="btn-aero-primary" style="width: 100%; justify-content: center;">
              <span>⬇</span>
              <span>DESCARGAR PARA macOS (CCI_System_macOS.dmg)</span>
            </a>
          </div>
        </div>

        <div class="glass-panel download-card">
          <div>
            <div class="os-header">
              <div class="os-badge-icon">🪟</div>
              <div>
                <h3 class="os-title">Windows 10 / 11 (64-bit)</h3>
                <span class="os-sub">Instalador Oficial (.EXE / .ZIP) · x86_64</span>
              </div>
            </div>
            <ul class="download-specs" style="margin-top: 20px;">
              <li>Consola <strong>OmniDash Frutiger Aero (PySide6 Qt6)</strong> lista para ejecutar sin dependencias externas.</li>
              <li>Biblioteca de <strong>{total_games} videojuegos</strong> con aprovisionamiento e instalación directa en Windows.</li>
              <li>Gestión de espacio estilo PS5 con preservación perpetua de Save Slots y progreso SQLite.</li>
              <li>Comunidades en tiempo real, streaming a 60 FPS y resguardo en Windows Credential Locker.</li>
            </ul>
          </div>
          <div>
            <a href="/download/windows" class="btn-aero-primary" style="width: 100%; justify-content: center;">
              <span>⬇</span>
              <span>DESCARGAR PARA WINDOWS (CCI_System_Windows)</span>
            </a>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- MODAL DE DETALLE TÉCNICO DE JUEGO -->
  <div class="modal-backdrop" id="gameModal">
    <div class="modal-window">
      <button type="button" class="modal-close" id="modalCloseBtn" aria-label="Cerrar">✕</button>
      <div class="modal-content-grid">
        <img id="modalCover" class="modal-cover" src="/assets/welcome.png" alt="Carátula" />
        <div>
          <span class="aero-badge" id="modalPlatform">PS5 · PKG</span>
          <h3 id="modalTitle" style="font-family: 'Outfit', sans-serif; font-size: 1.7rem; margin-bottom: 10px;">Título del Juego</h3>
          <p id="modalDesc" style="color: var(--text-soft); font-size: 0.94rem;">Descripción técnica del título.</p>

          <div class="modal-meta-list">
            <div class="modal-meta-item">
              <span>GÉNERO</span>
              <strong id="modalGenre">-</strong>
            </div>
            <div class="modal-meta-item">
              <span>ESTUDIO / DESARROLLADOR</span>
              <strong id="modalDeveloper">-</strong>
            </div>
            <div class="modal-meta-item">
              <span>LANZAMIENTO</span>
              <strong id="modalRelease">-</strong>
            </div>
            <div class="modal-meta-item">
              <span>JUGADORES</span>
              <strong id="modalPlayers">-</strong>
            </div>
            <div class="modal-meta-item">
              <span>FORMATO &amp; TAMAÑO</span>
              <strong id="modalFormat">-</strong>
            </div>
            <div class="modal-meta-item">
              <span>GUARDADO PERSISTENTE</span>
              <strong>Protegido en saves/games/</strong>
            </div>
          </div>

          <a href="#descarga" class="btn-aero-primary" onclick="document.getElementById('gameModal').classList.remove('open')">
            <span>⚡</span>
            <span>INSTALAR Y JUGAR DESDE LA CONSOLA OMNIDASH</span>
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="aero-footer">
    <div class="container footer-inner">
      <div>
        <strong>C.C.I. SYSTEM v{version}</strong> — OmniDash Virtual Console (Estética Frutiger Aero · PySide6 Qt6)
      </div>
      <div>
        {author_name} · {author_inst} ({author_year})
      </div>
    </div>
  </footer>

  <script src="/static/js/main.js"></script>
</body>
</html>
"""
