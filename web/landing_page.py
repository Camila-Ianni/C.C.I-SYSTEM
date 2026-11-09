"""web/landing_page.py - Generador 100% Python de la Landing Page de C.C.I. SYSTEM.
Estética oficial: Glassmorphism oscuro profundo, curvas suaves estilo píldora, iluminación sutil
blanco/plateado, tipografía moderna y minimalismo sci-fi de alta gama.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import html

CYBER_CSS = """
/* ==============================================================================
   C.C.I. SYSTEM VIRTUAL CONSOLE — OFFICIAL UI STYLESHEET (GLASSMORPHISM SCI-FI)
   Paleta oficial: Obsidian Dark Glass, Silver-White Gradient Highlights,
   Capsule Pills (border-radius: 9999px), Clean Modern Typography.
   Autora: Camila Carolina Ianni
   ============================================================================== */

:root {
  --cci-bg-void: #050608;
  --cci-bg-base: #08090c;
  --cci-bg-panel: rgba(13, 16, 23, 0.72);
  --cci-bg-surface: rgba(18, 22, 31, 0.62);
  --cci-bg-surface-hover: rgba(28, 33, 46, 0.82);
  --cci-bg-elevated: rgba(255, 255, 255, 0.04);
  --cci-bg-pill: rgba(255, 255, 255, 0.08);
  --cci-bg-pill-hover: rgba(255, 255, 255, 0.15);
  --cci-border-dim: rgba(255, 255, 255, 0.08);
  --cci-border-panel: rgba(255, 255, 255, 0.12);
  --cci-border-bright: rgba(255, 255, 255, 0.22);
  --cci-border-active: #ffffff;
  --cci-white: #ffffff;
  --cci-light: #e5e7eb;
  --cci-muted: #9ca3af;
  --cci-dim: #6b7280;
  --cci-green: #22c55e;
  --cci-green-dim: rgba(34, 197, 94, 0.15);
  --cci-green-glow: rgba(34, 197, 94, 0.4);
  --cci-glow-soft: rgba(255, 255, 255, 0.18);
  --font-display: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-ui: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
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
  -webkit-font-smoothing: antialiased;
}

body {
  position: relative;
  overflow-x: hidden;
  background-color: var(--cci-bg-void);
  background-image: 
    radial-gradient(ellipse 90% 45% at 50% -10%, rgba(255, 255, 255, 0.08), transparent),
    radial-gradient(circle 600px at 80% 20%, rgba(255, 255, 255, 0.03), transparent),
    radial-gradient(circle 500px at 15% 65%, rgba(255, 255, 255, 0.02), transparent);
  min-height: 100vh;
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
   CONSOLE TOP HUD BAR (Sleek Frosted Glass Capsule Style)
   ============================================================================== */
.top-hud {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 72px;
  background: rgba(8, 10, 15, 0.78);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--cci-border-panel);
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
  gap: 16px;
  text-decoration: none;
  color: inherit;
}

.brand-badge {
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 800;
  font-style: italic;
  letter-spacing: 2px;
  color: #fff;
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.brand-badge span {
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 4px;
  color: var(--cci-muted);
  margin-top: 3px;
  font-style: normal;
}

.hud-sys-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px;
  border-radius: 9999px;
  background: var(--cci-bg-elevated);
  border: 1px solid var(--cci-border-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 1px;
  color: var(--cci-light);
}

.led-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--cci-green);
  box-shadow: 0 0 10px var(--cci-green);
}

.hud-burger {
  display: none;
  flex-direction: column;
  justify-content: space-around;
  width: 38px;
  height: 38px;
  padding: 8px;
  background: var(--cci-bg-pill);
  border: 1px solid var(--cci-border-panel);
  border-radius: 9999px;
  cursor: pointer;
  z-index: 101;
}

.hud-burger span {
  width: 100%;
  height: 2px;
  background: #ffffff;
  border-radius: 2px;
  transition: all 0.25s ease;
}

.hud-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hud-tab {
  padding: 8px 16px;
  border-radius: 9999px;
  color: var(--cci-muted);
  text-decoration: none;
  font-size: 0.88rem;
  font-weight: 500;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.hud-tab:hover {
  color: #fff;
  background: var(--cci-bg-pill-hover);
  border-color: var(--cci-border-dim);
}

.hud-cta-download {
  background: #ffffff !important;
  color: #000000 !important;
  font-weight: 700 !important;
  box-shadow: 0 0 20px rgba(255, 255, 255, 0.22);
}

.hud-cta-download:hover {
  background: #f0f0f0 !important;
  transform: translateY(-1px);
  box-shadow: 0 0 28px rgba(255, 255, 255, 0.4);
}

/* ==============================================================================
   HERO STAGE (Sci-Fi Dark Glass)
   ============================================================================== */
.hero {
  padding-top: 140px;
  padding-bottom: 70px;
  position: relative;
}

.hero-layout {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 48px;
  align-items: center;
}

.telemetry-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 1.5px;
  color: var(--cci-light);
  padding: 5px 14px;
  border-radius: 9999px;
  background: var(--cci-bg-elevated);
  border: 1px solid var(--cci-border-panel);
  margin-bottom: 22px;
}

.hero-headline {
  font-family: var(--font-display);
  font-size: 2.85rem;
  font-weight: 800;
  line-height: 1.12;
  letter-spacing: -0.5px;
  margin-bottom: 20px;
  color: #ffffff;
}

.hero-headline span {
  background: linear-gradient(180deg, #ffffff 30%, #a1a1aa 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-lead {
  font-size: 1.05rem;
  line-height: 1.7;
  color: var(--cci-muted);
  margin-bottom: 32px;
}

.hero-lead strong {
  color: var(--cci-light);
  font-weight: 600;
}

.hero-actions {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 38px;
}

.btn-cci {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 24px;
  border-radius: 9999px;
  font-family: var(--font-ui);
  font-weight: 600;
  font-size: 0.92rem;
  text-decoration: none;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: pointer;
  border: 1px solid transparent;
}

.btn-primary-action {
  background: #ffffff;
  color: #07080b;
  box-shadow: 0 4px 20px rgba(255, 255, 255, 0.2);
}

.btn-primary-action:hover {
  background: #f5f5f7;
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(255, 255, 255, 0.35);
}

.btn-secondary-action {
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  border: 1px solid var(--cci-border-panel);
  backdrop-filter: blur(12px);
}

.btn-secondary-action:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
}

.btn-gamepad-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 9999px;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(0, 0, 0, 0.15);
}

.btn-secondary-action .btn-gamepad-key {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.spec-strip {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 24px;
  border-radius: 20px;
  background: var(--cci-bg-surface);
  backdrop-filter: blur(20px);
  border: 1px solid var(--cci-border-panel);
}

.spec-cell {
  display: flex;
  flex-direction: column;
}

.spec-val {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.1;
}

.spec-lbl {
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 1px;
  color: var(--cci-muted);
}

.spec-divider {
  width: 1px;
  height: 32px;
  background: var(--cci-border-panel);
}

/* ==============================================================================
   CONSOLE CHASSIS (Video / Live Demo Display)
   ============================================================================== */
.console-chassis {
  background: var(--cci-bg-panel);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.chassis-header {
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--cci-border-panel);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cci-muted);
}

.chassis-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chassis-led {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--cci-green);
  box-shadow: 0 0 8px var(--cci-green);
}

.chassis-screen {
  position: relative;
  background: #000000;
  aspect-ratio: 16/9;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.chassis-screen video, .chassis-screen img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.chassis-live-badge {
  position: absolute;
  top: 12px; right: 12px;
  padding: 4px 10px;
  border-radius: 9999px;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.blink-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--cci-green);
  box-shadow: 0 0 6px var(--cci-green);
}

.chassis-footer {
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.02);
  border-top: 1px solid var(--cci-border-panel);
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--cci-dim);
}

/* ==============================================================================
   SECTIONS GENERAL STYLES
   ============================================================================== */
.section {
  padding: 85px 0;
  position: relative;
}

.section-dark {
  background: rgba(6, 8, 12, 0.45);
}

.section-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  letter-spacing: 2px;
  color: var(--cci-light);
  margin-bottom: 12px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.3px;
  color: #ffffff;
  margin-bottom: 14px;
}

.section-desc {
  font-size: 1.02rem;
  line-height: 1.7;
  color: var(--cci-muted);
  max-width: 780px;
  margin-bottom: 40px;
}

.section-desc strong {
  color: var(--cci-light);
}

/* ==============================================================================
   ACADEMIC PILLARS GRID
   ============================================================================== */
.academic-pillars-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 22px;
}

.academic-pillar-card {
  background: var(--cci-bg-surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 20px;
  padding: 28px 24px;
  transition: all 0.22s ease;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.academic-pillar-card:hover {
  transform: translateY(-4px);
  border-color: var(--cci-border-bright);
  background: var(--cci-bg-surface-hover);
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.12);
}

.pillar-num {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--cci-muted);
  margin-bottom: 14px;
}

.pillar-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 12px;
}

.pillar-desc {
  font-size: 0.9rem;
  line-height: 1.65;
  color: var(--cci-muted);
}

/* ==============================================================================
   PROFILE SCREEN CARD (Camila Carolina Ianni)
   ============================================================================== */
.profile-screen-card {
  background: var(--cci-bg-surface);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.profile-hud-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cci-dim);
  border-bottom: 1px solid var(--cci-border-panel);
  padding-bottom: 16px;
  margin-bottom: 28px;
}

.profile-grid {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 36px;
  align-items: center;
}

.profile-avatar-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.profile-avatar-frame {
  width: 170px;
  height: 170px;
  border-radius: 24px;
  border: 1px solid var(--cci-border-bright);
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
}

.profile-avatar-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.profile-badge-pill {
  padding: 4px 14px;
  border-radius: 9999px;
  background: #ffffff;
  color: #000000;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 1px;
}

.profile-name {
  font-family: var(--font-display);
  font-size: 1.85rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.profile-inst {
  font-family: var(--font-mono);
  font-size: 0.82rem;
  color: var(--cci-light);
  margin-bottom: 14px;
}

.profile-bio {
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--cci-muted);
  margin-bottom: 24px;
}

.profile-specs-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 26px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--cci-border-dim);
  border-radius: 16px;
}

.profile-spec-item strong {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cci-muted);
  margin-bottom: 4px;
}

.profile-spec-item span {
  font-size: 0.88rem;
  color: #ffffff;
}

.btn-profile-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--cci-border-panel);
  color: #fff;
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  font-weight: 600;
  transition: all 0.2s ease;
}

.btn-profile-link:hover {
  background: #ffffff;
  color: #000;
}

/* ==============================================================================
   SUBSYSTEMS / ARCHITECTURE
   ============================================================================== */
.subsystems-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 22px;
}

.subsystem-card {
  background: var(--cci-bg-surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 20px;
  padding: 28px 24px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.subsystem-code {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 1px;
  color: var(--cci-muted);
  display: block;
  margin-bottom: 10px;
}

.subsystem-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 12px;
}

.subsystem-text {
  font-size: 0.88rem;
  line-height: 1.65;
  color: var(--cci-muted);
}

/* ==============================================================================
   GAMES CATALOG (BIBLIOTECA)
   ============================================================================== */
.catalog-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-chips-rack {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 32px;
}

.filter-chip {
  padding: 8px 18px;
  border-radius: 9999px;
  font-family: var(--font-ui);
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--cci-muted);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--cci-border-dim);
  backdrop-filter: blur(10px);
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-chip:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.09);
  border-color: var(--cci-border-bright);
}

.filter-chip.active {
  background: #ffffff;
  color: #000000;
  font-weight: 700;
  border-color: #ffffff;
  box-shadow: 0 0 16px rgba(255, 255, 255, 0.3);
}

.games-rack-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 24px;
}

.cartridge-card {
  position: relative;
  background: var(--cci-bg-surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  cursor: pointer;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.cartridge-card:hover {
  transform: translateY(-6px);
  border-color: var(--cci-border-bright);
  background: var(--cci-bg-surface-hover);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.55), 0 0 24px rgba(255, 255, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.16);
}

.cartridge-header {
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--cci-border-dim);
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.68rem;
  color: var(--cci-dim);
}

.cartridge-art {
  position: relative;
  width: 100%;
  aspect-ratio: 4/3;
  overflow: hidden;
  background: #000;
}

.cartridge-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
  display: block;
}

.cartridge-card:hover .cartridge-art img {
  transform: scale(1.04);
}

.cartridge-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
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
  padding: 8px 18px;
  border-radius: 9999px;
  background: #ffffff;
  color: #000000;
  font-family: var(--font-ui);
  font-size: 0.8rem;
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.cartridge-body {
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.cartridge-meta {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cci-muted);
  margin-bottom: 6px;
}

.cartridge-title {
  font-family: var(--font-display);
  font-size: 1.12rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.cartridge-sub {
  font-size: 0.82rem;
  color: var(--cci-muted);
  line-height: 1.45;
  margin-bottom: 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.cartridge-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: auto;
}

.cartridge-tag {
  padding: 3px 10px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--cci-border-dim);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--cci-light);
}

/* ==============================================================================
   DOWNLOADS SECTION
   ============================================================================== */
.downloads-panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 28px;
  margin-bottom: 40px;
}

.download-hardware-card {
  background: var(--cci-bg-surface);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--cci-border-panel);
  border-radius: 24px;
  padding: 36px 30px;
  box-shadow: 0 14px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
}

.hw-icon-box {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--cci-border-bright);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
  color: #fff;
}

.hw-title {
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 6px;
}

.hw-sub {
  font-size: 0.88rem;
  color: var(--cci-muted);
  margin-bottom: 20px;
}

.hw-checklist {
  list-style: none;
  margin-bottom: 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hw-checklist li {
  font-size: 0.88rem;
  color: var(--cci-light);
  display: flex;
  align-items: center;
  gap: 10px;
}

.hw-checklist li::before {
  content: "✓";
  color: var(--cci-green);
  font-weight: 700;
}

.hw-btn-wrap {
  margin-top: auto;
}

.hw-hint {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--cci-dim);
  text-align: center;
  margin-top: 10px;
}

/* ==============================================================================
   GAMEPAD LEGEND BAR
   ============================================================================== */
.gamepad-legend-bar {
  background: rgba(10, 12, 17, 0.85);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-top: 1px solid var(--cci-border-panel);
  border-bottom: 1px solid var(--cci-border-panel);
  padding: 14px 0;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  color: var(--cci-light);
}

.legend-container {
  display: flex;
  justify-content: space-around;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
}

.legend-key {
  padding: 2px 8px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid var(--cci-border-bright);
  color: #fff;
  font-weight: 700;
  margin-right: 6px;
}

/* ==============================================================================
   MODAL FICHA TÉCNICA
   ============================================================================== */
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-dialog {
  position: relative;
  background: rgba(15, 18, 26, 0.95);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid var(--cci-border-bright);
  border-radius: 24px;
  max-width: 760px;
  width: 100%;
  display: grid;
  grid-template-columns: 280px 1fr;
  overflow: hidden;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 35px rgba(255, 255, 255, 0.08);
}

.modal-close {
  position: absolute;
  top: 14px; right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid var(--cci-border-panel);
  color: #fff;
  font-size: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  transition: all 0.2s ease;
}

.modal-close:hover {
  background: #ffffff;
  color: #000;
}

.modal-art-box {
  background: #000;
  width: 100%;
  height: 100%;
}

.modal-art-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.modal-info-box {
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
}

.modal-tags-row {
  display: flex;
  gap: 12px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  margin-bottom: 10px;
}

.modal-title {
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 6px;
}

.modal-dev {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--cci-muted);
  margin-bottom: 16px;
}

.modal-desc {
  font-size: 0.92rem;
  line-height: 1.65;
  color: var(--cci-light);
  margin-bottom: 24px;
}

.modal-launch-note {
  margin-top: auto;
  padding: 10px 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--cci-border-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 1px;
  color: var(--cci-muted);
  text-align: center;
}

/* ==============================================================================
   FOOTER
   ============================================================================== */
.footer {
  background: rgba(8, 10, 14, 0.9);
  border-top: 1px solid var(--cci-border-panel);
  padding: 40px 0;
  position: relative;
  z-index: 2;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
}

.footer-left {
  max-width: 540px;
}

.footer-logo {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 800;
  font-style: italic;
  letter-spacing: 2px;
  color: #ffffff;
  display: block;
  margin-bottom: 6px;
}

.footer-copy {
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--cci-muted);
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.footer-links a {
  color: var(--cci-light);
  text-decoration: none;
  font-size: 0.88rem;
  transition: color 0.2s ease;
}

.footer-links a:hover {
  color: #ffffff;
}

.footer-sep {
  color: var(--cci-dim);
}

/* Responsive */
@media (max-width: 900px) {
  .hero-layout {
    grid-template-columns: 1fr;
  }
  .hud-burger {
    display: flex;
  }
  .hud-nav {
    display: none;
    position: absolute;
    top: 72px; left: 0; right: 0;
    background: rgba(10, 12, 17, 0.98);
    backdrop-filter: blur(24px);
    border-bottom: 1px solid var(--cci-border-panel);
    flex-direction: column;
    padding: 20px 28px;
    gap: 12px;
  }
  .hud-nav.open {
    display: flex;
  }
  .profile-grid {
    grid-template-columns: 1fr;
    text-align: center;
  }
  .modal-dialog {
    grid-template-columns: 1fr;
  }
  .modal-art-box {
    height: 220px;
  }
}
"""

CLIENT_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const hudBurger = document.getElementById('hudBurger');
  const hudNav = document.getElementById('hudNav');

  if (hudBurger && hudNav) {
    hudBurger.addEventListener('click', (e) => {
      e.stopPropagation();
      hudNav.classList.toggle('open');
      hudBurger.classList.toggle('active');
    });
    hudNav.querySelectorAll('.hud-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        hudNav.classList.remove('open');
        hudBurger.classList.remove('active');
      });
    });
    document.addEventListener('click', (e) => {
      if (!hudNav.contains(e.target) && !hudBurger.contains(e.target) && hudNav.classList.contains('open')) {
        hudNav.classList.remove('open');
        hudBurger.classList.remove('active');
      }
    });
  }

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
  const modalPlayers = document.getElementById('modalPlayers');
  const modalDev = document.getElementById('modalDev');
  const modalDesc = document.getElementById('modalDesc');

  function openModal(card) {
    modalTitle.textContent = card.dataset.title;
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
        <span>C.C.I SYSTEM</span>
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


def build_landing_page(
    games: list[dict],
    categories: list[str],
    author: dict,
    stats: dict,
    highscores: list[dict] = None
) -> str:
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
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>C.C.I. SYSTEM — Consola Virtual & Emulador Retro Multiplataforma</title>
  <meta name="description" content="Consola virtual y emulador multiplataforma 100% Python con 19 clásicos retro arcade. Autora: Camila Carolina Ianni.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/style.css">
  <style>
{CYBER_CSS}
  </style>
</head>
<body>

  <!-- HUD Top Bar (Estilo Consola) -->
  <header class="top-hud">
    <div class="container hud-container">
      <a href="#" class="hud-brand">
        <div class="brand-badge">C.C.I. <span>— SYSTEM —</span></div>
        <div class="hud-sys-status">
          <span class="led-indicator"></span>
          <span>SYS.ONLINE // 100% PYTHON</span>
        </div>
      </a>
      <button class="hud-burger" id="hudBurger" aria-label="Abrir menú de navegación">
        <span></span><span></span><span></span>
      </button>
      <nav class="hud-nav" id="hudNav">
        <a href="#proyecto" class="hud-tab">Proyecto</a>
        <a href="#autora" class="hud-tab">Autora</a>
        <a href="#arquitectura" class="hud-tab">Arquitectura</a>
        <a href="#catalogo" class="hud-tab">Biblioteca ({len(games)})</a>
        <a href="#descarga" class="hud-tab hud-cta-download">DESCARGAR EMULADOR</a>
      </nav>
    </div>
  </header>

  <!-- Hero: Virtual Console Stage -->
  <section class="hero">
    <div class="container hero-layout">
      <div class="hero-left">
        <span class="telemetry-tag">// PROYECTO ACADÉMICO · ANALISTA DE SISTEMAS · 100% PYTHON</span>
        <h1 class="hero-headline">CONSOLA VIRTUAL RETRO &amp; <span>EMULADOR</span></h1>
        <p class="hero-lead">
          <strong>C.C.I. SYSTEM</strong> es una plataforma de investigación y desarrollo concebida por
          <strong>Camila Carolina Ianni</strong> en la carrera de <strong>Analista de Sistemas</strong> (Escuela Da Vinci).
          Unifica <strong>19 videojuegos arcade clásicos</strong> en una consola virtual integral con arquitectura de estados en Python puro,
          renderizado a 60 FPS, sistema multiusuario con gestión de estadísticas independientes,
          soporte de joystick plug &amp; play y capturador HD sin dependencias externas.
        </p>
        <div class="hero-actions">
          <a href="#descarga" class="btn-cci btn-primary-action">
            <span class="btn-gamepad-key">⌧ A</span> DESCARGAR EMULADOR
          </a>
          <a href="#catalogo" class="btn-cci btn-secondary-action">
            <span class="btn-gamepad-key">△ Y</span> VER BIBLIOTECA ({len(games)} JUEGOS)
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
            <video autoplay loop muted playsinline poster="/assets/welcome.png">
              <source src="/assets/video/CCI_INTRO.mp4" type="video/mp4">
              <img src="/assets/welcome.png" alt="Pantalla C.C.I. SYSTEM">
            </video>
            <div class="chassis-live-badge">
              <span class="blink-dot"></span> EN VIVO // 60 FPS
            </div>
          </div>
          <div class="chassis-footer">
            <span>MOTOR: PYGAME-CE // STATE_MACHINE</span>
            <span>PLATAFORMA: MAC &amp; WINDOWS</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Proyecto Académico & Preservación Digital -->
  <section id="proyecto" class="section section-dark">
    <div class="container">
      <span class="section-tag">// PROYECTO ACADÉMICO · PARCIAL 2</span>
      <h2 class="section-title">¿QUÉ ES C.C.I. SYSTEM Y POR QUÉ NACE?</h2>
      <p class="section-desc">
        C.C.I. SYSTEM surge como un proyecto académico para el <strong>Parcial 2</strong> en la carrera de
        <strong>Analista de Sistemas</strong> (<strong>Escuela Da Vinci</strong>), orientado a la preservación del patrimonio del videojuego retro
        y a la aplicación práctica de arquitectura de software determinista en Python.
      </p>

      <div class="academic-pillars-grid">
        <div class="academic-pillar-card">
          <div class="pillar-num">01</div>
          <h3 class="pillar-title">Demostración Académica en Python</h3>
          <p class="pillar-desc">
            Desafiar el mito de que Python es inadecuado para software interactivo de alta demanda temporal.
            El sistema demuestra que con diseño orientado a objetos riguroso, sincronización precisa de ciclos y
            gestión de memoria eficiente, es factible mantener 60 FPS estables, control de hilos y renderizado fluido sin recurrir a motores comerciales prediseñados.
          </p>
        </div>

        <div class="academic-pillar-card">
          <div class="pillar-num">02</div>
          <h3 class="pillar-title">Preservación Digital de Clásicos</h3>
          <p class="pillar-desc">
            Rescate y adaptación de 19 obras maestras del arcade (1978–2009). Cada título ha sido
            integrado respetando su identidad estética original (desde resoluciones nativas Neo-Geo 320x224 hasta 720p),
            incorporando soporte para mandos modernos con vibración háptica y controles configurables.
          </p>
        </div>

        <div class="academic-pillar-card">
          <div class="pillar-num">03</div>
          <h3 class="pillar-title">Aislamiento &amp; Máquina de Estados (FSM)</h3>
          <p class="pillar-desc">
            Resolución de colisiones de namespaces globales y recarga dinámica de módulos en tiempo de ejecución.
            Al cambiar de juego o volver al menú principal, el sandbox de C.C.I. SYSTEM limpia descriptores, restablece canales de audio y restaura el estado determinista sin fugas de memoria.
          </p>
        </div>

        <div class="academic-pillar-card">
          <div class="pillar-num">04</div>
          <h3 class="pillar-title">Filosofía de Distribución Limpia</h3>
          <p class="pillar-desc">
            Diseño centrado en la experiencia del usuario: instaladores nativos de 1-clic (.dmg en macOS y .exe en Windows),
            arranque de fábrica con <strong>0 perfiles precargados</strong> para que cada jugador inicie su partida desde cero, y una plataforma web cloud ligera desplegada de forma continua.
          </p>
        </div>
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
              <img src="{html.escape(author.get('avatar_url', '/assets/fotos_web/Cami.jpg'))}" alt="{html.escape(author.get('name',''))}">
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
            <div class="profile-actions-bar">
              <a href="{html.escape(author.get('github_url', 'https://github.com/Camila-Ianni/C.C.I-SYSTEM'))}" target="_blank" rel="noopener noreferrer" class="btn-profile-link">
                ⬡ REPOSITORIO GITHUB
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Subsystems / Architecture -->
  <section id="arquitectura" class="section section-dark">
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
            Flujo determinista desacoplado gestionado por máquina de estados (<code>StateMachine</code>):
            <code>INTRO_VIDEO</code> &rarr; <code>USER_SELECT</code> &rarr; <code>MENU</code> &rarr; <code>GAME_RUNNER</code>.
            Cero fugas de memoria y bucle de eventos a 60 FPS estables.
          </p>
        </div>

        <div class="subsystem-card">
          <span class="subsystem-code">// SUBSYSTEM_02: MULTI-USER</span>
          <h3 class="subsystem-title">Gestión de Perfiles Limpia</h3>
          <p class="subsystem-text">
            Arranque oficial con 0 perfiles de fábrica. Al iniciar por primera vez, el asistente
            te invita a crear tu usuario, elegir tu avatar y guardar estadísticas de forma aislada.
          </p>
        </div>

        <div class="subsystem-card">
          <span class="subsystem-code">// SUBSYSTEM_03: INPUT ENGINE</span>
          <h3 class="subsystem-title">Control Universal Plug &amp; Play</h3>
          <p class="subsystem-text">
            Mapeo universal con <code>pygame.joystick</code> para DualShock 4, DualSense (PS5), mandos Xbox Series/One
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

      <!-- Demostración en Video & Pipeline Técnico -->
      <div style="margin-top: 48px; background: var(--cci-bg-surface); border: 1px solid var(--cci-border-panel); border-radius: 24px; padding: 32px 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid var(--cci-border-panel); padding-bottom: 14px;">
          <div>
            <span class="subsystem-code">// DEMOSTRACIÓN TÉCNICA EN EJECUCIÓN // PYGAME-CE KERNEL</span>
            <h3 style="margin: 4px 0 0; font-family: var(--font-display); font-size: 1.35rem; color: #fff; letter-spacing: -0.2px;">DEMO EN VIVO: ORQUESTACIÓN A 60 FPS &amp; AISLAMIENTO DE MEMORIA</h3>
          </div>
          <span style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--cci-green); background: var(--cci-green-dim); border: 1px solid rgba(34,197,94,0.3); padding: 5px 14px; border-radius: 9999px;">60.0 FPS ESTABLES · 0 MEMORY LEAKS</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 28px; align-items: center;">
          <div style="border: 1px solid var(--cci-border-panel); border-radius: 20px; background: #000; box-shadow: 0 10px 30px rgba(0,0,0,0.6); overflow: hidden;">
            <video controls playsinline poster="/assets/welcome.png" style="width: 100%; display: block; aspect-ratio: 16/9; background: #000;">
              <source src="/assets/video/CCI_INTRO.mp4" type="video/mp4">
              Tu navegador no soporta reproducción de video HTML5.
            </video>
            <div style="padding: 12px 16px; background: rgba(13, 16, 23, 0.9); border-top: 1px solid var(--cci-border-panel); display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 0.72rem; color: var(--cci-muted);">
              <span>REPRODUCCIÓN DEMO // CAPTURA REAL DE CONSOLA</span>
              <span style="color: #fff;">RESOLUCIÓN: 1280x720 NATIVA</span>
            </div>
          </div>

          <div>
            <h4 style="font-family: var(--font-display); font-size: 1.1rem; color: #fff; margin: 0 0 12px; text-transform: uppercase;">PIPELINE DE PROCESAMIENTO DETERMINISTA</h4>
            <div style="font-family: var(--font-mono); font-size: 0.8rem; line-height: 1.7; color: var(--cci-light); background: rgba(10, 12, 17, 0.6); border: 1px solid var(--cci-border-dim); border-radius: 16px; padding: 18px;">
              <div style="color: #ffffff; font-weight: 700; margin-bottom: 6px;">[01] INICIALIZACIÓN DEL NÚCLEO</div>
              <div>▸ Pygame-CE Runtime (1280x720, VSync ON)</div>
              <div>▸ Asignación de canales estéreo &amp; sintetizador BGM</div>
              <div style="color: #ffffff; font-weight: 700; margin: 10px 0 6px;">[02] STATE MACHINE DETERMINISTA</div>
              <div>▸ INTRO_VIDEO → USER_SELECT → MENU → GAME</div>
              <div>▸ Reciclaje estricto de sprites y recolector de basura</div>
              <div style="color: #ffffff; font-weight: 700; margin: 10px 0 6px;">[03] PERSISTENCIA 100% LOCAL &amp; PRIVACIDAD</div>
              <div>▸ Almacenamiento seguro en disco local (.cci-user-data)</div>
              <div>▸ Partidas, logros y récords guardados en tu propia máquina</div>
              <div>▸ Sin cuentas en la nube ni telemetría: privacidad absoluta</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Games Catalog Section -->
  <section id="catalogo" class="section">
    <div class="container">
      <div class="catalog-header-bar">
        <div>
          <span class="section-tag">// CATÁLOGO DE VIDEOJUEGOS RETRO</span>
          <h2 class="section-title">BIBLIOTECA ({len(games)} JUEGOS)</h2>
          <p class="section-desc" style="margin-bottom: 0;">
            Cada título cuenta con adaptación precisa a 60 FPS, control analógico/digital y preservación de mecánicas originales.
          </p>
        </div>
      </div>

      <div class="filter-chips-rack">
        {filters_html}
      </div>

      <div class="games-rack-grid">
        {games_cards_html}
      </div>
    </div>
  </section>

  <!-- Downloads Section -->
  <section id="descarga" class="section section-dark">
    <div class="container">
      <div class="text-center" style="max-width: 720px; margin: 0 auto 30px; text-align: center;">
        <span class="section-tag">// HARDWARE RELEASES</span>
        <h2 class="section-title">DESCARGA DEL EMULADOR</h2>
        <p class="section-desc" style="margin: 0 auto;">
          Elige tu sistema operativo. Ambas descargas incluyen los 19 juegos, el asistente gráfico de 1-clic
          y <strong>0 perfiles precargados</strong> para que crees tu partida desde cero.
        </p>
      </div>

      <div class="downloads-panel-grid">
        <!-- macOS -->
        <div class="download-hardware-card">
          <div class="hw-icon-box">
            <svg class="os-svg" width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.37c.63-.77 1.06-1.85.94-2.93-.91.04-2.02.61-2.67 1.37-.58.67-.99 1.77-.85 2.83 1.02.08 2.05-.51 2.58-1.27z"/></svg>
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
            <span class="hw-hint">Abre el archivo .dmg y ejecuta C.C.I. SYSTEM</span>
          </div>
          <div class="mac-security-notice" style="margin-top: 18px; padding: 14px 16px; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--cci-border-dim); border-radius: 16px; font-size: 0.8rem; text-align: left; line-height: 1.45;">
            <div style="color: #ffffff; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
              <span>ⓘ</span> Primer inicio en macOS (Gatekeeper):
            </div>
            <div style="color: var(--cci-muted);">
              Al ser un emulador independiente, si macOS muestra verificación: haz <strong>Clic derecho (o Control + Clic)</strong> en <code style="color: #fff; background: rgba(255,255,255,0.08); padding: 1px 6px; border-radius: 4px;">C.C.I. SYSTEM</code> y selecciona <strong>«Abrir»</strong>. ¡Solo la primera vez!
            </div>
          </div>
        </div>

        <!-- Windows -->
        <div class="download-hardware-card">
          <div class="hw-icon-box">
            <svg class="os-svg" width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/></svg>
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
          <div class="win-security-notice" style="margin-top: 18px; padding: 14px 16px; background: rgba(255, 255, 255, 0.03); border: 1px solid var(--cci-border-dim); border-radius: 16px; font-size: 0.8rem; text-align: left; line-height: 1.45;">
            <div style="color: #ffffff; font-weight: 700; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
              <span>🛡️</span> Primer inicio en Windows (SmartScreen):
            </div>
            <div style="color: var(--cci-muted);">
              Si Windows SmartScreen advierte aplicación desconocida: haz clic en <strong>«Más información»</strong> y luego en <strong>«Ejecutar de todas formas»</strong>.
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
          <span style="color: #ffffff; font-weight: 700;" id="modalYear"></span>
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
        <span class="footer-logo">C.C.I. — SYSTEM —</span>
        <p class="footer-copy">
          Virtual Console &amp; Multiplatform Retro Emulator · Diseñado y desarrollado por <strong>Camila Carolina Ianni</strong>.
          <br>Arquitectura 100% Python puro con fines de preservación y divulgación académica (2026).
        </p>
      </div>
      <div class="footer-links">
        <a href="#proyecto">Proyecto</a>
        <a href="#arquitectura">Arquitectura</a>
        <a href="#catalogo">Biblioteca</a>
        <a href="#autora">Autora</a>
        <a href="#descarga">Descargas</a>
        <span class="footer-sep">·</span>
        <a href="{html.escape(author.get('github_url', 'https://github.com/Camila-Ianni/C.C.I-SYSTEM'))}" target="_blank" rel="noopener noreferrer">GitHub</a>
      </div>
    </div>
  </footer>

  <script>{CLIENT_JS}</script>
</body>
</html>"""
