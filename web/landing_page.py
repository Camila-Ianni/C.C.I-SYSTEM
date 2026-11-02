"""web/landing_page.py - Generador 100% Python de la Landing Page de C.C.I. SYSTEM.
Elimina la necesidad de archivos .html, .css y .js en disco: todo se genera dinámicamente
en memoria desde este módulo Python nativo.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import html

CYBER_CSS = """
:root {
  --bg-darkest: #05070a;
  --bg-dark: #0a0e15;
  --bg-card: #101622;
  --bg-card-hover: #162032;
  --border-dim: #1e293b;
  --border-bright: #334155;
  --accent-cyan: #00e5ff;
  --accent-cyan-glow: rgba(0, 229, 255, 0.25);
  --accent-green: #00ff88;
  --accent-green-glow: rgba(0, 255, 136, 0.25);
  --accent-yellow: #ffcf25;
  --accent-purple: #b347eb;
  --text-main: #f0f4f8;
  --text-muted: #8b9bb4;
  --text-dim: #5c6b84;
  --font-display: 'Orbitron', -apple-system, sans-serif;
  --font-ui: 'Rajdhani', -apple-system, sans-serif;
  --font-mono: 'Share Tech Mono', monospace;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 14px;
  --container-w: 1200px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html {
  scroll-behavior: smooth;
  background-color: var(--bg-darkest);
  color: var(--text-main);
  font-family: var(--font-ui);
  font-size: 16px;
  line-height: 1.5;
}

body {
  position: relative;
  overflow-x: hidden;
  background: radial-gradient(circle at 50% 0%, #0e1626 0%, var(--bg-darkest) 75%);
  min-height: 100vh;
}

.bg-grid {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background-image: 
    linear-gradient(to right, rgba(0, 229, 255, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(0, 229, 255, 0.03) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
  z-index: 0;
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
  z-index: 0;
}
.orb-1 {
  width: 450px; height: 450px;
  top: 100px; right: 5%;
  background: rgba(0, 229, 255, 0.08);
}
.orb-2 {
  width: 500px; height: 500px;
  top: 600px; left: -100px;
  background: rgba(179, 71, 235, 0.06);
}

.container {
  width: 100%;
  max-width: var(--container-w);
  margin: 0 auto;
  padding: 0 24px;
  position: relative;
  z-index: 1;
}

.header {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 72px;
  background: rgba(10, 14, 21, 0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-dim);
  z-index: 100;
  display: flex;
  align-items: center;
}

.nav-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
}

.brand-glitch {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: 2px;
  text-shadow: 0 0 12px var(--accent-cyan);
}

.brand-sub {
  font-family: var(--font-display);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--accent-cyan);
  letter-spacing: 3px;
}

.badge-v {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: rgba(0, 229, 255, 0.15);
  color: var(--accent-cyan);
  border: 1px solid var(--accent-cyan);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.nav-menu {
  display: flex;
  align-items: center;
  gap: 28px;
}

.nav-link {
  font-family: var(--font-ui);
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.25s ease;
  position: relative;
}

.nav-link:hover, .nav-link.active {
  color: #fff;
}

.nav-link.nav-cta {
  background: rgba(0, 229, 255, 0.1);
  border: 1px solid var(--accent-cyan);
  color: var(--accent-cyan);
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-family: var(--font-display);
  letter-spacing: 1.5px;
}
.nav-link.nav-cta:hover {
  background: var(--accent-cyan);
  color: #000;
  box-shadow: 0 0 16px var(--accent-cyan-glow);
}

.nav-badge-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  background: #111724;
  border: 1px solid var(--border-bright);
  padding: 5px 12px;
  border-radius: 20px;
  color: var(--accent-green);
}

.status-dot {
  width: 7px; height: 7px;
  background: var(--accent-green);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--accent-green);
  animation: pulse-dot 2s infinite ease-in-out;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.hero {
  padding: 140px 0 80px;
  min-height: 88vh;
  display: flex;
  align-items: center;
}

.hero-grid {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 48px;
  align-items: center;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  background: rgba(0, 229, 255, 0.08);
  border: 1px solid rgba(0, 229, 255, 0.3);
  color: var(--accent-cyan);
  padding: 6px 14px;
  border-radius: 20px;
  margin-bottom: 20px;
  letter-spacing: 1px;
}

.hero-title {
  font-family: var(--font-display);
  font-size: 2.75rem;
  font-weight: 900;
  line-height: 1.15;
  letter-spacing: -0.5px;
  margin-bottom: 20px;
  background: linear-gradient(135deg, #ffffff 40%, #b0c6e4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero-desc {
  font-size: 1.2rem;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 32px;
}
.hero-desc strong {
  color: #fff;
}

.hero-actions {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 40px;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 14px 28px;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: all 0.25s ease;
  cursor: pointer;
}

.btn-primary {
  background: linear-gradient(135deg, #00e5ff 0%, #0099cc 100%);
  color: #040810;
  border: none;
  box-shadow: 0 4px 20px var(--accent-cyan-glow);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(0, 229, 255, 0.45);
  color: #000;
}

.btn-secondary {
  background: #121824;
  color: #fff;
  border: 1px solid var(--border-bright);
}
.btn-secondary:hover {
  border-color: var(--accent-cyan);
  background: #182234;
  color: var(--accent-cyan);
  transform: translateY(-2px);
}

.btn-block {
  width: 100%;
}

.hero-features-strip {
  display: flex;
  align-items: center;
  gap: 24px;
  background: rgba(16, 22, 34, 0.7);
  border: 1px solid var(--border-dim);
  padding: 16px 24px;
  border-radius: var(--radius-md);
  max-width: 580px;
}

.strip-item {
  display: flex;
  flex-direction: column;
}

.strip-num {
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--accent-cyan);
}

.strip-lbl {
  font-size: 0.8rem;
  color: var(--text-dim);
  font-family: var(--font-mono);
}

.strip-divider {
  width: 1px;
  height: 32px;
  background: var(--border-dim);
}

.console-frame {
  background: #090d14;
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 229, 255, 0.08);
  overflow: hidden;
}

.frame-header {
  height: 36px;
  background: #111722;
  border-bottom: 1px solid var(--border-dim);
  display: flex;
  align-items: center;
  padding: 0 14px;
  gap: 8px;
}

.dot {
  width: 10px; height: 10px;
  border-radius: 50%;
}
.dot.red { background: #ff5f56; }
.dot.yellow { background: #ffbd2e; }
.dot.green { background: #27c93f; }

.frame-title {
  margin-left: 8px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-dim);
  letter-spacing: 1px;
}

.frame-body {
  position: relative;
  background: #000;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.console-screen-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.screen-overlay-scanline {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%);
  background-size: 100% 4px;
  pointer-events: none;
}

.screen-badge {
  position: absolute;
  top: 12px; right: 12px;
  background: rgba(0, 0, 0, 0.8);
  border: 1px solid var(--accent-green);
  color: var(--accent-green);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  letter-spacing: 1px;
}

.frame-footer {
  background: #0c111a;
  border-top: 1px solid var(--border-dim);
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--text-dim);
}

.section {
  padding: 90px 0;
  position: relative;
  z-index: 1;
}

.section-dark {
  background: rgba(7, 10, 16, 0.65);
  border-top: 1px solid var(--border-dim);
  border-bottom: 1px solid var(--border-dim);
}

.section-header {
  margin-bottom: 50px;
}
.section-header.text-center {
  text-align: center;
  max-width: 720px;
  margin-left: auto;
  margin-right: auto;
}

.section-tag {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--accent-cyan);
  letter-spacing: 2px;
  margin-bottom: 10px;
}

.section-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

.section-desc {
  font-size: 1.15rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 24px;
}

.feature-card {
  background: var(--bg-card);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  padding: 32px 28px;
  transition: all 0.3s ease;
}
.feature-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--accent-cyan);
  transform: translateY(-4px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.feature-icon {
  font-size: 2.4rem;
  margin-bottom: 18px;
}

.feature-title {
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 12px;
}

.feature-text {
  font-size: 1rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.filters-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 24px;
}

.filter-btn {
  background: #111724;
  border: 1px solid var(--border-dim);
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  letter-spacing: 1px;
  transition: all 0.2s ease;
}
.filter-btn:hover {
  background: #182236;
  color: #fff;
  border-color: var(--border-bright);
}
.filter-btn.active {
  background: var(--accent-cyan);
  color: #040810;
  border-color: var(--accent-cyan);
  font-weight: 700;
  box-shadow: 0 0 12px var(--accent-cyan-glow);
}

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  margin-top: 36px;
}

.game-card {
  background: var(--bg-card);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  display: flex;
  flex-direction: column;
  cursor: pointer;
}
.game-card:hover {
  transform: translateY(-5px);
  border-color: var(--accent-cyan);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.7), 0 0 16px rgba(0, 229, 255, 0.15);
}

.game-card-art {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}
.game-card-art img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}
.game-card:hover .game-card-art img {
  transform: scale(1.05);
}

.game-card-hover-overlay {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 229, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.game-card:hover .game-card-hover-overlay {
  opacity: 1;
}

.hover-btn {
  background: #000;
  color: var(--accent-cyan);
  border: 1px solid var(--accent-cyan);
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  letter-spacing: 1px;
}

.game-card-info {
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.game-card-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.game-badge-year {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--accent-yellow);
}
.game-badge-players {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--text-dim);
}

.game-title {
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.game-subtitle {
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: 12px;
  flex-grow: 1;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.game-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.game-tag {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
}

.author-box {
  background: linear-gradient(145deg, #111724 0%, #0c101a 100%);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 50px 48px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.author-badge-top {
  position: absolute;
  top: 0; right: 48px;
  background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
  color: #040810;
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 800;
  padding: 4px 16px;
  border-bottom-left-radius: var(--radius-md);
  border-bottom-right-radius: var(--radius-md);
  letter-spacing: 1.5px;
}

.author-content-grid {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 40px;
  align-items: flex-start;
}

.author-avatar-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.author-avatar-circle {
  width: 140px; height: 140px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border: 3px solid var(--accent-cyan);
  box-shadow: 0 0 24px var(--accent-cyan-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.avatar-silhouette {
  width: 100%; height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle, #1a2538 30%, #0a0f19 90%);
}

.author-initials {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 900;
  color: var(--accent-cyan);
  letter-spacing: 2px;
}

.author-title-pill {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  background: #192233;
  color: var(--text-muted);
  border: 1px solid var(--border-bright);
  padding: 3px 12px;
  border-radius: 20px;
  letter-spacing: 1px;
}

.author-name {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 900;
  letter-spacing: 1px;
  color: #fff;
  margin-bottom: 4px;
}

.author-institution {
  font-family: var(--font-mono);
  font-size: 0.95rem;
  color: var(--accent-cyan);
  margin-bottom: 20px;
}

.author-bio {
  font-size: 1.1rem;
  color: var(--text-muted);
  line-height: 1.7;
  margin-bottom: 28px;
}

.author-highlights {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.highlight-item {
  display: flex;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  padding: 14px 16px;
  border-radius: var(--radius-sm);
}

.hl-icon {
  font-size: 1.2rem;
}

.highlight-item strong {
  display: block;
  font-size: 0.95rem;
  color: #fff;
  margin-bottom: 2px;
}
.highlight-item span {
  font-size: 0.85rem;
  color: var(--text-dim);
}

.download-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 32px;
  margin-bottom: 48px;
}

.download-card {
  background: var(--bg-card);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  position: relative;
}
.download-card:hover {
  border-color: var(--accent-cyan);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.7);
  transform: translateY(-4px);
}

.os-icon-wrap {
  width: 56px; height: 56px;
  background: #162030;
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.os-svg {
  width: 32px !important;
  height: 32px !important;
  max-width: 32px !important;
  max-height: 32px !important;
  color: var(--accent-cyan);
}

.download-os-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  font-weight: 800;
  color: #fff;
  margin-bottom: 6px;
}

.download-os-sub {
  font-size: 0.95rem;
  color: var(--text-dim);
  margin-bottom: 24px;
}

.download-specs {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 32px;
  flex-grow: 1;
}

.download-specs li {
  font-size: 0.95rem;
  color: var(--text-muted);
}
.download-specs code {
  font-family: var(--font-mono);
  background: #182234;
  color: var(--accent-green);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}

.download-hint {
  display: block;
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-dim);
  margin-top: 12px;
  font-family: var(--font-mono);
}

.steps-card {
  background: rgba(16, 22, 34, 0.5);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  padding: 32px 36px;
}

.steps-title {
  font-family: var(--font-display);
  font-size: 1.05rem;
  letter-spacing: 1.5px;
  color: var(--accent-cyan);
  margin-bottom: 24px;
  text-align: center;
}

.steps-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 28px;
}

.step-item {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.step-num {
  width: 36px; height: 36px;
  background: var(--accent-cyan);
  color: #040810;
  font-family: var(--font-display);
  font-weight: 900;
  font-size: 1.1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-desc {
  font-size: 0.95rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(8px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-dialog {
  background: #0d121c;
  border: 1px solid var(--accent-cyan);
  box-shadow: 0 0 40px var(--accent-cyan-glow);
  border-radius: var(--radius-lg);
  max-width: 680px;
  width: 100%;
  overflow: hidden;
  position: relative;
  animation: modal-pop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-pop {
  from { opacity: 0; transform: scale(0.92); }
  to { opacity: 1; transform: scale(1); }
}

.modal-close {
  position: absolute;
  top: 14px; right: 16px;
  background: rgba(0, 0, 0, 0.6);
  border: 1px solid var(--border-bright);
  color: #fff;
  width: 34px; height: 34px;
  border-radius: 50%;
  font-size: 1.4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 2;
  transition: all 0.2s ease;
}
.modal-close:hover {
  background: var(--accent-cyan);
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
}

.modal-info-box {
  padding: 24px 28px;
}

.modal-tags-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.modal-title {
  font-family: var(--font-display);
  font-size: 1.7rem;
  font-weight: 800;
  color: #fff;
  margin-bottom: 4px;
}

.modal-dev {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--accent-cyan);
  margin-bottom: 14px;
}

.modal-desc {
  font-size: 1.05rem;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 20px;
}

.modal-launch-note {
  background: rgba(0, 255, 136, 0.08);
  border: 1px solid var(--accent-green);
  color: var(--accent-green);
  font-family: var(--font-mono);
  font-size: 0.8rem;
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  text-align: center;
}

.footer {
  background: #06080d;
  border-top: 1px solid var(--border-dim);
  padding: 48px 0;
  color: var(--text-dim);
  position: relative;
  z-index: 1;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
}

.footer-left {
  max-width: 580px;
}

.footer-logo {
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: 2px;
  display: block;
  margin-bottom: 8px;
}

.footer-copy {
  font-size: 0.85rem;
  line-height: 1.5;
}
.footer-copy strong {
  color: var(--text-muted);
}

.footer-right {
  display: flex;
  gap: 20px;
}

.footer-right a {
  color: var(--text-muted);
  text-decoration: none;
  font-size: 0.9rem;
  transition: color 0.2s ease;
}
.footer-right a:hover {
  color: var(--accent-cyan);
}

@media (max-width: 992px) {
  .hero-grid { grid-template-columns: 1fr; gap: 40px; }
  .author-content-grid { grid-template-columns: 1fr; text-align: center; justify-items: center; }
  .author-badge-top { right: 50%; transform: translateX(50%); }
}

@media (max-width: 768px) {
  .nav-menu { display: none; }
  .hero-title { font-size: 2.1rem; }
  .section-title { font-size: 1.8rem; }
  .footer-content { flex-direction: column; text-align: center; }
}
"""

CLIENT_JS = """
document.addEventListener('DOMContentLoaded', () => {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const gameCards = document.querySelectorAll('.game-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const selectedCat = (btn.dataset.cat || '').toUpperCase();

      gameCards.forEach(card => {
        const cardCats = (card.dataset.categories || '').toUpperCase().split(' ');
        if (selectedCat === 'TODOS' || cardCats.includes(selectedCat)) {
          card.style.display = 'flex';
          card.style.animation = 'fadeIn 0.3s ease';
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
    tags_html = "".join(f'<span class="game-tag">{html.escape(t)}</span>' for t in g.get("tags", []))
    return f"""
    <div class="game-card" data-categories="{html.escape(cats_str)}" data-title="{html.escape(g.get('title',''))}" data-genre="{html.escape(g.get('genre',''))}" data-dev="{html.escape(g.get('developer',''))}" data-year="{html.escape(str(g.get('year','')))}" data-players="{html.escape(str(g.get('players','')))}" data-desc="{html.escape(g.get('subtitle',''))}">
      <div class="game-card-art">
        <img src="{html.escape(g.get('card_url',''))}" alt="{html.escape(g.get('title',''))}" loading="lazy">
        <div class="game-card-hover-overlay">
          <span class="hover-btn">VER FICHA</span>
        </div>
      </div>
      <div class="game-card-info">
        <div class="game-card-meta">
          <span class="game-badge-year">{html.escape(str(g.get('year','')))}</span>
          <span class="game-badge-players">{html.escape(str(g.get('players','')))} JUGADORES</span>
        </div>
        <h3 class="game-title">{html.escape(g.get("title",""))}</h3>
        <p class="game-subtitle">{html.escape(g.get("subtitle",""))}</p>
        <div class="game-tags">
          {tags_html}
        </div>
      </div>
    </div>
    """


def build_landing_page(games: list[dict], categories: list[str], author: dict, stats: dict) -> str:
    """Construye y retorna el documento HTML completo generado al 100% en Python."""
    filters_html = "".join(
        f'<button class="filter-btn {"active" if cat == "TODOS" else ""}" data-cat="{html.escape(cat)}">{html.escape(cat)}</button>'
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
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@600;700;800;900&family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/css/style.css">
  <link rel="stylesheet" href="/style.css">
  <style>
{CYBER_CSS}
  </style>
</head>
<body>
  <div class="bg-grid"></div>
  <div class="glow-orb orb-1"></div>
  <div class="glow-orb orb-2"></div>

  <!-- Header -->
  <header class="header">
    <div class="container nav-container">
      <a href="#" class="brand">
        <span class="brand-glitch">C.C.I.</span>
        <span class="brand-sub">SYSTEM</span>
        <span class="badge-v">EMULATOR v1.0</span>
      </a>
      <nav class="nav-menu">
        <a href="#arquitectura" class="nav-link">Arquitectura</a>
        <a href="#juegos" class="nav-link">Juegos ({len(games)})</a>
        <a href="#autora" class="nav-link">Autora</a>
        <a href="#descarga" class="nav-link nav-cta">DESCARGAR</a>
      </nav>
      <div class="nav-badge-pill">
        <span class="status-dot"></span>
        <span>100% PYTHON NATIVO</span>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="hero">
    <div class="container hero-grid">
      <div class="hero-content">
        <span class="hero-tag">CONSOLA VIRTUAL RETRO · ARQUITECTURA PYTHON PURA</span>
        <h1 class="hero-title">EXPERIENCIA ARCADE RETROFUTURISTA</h1>
        <p class="hero-desc">
          <strong>C.C.I. SYSTEM</strong> es una suite emuladora que integra <strong>19 videojuegos arcade legendarios</strong>
          en una interfaz de consola con estética Cyberpunk / PS5, sistema multiusuario con perfiles independientes,
          soporte de gamepad universal y capturador en alta fidelidad.
        </p>
        <div class="hero-actions">
          <a href="#descarga" class="btn btn-primary">
            DESCARGAR EMULADOR
          </a>
          <a href="#juegos" class="btn btn-secondary">
            VER CATÁLOGO ({len(games)} JUEGOS)
          </a>
        </div>
        <div class="hero-features-strip">
          <div class="strip-item">
            <span class="strip-num">{len(games)}</span>
            <span class="strip-lbl">Juegos Integrados</span>
          </div>
          <div class="strip-divider"></div>
          <div class="strip-item">
            <span class="strip-num">0</span>
            <span class="strip-lbl">Perfiles de Fábrica</span>
          </div>
          <div class="strip-divider"></div>
          <div class="strip-item">
            <span class="strip-num">100%</span>
            <span class="strip-lbl">Python Puro</span>
          </div>
        </div>
      </div>

      <div class="hero-visual">
        <div class="console-frame">
          <div class="frame-header">
            <span class="dot red"></span>
            <span class="dot yellow"></span>
            <span class="dot green"></span>
            <span class="frame-title">CCI_SYSTEM_VIRTUAL_CONSOLE_CORE</span>
          </div>
          <div class="frame-body">
            <img src="/assets/pantallas/Bienvenida al sistema C.C.I.png" alt="C.C.I. SYSTEM Virtual Console" class="console-screen-img">
            <div class="screen-overlay-scanline"></div>
            <div class="screen-badge">1280x720 60FPS</div>
          </div>
          <div class="frame-footer">
            <span>PLATAFORMA: MAC &amp; WINDOWS</span>
            <span>MOTOR: PYGAME-CE CORE</span>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Architecture Section -->
  <section id="arquitectura" class="section">
    <div class="container">
      <div class="section-header text-center">
        <span class="section-tag">CARACTERÍSTICAS TÉCNICAS</span>
        <h2 class="section-title">INGENIERÍA &amp; DISEÑO DE LA CONSOLA</h2>
        <p class="section-desc">
          Construida desde cero con estándares de arquitectura orientada a estados y emulación modular en Python.
        </p>
      </div>

      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon">⚡</div>
          <h3 class="feature-title">Motor 100% Python</h3>
          <p class="feature-text">
            Sin dependencias binarias externas ni shells. Toda la suite se ejecuta de forma nativa a través
            del motor de renderizado Pygame-CE con ciclo de eventos a 60 FPS estables.
          </p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">👤</div>
          <h3 class="feature-title">Perfiles &amp; Multiusuario</h3>
          <p class="feature-text">
            Descarga limpia con 0 perfiles. Al abrir la consola por primera vez, el asistente te invita a crear
            tu propio perfil personal con avatar Cyberpunk y registro individual de logros y estadísticas.
          </p>
        </div>
        <div class="feature-card">
          <div class="feature-icon">🎮</div>
          <h3 class="feature-title">Control Universal Plug &amp; Play</h3>
          <p class="feature-text">
            Compatibilidad total con mandos de PS4, PS5, Xbox Series/One y joysticks USB genéricos, con vibración
            háptica configurable y navegación total por joystick y cruceta D-Pad.
          </p>
        </div>
      </div>
    </div>
  </section>

  <!-- Games Catalog Section -->
  <section id="juegos" class="section section-dark">
    <div class="container">
      <div class="section-header">
        <span class="section-tag">CATÁLOGO OFICIAL</span>
        <h2 class="section-title">{len(games)} JUEGOS DISPONIBLES</h2>
        <p class="section-desc">
          Filtra por categoría para explorar cada aventura:
        </p>
        <div class="filters-bar" id="filtersBar">
          {filters_html}
        </div>
      </div>

      <div class="games-grid" id="gamesGrid">
        {games_cards_html}
      </div>
    </div>
  </section>

  <!-- Author Section -->
  <section id="autora" class="section">
    <div class="container">
      <div class="author-box">
        <div class="author-badge-top">AUTORA &amp; CREADORA DEL PROYECTO</div>
        <div class="author-content-grid">
          <div class="author-avatar-wrap">
            <div class="author-avatar-circle">
              <div class="avatar-silhouette">
                <span class="author-initials">CCI</span>
              </div>
            </div>
            <div class="author-title-pill">DESARROLLADORA</div>
          </div>
          <div class="author-details">
            <h2 class="author-name">{html.escape(author.get("name",""))}</h2>
            <p class="author-institution">{html.escape(author.get("institution",""))} · {html.escape(author.get("year",""))}</p>
            <p class="author-bio">{html.escape(author.get("bio",""))}</p>
            <div class="author-highlights">
              <div class="highlight-item">
                <span class="hl-icon">🐍</span>
                <div>
                  <strong>Desarrollo 100% Python:</strong>
                  <span>Arquitectura de estados finitos, orquestación de subprocesos y virtualización.</span>
                </div>
              </div>
              <div class="highlight-item">
                <span class="hl-icon">🕹️</span>
                <div>
                  <strong>Preservación Retro:</strong>
                  <span>Recreación fidedigna con controles modernos y balance pulido.</span>
                </div>
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
      <div class="section-header text-center">
        <span class="section-tag">INSTALACIÓN &amp; DESCARGA</span>
        <h2 class="section-title">DESCARGA C.C.I. SYSTEM EMULADOR</h2>
        <p class="section-desc">
          Elige tu sistema operativo. Ambas versiones vienen con los 19 juegos, instalador gráfico 1-clic
          y <strong>0 perfiles precargados</strong> para arrancar desde cero.
        </p>
      </div>

      <div class="download-grid">
        <!-- macOS -->
        <div class="download-card">
          <div class="os-icon-wrap">
            <svg class="os-svg" width="32" height="32" style="width:32px;height:32px;max-width:32px;max-height:32px;" viewBox="0 0 24 24" fill="currentColor"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.37c.63-.77 1.06-1.85.94-2.93-.91.04-2.02.61-2.67 1.37-.58.67-.99 1.77-.85 2.83 1.02.08 2.05-.51 2.58-1.27z"/></svg>
          </div>
          <h3 class="download-os-title">C.C.I. SYSTEM para macOS</h3>
          <p class="download-os-sub">Compatible con Apple Silicon (M1/M2/M3/M4) e Intel (macOS 12+)</p>
          <ul class="download-specs">
            <li>✔ Código 100% Python nativo multiplataforma</li>
            <li>✔ Instalador gráfico interactivo de 1-clic</li>
            <li>✔ Asistente pop-up de instalación (Escritorio por defecto)</li>
            <li>✔ 0 perfiles de fábrica (asistente de bienvenida en primer boot)</li>
          </ul>
          <a href="/download/mac" class="btn btn-primary btn-block">DESCARGAR EMULADOR MAC</a>
          <span class="download-hint">Descomprime y ejecuta el instalador gráfico</span>
        </div>

        <!-- Windows -->
        <div class="download-card">
          <div class="os-icon-wrap">
            <svg class="os-svg" width="32" height="32" style="width:32px;height:32px;max-width:32px;max-height:32px;" viewBox="0 0 24 24" fill="currentColor"><path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/></svg>
          </div>
          <h3 class="download-os-title">C.C.I. SYSTEM para Windows</h3>
          <p class="download-os-sub">Compatible con Windows 10 y Windows 11 (100% Python)</p>
          <ul class="download-specs">
            <li>✔ Código 100% Python nativo multiplataforma</li>
            <li>✔ Instalador gráfico directo sin ventana de terminal</li>
            <li>✔ Asistente pop-up con ubicación por defecto en tu Escritorio</li>
            <li>✔ 0 perfiles de fábrica (crea tu jugador al instante)</li>
          </ul>
          <a href="/download/windows" class="btn btn-secondary btn-block">DESCARGAR EMULADOR WINDOWS</a>
          <span class="download-hint">Descomprime y ejecuta el instalador gráfico</span>
        </div>
      </div>

      <div class="steps-card">
        <h4 class="steps-title">EXPERIENCIA DE INSTALACIÓN DE EMULADOR REAL</h4>
        <div class="steps-row">
          <div class="step-item">
            <div class="step-num">1</div>
            <div class="step-desc"><strong>Descarga el emulador</strong> para tu sistema operativo (Mac o Windows).</div>
          </div>
          <div class="step-item">
            <div class="step-num">2</div>
            <div class="step-desc"><strong>Abre el instalador:</strong> un asistente emergente te preguntará dónde ubicar tu consola (por defecto en tu Escritorio).</div>
          </div>
          <div class="step-item">
            <div class="step-num">3</div>
            <div class="step-desc"><strong>¡Listo para jugar!</strong> Se crea tu acceso directo y la consola se abre de inmediato. Crea tu nuevo jugador desde cero y disfruta.</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Modal -->
  <div class="modal-backdrop" id="gameModal" style="display: none;">
    <div class="modal-dialog">
      <button class="modal-close" id="modalClose">&times;</button>
      <div class="modal-art-box">
        <img src="" id="modalImg" alt="Juego">
      </div>
      <div class="modal-info-box">
        <div class="modal-tags-row">
          <span class="game-badge-year" id="modalYear"></span>
          <span class="game-badge-players" id="modalPlayers"></span>
        </div>
        <h2 class="modal-title" id="modalTitle"></h2>
        <p class="modal-dev" id="modalDev"></p>
        <p class="modal-desc" id="modalDesc"></p>
        <div class="modal-launch-note">Disponible en la suite C.C.I. SYSTEM</div>
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
          <br>Arquitectura 100% Python puro con fines de preservación y divulgación académica.
        </p>
      </div>
      <div class="footer-right">
        <a href="#arquitectura">Arquitectura</a>
        <a href="#juegos">Juegos</a>
        <a href="#autora">Autora</a>
        <a href="#descarga">Descargas</a>
      </div>
    </div>
  </footer>

  <script>{CLIENT_JS}</script>
</body>
</html>"""
