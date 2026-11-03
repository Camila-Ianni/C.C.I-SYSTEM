"""web/landing_page.py - Generador 100% Python de la Landing Page de C.C.I. SYSTEM.
Estética fidedigna a la consola virtual: chasis oscuro mate, marcos técnicos biselados,
telemetría HUD, barras de navegación idénticas a sidebar_ui.py y sin clichés genéricos de IA.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import html

CYBER_CSS = """
/* ==============================================================================
   C.C.I. SYSTEM VIRTUAL CONSOLE — OFFICIAL UI STYLESHEET
   Paleta extraída de cci_console.py y sidebar_ui.py:
   DARK=(7,8,10), PANEL=(10,11,13), MID=(95,98,103), LIGHT=(218,220,224),
   WHITE=(246,247,249), MUTED=(153,157,163), CYAN=#00f0ff, GOLD=#ffb800
   Autora: Camila Carolina Ianni
   ============================================================================== */

:root {
  --cci-bg-void: #050608;
  --cci-bg-base: #07080a;
  --cci-bg-panel: #0a0b0d;
  --cci-bg-surface: #111317;
  --cci-bg-surface-hover: #171b22;
  --cci-bg-elevated: #1b1c1f;
  --cci-border-dim: #1e222b;
  --cci-border-panel: #2b313d;
  --cci-border-bright: #3f4756;
  --cci-border-active: #00f0ff;
  --cci-cyan: #00f0ff;
  --cci-cyan-dim: rgba(0, 240, 255, 0.15);
  --cci-cyan-glow: rgba(0, 240, 255, 0.4);
  --cci-gold: #ffb800;
  --cci-green: #00ff88;
  --cci-white: #f6f7f9;
  --cci-light: #dadce4;
  --cci-muted: #999da3;
  --cci-dim: #5f6267;
  --font-display: 'Chakra Petch', 'Orbitron', -apple-system, sans-serif;
  --font-ui: 'Rajdhani', -apple-system, sans-serif;
  --font-mono: 'Share Tech Mono', monospace;
  --font-pixel: 'Press Start 2P', monospace;
  --container-w: 1240px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  scroll-behavior: smooth;
  background-color: var(--cci-bg-void);
  color: var(--cci-white);
  font-family: var(--font-ui);
  font-size: 16px;
  line-height: 1.5;
}

body {
  position: relative;
  overflow-x: hidden;
  background: var(--cci-bg-base);
  min-height: 100vh;
}

/* CRT Scanlines sutiles de monitor arcade */
.crt-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.22) 50%);
  background-size: 100% 4px;
  pointer-events: none;
  z-index: 999;
  opacity: 0.7;
}

/* Trama técnica de cuadrícula industrial */
.tech-grid-bg {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(255, 255, 255, 0.015) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
  z-index: 0;
}

.container {
  width: 100%;
  max-width: var(--container-w);
  margin: 0 auto;
  padding: 0 28px;
  position: relative;
  z-index: 2;
}

/* ==============================================================================
   CONSOLE TOP HUD BAR (Idéntica a la barra de estado de C.C.I. System)
   ============================================================================== */
.top-hud {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 64px;
  background: rgba(7, 8, 10, 0.94);
  backdrop-filter: blur(12px);
  border-bottom: 2px solid var(--cci-border-panel);
  z-index: 100;
  display: flex;
  align-items: center;
}

.hud-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.hud-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.brand-badge {
  background: #000;
  border: 1px solid var(--cci-cyan);
  padding: 3px 8px;
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: 2px;
  color: #fff;
  box-shadow: 0 0 10px var(--cci-cyan-dim);
}
.brand-badge span {
  color: var(--cci-cyan);
}

.hud-sys-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-muted);
  border-left: 1px solid var(--cci-border-panel);
  padding-left: 12px;
}

.led-indicator {
  width: 8px; height: 8px;
  background: var(--cci-green);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--cci-green);
  animation: pulse-led 2s infinite ease-in-out;
}

@keyframes pulse-led {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.9); }
}

.hud-nav {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Pestañas de navegación con la misma estética de la barra lateral de la consola */
.hud-tab {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--cci-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.hud-tab:hover {
  color: var(--cci-white);
  background: rgba(255, 255, 255, 0.03);
}

.hud-tab.active, .hud-tab:hover {
  border-bottom-color: var(--cci-cyan);
  color: #fff;
}

.hud-cta-download {
  background: var(--cci-cyan);
  color: #000 !important;
  font-family: var(--font-display);
  font-weight: 800;
  padding: 8px 18px;
  letter-spacing: 1.5px;
  border: 1px solid var(--cci-cyan);
  box-shadow: 0 0 14px var(--cci-cyan-dim);
  clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px));
  transition: all 0.2s ease;
}
.hud-cta-download:hover {
  background: #fff;
  border-color: #fff;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
}

/* ==============================================================================
   HERO: CONSOLE VIRTUAL STAGE
   ============================================================================== */
.hero {
  padding: 130px 0 70px;
  position: relative;
  border-bottom: 1px solid var(--cci-border-panel);
  background: radial-gradient(circle at 50% 15%, #10141d 0%, var(--cci-bg-base) 80%);
}

.hero-layout {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 40px;
  align-items: center;
}

.telemetry-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-cyan);
  background: rgba(0, 240, 255, 0.08);
  border: 1px solid var(--cci-border-panel);
  padding: 4px 12px;
  margin-bottom: 18px;
  letter-spacing: 1.5px;
}

.hero-headline {
  font-family: var(--font-display);
  font-size: 2.85rem;
  font-weight: 900;
  line-height: 1.1;
  letter-spacing: 0.5px;
  color: #fff;
  margin-bottom: 18px;
  text-transform: uppercase;
}
.hero-headline span {
  color: var(--cci-cyan);
  text-shadow: 0 0 16px var(--cci-cyan-dim);
}

.hero-lead {
  font-size: 1.15rem;
  color: var(--cci-light);
  line-height: 1.6;
  margin-bottom: 28px;
  max-width: 620px;
}
.hero-lead strong {
  color: #fff;
  font-weight: 700;
}

.hero-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 36px;
}

/* Botones técnicos estilo arcade / gamepad */
.btn-cci {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 26px;
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 1.5px;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  text-transform: uppercase;
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));
}

.btn-primary-action {
  background: var(--cci-cyan);
  color: #04060a;
  border: 1px solid var(--cci-cyan);
  box-shadow: 0 4px 20px var(--cci-cyan-glow);
}
.btn-primary-action:hover {
  background: #fff;
  border-color: #fff;
  color: #000;
  box-shadow: 0 6px 28px rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.btn-secondary-action {
  background: var(--cci-bg-surface);
  color: var(--cci-white);
  border: 1px solid var(--cci-border-bright);
}
.btn-secondary-action:hover {
  border-color: var(--cci-cyan);
  background: var(--cci-bg-surface-hover);
  color: var(--cci-cyan);
  transform: translateY(-2px);
}

.btn-gamepad-key {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: rgba(0, 0, 0, 0.4);
  padding: 2px 6px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

/* Tira de telemetría de especificaciones */
.spec-strip {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--cci-bg-surface);
  border: 1px solid var(--cci-border-panel);
  padding: 14px 20px;
}

.spec-cell {
  display: flex;
  flex-direction: column;
}
.spec-val {
  font-family: var(--font-display);
  font-size: 1.3rem;
  font-weight: 900;
  color: var(--cci-cyan);
}
.spec-lbl {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--cci-muted);
  letter-spacing: 1px;
}
.spec-divider {
  width: 1px;
  height: 28px;
  background: var(--cci-border-panel);
}

/* Chasis de pantalla de la consola virtual */
.console-chassis {
  background: #000;
  border: 2px solid var(--cci-border-bright);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9), 0 0 30px rgba(0, 240, 255, 0.1);
  position: relative;
  overflow: hidden;
}

.chassis-header {
  height: 32px;
  background: #0a0c10;
  border-bottom: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
}

.chassis-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}
.chassis-led {
  width: 8px; height: 8px;
  background: var(--cci-cyan);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--cci-cyan);
}
.chassis-title {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--cci-light);
  letter-spacing: 1px;
}

.chassis-res {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--cci-green);
  background: rgba(0, 255, 136, 0.1);
  padding: 2px 6px;
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.chassis-screen {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #000;
}
.chassis-screen img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.chassis-footer {
  height: 30px;
  background: #080a0e;
  border-top: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--cci-muted);
}

/* ==============================================================================
   SECTION HEADERS
   ============================================================================== */
.section {
  padding: 80px 0;
  position: relative;
}
.section-dark {
  background: var(--cci-bg-panel);
  border-top: 1px solid var(--cci-border-panel);
  border-bottom: 1px solid var(--cci-border-panel);
}

.section-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-cyan);
  letter-spacing: 2px;
  margin-bottom: 8px;
  text-transform: uppercase;
}

.section-title {
  font-family: var(--font-display);
  font-size: 2.1rem;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--cci-white);
  margin-bottom: 12px;
  text-transform: uppercase;
}

.section-desc {
  font-size: 1.1rem;
  color: var(--cci-light);
  line-height: 1.6;
  max-width: 760px;
}

/* ==============================================================================
   ARCHITECTURE & SUBSYSTEMS (Sin emojis de juguete, estilo industrial)
   ============================================================================== */
.subsystems-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-top: 40px;
}

.subsystem-card {
  background: var(--cci-bg-surface);
  border: 1px solid var(--cci-border-panel);
  padding: 28px 24px;
  position: relative;
  transition: all 0.25s ease;
}
.subsystem-card:hover {
  border-color: var(--cci-cyan);
  background: var(--cci-bg-surface-hover);
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.7);
}

.subsystem-code {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-cyan);
  margin-bottom: 12px;
  letter-spacing: 1px;
  display: block;
}

.subsystem-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 800;
  color: #fff;
  margin-bottom: 10px;
  text-transform: uppercase;
}

.subsystem-text {
  font-size: 0.95rem;
  color: var(--cci-light);
  line-height: 1.6;
}

/* ==============================================================================
   GAMES CATALOG (Estilo Cartucho / Rack Arcade)
   ============================================================================== */
.catalog-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 30px;
}

.filters-rack {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-chip {
  background: var(--cci-bg-surface);
  border: 1px solid var(--cci-border-panel);
  color: var(--cci-muted);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 8px 16px;
  cursor: pointer;
  letter-spacing: 1px;
  transition: all 0.2s ease;
  text-transform: uppercase;
}
.filter-chip:hover {
  background: var(--cci-bg-surface-hover);
  color: #fff;
  border-color: var(--cci-border-bright);
}
.filter-chip.active {
  background: var(--cci-bg-elevated);
  border-color: var(--cci-cyan);
  color: var(--cci-cyan);
  box-shadow: inset 3px 0 0 var(--cci-cyan);
}

.games-rack-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 20px;
}

.cartridge-card {
  background: var(--cci-bg-surface);
  border: 1px solid var(--cci-border-panel);
  overflow: hidden;
  position: relative;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
}

.cartridge-card:hover {
  border-color: var(--cci-cyan);
  transform: translateY(-4px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.8), 0 0 16px var(--cci-cyan-dim);
}

.cartridge-header {
  height: 24px;
  background: #090b0e;
  border-bottom: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--cci-muted);
}

.cartridge-slot {
  color: var(--cci-cyan);
  font-weight: 700;
}

.cartridge-art {
  position: relative;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}
.cartridge-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
  display: block;
}
.cartridge-card:hover .cartridge-art img {
  transform: scale(1.06);
}

.cartridge-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 240, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.cartridge-card:hover .cartridge-overlay {
  opacity: 1;
}

.overlay-action-btn {
  background: #000;
  color: var(--cci-cyan);
  border: 1px solid var(--cci-cyan);
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 800;
  padding: 6px 14px;
  letter-spacing: 1px;
}

.cartridge-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.cartridge-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
}
.cartridge-year {
  color: var(--cci-gold);
}
.cartridge-players {
  color: var(--cci-muted);
}

.cartridge-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 800;
  color: #fff;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cartridge-sub {
  font-size: 0.85rem;
  color: var(--cci-light);
  line-height: 1.4;
  margin-bottom: 14px;
  flex-grow: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cartridge-tags {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.cartridge-tag {
  background: #090b0e;
  border: 1px solid var(--cci-border-panel);
  color: var(--cci-muted);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 6px;
}

/* ==============================================================================
   AUTHOR PROFILE (Estilo Idéntico a la pantalla 'PERFIL' de C.C.I. System)
   ============================================================================== */
.profile-screen-card {
  background: var(--cci-bg-surface);
  border: 2px solid var(--cci-border-bright);
  padding: 44px;
  position: relative;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.8);
}

.profile-hud-header {
  position: absolute;
  top: 0; left: 44px; right: 44px;
  height: 28px;
  background: #0a0c10;
  border-bottom: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--cci-muted);
}

.profile-grid {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 40px;
  align-items: flex-start;
  margin-top: 10px;
}

.profile-avatar-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.profile-avatar-frame {
  width: 140px; height: 140px;
  background: #07080a;
  border: 3px solid var(--cci-cyan);
  box-shadow: 0 0 20px var(--cci-cyan-dim);
  display: flex;
  align-items: center;
  justify-content: center;
}

.profile-monogram {
  font-family: var(--font-display);
  font-size: 2.8rem;
  font-weight: 900;
  color: var(--cci-cyan);
  letter-spacing: 2px;
}

.profile-badge-pill {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--cci-gold);
  background: #090b0e;
  border: 1px solid var(--cci-border-panel);
  padding: 4px 10px;
  text-transform: uppercase;
}

.profile-name {
  font-family: var(--font-display);
  font-size: 2.4rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.profile-inst {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--cci-cyan);
  margin-bottom: 20px;
  letter-spacing: 0.5px;
}

.profile-bio {
  font-size: 1.1rem;
  color: var(--cci-light);
  line-height: 1.7;
  margin-bottom: 26px;
}

.profile-specs-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.profile-spec-item {
  background: #0a0c10;
  border: 1px solid var(--cci-border-panel);
  padding: 12px 16px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}
.profile-spec-item strong {
  display: block;
  color: #fff;
  font-size: 0.9rem;
  margin-bottom: 2px;
  font-family: var(--font-display);
}
.profile-spec-item span {
  color: var(--cci-muted);
}

/* ==============================================================================
   DOWNLOADS & INSTALLER SECTION
   ============================================================================== */
.downloads-panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 28px;
  margin-top: 40px;
}

.download-hardware-card {
  background: var(--cci-bg-surface);
  border: 2px solid var(--cci-border-panel);
  padding: 36px 32px;
  display: flex;
  flex-direction: column;
  transition: all 0.25s ease;
  position: relative;
}
.download-hardware-card:hover {
  border-color: var(--cci-cyan);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.8);
  transform: translateY(-3px);
}

.hw-icon-box {
  width: 52px; height: 52px;
  background: #090b0e;
  border: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: var(--cci-cyan);
}

.os-svg {
  width: 30px !important;
  height: 30px !important;
  max-width: 30px !important;
  max-height: 30px !important;
  color: var(--cci-cyan);
}

.hw-title {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 800;
  color: #fff;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.hw-sub {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--cci-muted);
  margin-bottom: 24px;
}

.hw-checklist {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 30px;
  flex-grow: 1;
}

.hw-checklist li {
  font-size: 0.95rem;
  color: var(--cci-light);
  display: flex;
  align-items: center;
  gap: 10px;
}
.hw-checklist li::before {
  content: '▸';
  color: var(--cci-cyan);
  font-weight: 900;
}

.hw-btn-wrap {
  margin-top: auto;
}

.hw-hint {
  display: block;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-muted);
  margin-top: 10px;
}

/* Quick Start 3-Step Console Boot */
.boot-steps-card {
  margin-top: 40px;
  background: #0a0c10;
  border: 1px solid var(--cci-border-panel);
  padding: 30px 32px;
}

.boot-steps-title {
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: 1.5px;
  color: var(--cci-cyan);
  text-align: center;
  margin-bottom: 24px;
  text-transform: uppercase;
}

.boot-steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px;
}

.boot-step {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}

.boot-step-num {
  width: 32px; height: 32px;
  background: var(--cci-cyan);
  color: #000;
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.boot-step-content {
  font-size: 0.95rem;
  color: var(--cci-light);
  line-height: 1.5;
}
.boot-step-content strong {
  color: #fff;
  display: block;
  margin-bottom: 2px;
  font-family: var(--font-display);
}

/* ==============================================================================
   GAMEPAD CONTROLLER LEGEND BAR (Barra fija / footer de la consola)
   ============================================================================== */
.gamepad-legend-bar {
  background: #06070a;
  border-top: 2px solid var(--cci-border-panel);
  padding: 14px 0;
}

.legend-container {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--cci-muted);
}

.legend-key {
  color: var(--cci-cyan);
  font-weight: 700;
  background: #0e1117;
  padding: 2px 7px;
  border: 1px solid var(--cci-border-panel);
}

/* ==============================================================================
   FOOTER
   ============================================================================== */
.footer {
  background: var(--cci-bg-void);
  border-top: 1px solid var(--cci-border-panel);
  padding: 44px 0 30px;
  color: var(--cci-dim);
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.footer-logo {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: 2px;
  display: block;
  margin-bottom: 6px;
}

.footer-copy {
  font-size: 0.85rem;
  color: var(--cci-muted);
  line-height: 1.6;
}
.footer-copy strong {
  color: #fff;
}

.footer-links {
  display: flex;
  gap: 20px;
}
.footer-links a {
  color: var(--cci-muted);
  text-decoration: none;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 1px;
  transition: color 0.2s ease;
}
.footer-links a:hover {
  color: var(--cci-cyan);
}

/* ==============================================================================
   MODAL FICHA TÉCNICA
   ============================================================================== */
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.88);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-dialog {
  background: var(--cci-bg-surface);
  border: 2px solid var(--cci-cyan);
  box-shadow: 0 0 50px var(--cci-cyan-dim);
  max-width: 680px;
  width: 100%;
  overflow: hidden;
  position: relative;
  animation: modal-pop 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-pop {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

.modal-close {
  position: absolute;
  top: 12px; right: 14px;
  background: #000;
  border: 1px solid var(--cci-border-panel);
  color: #fff;
  width: 32px; height: 32px;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s ease;
}
.modal-close:hover {
  background: var(--cci-cyan);
  color: #000;
}

.modal-art-box {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}
.modal-art-box img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}

.modal-info-box {
  padding: 24px 28px;
}

.modal-tags-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
}

.modal-title {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 900;
  color: #fff;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.modal-dev {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--cci-cyan);
  margin-bottom: 14px;
}

.modal-desc {
  font-size: 1.05rem;
  color: var(--cci-light);
  line-height: 1.6;
  margin-bottom: 20px;
}

.modal-launch-note {
  background: #090b0e;
  border: 1px solid var(--cci-green);
  color: var(--cci-green);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  padding: 8px 14px;
  text-align: center;
  letter-spacing: 1px;
}

/* ==============================================================================
   RESPONSIVE DESIGN
   ============================================================================== */
@media (max-width: 992px) {
  .hero-layout { grid-template-columns: 1fr; gap: 40px; }
  .profile-grid { grid-template-columns: 1fr; text-align: center; justify-items: center; }
  .profile-specs-row { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .hud-nav { display: none; }
  .hero-headline { font-size: 2.1rem; }
  .section-title { font-size: 1.7rem; }
  .footer-content { flex-direction: column; text-align: center; }
}
"""

CLIENT_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const filterBtns = document.querySelectorAll('.filter-chip');
  const gameCards = document.querySelectorAll('.cartridge-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const selectedCat = (btn.dataset.cat || '').toUpperCase();

      gameCards.forEach(card => {
        const cardCats = (card.dataset.categories || '').toUpperCase().split(' ');
        if (selectedCat === 'TODOS' || cardCats.includes(selectedCat)) {
          card.style.display = 'flex';
        } else {
          card.style.display = 'none';
        }
      });
    });
  });

  const modal = document.getElementById('gameModal');
  const modalClose = document.getElementById('modalClose');
  const modalImg = document.getElementById('modalImg');
  const modalTitle = document.getElementById('modalTitle');
  const modalYear = document.getElementById('modalYear');
  const modalGenre = document.getElementById('modalGenre');
  const modalPlayers = document.getElementById('modalPlayers');
  const modalDev = document.getElementById('modalDev');
  const modalDesc = document.getElementById('modalDesc');

  function openModal(card) {
    modalTitle.textContent = card.dataset.title;
    modalGenre.textContent = card.dataset.genre;
    modalDev.textContent = 'Desarrollador: ' + card.dataset.dev;
    modalYear.textContent = card.dataset.year;
    modalPlayers.textContent = card.dataset.players + ' Jugador(es)';
    modalDesc.textContent = card.dataset.desc;
    modalImg.src = card.querySelector('img').src;
    modalImg.alt = card.dataset.title;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.style.display = 'none';
    document.body.style.overflow = '';
  }

  gameCards.forEach(card => card.addEventListener('click', () => openModal(card)));
  if (modalClose) modalClose.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.style.display === 'flex') closeModal();
  });
});
"""


def _render_game_card(g: dict) -> str:
    cats_str = " ".join(g.get("categories", []))
    tags_html = "".join(f'<span class="cartridge-tag">{html.escape(t)}</span>' for t in g.get("tags", []))
    slot_num = f"{g.get('slot', 0):02d}"
    return f"""
    <div class="cartridge-card" data-categories="{html.escape(cats_str)}" data-title="{html.escape(g.get('title',''))}" data-genre="{html.escape(g.get('genre',''))}" data-dev="{html.escape(g.get('developer',''))}" data-year="{html.escape(str(g.get('year','')))}" data-players="{html.escape(str(g.get('players','')))}" data-desc="{html.escape(g.get('subtitle',''))}">
      <div class="cartridge-header">
        <span class="cartridge-slot">SLOT {slot_num} // 19</span>
        <span>REV 2026</span>
      </div>
      <div class="cartridge-art">
        <img src="{html.escape(g.get('card_url',''))}" alt="{html.escape(g.get('title',''))}" loading="lazy">
        <div class="cartridge-overlay">
          <span class="overlay-action-btn">[ ⌧ A ] VER FICHA</span>
        </div>
      </div>
      <div class="cartridge-body">
        <div class="cartridge-meta">
          <span class="cartridge-year">[ {html.escape(str(g.get('year','')))} ]</span>
          <span class="cartridge-players">{html.escape(str(g.get('players','')))} JUGADOR(ES)</span>
        </div>
        <h3 class="cartridge-title">{html.escape(g.get("title",""))}</h3>
        <p class="cartridge-sub">{html.escape(g.get("subtitle",""))}</p>
        <div class="cartridge-tags">
          {tags_html}
        </div>
      </div>
    </div>
    """


def build_landing_page(games: list[dict], categories: list[str], author: dict, stats: dict) -> str:
    """Construye y retorna el documento HTML completo generado al 100% en Python."""
    filters_html = "".join(
        f'<button class="filter-chip {"active" if cat == "TODOS" else ""}" data-cat="{html.escape(cat)}">{html.escape(cat)}</button>'
        for cat in categories
    )
    games_cards_html = "".join(_render_game_card(g) for g in games)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>C.C.I. SYSTEM — Consola Virtual & Emulador Retro Multiplataforma</title>
  <meta name="description" content="Consola virtual y emulador multiplataforma 100% Python con 19 clásicos retro arcade. Autora: Camila Carolina Ianni.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/style.css">
  <style>
{CYBER_CSS}
  </style>
</head>
<body>
  <div class="crt-overlay"></div>
  <div class="tech-grid-bg"></div>

  <!-- HUD Top Bar (Estilo Consola) -->
  <header class="top-hud">
    <div class="container hud-container">
      <a href="#" class="hud-brand">
        <div class="brand-badge">C.C.I. <span>SYSTEM</span></div>
        <div class="hud-sys-status">
          <span class="led-indicator"></span>
          <span>SYS.ONLINE // 100% PYTHON</span>
        </div>
      </a>
      <nav class="hud-nav">
        <a href="#arquitectura" class="hud-tab">Arquitectura</a>
        <a href="#catalogo" class="hud-tab">Catálogo ({len(games)})</a>
        <a href="#autora" class="hud-tab">Autora</a>
        <a href="#descarga" class="hud-tab hud-cta-download">DESCARGAR EMULADOR</a>
      </nav>
    </div>
  </header>

  <!-- Hero: Virtual Console Stage -->
  <section class="hero">
    <div class="container hero-layout">
      <div class="hero-left">
        <span class="telemetry-tag">// VIRTUAL CONSOLE ARCHITECTURE · 100% PYTHON</span>
        <h1 class="hero-headline">CONSOLA VIRTUAL RETRO &amp; <span>EMULADOR</span></h1>
        <p class="hero-lead">
          <strong>C.C.I. SYSTEM</strong> integra <strong>19 videojuegos arcade clásicos</strong>
          en una consola virtual integral con arquitectura de estados en Python,
          renderizado a 60 FPS, sistema multiusuario con gestión de estadísticas independientes,
          soporte de joystick plug &amp; play y capturador HD sin dependencias externas.
        </p>
        <div class="hero-actions">
          <a href="#descarga" class="btn-cci btn-primary-action">
            <span class="btn-gamepad-key">⌧ A</span> DESCARGAR EMULADOR
          </a>
          <a href="#catalogo" class="btn-cci btn-secondary-action">
            <span class="btn-gamepad-key">△ Y</span> VER CATÁLOGO ({len(games)} JUEGOS)
          </a>
        </div>
        <div class="spec-strip">
          <div class="spec-cell">
            <span class="spec-val">{len(games)}</span>
            <span class="spec-lbl">JUEGOS ARCADE</span>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-cell">
            <span class="spec-val">0</span>
            <span class="spec-lbl">PERFILES DE FÁBRICA</span>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-cell">
            <span class="spec-val">100%</span>
            <span class="spec-lbl">PYTHON PURO</span>
          </div>
          <div class="spec-divider"></div>
          <div class="spec-cell">
            <span class="spec-val">60</span>
            <span class="spec-lbl">FPS ESTABLES</span>
          </div>
        </div>
      </div>

      <div class="hero-right">
        <div class="console-chassis">
          <div class="chassis-header">
            <div class="chassis-header-left">
              <span class="chassis-led"></span>
              <span class="chassis-title">CCI_SYSTEM_VIRTUAL_CORE</span>
            </div>
            <span class="chassis-res">1280x720 @ 60FPS</span>
          </div>
          <div class="chassis-screen">
            <img src="/assets/welcome.png" alt="Pantalla C.C.I. SYSTEM">
          </div>
          <div class="chassis-footer">
            <span>MOTOR: PYGAME-CE // STATE_MACHINE</span>
            <span>PLATAFORMA: MAC &amp; WINDOWS</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Subsystems / Architecture -->
  <section id="arquitectura" class="section">
    <div class="container">
      <span class="section-tag">// INGENIERÍA DE LA CONSOLA</span>
      <h2 class="section-title">ARQUITECTURA DE SOFTWARE 100% PYTHON</h2>
      <p class="section-desc">
        Diseñada y desarrollada sin empaquetadores binarios opacos ni wrappers.
        Cada pantalla, transición, controlador de audio y sistema de entrada funciona íntegramente en Python.
      </p>

      <div class="subsystems-grid">
        <div class="subsystem-card">
          <span class="subsystem-code">// KERNEL_01: STATE MACHINE</span>
          <h3 class="subsystem-title">Motor de Estados Finitos</h3>
          <p class="subsystem-text">
            Flujo determinista desacoplado gestionado por máquina de estados (`StateMachine`):
            `INTRO_VIDEO` → `USER_SELECT` → `MENU` → `GAME_RUNNER`.
            Cero fugas de memoria y bucle de eventos a 60 FPS estables.
          </p>
        </div>

        <div class="subsystem-card">
          <span class="subsystem-code">// SUBSYSTEM_02: MULTI-USER</span>
          <h3 class="subsystem-title">Gestión de Perfiles Limpia</h3>
          <p class="subsystem-text">
            Arranque oficial con 0 perfiles de fábrica. Al iniciar por primera vez, el asistente
            te invita a crear tu usuario, elegir tu avatar cyberpunk y guardar estadísticas de forma aislada.
          </p>
        </div>

        <div class="subsystem-card">
          <span class="subsystem-code">// SUBSYSTEM_03: INPUT ENGINE</span>
          <h3 class="subsystem-title">Control Universal Plug &amp; Play</h3>
          <p class="subsystem-text">
            Mapeo universal con `pygame.joystick` para DualShock 4, DualSense (PS5), mandos Xbox Series/One
            y joysticks USB arcade. Soporta reconexión en caliente y vibración háptica.
          </p>
        </div>

        <div class="subsystem-card">
          <span class="subsystem-code">// SUBSYSTEM_04: CAPTURE &amp; AUDIO</span>
          <h3 class="subsystem-title">Captura F12 &amp; Sintetizador</h3>
          <p class="subsystem-text">
            Capturador nativo F12 a 720p sin compresión con guardado instantáneo y notificación toast.
            Sintetizador de audio en tiempo real y banda sonora ambiental BGM.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Games Catalog Section -->
  <section id="catalogo" class="section section-dark">
    <div class="container">
      <div class="catalog-header-bar">
        <div>
          <span class="section-tag">// RACK OFICIAL DE TÍTULOS</span>
          <h2 class="section-title">BIBLIOTECA ({len(games)} JUEGOS)</h2>
          <p class="section-desc">Selecciona una categoría para filtrar los títulos:</p>
        </div>
        <div class="filters-rack">
          {filters_html}
        </div>
      </div>

      <div class="games-rack-grid">
        {games_cards_html}
      </div>
    </div>
  </section>

  <!-- Author Section (Estilo pantalla 'PERFIL' de la consola) -->
  <section id="autora" class="section">
    <div class="container">
      <div class="profile-screen-card">
        <div class="profile-hud-header">
          <span>// C.C.I. SYSTEM · FICHA OFICIAL DE AUTORÍA Y DIRECCIÓN</span>
          <span>DEV_ID: CCI-2026-001</span>
        </div>
        <div class="profile-grid">
          <div class="profile-avatar-block">
            <div class="profile-avatar-frame">
              <span class="profile-monogram">CCI</span>
            </div>
            <span class="profile-badge-pill">DESARROLLADORA</span>
          </div>
          <div class="profile-details-block">
            <h2 class="profile-name">{html.escape(author.get("name",""))}</h2>
            <p class="profile-inst">{html.escape(author.get("institution",""))} · {html.escape(author.get("year",""))}</p>
            <p class="profile-bio">{html.escape(author.get("bio",""))}</p>
            <div class="profile-specs-row">
              <div class="profile-spec-item">
                <strong>ARQUITECTURA CORE</strong>
                <span>100% Python nativo sin dependencias externas</span>
              </div>
              <div class="profile-spec-item">
                <strong>PRESERVACIÓN ARCADE</strong>
                <span>19 títulos adaptados a resolución 720p</span>
              </div>
              <div class="profile-spec-item">
                <strong>SISTEMA MULTIUSUARIO</strong>
                <span>0 perfiles de fábrica, guardado en JSON local</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Downloads Section -->
  <section id="descarga" class="section section-dark">
    <div class="container">
      <div class="text-center" style="max-width: 720px; margin: 0 auto 30px;">
        <span class="section-tag">// HARDWARE RELEASES</span>
        <h2 class="section-title">DESCARGA DEL EMULADOR</h2>
        <p class="section-desc">
          Elige tu sistema operativo. Ambas descargas incluyen los 19 juegos, el asistente gráfico de 1-clic
          y <strong>0 perfiles precargados</strong> para que crees tu partida desde cero.
        </p>
      </div>

      <div class="downloads-panel-grid">
        <!-- macOS -->
        <div class="download-hardware-card">
          <div class="hw-icon-box">
            <svg class="os-svg" width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.37c.63-.77 1.06-1.85.94-2.93-.91.04-2.02.61-2.67 1.37-.58.67-.99 1.77-.85 2.83 1.02.08 2.05-.51 2.58-1.27z"/></svg>
          </div>
          <h3 class="hw-title">C.C.I. SYSTEM para macOS (.dmg)</h3>
          <p class="hw-sub">Instalador nativo Apple Disk Image con C.C.I. SYSTEM.app</p>
          <ul class="hw-checklist">
            <li>Imagen de disco nativa Apple Disk Image (.dmg)</li>
            <li>App bundle C.C.I. SYSTEM.app de 1-clic</li>
            <li>Asistente pop-up de destino (Escritorio por defecto)</li>
            <li>0 perfiles de fábrica (creación de jugador en primer boot)</li>
          </ul>
          <div class="hw-btn-wrap">
            <a href="/download/mac" class="btn-cci btn-primary-action" style="width: 100%;">
              <span class="btn-gamepad-key">⌧ A</span> DESCARGAR INSTALADOR DMG (MAC)
            </a>
            <span class="hw-hint">Abre el archivo .dmg y haz doble clic en C.C.I. SYSTEM</span>
          </div>
        </div>

        <!-- Windows -->
        <div class="download-hardware-card">
          <div class="hw-icon-box">
            <svg class="os-svg" width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/></svg>
          </div>
          <h3 class="hw-title">C.C.I. SYSTEM para Windows (.exe)</h3>
          <p class="hw-sub">Instalador ejecutable nativo PE32 con asistente interactivo</p>
          <ul class="hw-checklist">
            <li>Instalador ejecutable nativo .exe (PE32 GUI)</li>
            <li>Ejecución directa sin terminal ni comandos</li>
            <li>Asistente pop-up con ubicación por defecto en Escritorio</li>
            <li>0 perfiles de fábrica (crea tu jugador al instante)</li>
          </ul>
          <div class="hw-btn-wrap">
            <a href="/download/windows" class="btn-cci btn-secondary-action" style="width: 100%;">
              <span class="btn-gamepad-key">⌧ A</span> DESCARGAR INSTALADOR EXE (WINDOWS)
            </a>
            <span class="hw-hint">Ejecuta el archivo .exe y sigue el asistente interactivo</span>
          </div>
        </div>
      </div>

      <!-- Boot Steps -->
      <div class="boot-steps-card">
        <h4 class="boot-steps-title">// SECUENCIA DE ARRANQUE DE UN EMULADOR REAL</h4>
        <div class="boot-steps-grid">
          <div class="boot-step">
            <div class="boot-step-num">01</div>
            <div class="boot-step-content">
              <strong>DESCARGA EL INSTALADOR OFICIAL</strong>
              Descarga la imagen .dmg para macOS o el ejecutable .exe para Windows.
            </div>
          </div>
          <div class="boot-step">
            <div class="boot-step-num">02</div>
            <div class="boot-step-content">
              <strong>MONTA Y ABRE LA APP</strong>
              Haz doble clic en C.C.I. SYSTEM: un diálogo te preguntará dónde ubicar la consola (Escritorio por defecto).
            </div>
          </div>
          <div class="boot-step">
            <div class="boot-step-num">03</div>
            <div class="boot-step-content">
              <strong>BOOT INMEDIATO Y NUEVO PERFIL</strong>
              Se genera el acceso directo en tu Escritorio y la consola se abre de inmediato lista para crear tu perfil y jugar.
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Gamepad Legend Bar (Barra de comandos de la consola) -->
  <div class="gamepad-legend-bar">
    <div class="container legend-container">
      <div><span class="legend-key">⌧ A</span> SELECCIONAR / INICIAR</div>
      <div><span class="legend-key">◯ B</span> VOLVER</div>
      <div><span class="legend-key">△ Y</span> DETALLES DE JUEGO</div>
      <div><span class="legend-key">F12</span> CAPTURADOR HD</div>
      <div><span class="legend-key">🕹️ STICK / D-PAD</span> NAVEGACIÓN</div>
    </div>
  </div>

  <!-- Modal Ficha Técnica -->
  <div class="modal-backdrop" id="gameModal" style="display: none;">
    <div class="modal-dialog">
      <button class="modal-close" id="modalClose">&times;</button>
      <div class="modal-art-box">
        <img src="" id="modalImg" alt="Juego">
      </div>
      <div class="modal-info-box">
        <div class="modal-tags-row">
          <span style="color: var(--cci-gold);" id="modalYear"></span>
          <span style="color: var(--cci-muted);" id="modalPlayers"></span>
        </div>
        <h2 class="modal-title" id="modalTitle"></h2>
        <p class="modal-dev" id="modalDev"></p>
        <p class="modal-desc" id="modalDesc"></p>
        <div class="modal-launch-note">DISPONIBLE EN C.C.I. SYSTEM VIRTUAL CONSOLE</div>
      </div>
    </div>
  </div>

  <!-- Footer -->
  <footer class="footer">
    <div class="container footer-content">
      <div class="footer-left">
        <span class="footer-logo">C.C.I. SYSTEM</span>
        <p class="footer-copy">
          Virtual Console &amp; Multiplatform Retro Emulator · Diseñado y desarrollado por <strong>Camila Carolina Ianni</strong>.
          <br>Arquitectura 100% Python puro con fines de preservación y divulgación académica (2026).
        </p>
      </div>
      <div class="footer-links">
        <a href="#arquitectura">Arquitectura</a>
        <a href="#catalogo">Catálogo</a>
        <a href="#autora">Autora</a>
        <a href="#descarga">Descargas</a>
      </div>
    </div>
  </footer>

  <script>{CLIENT_JS}</script>
</body>
</html>"""
