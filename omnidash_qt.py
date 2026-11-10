"""omnidash_qt.py - Consola Virtual C.C.I. SYSTEM en PySide6 (Frutiger Aero).
Arquitectura moderna desacoplada de Pygame:
- Renderizado acelerado por hardware con Qt Quick / PySide6.
- Cristal acrílico Frutiger Aero (Backdrop Blur, gradiente aguamarina, reflejos especulares).
- Iconos vectoriales Microsoft Fluent / Lucide.
- Integración 100% nativa con C.C.I. (CATALOG, CommunitiesService, UserManager, LibretroRunner).
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import (
    Qt, QSize, QTimer, QRectF, QPropertyAnimation, QEasingCurve, Signal, Slot, QPoint
)
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QLinearGradient, QBrush, QPen, QImage
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QScrollArea, QGridLayout, QFrame, QSizePolicy,
    QProgressBar, QSlider, QFileDialog
)

from cci_console import CATALOG, UserData
from cci_users import UserManager
from retro_core_runner import LibretroRunner
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from omnidash_screens import ALL_GAMES

ROOT = Path(__file__).resolve().parent

# Estado global de fondo óptico desenfocado y detección de tonalidad
GLOBAL_BLURRED_BG: QPixmap | None = None
WALLPAPER_IS_DARK: bool = True


def update_global_blurred_wallpaper(path: str | Path, target_size: tuple[int, int] = (1280, 720)):
    """Calcula el desenfoque óptico del fondo (Backdrop Blur) y detecta si es oscuro o claro."""
    global GLOBAL_BLURRED_BG, WALLPAPER_IS_DARK
    p = Path(path).resolve()
    if not p.exists():
        return

    from PIL import Image, ImageFilter, ImageStat
    try:
        pil_img = Image.open(str(p)).convert("RGB")
        stat = ImageStat.Stat(pil_img)
        avg_r, avg_g, avg_b = stat.mean[:3]
        lum = 0.299 * avg_r + 0.587 * avg_g + 0.114 * avg_b
        WALLPAPER_IS_DARK = (lum < 100)

        tw, th = max(100, target_size[0]), max(100, target_size[1])
        pil_blurred = pil_img.resize((tw, th)).filter(ImageFilter.GaussianBlur(radius=26))
        raw_bytes = pil_blurred.tobytes("raw", "RGB")
        qimg = QImage(raw_bytes, tw, th, tw * 3, QImage.Format_RGB888)
        GLOBAL_BLURRED_BG = QPixmap.fromImage(qimg)
    except Exception as err:
        print(f"[OmniDash-Qt] Error actualizando desenfoque de fondo: {err}")


def get_rounded_pixmap(pix: QPixmap, w: int, h: int, radius: int = 10) -> QPixmap:
    """Recorta una imagen con bordes redondeados y escalado de alta calidad (HiDPI) sin deformar."""
    if not pix or pix.isNull():
        return QPixmap()
    target = QPixmap(w, h)
    target.fill(Qt.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.setClipPath(path)
    scaled = pix.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    sx = max(0, (scaled.width() - w) // 2)
    sy = max(0, (scaled.height() - h) // 2)
    painter.drawPixmap(0, 0, scaled, sx, sy, w, h)
    painter.end()
    return target


# ==============================================================================
# ESTILOS FRUTIGER AERO GLOBALES (QSS)
# ==============================================================================
AERO_STYLE_SHEET = """
QWidget {
    font-family: "Helvetica Neue", Arial, sans-serif;
    color: #ffffff;
}

/* ScrollBar de Cristal */
QScrollBar:vertical {
    border: none;
    background: rgba(0, 0, 0, 45);
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 130);
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 210);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Buscador de cristal adaptativo */
QLineEdit#searchBox {
    background: rgba(0, 0, 0, 85);
    border: 1px solid rgba(255, 255, 255, 120);
    border-radius: 16px;
    padding: 6px 14px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: rgba(255, 255, 255, 60);
}
QLineEdit#searchBox:focus {
    border: 1.5px solid rgba(255, 255, 255, 230);
    background: rgba(0, 0, 0, 130);
}

/* Botones genéricos de cristal adaptativo */
QPushButton.glassBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 65),
        stop:0.45 rgba(255, 255, 255, 25),
        stop:1 rgba(0, 0, 0, 75));
    border: 1px solid rgba(255, 255, 255, 135);
    border-radius: 14px;
    padding: 6px 16px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
}
QPushButton.glassBtn:hover {
    border: 1.5px solid rgba(255, 255, 255, 240);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 115),
        stop:0.45 rgba(255, 255, 255, 55),
        stop:1 rgba(0, 0, 0, 95));
}

/* Botón Gel de Inicio Adaptativo */
QPushButton.playGelBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 160),
        stop:0.4 rgba(210, 225, 240, 110),
        stop:1 rgba(30, 40, 55, 220));
    border: 1.5px solid rgba(255, 255, 255, 210);
    border-radius: 14px;
    padding: 10px 24px;
    color: #ffffff;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton.playGelBtn:hover {
    border: 2px solid #ffffff;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(255, 255, 255, 215),
        stop:0.4 rgba(230, 240, 250, 150),
        stop:1 rgba(45, 60, 80, 240));
}
"""


# ==============================================================================
# COMPONENTE DE TARJETA ACRÍLICA ADAPTATIVA AL FONDO
# ==============================================================================
class AcrylicGlassCard(QFrame):
    """Panel contenedor con desenfoque óptico adaptativo:
    - Muestra el desenfoque real del fondo detrás del widget (Backdrop Blur).
    - Si el fondo es negro -> se vuelve ahumado oscuro con brillo blanco.
    - Si el fondo es celeste -> se vuelve celeste con reflejos aguamarina.
    - Borde adaptativo: blanco de cristal iluminado en fondos oscuros (o celeste hielo en claros).
    """
    def __init__(self, parent=None, border_radius=14, is_interactive=False):
        super().__init__(parent)
        self.border_radius = border_radius
        self.is_interactive = is_interactive
        self.is_hovered = False
        self.is_focused = False
        self.setAttribute(Qt.WA_Hover, is_interactive)

    def set_focused(self, focused: bool):
        if self.is_focused != focused:
            self.is_focused = focused
            self.update()

    def enterEvent(self, event):
        if self.is_interactive:
            self.is_hovered = True
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_interactive:
            self.is_hovered = False
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, w - 1, h - 1, self.border_radius, self.border_radius)

        painter.save()
        painter.setClipPath(path)

        # 1. Desenfoque óptico del fondo de pantalla detrás del widget
        drawn_blur = False
        if GLOBAL_BLURRED_BG and not GLOBAL_BLURRED_BG.isNull():
            try:
                win = self.window()
                pt = self.mapTo(win, QPoint(0, 0))
                gx, gy = pt.x(), pt.y()

                bw, bh = GLOBAL_BLURRED_BG.width(), GLOBAL_BLURRED_BG.height()
                rx = max(0, min(gx, max(0, bw - 1)))
                ry = max(0, min(gy, max(0, bh - 1)))
                rw = max(1, min(w, bw - rx))
                rh = max(1, min(h, bh - ry))
                patch = GLOBAL_BLURRED_BG.copy(rx, ry, rw, rh)
                if not patch.isNull():
                    painter.drawPixmap(0, 0, w, h, patch)
                    drawn_blur = True
            except Exception:
                pass

        active = self.is_hovered or self.is_focused

        # 2. Capa translúcida adaptativa según el brillo del fondo
        if not drawn_blur:
            fallback_col = QColor(18, 22, 30, 220) if WALLPAPER_IS_DARK else QColor(10, 55, 95, 210)
            painter.fillRect(0, 0, w, h, fallback_col)

        if WALLPAPER_IS_DARK:
            # Fondo oscuro: cristal ahumado con destello blanco
            dark_film = QColor(0, 0, 0, 90 if active else 130)
            white_sheen = QColor(255, 255, 255, 45 if active else 18)
            painter.fillRect(0, 0, w, h, dark_film)
            painter.fillRect(0, 0, w, h, white_sheen)
        else:
            # Fondo claro/marino: tinte aguamarina suave
            aqua_film = QColor(8, 48, 85, 95 if active else 135)
            aqua_sheen = QColor(255, 255, 255, 60 if active else 30)
            painter.fillRect(0, 0, w, h, aqua_film)
            painter.fillRect(0, 0, w, h, aqua_sheen)

        # 3. Brillo gel especular superior
        spec_h = int(h * 0.42)
        if spec_h > 10:
            spec_grad = QLinearGradient(0, 0, 0, spec_h)
            spec_grad.setColorAt(0.0, QColor(255, 255, 255, 75 if active else 45))
            spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.fillRect(0, 0, w, spec_h, QBrush(spec_grad))

        # 4. Línea de brillo inset superior
        painter.setPen(QColor(255, 255, 255, 160))
        painter.drawLine(self.border_radius, 1, w - self.border_radius, 1)

        painter.restore()

        # 5. Borde exterior adaptativo (Sin bordes verdes discordantes)
        if active:
            if WALLPAPER_IS_DARK:
                painter.setPen(QPen(QColor(255, 255, 255, 250), 2.0))
            else:
                painter.setPen(QPen(QColor(160, 235, 255, 250), 2.0))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 115), 1.0))
        painter.drawPath(path)


# ==============================================================================
# BARRA SUPERIOR DE NAVEGACIÓN DOCK
# ==============================================================================
class OmniDashNavBar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(36, 12, 36, 12)
        layout.setSpacing(16)

        # 1. Perfil del jugador (Izquierda)
        self.profile_btn = QPushButton("  Alex  •  18,450 G")
        self.profile_btn.setObjectName("profileBtn")
        self.profile_btn.setProperty("class", "glassBtn")
        self.profile_btn.setCursor(Qt.PointingHandCursor)
        self.profile_btn.clicked.connect(lambda: self.navigate.emit("PROFILE"))
        layout.addWidget(self.profile_btn)

        layout.addStretch(1)

        # 2. Dock de Navegación Central de Cristal
        dock_container = AcrylicGlassCard(self, border_radius=20)
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(6, 4, 6, 4)
        dock_layout.setSpacing(6)

        nav_items = [
            ("Inicio", "home", "HOME"),
            ("Biblioteca", "library", "LIBRARY"),
            ("Amigos", "people", "COMMUNITY"),
            ("Ajustes", "settings", "SETTINGS"),
        ]

        self.nav_buttons = {}
        for label, icon_name, view_id in nav_items:
            btn = QPushButton(f" {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 14px;
                    padding: 6px 14px;
                    font-size: 13px;
                    font-weight: 600;
                    color: rgba(255, 255, 255, 210);
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 45);
                    color: #ffffff;
                }
            """)
            ipath = ROOT / "assets_omnidash" / "icons" / f"{icon_name}.png"
            if ipath.exists():
                btn.setIcon(QIcon(str(ipath)))
                btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _, v=view_id: self.navigate.emit(v))
            dock_layout.addWidget(btn)
            self.nav_buttons[view_id] = btn

        layout.addWidget(dock_container)
        layout.addStretch(1)

        # 3. Reloj Digital Oficial (Derecha)
        self.clock_card = AcrylicGlassCard(self, border_radius=16)
        clock_layout = QHBoxLayout(self.clock_card)
        clock_layout.setContentsMargins(14, 4, 14, 4)
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        clock_layout.addWidget(self.clock_label)
        layout.addWidget(self.clock_card)

        # Timer para reloj en vivo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%I:%M %p"))


# ==============================================================================
# 1. VISTA DE INICIO (HOME)
# ==============================================================================
class HomeView(QWidget):
    launch_game = Signal(dict)
    open_details = Signal(dict)
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 12, 48, 24)
        layout.setSpacing(20)

        # 1. Fila Superior: Hero Card + Mosaicos Cuadrados Glossy
        top_row = QHBoxLayout()
        top_row.setSpacing(18)

        # Hero Card (Super Mario / Super Nintendo)
        mario_candidates = [g for g in ALL_GAMES if "mario" in g.get("title", "").lower() or "super" in g.get("console", "").lower()]
        self.hero_game = mario_candidates[0] if mario_candidates else (ALL_GAMES[0] if ALL_GAMES else {"title": "Super Nintendo", "console": "SNES"})
        self.hero_card = AcrylicGlassCard(self, border_radius=16, is_interactive=True)
        self.hero_card.setFixedSize(300, 310)
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(16, 16, 16, 16)

        # Carátula Hero
        self.hero_img = QLabel()
        self.hero_img.setFixedSize(268, 160)
        self.hero_img.setStyleSheet("border-radius: 10px; background: rgba(0,0,0,80);")
        cov_path = self.hero_game.get("cover")
        if cov_path and (ROOT / cov_path).exists():
            raw_pix = QPixmap(str(ROOT / cov_path))
            self.hero_img.setPixmap(get_rounded_pixmap(raw_pix, 268, 160, 12))
        hero_layout.addWidget(self.hero_img)

        # Título y consola
        h_title = QLabel(self.hero_game.get("title", "Super Nintendo"))
        h_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        h_sub = QLabel(f"{self.hero_game.get('console', 'SNES')}  •  16-Bit Preservation")
        h_sub.setStyleSheet("font-size: 12px; color: #bde4ff; font-weight: 600;")
        hero_layout.addWidget(h_title)
        hero_layout.addWidget(h_sub)

        # Botón Iniciar Consola
        play_btn = QPushButton("▶  INICIAR JUEGO (60 FPS)")
        play_btn.setProperty("class", "playGelBtn")
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.clicked.connect(lambda: self.launch_game.emit(self.hero_game))
        hero_layout.addWidget(play_btn)

        top_row.addWidget(self.hero_card)

        # Fila de mosaicos recientes (5 juegos destacados de diversas plataformas)
        recent_picks = []
        seen_consoles = {self.hero_game.get("console", "")}
        for g in ALL_GAMES:
            c = g.get("console", "")
            if c not in seen_consoles and len(recent_picks) < 5:
                recent_picks.append(g)
                seen_consoles.add(c)
        if len(recent_picks) < 5:
            recent_picks = [g for g in ALL_GAMES if g.get("id") != self.hero_game.get("id")][:5]

        self.recent_cards = []
        for game in recent_picks:
            card = AcrylicGlassCard(self, border_radius=14, is_interactive=True)
            card.setFixedSize(148, 310)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 12, 10, 12)

            # Imagen cuadrada
            img_lbl = QLabel()
            img_lbl.setFixedSize(128, 128)
            img_lbl.setStyleSheet("border-radius: 10px; background: rgba(0,0,0,80);")
            cov = game.get("cover")
            if cov and (ROOT / cov).exists():
                raw_pix = QPixmap(str(ROOT / cov))
                img_lbl.setPixmap(get_rounded_pixmap(raw_pix, 128, 128, 10))
            c_layout.addWidget(img_lbl)

            # Título
            g_title = QLabel(game.get("title", "Game"))
            g_title.setWordWrap(True)
            g_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #ffffff;")
            c_layout.addWidget(g_title)

            g_plat = QLabel(game.get("console", "Retro"))
            g_plat.setStyleSheet("font-size: 11px; color: #a5d8ff;")
            c_layout.addWidget(g_plat)
            c_layout.addStretch(1)

            # Botón Detalles / Jugar
            view_btn = QPushButton("Detalles")
            view_btn.setProperty("class", "glassBtn")
            view_btn.setCursor(Qt.PointingHandCursor)
            view_btn.clicked.connect(lambda _, gm=game: self.open_details.emit(gm))
            c_layout.addWidget(view_btn)

            card.mousePressEvent = lambda _, gm=game: self.open_details.emit(gm)
            self.recent_cards.append(card)
            top_row.addWidget(card)

        layout.addLayout(top_row)

        # 2. Fila Inferior: 4 Tarjetas de Cristal Frutiger Aero
        bot_row = QHBoxLayout()
        bot_row.setSpacing(18)

        cards_data = [
            ("My games & apps", f"{len(ALL_GAMES)} games ready to play", "LIBRARY", "apps_list"),
            ("Friends", "Seeker & Night Raid • 3 online", "COMMUNITY", "people"),
            ("GAME PASS", "Discover hundreds of games", "LIBRARY", "games"),
            ("Achievements", "18,450 G • 110 Trophies", "PROFILE", "star"),
        ]

        self.util_cards = []
        for title, subtitle, dest, icon_name in cards_data:
            c = AcrylicGlassCard(self, border_radius=14, is_interactive=True)
            c.setFixedHeight(94)
            c_lay = QHBoxLayout(c)
            c_lay.setContentsMargins(18, 12, 18, 12)

            txt_box = QVBoxLayout()
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
            s_lbl = QLabel(subtitle)
            s_lbl.setStyleSheet("font-size: 11px; color: #bde4ff;")
            txt_box.addWidget(t_lbl)
            txt_box.addWidget(s_lbl)
            c_lay.addLayout(txt_box)

            c_lay.addStretch(1)

            # Icono Fluent
            ico_lbl = QLabel()
            ipath = ROOT / "assets_omnidash" / "icons" / f"{icon_name}.png"
            if ipath.exists():
                ico_lbl.setPixmap(QPixmap(str(ipath)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            c_lay.addWidget(ico_lbl)

            c.mousePressEvent = lambda _, d=dest: self.navigate_to.emit(d)
            c.setCursor(Qt.PointingHandCursor)
            self.util_cards.append(c)
            bot_row.addWidget(c)

        layout.addLayout(bot_row)

        # Sistema de navegación por teclado
        self.nav_items: list[tuple[AcrylicGlassCard, callable]] = []
        self.nav_items.append((self.hero_card, lambda: self.launch_game.emit(self.hero_game)))
        for idx, gm in enumerate(recent_picks):
            self.nav_items.append((self.recent_cards[idx], lambda g=gm: self.open_details.emit(g)))
        for idx, (_, _, dest, _) in enumerate(cards_data):
            self.nav_items.append((self.util_cards[idx], lambda d=dest: self.navigate_to.emit(d)))

        self.focus_idx = 0
        self._update_focus()

    def _update_focus(self):
        for idx, (card, _) in enumerate(self.nav_items):
            card.set_focused(idx == self.focus_idx)

    def handle_key(self, key: int) -> bool:
        if key in (Qt.Key_Left, Qt.Key_A):
            if 0 < self.focus_idx <= 5:
                self.focus_idx -= 1
                self._update_focus()
                return True
            elif 6 < self.focus_idx <= 9:
                self.focus_idx -= 1
                self._update_focus()
                return True
        elif key in (Qt.Key_Right, Qt.Key_D):
            if 0 <= self.focus_idx < 5:
                self.focus_idx += 1
                self._update_focus()
                return True
            elif 6 <= self.focus_idx < 9:
                self.focus_idx += 1
                self._update_focus()
                return True
        elif key in (Qt.Key_Down, Qt.Key_S):
            if 0 <= self.focus_idx <= 5:
                self.focus_idx = min(9, 6 + (self.focus_idx * 4 // 6))
                self._update_focus()
                return True
        elif key in (Qt.Key_Up, Qt.Key_W):
            if 6 <= self.focus_idx <= 9:
                self.focus_idx = min(5, (self.focus_idx - 6) * 6 // 4)
                self._update_focus()
                return True
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self.focus_idx < len(self.nav_items):
                _, action = self.nav_items[self.focus_idx]
                action()
                return True
        return False


# ==============================================================================
# 2. VISTA DE BIBLIOTECA (LIBRARY)
# ==============================================================================
class LibraryView(QWidget):
    open_game = Signal(dict)
    back_home = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.grid_cards: list[AcrylicGlassCard] = []
        self.grid_games: list[dict] = []
        self.selected_idx = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(36, 12, 36, 24)
        layout.setSpacing(20)

        # 1. Barra Lateral Izquierda de Cristal
        self.sidebar = AcrylicGlassCard(self, border_radius=16)
        self.sidebar.setFixedWidth(240)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(18, 18, 18, 18)
        side_layout.setSpacing(14)

        # Botón Volver a Home
        back_btn = QPushButton("  Home")
        back_btn.setProperty("class", "glassBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        ip = ROOT / "assets_omnidash" / "icons" / "home.png"
        if ip.exists():
            back_btn.setIcon(QIcon(str(ip)))
        back_btn.clicked.connect(self.back_home.emit)
        side_layout.addWidget(back_btn)

        # Anillo de almacenamiento ("72% used")
        storage_box = AcrylicGlassCard(self, border_radius=12)
        st_lay = QVBoxLayout(storage_box)
        st_lay.setContentsMargins(12, 8, 12, 8)
        st_title = QLabel("Storage: 72% used")
        st_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #bde4ff;")
        st_sub = QLabel("128 GB Free of 512 GB")
        st_sub.setStyleSheet("font-size: 10px; color: #bde4ff;")
        st_lay.addWidget(st_title)
        st_lay.addWidget(st_sub)
        side_layout.addWidget(storage_box)

        # Buscador interactivo
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBox")
        self.search_input.setPlaceholderText("Buscar juegos...")
        self.search_input.textChanged.connect(self._filter_games)
        side_layout.addWidget(self.search_input)

        # Filtros por consola
        side_layout.addWidget(QLabel("CATEGORÍAS"))
        self.current_plat_name = "Todas"
        self.current_plat_code = "todas"

        platforms = [
            ("Todas", "todas"),
            ("Super Nintendo", "super"),
            ("Arcade MAME", "arcade"),
            ("Nintendo 64", "64"),
            ("PlayStation 1", "playstation"),
            ("Nintendo DS", "ds"),
            ("Neo-Geo", "neo"),
            ("C.C.I.", "c.c.i"),
        ]
        self.cat_buttons = []
        for name, code in platforms:
            b = QPushButton(name)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    border: none;
                    border-radius: 8px;
                    background: transparent;
                    color: rgba(255, 255, 255, 190);
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 30);
                    color: #ffffff;
                }
            """)
            b.clicked.connect(lambda _, n=name, c=code: self._set_platform(n, c))
            side_layout.addWidget(b)
            self.cat_buttons.append(b)

        side_layout.addStretch(1)
        layout.addWidget(self.sidebar)

        # 2. Panel Principal de Juegos (Scroll con Grid)
        self.content_panel = AcrylicGlassCard(self, border_radius=16)
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(18, 18, 18, 18)

        # Cabecera de contenido
        header_row = QHBoxLayout()
        self.count_label = QLabel(f"Todas ({len(ALL_GAMES)} disponibles)")
        self.count_label.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        header_row.addWidget(self.count_label)
        header_row.addStretch(1)
        content_layout.addLayout(header_row)

        # Scroll Area transparente
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(scroll_content)
        self.grid.setSpacing(14)
        self.scroll.setWidget(scroll_content)
        content_layout.addWidget(self.scroll)

        layout.addWidget(self.content_panel, 1)

        self._populate_grid(ALL_GAMES)

    def _set_platform(self, name: str, code: str):
        self.current_plat_name = name
        self.current_plat_code = code
        self._filter_games()

    def _filter_games(self):
        query = self.search_input.text().lower().strip()
        filtered = []
        code = self.current_plat_code
        for g in ALL_GAMES:
            title = g.get("title", "").lower()
            console = g.get("console", "").lower()
            if not code or code == "todas":
                plat_match = True
            else:
                plat_match = (code in console)
            query_match = not query or (query in title) or (query in console)
            if plat_match and query_match:
                filtered.append(g)
        self.count_label.setText(f"{self.current_plat_name} ({len(filtered)} disponibles)")
        self._populate_grid(filtered)

    def _update_grid_focus(self):
        for idx, card in enumerate(self.grid_cards):
            is_sel = (idx == self.selected_idx)
            card.set_focused(is_sel)
            if is_sel:
                self.scroll.ensureWidgetVisible(card, 20, 20)

    def _populate_grid(self, games: list[dict]):
        # Limpiar grid
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.grid_cards = []
        self.grid_games = list(games)
        self.selected_idx = 0

        cols = 4
        for idx, g in enumerate(games):
            card = AcrylicGlassCard(self, border_radius=12, is_interactive=True)
            card.setFixedSize(210, 240)
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(10, 10, 10, 10)

            # Carátula
            img_l = QLabel()
            img_l.setFixedSize(190, 140)
            img_l.setStyleSheet("border-radius: 8px; background: rgba(0,0,0,80);")
            cov = g.get("cover")
            if cov and (ROOT / cov).exists():
                raw_pix = QPixmap(str(ROOT / cov))
                img_l.setPixmap(get_rounded_pixmap(raw_pix, 190, 140, 8))
            c_lay.addWidget(img_l)

            # Título
            t_lbl = QLabel(g.get("title", "Game"))
            t_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
            t_lbl.setWordWrap(True)
            c_lay.addWidget(t_lbl)

            c_plat = QLabel(f"{g.get('console', 'Retro')}  •  60 FPS")
            c_plat.setStyleSheet("font-size: 11px; color: #bde4ff; font-weight: 600;")
            c_lay.addWidget(c_plat)

            card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
            card.setCursor(Qt.PointingHandCursor)

            self.grid_cards.append(card)

            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)

        if self.grid_cards:
            self._update_grid_focus()

    def handle_key(self, key: int) -> bool:
        if not self.grid_cards:
            return False
        cols = 4
        total = len(self.grid_cards)

        if key in (Qt.Key_Left, Qt.Key_A):
            self.selected_idx = max(0, self.selected_idx - 1)
            self._update_grid_focus()
            return True
        elif key in (Qt.Key_Right, Qt.Key_D):
            self.selected_idx = min(total - 1, self.selected_idx + 1)
            self._update_grid_focus()
            return True
        elif key in (Qt.Key_Up, Qt.Key_W):
            self.selected_idx = max(0, self.selected_idx - cols)
            self._update_grid_focus()
            return True
        elif key in (Qt.Key_Down, Qt.Key_S):
            self.selected_idx = min(total - 1, self.selected_idx + cols)
            self._update_grid_focus()
            return True
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self.selected_idx < len(self.grid_games):
                self.open_game.emit(self.grid_games[self.selected_idx])
                return True
        elif key == Qt.Key_PageDown:
            self.selected_idx = min(total - 1, self.selected_idx + cols * 2)
            self._update_grid_focus()
            return True
        elif key == Qt.Key_PageUp:
            self.selected_idx = max(0, self.selected_idx - cols * 2)
            self._update_grid_focus()
            return True
        return False


# ==============================================================================
# 3. VISTA DE DETALLES DEL JUEGO (GAME DETAILS)
# ==============================================================================
class GameDetailsView(QWidget):
    launch_game = Signal(dict)
    back_to_library = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 20, 48, 24)

        self.panel = AcrylicGlassCard(self, border_radius=18)
        p_layout = QVBoxLayout(self.panel)
        p_layout.setContentsMargins(28, 24, 28, 24)
        p_layout.setSpacing(18)

        # Barra superior con Volver
        top_bar = QHBoxLayout()
        back_btn = QPushButton("  Volver")
        back_btn.setProperty("class", "glassBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        ip = ROOT / "assets_omnidash" / "icons" / "home.png"
        if ip.exists():
            back_btn.setIcon(QIcon(str(ip)))
        back_btn.clicked.connect(self.back_to_library.emit)
        top_bar.addWidget(back_btn)
        top_bar.addStretch(1)
        p_layout.addLayout(top_bar)

        # Contenido dividido en 2 columnas
        content_row = QHBoxLayout()
        content_row.setSpacing(32)

        # Columna Izquierda: Carátula Grande + Botón Play Gel
        left_box = QVBoxLayout()
        self.cover_lbl = QLabel()
        self.cover_lbl.setFixedSize(280, 280)
        self.cover_lbl.setStyleSheet("border-radius: 12px; background: rgba(0,0,0,120); border: 2px solid rgba(255,255,255,100);")
        self.cover_lbl.setScaledContents(True)
        left_box.addWidget(self.cover_lbl)

        self.play_btn = QPushButton("▶  JUGAR AHORA (60 FPS)")
        self.play_btn.setProperty("class", "playGelBtn")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(lambda: self.launch_game.emit(self.game))
        left_box.addWidget(self.play_btn)
        left_box.addStretch(1)
        content_row.addLayout(left_box)

        # Columna Derecha: Metadatos y Capacidades
        right_box = QVBoxLayout()
        right_box.setSpacing(14)

        self.title_lbl = QLabel("Título del Juego")
        self.title_lbl.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff;")
        right_box.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("Consola • Desarrollador • 2024")
        self.meta_lbl.setStyleSheet("font-size: 14px; color: #bde4ff; font-weight: 600;")
        right_box.addWidget(self.meta_lbl)

        # Chips de capacidades
        caps_card = AcrylicGlassCard(self, border_radius=12)
        caps_layout = QHBoxLayout(caps_card)
        caps_layout.setContentsMargins(14, 10, 14, 10)
        caps = ["Single Player", "60 FPS V-Sync", "Controller Support", "Full HD Audio", "State Save"]
        for c in caps:
            lbl = QLabel(c)
            lbl.setStyleSheet("background: rgba(31, 134, 214, 180); border: 1px solid rgba(255,255,255,120); border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: 600;")
            caps_layout.addWidget(lbl)
        caps_layout.addStretch(1)
        right_box.addWidget(caps_card)

        # Descripción
        desc_card = AcrylicGlassCard(self, border_radius=12)
        desc_lay = QVBoxLayout(desc_card)
        desc_lay.setContentsMargins(16, 12, 16, 12)
        d_title = QLabel("Descripción Oficial")
        d_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        self.desc_txt = QLabel("Preservado para C.C.I. SYSTEM.")
        self.desc_txt.setStyleSheet("font-size: 12px; color: #cbe6ff; line-height: 1.4;")
        self.desc_txt.setWordWrap(True)
        desc_lay.addWidget(d_title)
        desc_lay.addWidget(self.desc_txt)
        right_box.addWidget(desc_card)

        # Info del Core
        core_card = AcrylicGlassCard(self, border_radius=12)
        core_lay = QVBoxLayout(core_card)
        core_lay.setContentsMargins(16, 12, 16, 12)
        self.core_info = QLabel("Libretro Core: Native C.C.I. Engine")
        self.core_info.setStyleSheet("font-size: 12px; color: #bde4ff;")
        self.rom_info = QLabel("ROM Path: Builtin")
        self.rom_info.setStyleSheet("font-size: 12px; color: #bde4ff;")
        cert = QLabel("✓ Certificado 60 FPS Low-Latency Framebuffer")
        cert.setStyleSheet("font-size: 11px; color: #bde4ff; font-weight: 700;")
        core_lay.addWidget(self.core_info)
        core_lay.addWidget(self.rom_info)
        core_lay.addWidget(cert)
        right_box.addWidget(core_card)

        right_box.addStretch(1)
        content_row.addLayout(right_box, 1)

        p_layout.addLayout(content_row)
        layout.addWidget(self.panel)

    def load_game(self, game: dict):
        self.game = game
        self.title_lbl.setText(game.get("title", "Game"))
        self.meta_lbl.setText(f"{game.get('console', 'Retro')}  •  {game.get('developer', 'Official')}  •  {game.get('year', '2024')}")
        self.desc_txt.setText(game.get("desc", "Official title preserved for C.C.I. SYSTEM Virtual Console."))
        self.core_info.setText(f"Libretro Core: {game.get('core', 'Native C.C.I. Engine')}")
        self.rom_info.setText(f"ROM Path: {game.get('rom', 'Builtin')}")

        cov = game.get("cover")
        if cov and (ROOT / cov).exists():
            raw_pix = QPixmap(str(ROOT / cov))
            self.cover_lbl.setPixmap(get_rounded_pixmap(raw_pix, 280, 280, 12))

    def handle_key(self, key: int) -> bool:
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.launch_game.emit(self.game)
            return True
        elif key in (Qt.Key_Escape, Qt.Key_Backspace, Qt.Key_Left):
            self.back_to_library.emit()
            return True
        return False


# ==============================================================================
# 4. VISTA DE AJUSTES (SETTINGS - 1:1 AERO-SETTINGS.JPG)
# ==============================================================================
class SettingsView(QWidget):
    wallpaper_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(48, 20, 48, 24)
        layout.setSpacing(24)

        # Panel Izquierdo: Categorías (.as-cats)
        self.cats_panel = AcrylicGlassCard(self, border_radius=16)
        self.cats_panel.setFixedWidth(280)
        cats_lay = QVBoxLayout(self.cats_panel)
        cats_lay.setContentsMargins(18, 18, 18, 18)
        cats_lay.setSpacing(10)

        c_title = QLabel("Settings")
        c_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        c_sub = QLabel("Customise console, display, audio")
        c_sub.setStyleSheet("font-size: 11px; color: #a5d8ff;")
        cats_lay.addWidget(c_title)
        cats_lay.addWidget(c_sub)
        cats_lay.addSpacing(8)

        categories = [
            ("Appearance", "paint_brush"),
            ("Display & sound", "speaker_2"),
            ("Controllers & headsets", "xbox_controller"),
            ("Notifications", "alert"),
            ("Library & emulation", "games"),
            ("Profile & system", "person"),
            ("Accessibility", "accessibility"),
            ("System", "desktop"),
        ]

        self.cat_btns = []
        for name, icon in categories:
            btn = QPushButton(f"  {name}")
            btn.setCursor(Qt.PointingHandCursor)
            ip = ROOT / "assets_omnidash" / "icons" / f"{icon}.png"
            if ip.exists():
                btn.setIcon(QIcon(str(ip)))
                btn.setIconSize(QSize(18, 18))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 9px 14px;
                    border: 1px solid transparent;
                    border-radius: 10px;
                    background: rgba(255, 255, 255, 15);
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    border: 1px solid rgba(255, 255, 255, 180);
                    background: rgba(255, 255, 255, 45);
                }
            """)
            cats_lay.addWidget(btn)
            self.cat_btns.append(btn)

        cats_lay.addStretch(1)
        layout.addWidget(self.cats_panel)

        # Panel Derecho: Configuración Activa (.as-page)
        self.page_panel = AcrylicGlassCard(self, border_radius=16)
        page_lay = QVBoxLayout(self.page_panel)
        page_lay.setContentsMargins(28, 24, 28, 24)
        page_lay.setSpacing(16)

        p_head = QLabel("Profile & Appearance")
        p_head.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        page_lay.addWidget(p_head)

        # Sección interactiva de Fondo de Pantalla (Wallpaper)
        wp_card = AcrylicGlassCard(self, border_radius=12)
        wp_lay = QVBoxLayout(wp_card)
        wp_lay.setContentsMargins(18, 14, 18, 14)
        wp_lay.setSpacing(10)

        wp_header = QHBoxLayout()
        wp_title = QLabel("Fondo de Pantalla de la Consola")
        wp_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        wp_header.addWidget(wp_title)
        wp_header.addStretch(1)
        self.wp_current_lbl = QLabel("Spider-Man (background.jpg)")
        self.wp_current_lbl.setStyleSheet("font-size: 12px; color: #bde4ff; font-weight: 600;")
        wp_header.addWidget(self.wp_current_lbl)
        wp_lay.addLayout(wp_header)

        # Botones de presets rápidos y selector de archivo
        presets_row = QHBoxLayout()
        presets_row.setSpacing(10)

        spidey_btn = QPushButton("🕷️ Spider-Man")
        spidey_btn.setProperty("class", "glassBtn")
        spidey_btn.setCursor(Qt.PointingHandCursor)
        spidey_btn.clicked.connect(lambda: self._select_wallpaper(ROOT / "background.jpg", "Spider-Man (background.jpg)"))
        presets_row.addWidget(spidey_btn)

        aero_btn = QPushButton("🏝️ Frutiger Aero (Mar)")
        aero_btn.setProperty("class", "glassBtn")
        aero_btn.setCursor(Qt.PointingHandCursor)
        aero_btn.clicked.connect(lambda: self._select_wallpaper(ROOT / "assets_omnidash" / "aero-background.webp", "Frutiger Aero (Mar Soleado)"))
        presets_row.addWidget(aero_btn)

        browse_btn = QPushButton("📁 Cambiar Fondo...")
        browse_btn.setProperty("class", "glassBtn")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_wallpaper)
        presets_row.addWidget(browse_btn)

        wp_lay.addLayout(presets_row)
        page_lay.addWidget(wp_card)

        # Opciones interactivas de cristal
        settings_rows = [
            ("Active Player", "Alex (18,450 G, Frutiger Master)"),
            ("Total Gamerscore", "18,450 G acumulados en 7 plataformas"),
            ("Libretro Framebuffer", "V-Sync 60 FPS Hardware Glitched = OFF"),
            ("Audio Sink", "Qt Multimedia Core Stereo (44.1 kHz 16-bit)"),
        ]

        for title, val in settings_rows:
            row_card = AcrylicGlassCard(self, border_radius=10, is_interactive=True)
            row_card.setFixedHeight(56)
            r_lay = QHBoxLayout(row_card)
            r_lay.setContentsMargins(18, 6, 18, 6)

            t_l = QLabel(title)
            t_l.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
            v_l = QLabel(val)
            v_l.setStyleSheet("font-size: 12px; color: #bde4ff; font-weight: 600;")

            r_lay.addWidget(t_l)
            r_lay.addStretch(1)
            r_lay.addWidget(v_l)

            page_lay.addWidget(row_card)

        page_lay.addStretch(1)
        layout.addWidget(self.page_panel, 1)

    def _select_wallpaper(self, path, label: str):
        p = Path(path).resolve()
        if p.exists():
            self.wp_current_lbl.setText(label)
            self.wallpaper_changed.emit(str(p))

    def _browse_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Fondo de Pantalla",
            str(ROOT),
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp *.tif)"
        )
        if file_path:
            self._select_wallpaper(file_path, Path(file_path).name)


# ==============================================================================
# 5. VISTA DE COMUNIDADES Y AMIGOS (COMMUNITIES / FRIENDS)
# ==============================================================================
class FriendsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 20, 48, 24)

        self.panel = AcrylicGlassCard(self, border_radius=18)
        p_lay = QVBoxLayout(self.panel)
        p_lay.setContentsMargins(28, 24, 28, 24)
        p_lay.setSpacing(16)

        title = QLabel("C.C.I. Gaming Communities & Friends")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        sub = QLabel("Live multiplayer lobbies, tournament chats and presence")
        sub.setStyleSheet("font-size: 12px; color: #a5d8ff;")
        p_lay.addWidget(title)
        p_lay.addWidget(sub)

        # Conectar con backend real CommunitiesService
        try:
            repo = CommunitiesRepository.get_instance()
            service = CommunitiesService(repo)
            rooms = service.list_rooms()
        except Exception:
            rooms = []

        if not rooms:
            rooms = [
                {"id": "r1", "name": "Seeker Hub Central", "description": "3 friends playing Metal Slug 2", "members_count": 14},
                {"id": "r2", "name": "Night Raid Elite", "description": "Street Fighter II Turbo Tournament", "members_count": 8},
                {"id": "r3", "name": "Retro Preservation Society", "description": "Castlevania Symphony of the Night Party", "members_count": 22},
            ]

        for r in rooms:
            card = AcrylicGlassCard(self, border_radius=12, is_interactive=True)
            card.setFixedHeight(72)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(18, 10, 18, 10)

            ico = QLabel()
            ip = ROOT / "assets_omnidash" / "icons" / "chat.png"
            if ip.exists():
                ico.setPixmap(QPixmap(str(ip)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            c_lay.addWidget(ico)

            info_box = QVBoxLayout()
            r_name = QLabel(r.get("name", "Room"))
            r_name.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
            r_desc = QLabel(r.get("description", "Community Lobby"))
            r_desc.setStyleSheet("font-size: 11px; color: #cbe6ff;")
            info_box.addWidget(r_name)
            info_box.addWidget(r_desc)
            c_lay.addLayout(info_box)

            c_lay.addStretch(1)

            online_lbl = QLabel(f"● {r.get('members_count', 1)} online")
            online_lbl.setStyleSheet("font-size: 12px; color: #70d6ff; font-weight: 700;")
            c_lay.addWidget(online_lbl)

            join_btn = QPushButton("Unirse")
            join_btn.setProperty("class", "glassBtn")
            join_btn.setCursor(Qt.PointingHandCursor)
            c_lay.addWidget(join_btn)

            p_lay.addWidget(card)

        p_lay.addStretch(1)
        layout.addWidget(self.panel)


# ==============================================================================
# 6. VISTA DE PERFIL Y LOGROS (PROFILE & ACHIEVEMENTS)
# ==============================================================================
class ProfileView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 20, 48, 24)

        self.panel = AcrylicGlassCard(self, border_radius=18)
        p_lay = QVBoxLayout(self.panel)
        p_lay.setContentsMargins(28, 24, 28, 24)
        p_lay.setSpacing(16)

        # Header con Avatar
        head_box = QHBoxLayout()
        av = QLabel("A")
        av.setFixedSize(64, 64)
        av.setAlignment(Qt.AlignCenter)
        av.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8cd7f5, stop:1 #06345a);
            border: 2px solid #ffffff;
            border-radius: 32px;
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
        """)
        head_box.addWidget(av)

        name_box = QVBoxLayout()
        name_l = QLabel("Alex  •  Frutiger Pilot")
        name_l.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        score_l = QLabel("18,450 G  •  Level 42 Master  •  110 Trofeos C.C.I.")
        score_l.setStyleSheet("font-size: 13px; color: #ffd166; font-weight: 700;")
        name_box.addWidget(name_l)
        name_box.addWidget(score_l)
        head_box.addLayout(name_box)
        head_box.addStretch(1)
        p_lay.addLayout(head_box)

        # Lista de logros
        p_lay.addWidget(QLabel("Logros Desbloqueados:"))
        trophies = [
            ("Master of Preservation", "Run 50 classic titles with rock-solid 60 FPS.", "🥇 GOLD"),
            ("Super Mario 16-Bit Legend", "Completed Super Mario World with all secrets.", "🥈 SILVER"),
            ("Night Raid Champion", "Won an online match in Street Fighter II Turbo.", "🥉 BRONZE"),
            ("C.C.I. Photomaster", "Captured HD gameplay frame with F12.", "🥉 BRONZE"),
        ]

        for tname, tdesc, tbadge in trophies:
            t_card = AcrylicGlassCard(self, border_radius=10, is_interactive=True)
            t_card.setFixedHeight(60)
            t_lay = QHBoxLayout(t_card)
            t_lay.setContentsMargins(16, 8, 16, 8)

            b_lbl = QLabel(tbadge)
            b_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #ffd700;")
            t_lay.addWidget(b_lbl)

            n_lbl = QLabel(tname)
            n_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
            t_lay.addWidget(n_lbl)

            t_lay.addStretch(1)

            d_lbl = QLabel(tdesc)
            d_lbl.setStyleSheet("font-size: 11px; color: #cbe6ff;")
            t_lay.addWidget(d_lbl)

            p_lay.addWidget(t_card)

        p_lay.addStretch(1)
        layout.addWidget(self.panel)


# ==============================================================================
# 7. VENTANA PRINCIPAL OMNIDASH EN PYSIDE6 (OmniDashMainWindow)
# ==============================================================================
class OmniDashMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("C.C.I. SYSTEM — OmniDash Virtual Console (Frutiger Aero)")
        self.resize(1280, 720)
        self.setMinimumSize(1024, 600)

        # Cargar fondo predeterminado (prioriza background.jpg subido por el usuario)
        self.bg_pixmap = None
        self.bg_path = ROOT / "background.jpg"
        if not self.bg_path.exists():
            self.bg_path = ROOT / "assets_omnidash" / "aero-background.webp"
        if self.bg_path.exists():
            self.bg_pixmap = QPixmap(str(self.bg_path))
            update_global_blurred_wallpaper(self.bg_path, (1280, 720))

        # Widget central
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Barra Superior
        self.nav_bar = OmniDashNavBar(self)
        self.nav_bar.navigate.connect(self.switch_view)
        root_layout.addWidget(self.nav_bar)

        # Stack de Vistas
        self.stack = QStackedWidget(self)
        root_layout.addWidget(self.stack, 1)

        # Crear vistas
        self.home_view = HomeView(self)
        self.library_view = LibraryView(self)
        self.details_view = GameDetailsView(self)
        self.settings_view = SettingsView(self)
        self.friends_view = FriendsView(self)
        self.profile_view = ProfileView(self)

        # Registrar en stack
        self.stack.addWidget(self.home_view)       # 0: HOME
        self.stack.addWidget(self.library_view)    # 1: LIBRARY
        self.stack.addWidget(self.details_view)    # 2: DETAILS
        self.stack.addWidget(self.settings_view)   # 3: SETTINGS
        self.stack.addWidget(self.friends_view)    # 4: COMMUNITY
        self.stack.addWidget(self.profile_view)    # 5: PROFILE

        # Conectar señales
        self.home_view.navigate_to.connect(self.switch_view)
        self.home_view.open_details.connect(self.show_details)
        self.home_view.launch_game.connect(self.launch_game)

        self.library_view.open_game.connect(self.show_details)
        self.library_view.back_home.connect(lambda: self.switch_view("HOME"))

        self.details_view.back_to_library.connect(lambda: self.switch_view("LIBRARY"))
        self.details_view.launch_game.connect(self.launch_game)

        self.settings_view.wallpaper_changed.connect(self.set_wallpaper)

    def set_wallpaper(self, path: str):
        p = Path(path).resolve()
        if p.exists():
            self.bg_path = p
            self.bg_pixmap = QPixmap(str(p))
            update_global_blurred_wallpaper(p, (self.width(), self.height()))
            self.update()
            for child in self.findChildren(AcrylicGlassCard):
                child.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "bg_path") and self.bg_path:
            update_global_blurred_wallpaper(self.bg_path, (self.width(), self.height()))
            self.update()
            for child in self.findChildren(AcrylicGlassCard):
                child.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.bg_pixmap:
            scaled = self.bg_pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled)
        else:
            painter.fillRect(self.rect(), QColor(10, 45, 80))

    def switch_view(self, view_id: str):
        mapping = {
            "HOME": 0,
            "LIBRARY": 1,
            "DETAILS": 2,
            "SETTINGS": 3,
            "COMMUNITY": 4,
            "FRIENDS": 4,
            "PROFILE": 5,
        }
        idx = mapping.get(view_id, 0)
        self.stack.setCurrentIndex(idx)

    def show_details(self, game: dict):
        self.details_view.load_game(game)
        self.stack.setCurrentIndex(2)

    def keyPressEvent(self, event):
        key = event.key()
        curr = self.stack.currentIndex()

        if key in (Qt.Key_Escape, Qt.Key_Backspace):
            if curr != 0:
                self.switch_view("HOME")
                return

        # Atajos de teclado 1-5 para navegación rápida
        if key == Qt.Key_1:
            self.switch_view("HOME")
            return
        elif key == Qt.Key_2:
            self.switch_view("LIBRARY")
            return
        elif key == Qt.Key_3:
            self.switch_view("COMMUNITY")
            return
        elif key == Qt.Key_4:
            self.switch_view("SETTINGS")
            return
        elif key == Qt.Key_5:
            self.switch_view("PROFILE")
            return

        cw = self.stack.currentWidget()
        if hasattr(cw, "handle_key") and cw.handle_key(key):
            return

        super().keyPressEvent(event)

    def launch_game(self, game: dict):
        core = game.get("core")
        rom = game.get("rom")
        title = game.get("title", "Game")

        if core and rom:
            print(f"[OmniDash-Qt] Lanzando emulador Libretro 60 FPS: {title} ({core})...")
            try:
                runner = LibretroRunner(
                    core_path=core,
                    rom_path=rom,
                    screen_w=1280,
                    screen_h=720
                )
                runner.run_standalone(title=f"C.C.I. SYSTEM — {title} (60 FPS)")
            except Exception as exc:
                print(f"[OmniDash-Qt] Error al ejecutar core: {exc}")
            finally:
                self.activateWindow()
                self.raise_()
        else:
            print(f"[OmniDash-Qt] Ejecutando juego nativo C.C.I.: {title}")


def run_qt_app():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    app.setStyleSheet(AERO_STYLE_SHEET)

    win = OmniDashMainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_qt_app())
