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
    QProgressBar, QSlider, QFileDialog, QGraphicsDropShadowEffect
)

from cci_console import CATALOG, UserData
from cci_users import UserManager
from retro_core_runner import LibretroRunner
from backend.communities.repository import CommunitiesRepository
from backend.communities.service import CommunitiesService
from omnidash_screens import ALL_GAMES, OFFICIAL_GAME_COVERS

ROOT = Path(__file__).resolve().parent

# Estado global de fondo óptico desenfocado y detección de tonalidad
GLOBAL_BLURRED_BG: QPixmap | None = None
WALLPAPER_IS_DARK: bool = True


def update_global_blurred_wallpaper(path: str | Path, target_size: tuple[int, int] = (1672, 941)):
    """Calcula el desenfoque óptico del fondo (Backdrop Blur) en resolución adaptativa 1-a-1."""
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

        # Muestreo a tamaño lógico de la ventana para correspondencia de coordenadas 1-a-1
        tw, th = max(200, int(target_size[0])), max(200, int(target_size[1]))
        pil_blurred = pil_img.resize((tw, th), Image.Resampling.LANCZOS).filter(
            ImageFilter.GaussianBlur(radius=14)
        )
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

/* Botón circular de navegación de cristal */
QPushButton.circleGlassBtn {
    background: rgba(10, 20, 35, 140);
    border: 1.5px solid rgba(255, 255, 255, 150);
    border-radius: 19px;
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}
QPushButton.circleGlassBtn:hover {
    background: rgba(0, 180, 255, 120);
    border: 2px solid #00d2ff;
}

/* Botón flotante Liquid Glass para Iniciar Juego */
QPushButton.heroPlayBtn {
    background: rgba(8, 18, 32, 175);
    border: 1.5px solid rgba(255, 255, 255, 220);
    border-radius: 20px;
    color: #ffffff;
    font-size: 13px;
    font-weight: 700;
    padding: 6px 18px;
}
QPushButton.heroPlayBtn:hover {
    background: rgba(0, 180, 255, 140);
    border: 2px solid #ffffff;
}
"""


# ==============================================================================
# COMPONENTE DE TARJETA ACRÍLICA ADAPTATIVA AL FONDO (GLASSMORPHISM + LIQUID GLASS)
# ==============================================================================
class AcrylicGlassCard(QFrame):
    """Panel contenedor con desenfoque óptico adaptativo, Glassmorphism y Liquid Glass:
    - Muestra el desenfoque real del fondo detrás del widget (Backdrop Blur calibrado).
    - Reflejos especulares multicapa de cristal líquido (Liquid Glass).
    - Brillo ambiental y bordes luminosos con QGraphicsDropShadowEffect.
    - Tonos azules adaptativos según la imagen de fondo.
    """
    def __init__(
        self,
        parent=None,
        border_radius=16,
        is_interactive=False,
        glow_color: QColor | None = None,
        glow_radius: int = 18,
        border_color: QColor | None = None,
        show_specular: bool = True,
        bg_image: QPixmap | None = None,
        inner_padding: int = 0,
    ):
        super().__init__(parent)
        self.border_radius = border_radius
        self.is_interactive = is_interactive
        self.glow_color = glow_color
        self.base_glow_radius = glow_radius
        self.border_color = border_color
        self.show_specular = show_specular
        self.bg_image = bg_image
        self.inner_padding = inner_padding
        self.is_hovered = False
        self.is_focused = False
        self.setAttribute(Qt.WA_Hover, is_interactive)

        self.shadow_effect: QGraphicsDropShadowEffect | None = None
        if glow_color:
            self.shadow_effect = QGraphicsDropShadowEffect(self)
            self.shadow_effect.setBlurRadius(glow_radius)
            self.shadow_effect.setColor(glow_color)
            self.shadow_effect.setOffset(0, 0)
            self.setGraphicsEffect(self.shadow_effect)

    def set_bg_image(self, pix: QPixmap | None):
        self.bg_image = pix
        self.update()

    def set_glow(self, color: QColor, radius: int = 20):
        self.glow_color = color
        self.base_glow_radius = radius
        if not self.shadow_effect:
            self.shadow_effect = QGraphicsDropShadowEffect(self)
            self.shadow_effect.setOffset(0, 0)
            self.setGraphicsEffect(self.shadow_effect)
        self.shadow_effect.setColor(color)
        self.shadow_effect.setBlurRadius(radius)
        self.update()

    def set_focused(self, focused: bool):
        if self.is_focused != focused:
            self.is_focused = focused
            if self.shadow_effect and self.glow_color:
                rad = self.base_glow_radius + (10 if focused else 0)
                self.shadow_effect.setBlurRadius(rad)
            self.update()

    def enterEvent(self, event):
        if self.is_interactive:
            self.is_hovered = True
            if self.shadow_effect and self.glow_color:
                self.shadow_effect.setBlurRadius(self.base_glow_radius + 8)
            self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.is_interactive:
            self.is_hovered = False
            if self.shadow_effect and self.glow_color:
                rad = self.base_glow_radius + (10 if self.is_focused else 0)
                self.shadow_effect.setBlurRadius(rad)
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

        # 1. Desenfoque óptico del fondo de pantalla detrás del widget (Backdrop Blur)
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

        # 2. Capa translúcida de cristal líquido adaptativo (alta transparencia para ver fondo y charcos)
        if not drawn_blur:
            fallback_col = QColor(14, 24, 40, 180) if WALLPAPER_IS_DARK else QColor(10, 50, 85, 180)
            painter.fillRect(0, 0, w, h, fallback_col)
        elif WALLPAPER_IS_DARK:
            # Cristal líquido oscuro pero diáfano (permite ver el agua y reflejos del fondo)
            dark_film = QColor(8, 20, 36, 65 if active else 85)
            blue_refraction = QColor(0, 140, 255, 22 if active else 12)
            painter.fillRect(0, 0, w, h, dark_film)
            painter.fillRect(0, 0, w, h, blue_refraction)
        else:
            aqua_film = QColor(8, 48, 85, 65 if active else 90)
            aqua_sheen = QColor(255, 255, 255, 45 if active else 20)
            painter.fillRect(0, 0, w, h, aqua_film)
            painter.fillRect(0, 0, w, h, aqua_sheen)

        # Gradiente especular multicapa (Glassmorphism & Liquid Glass)
        glass_sheen = QLinearGradient(0, 0, 0, h)
        glass_sheen.setColorAt(0.0, QColor(255, 255, 255, 40 if active else 22))
        glass_sheen.setColorAt(0.4, QColor(255, 255, 255, 8))
        glass_sheen.setColorAt(1.0, QColor(255, 255, 255, 2))
        painter.fillRect(0, 0, w, h, QBrush(glass_sheen))

        # 2.5 Arte del juego inset (Borde de cristal transparente alrededor de la imagen)
        if self.bg_image and not self.bg_image.isNull():
            pad = max(0, self.inner_padding)
            if pad > 0:
                iw = max(10, w - 2 * pad)
                ih = max(10, h - 2 * pad)
                irad = max(6, self.border_radius - pad // 2)

                inner_path = QPainterPath()
                inner_path.addRoundedRect(pad, pad, iw, ih, irad, irad)

                painter.save()
                painter.setClipPath(inner_path)
                scaled_bg = self.bg_image.scaled(iw, ih, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                sx = max(0, (scaled_bg.width() - iw) // 2)
                sy = max(0, (scaled_bg.height() - ih) // 2)
                painter.drawPixmap(pad, pad, scaled_bg, sx, sy, iw, ih)
                painter.restore()

                # Línea interior sutil en el marco del arte
                painter.setPen(QPen(QColor(255, 255, 255, 75), 1.0))
                painter.drawPath(inner_path)
            else:
                scaled_bg = self.bg_image.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                sx = max(0, (scaled_bg.width() - w) // 2)
                sy = max(0, (scaled_bg.height() - h) // 2)
                painter.drawPixmap(0, 0, scaled_bg, sx, sy, w, h)
                tint = QColor(0, 0, 0, 25 if active else 45)
                painter.fillRect(0, 0, w, h, tint)

        # 3. Reflejo especular Liquid Glass (curva o gradiente superior sobre todo el cristal)
        if self.show_specular:
            spec_h = int(h * 0.45)
            if spec_h > 8:
                spec_grad = QLinearGradient(0, 0, 0, spec_h)
                spec_grad.setColorAt(0.0, QColor(255, 255, 255, 65 if active else 35))
                spec_grad.setColorAt(0.35, QColor(255, 255, 255, 15))
                spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.fillRect(0, 0, w, spec_h, QBrush(spec_grad))

        # 4. Línea de brillo inset superior (hairline de cristal líquido)
        painter.setPen(QColor(255, 255, 255, 195 if active else 135))
        painter.drawLine(self.border_radius, 1, w - self.border_radius, 1)

        painter.restore()

        # 5. Borde transparente con glow de color temático permanente
        if self.border_color:
            painter.setPen(QPen(self.border_color, 2.2 if active else 1.8))
        elif active:
            painter.setPen(QPen(QColor(0, 210, 255, 250), 2.2))
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1.4))

        painter.drawPath(path)


# ==============================================================================
# BARRA SUPERIOR DE NAVEGACIÓN DOCK (C.C.I. SYSTEM + LIQUID DOCK + STATUS)
# ==============================================================================
class OmniDashNavBar(QWidget):
    navigate = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(76)
        self.current_view = "HOME"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(60, 14, 60, 6)
        layout.setSpacing(16)

        # 1. Left Corner: Logo C.C.I. SYSTEM o Perfil del Jugador según la vista activa
        self.left_stack = QStackedWidget(self)
        self.left_stack.setFixedHeight(50)

        # Index 0: Brand Logo C.C.I. SYSTEM
        brand_widget = QWidget()
        brand_box = QHBoxLayout(brand_widget)
        brand_box.setContentsMargins(0, 0, 0, 0)
        brand_box.setSpacing(10)

        ico_lbl = QLabel()
        ico_p = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not ico_p.exists():
            ico_p = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if ico_p.exists():
            ico_lbl.setPixmap(QPixmap(str(ico_p)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_box.addWidget(ico_lbl)

        txt_v = QVBoxLayout()
        txt_v.setSpacing(0)
        t_cci = QLabel("C.C.I.")
        t_cci.setStyleSheet("font-size: 22px; font-weight: 900; color: #ffffff; letter-spacing: 2px;")
        t_sys = QLabel("SYSTEM")
        t_sys.setStyleSheet("font-size: 10px; font-weight: 800; color: #00d2ff; letter-spacing: 3px;")
        txt_v.addWidget(t_cci)
        txt_v.addWidget(t_sys)
        brand_box.addLayout(txt_v)

        sep = QLabel("|")
        sep.setStyleSheet("color: rgba(255, 255, 255, 80); font-size: 24px; font-weight: 200; margin-left: 6px;")
        brand_box.addWidget(sep)
        self.left_stack.addWidget(brand_widget)

        # Index 1: Cápsula de Perfil de Jugador (Alex • 18,450 G) para Comunidades (1:1 Imagen 2)
        profile_widget = QWidget()
        pr_box = QHBoxLayout(profile_widget)
        pr_box.setContentsMargins(0, 0, 0, 0)
        self.profile_pill = AcrylicGlassCard(
            self,
            border_radius=22,
            border_color=QColor(145, 165, 179, 85),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=8
        )
        self.profile_pill.setFixedSize(190, 44)
        pp_lay = QHBoxLayout(self.profile_pill)
        pp_lay.setContentsMargins(6, 4, 14, 4)
        pp_lay.setSpacing(8)

        av_l = QLabel()
        av_p = ROOT / "assets_omnidash" / "spidey_avatar.png"
        if av_p.exists():
            av_l.setPixmap(get_rounded_pixmap(QPixmap(str(av_p)), 32, 32, 16))
        pp_lay.addWidget(av_l)

        txt_l = QLabel("Alex  <span style='color: #32D875;'>●</span>  18,450 G")
        txt_l.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        pp_lay.addWidget(txt_l)
        pr_box.addWidget(self.profile_pill)
        pr_box.addStretch(1)
        self.left_stack.addWidget(profile_widget)

        layout.addWidget(self.left_stack)
        layout.addStretch(1)

        # 2. Dock de Navegación Central Flotante de Cristal Líquido (Glow Cyan)
        dock_container = AcrylicGlassCard(
            self,
            border_radius=26,
            glow_color=QColor(0, 170, 255, 80),
            glow_radius=16,
            border_color=QColor(255, 255, 255, 90),
        )
        dock_container.setFixedHeight(54)
        dock_layout = QHBoxLayout(dock_container)
        dock_layout.setContentsMargins(8, 4, 8, 4)
        dock_layout.setSpacing(6)

        nav_items = [
            ("Inicio", "home", "HOME"),
            ("Biblioteca", "library", "LIBRARY"),
            ("Comunidades", "people", "COMMUNITY"),
            ("Amigos", "friends_duo", "FRIENDS"),
            ("Ajustes", "settings", "SETTINGS"),
        ]

        self.nav_buttons = {}
        for label, icon_name, view_id in nav_items:
            btn = QPushButton(f"  {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setMinimumWidth(100)
            btn.setFixedHeight(40)
            ipath = ROOT / "assets_omnidash" / "icons" / f"{icon_name}.png"
            if ipath.exists():
                btn.setIcon(QIcon(str(ipath)))
                btn.setIconSize(QSize(18, 18))
            btn.clicked.connect(lambda _, v=view_id: self._on_nav_click(v))
            dock_layout.addWidget(btn)
            self.nav_buttons[view_id] = btn

        self._update_nav_styles()
        layout.addWidget(dock_container)
        layout.addStretch(1)

        # 3. Status Widgets (Campana notificaciones con badge, Wifi, Gamepad, Reloj)
        status_box = QHBoxLayout()
        status_box.setSpacing(16)

        # Campana con indicador 1
        bell_lbl = QLabel()
        bell_lbl.setCursor(Qt.PointingHandCursor)
        bell_p = ROOT / "assets_omnidash" / "icons" / "bell_badge.png"
        if not bell_p.exists():
            bell_p = ROOT / "assets_omnidash" / "icons" / "alert.png"
        if bell_p.exists():
            bell_lbl.setPixmap(QPixmap(str(bell_p)).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        status_box.addWidget(bell_lbl)

        # WiFi
        wifi_lbl = QLabel()
        wifi_p = ROOT / "assets_omnidash" / "icons" / "wifi_signal.png"
        if not wifi_p.exists():
            wifi_p = ROOT / "assets_omnidash" / "icons" / "globe.png"
        if wifi_p.exists():
            wifi_lbl.setPixmap(QPixmap(str(wifi_p)).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        status_box.addWidget(wifi_lbl)

        # Gamepad
        gp_lbl = QLabel()
        gp_p = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not gp_p.exists():
            gp_p = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if gp_p.exists():
            gp_lbl.setPixmap(QPixmap(str(gp_p)).scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        status_box.addWidget(gp_lbl)

        # Reloj digital oficial en cápsula de cristal
        self.clock_card = AcrylicGlassCard(
            self,
            border_radius=20,
            glow_color=QColor(0, 180, 255, 50),
            glow_radius=12,
            border_color=QColor(255, 255, 255, 110),
        )
        self.clock_card.setFixedSize(130, 42)
        clock_layout = QHBoxLayout(self.clock_card)
        clock_layout.setContentsMargins(12, 2, 12, 2)
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        self.clock_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        clock_layout.addWidget(self.clock_label)
        status_box.addWidget(self.clock_card)

        layout.addLayout(status_box)

        # Timer para reloj en vivo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def set_active_view(self, view_id: str):
        self.current_view = view_id
        if hasattr(self, "left_stack"):
            if view_id in ("COMMUNITY", "COMMUNITIES"):
                self.left_stack.setCurrentIndex(1)
            else:
                self.left_stack.setCurrentIndex(0)
        self._update_nav_styles()

    def _on_nav_click(self, view_id: str):
        self.set_active_view(view_id)
        self.navigate.emit(view_id)

    def _update_nav_styles(self):
        for vid, btn in self.nav_buttons.items():
            if vid == self.current_view:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(0, 150, 230, 0.45);
                        border: 1.8px solid #00e5ff;
                        border-radius: 18px;
                        padding: 4px 14px;
                        font-size: 13px;
                        font-weight: 800;
                        color: #ffffff;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: 1.5px solid transparent;
                        border-radius: 18px;
                        padding: 4px 12px;
                        font-size: 13px;
                        font-weight: 600;
                        color: rgba(255, 255, 255, 215);
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 30);
                        color: #ffffff;
                    }
                """)

    def _update_clock(self):
        self.clock_label.setText(datetime.now().strftime("%I:%M %p"))


# ==============================================================================
# 1. VISTA DE INICIO (HOME REDESIGN - LIQUID GLASS & GLOW CARDS)
# ==============================================================================
class HomeView(QWidget):
    launch_game = Signal(dict)
    open_details = Signal(dict)
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 4, 60, 24)
        layout.setSpacing(0)

        # 0. PERFIL DE USUARIO ALEX (Debajo del logotipo C.C.I. SYSTEM en el margen izquierdo)
        profile_row = QHBoxLayout()
        profile_row.setContentsMargins(0, 0, 0, 0)

        self.profile_card = AcrylicGlassCard(
            self,
            border_radius=28,
            is_interactive=True,
            glow_color=QColor(0, 180, 255, 60),
            glow_radius=14,
            border_color=QColor(255, 255, 255, 95),
        )
        self.profile_card.setFixedSize(255, 58)
        p_lay = QHBoxLayout(self.profile_card)
        p_lay.setContentsMargins(8, 4, 16, 4)
        p_lay.setSpacing(10)

        av_lbl = QLabel()
        av_p = ROOT / "assets_omnidash" / "spidey_avatar.png"
        if av_p.exists():
            raw_av = QPixmap(str(av_p))
            av_lbl.setPixmap(get_rounded_pixmap(raw_av, 44, 44, 22))
        p_lay.addWidget(av_lbl)

        name_v = QVBoxLayout()
        name_v.setSpacing(1)
        name_lbl = QLabel("Alex  <span style='color: #00ff88; font-size: 13px;'>●</span>")
        name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        pts_lbl = QLabel("18,450 G")
        pts_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #bde4ff;")
        name_v.addWidget(name_lbl)
        name_v.addWidget(pts_lbl)
        p_lay.addLayout(name_v)

        self.profile_card.mousePressEvent = lambda _: self.navigate_to.emit("PROFILE")
        self.profile_card.setCursor(Qt.PointingHandCursor)
        profile_row.addWidget(self.profile_card)
        profile_row.addStretch(1)
        layout.addLayout(profile_row)
        layout.addSpacing(10)

        # 1. FILA PRINCIPAL: Botón Izq + Hero Card + Grid 3x2 + Botón Der
        main_row = QHBoxLayout()
        main_row.setSpacing(14)
        main_row.setAlignment(Qt.AlignCenter)

        # Botón Flecha Izquierda Circular de Cristal
        self.left_arrow = QPushButton("<")
        self.left_arrow.setFixedSize(42, 42)
        self.left_arrow.setCursor(Qt.PointingHandCursor)
        self.left_arrow.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 35, 140);
                border: 1.6px solid rgba(255, 255, 255, 160);
                border-radius: 21px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(0, 180, 255, 160);
                border: 1.6px solid #00e5ff;
            }
        """)
        main_row.addWidget(self.left_arrow)

        # --- A. HERO CARD (SUPER MARIO BROS - 60 FPS) ---
        mario_candidates = [
            g for g in ALL_GAMES
            if "mario" in g.get("title", "").lower() and "kart" not in g.get("title", "").lower()
        ]
        self.hero_game = mario_candidates[0] if mario_candidates else (ALL_GAMES[0] if ALL_GAMES else {"title": "Super Mario Bros", "console": "SNES"})

        # Cargar arte del Hero (versión limpia sin botón horneado)
        hero_pix = None
        hero_art_path = ROOT / "assets_omnidash" / "mockup_cards" / "hero_mario_clean.png"
        if not hero_art_path.exists():
            hero_art_path = ROOT / "assets_omnidash" / "mockup_cards" / "hero_mario.png"
        if not hero_art_path.exists():
            hero_art_path = ROOT / "fotos web" / "super mario.jpg"
        if hero_art_path.exists():
            hero_pix = QPixmap(str(hero_art_path))

        self.hero_card = AcrylicGlassCard(
            self,
            border_radius=36,
            is_interactive=True,
            glow_color=QColor(0, 210, 255, 220),
            glow_radius=26,
            border_color=QColor(160, 230, 255, 240),
            bg_image=hero_pix,
            inner_padding=6,
        )
        self.hero_card.setFixedSize(490, 416)
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(16, 14, 16, 16)

        # Botón Favorito (Corazón) en esquina superior derecha
        h_top_row = QHBoxLayout()
        h_top_row.addStretch(1)
        self.fav_btn = QPushButton("♡")
        self.fav_btn.setFixedSize(36, 36)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 35, 140);
                border: 1.5px solid rgba(255, 255, 255, 180);
                border-radius: 18px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 75, 110, 190);
                border: 1.5px solid #ffffff;
            }
        """)
        h_top_row.addWidget(self.fav_btn)
        hero_layout.addLayout(h_top_row)
        hero_layout.addStretch(1)

        # Botón Flotante Liquid Glass "▶ Iniciar (60 FPS)"
        h_bot_row = QHBoxLayout()
        h_bot_row.addStretch(1)
        self.play_btn = QPushButton(" ▶   Iniciar (60 FPS)")
        self.play_btn.setFixedSize(270, 48)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: rgba(10, 22, 38, 190);
                border: 1.8px solid rgba(255, 255, 255, 230);
                border-radius: 24px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background: rgba(0, 180, 255, 180);
                border: 1.8px solid #ffffff;
            }
        """)
        self.play_btn.clicked.connect(lambda: self.launch_game.emit(self.hero_game))
        h_bot_row.addWidget(self.play_btn)
        h_bot_row.addStretch(1)
        hero_layout.addLayout(h_bot_row)

        self.hero_card.mousePressEvent = lambda _: self.launch_game.emit(self.hero_game)
        self.hero_card.setCursor(Qt.PointingHandCursor)
        main_row.addWidget(self.hero_card)

        # --- B. GRID DE 6 TARJETAS (2 FILAS x 3 COLUMNAS) ---
        grid_items_data = [
            (
                "Super Mario Bros",
                "grid_mario.png",
                "fotos juegos/Super Mario World 2- Yoshi's Island.jpg",
                QColor(0, 210, 255, 190),
                QColor(0, 210, 255, 230),
            ),
            (
                "Metal Slug",
                "grid_metalslug.png",
                "fotos juegos/Metal Slug 2- Super Vehicle-001:II.jpg",
                QColor(255, 159, 28, 190),
                QColor(255, 159, 28, 230),
            ),
            (
                "The Legend Of Zelda",
                "grid_zelda.png",
                "fotos juegos/The Legend of Zelda- Ocarina of Time.jpg",
                QColor(255, 215, 0, 190),
                QColor(255, 215, 0, 230),
            ),
            (
                "Donkey Kong 64",
                "grid_donkeykong.png",
                "fotos juegos/Donkey Kong 64.jpg",
                QColor(46, 204, 113, 190),
                QColor(46, 204, 113, 230),
            ),
            (
                "Castlevania - Symphony of the Night",
                "grid_castlevania.png",
                "fotos juegos/Castlevania- Symphony of the Night.webp",
                QColor(230, 57, 70, 190),
                QColor(230, 57, 70, 230),
            ),
            (
                "Mario Kart DS",
                "grid_mariokart.png",
                "fotos juegos/Mario Kart DS.jpg",
                QColor(112, 214, 255, 190),
                QColor(112, 214, 255, 230),
            ),
        ]

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(14)

        self.grid_cards = []
        for idx, (title, mock_file, fallback, glow_col, border_col) in enumerate(grid_items_data):
            img_path = ROOT / "assets_omnidash" / "mockup_cards" / mock_file
            if not img_path.exists():
                img_path = ROOT / fallback
            card_pix = QPixmap(str(img_path)) if img_path.exists() else None

            # Buscar juego real en ALL_GAMES
            matched_game = next((g for g in ALL_GAMES if title.lower() in g.get("title", "").lower()), None)
            if not matched_game:
                matched_game = {"title": title, "console": "Retro", "cover": fallback}

            card = AcrylicGlassCard(
                self,
                border_radius=22,
                is_interactive=True,
                glow_color=glow_col,
                glow_radius=18,
                border_color=border_col,
                bg_image=card_pix,
                inner_padding=6,
            )
            card.setFixedSize(228, 194)
            card.mousePressEvent = lambda _, gm=matched_game: self.open_details.emit(gm)
            card.setCursor(Qt.PointingHandCursor)

            row = idx // 3
            col = idx % 3
            grid_layout.addWidget(card, row, col)
            self.grid_cards.append((card, matched_game))

        main_row.addWidget(grid_container)

        # Botón Flecha Derecha Circular de Cristal
        self.right_arrow = QPushButton(">")
        self.right_arrow.setFixedSize(42, 42)
        self.right_arrow.setCursor(Qt.PointingHandCursor)
        self.right_arrow.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 35, 140);
                border: 1.6px solid rgba(255, 255, 255, 160);
                border-radius: 21px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(0, 180, 255, 160);
                border: 1.6px solid #00e5ff;
            }
        """)
        main_row.addWidget(self.right_arrow)

        layout.addLayout(main_row)
        layout.addSpacing(10)

        # 2. INDICADORES DE CARRUSEL (PUNTOS • • • •)
        dots_box = QHBoxLayout()
        dots_box.setSpacing(8)
        dots_box.setAlignment(Qt.AlignCenter)

        dot_active = QLabel()
        dot_active.setFixedSize(30, 6)
        dot_active.setStyleSheet("background: #00d2ff; border-radius: 3px;")
        dots_box.addWidget(dot_active)

        for _ in range(3):
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet("background: rgba(255, 255, 255, 110); border-radius: 3px;")
            dots_box.addWidget(dot)

        layout.addLayout(dots_box)
        layout.addSpacing(14)

        # 3. FILA INFERIOR: 4 TARJETAS ANCHAS DE CRISTAL LÍQUIDO CON GLOW TEMÁTICO
        bot_row = QHBoxLayout()
        bot_row.setSpacing(18)

        cards_data = [
            (
                "Mis juegos y apps",
                f"{len(ALL_GAMES)} juegos listos para jugar",
                "LIBRARY",
                "apps_grid",
                QColor(0, 180, 255, 200),
                QColor(0, 180, 255, 230),
            ),
            (
                "Amigos",
                "Seeker & Night Raid • 3 en línea",
                "COMMUNITY",
                "friends_duo",
                QColor(0, 235, 255, 190),
                QColor(0, 235, 255, 230),
            ),
            (
                "GAME PASS",
                "Descubre cientos de juegos",
                "LIBRARY",
                "xbox_gamepass",
                QColor(46, 204, 113, 210),
                QColor(46, 204, 113, 240),
            ),
            (
                "Logros",
                "18,450 G • 110 trofeos",
                "PROFILE",
                "trophy",
                QColor(192, 96, 255, 210),
                QColor(192, 96, 255, 240),
            ),
        ]

        self.util_cards = []
        for title, subtitle, dest, icon_name, glow_c, border_c in cards_data:
            c = AcrylicGlassCard(
                self,
                border_radius=22,
                is_interactive=True,
                glow_color=glow_c,
                glow_radius=20,
                border_color=border_c,
            )
            c.setFixedHeight(90)
            c_lay = QHBoxLayout(c)
            c_lay.setContentsMargins(18, 8, 18, 8)
            c_lay.setSpacing(14)

            # Icono temático
            ico_lbl = QLabel()
            ipath = ROOT / "assets_omnidash" / "icons" / f"{icon_name}.png"
            if not ipath.exists():
                ipath = ROOT / "assets_omnidash" / "icons" / "grid.png"
            if ipath.exists():
                ico_lbl.setPixmap(QPixmap(str(ipath)).scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            c_lay.addWidget(ico_lbl)

            # Textos
            txt_box = QVBoxLayout()
            txt_box.setSpacing(2)
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
            s_lbl = QLabel(subtitle)
            s_lbl.setStyleSheet("font-size: 11px; color: #bde4ff;")
            txt_box.addWidget(t_lbl)
            txt_box.addWidget(s_lbl)
            c_lay.addLayout(txt_box)

            c_lay.addStretch(1)

            # Chevron indicador derecha
            chev_lbl = QLabel("›")
            chev_lbl.setStyleSheet("font-size: 22px; font-weight: 600; color: rgba(255, 255, 255, 190);")
            c_lay.addWidget(chev_lbl)

            c.mousePressEvent = lambda _, d=dest: self.navigate_to.emit(d)
            c.setCursor(Qt.PointingHandCursor)
            self.util_cards.append(c)
            bot_row.addWidget(c)

        layout.addLayout(bot_row)

        # Stretch inferior para fijar la distancia y que el suelo mojado quede visible abajo
        layout.addStretch(2)

        # Sistema de navegación por teclado unificado
        self.nav_items: list[tuple[AcrylicGlassCard, callable]] = []
        self.nav_items.append((self.hero_card, lambda: self.launch_game.emit(self.hero_game)))
        for card, gm in self.grid_cards:
            self.nav_items.append((card, lambda g=gm: self.open_details.emit(g)))
        for idx, (_, _, dest, _, _, _) in enumerate(cards_data):
            self.nav_items.append((self.util_cards[idx], lambda d=dest: self.navigate_to.emit(d)))

        self.focus_idx = 0
        self._update_focus()

    def _update_focus(self):
        for idx, (card, _) in enumerate(self.nav_items):
            card.set_focused(idx == self.focus_idx)

    def handle_key(self, key: int) -> bool:
        if key in (Qt.Key_Left, Qt.Key_A):
            if self.focus_idx > 0:
                self.focus_idx -= 1
                self._update_focus()
                return True
        elif key in (Qt.Key_Right, Qt.Key_D):
            if self.focus_idx < len(self.nav_items) - 1:
                self.focus_idx += 1
                self._update_focus()
                return True
        elif key in (Qt.Key_Down, Qt.Key_S):
            if self.focus_idx <= 6:
                # Salto de la fila superior a la fila inferior de utilidades
                self.focus_idx = min(len(self.nav_items) - 1, 7 + (self.focus_idx * 4 // 7))
                self._update_focus()
                return True
        elif key in (Qt.Key_Up, Qt.Key_W):
            if self.focus_idx >= 7:
                # Salto de la fila inferior a la fila superior
                self.focus_idx = min(6, (self.focus_idx - 7) * 7 // 4)
                self._update_focus()
                return True
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self.focus_idx < len(self.nav_items):
                _, action = self.nav_items[self.focus_idx]
                action()
                return True
        return False


# ==============================================================================
# 2. VISTA DE BIBLIOTECA (LIBRARY REDESIGN - LIQUID GLASS & SIDEBAR)
# ==============================================================================
def resolve_game_cover(game: dict) -> QPixmap | None:
    """Busca y resuelve la carátula oficial en alta definición para el juego."""
    # 1. Carátula oficial asignada directamente
    cov = game.get("cover")
    if cov and (ROOT / cov).exists():
        pm = QPixmap(str(ROOT / cov))
        if not pm.isNull():
            return pm

    # 2. Búsqueda por ID oficial en fotos juegos/
    gid = game.get("id")
    if gid and gid in OFFICIAL_GAME_COVERS:
        cand = ROOT / OFFICIAL_GAME_COVERS[gid]
        if cand.exists():
            pm = QPixmap(str(cand))
            if not pm.isNull():
                return pm

    # 3. Fallbacks secundarios de títulos y clásicos
    title = (game.get("title") or "").lower()
    priority_map = [
        ("da vinci", ROOT / "assets_omnidash" / "covers" / "elden.png"),
        ("asteroids", ROOT / "fotos web" / "asteroids.jpg"),
        ("tetris", ROOT / "fotos web" / "tetris logo .jpg"),
        ("space invaders", ROOT / "fotos web" / "space nvaders.jpg"),
        ("super mario", ROOT / "fotos juegos" / "Super Mario World 2- Yoshi's Island.jpg"),
        ("zelda", ROOT / "fotos juegos" / "The Legend of Zelda- Ocarina of Time.jpg"),
        ("metal slug", ROOT / "fotos juegos" / "Metal Slug 2- Super Vehicle-001:II.jpg"),
        ("castlevania", ROOT / "fotos juegos" / "Castlevania- Symphony of the Night.webp"),
    ]
    for key, path in priority_map:
        if key in title and path.exists():
            pm = QPixmap(str(path))
            if not pm.isNull():
                return pm

    return None


# ==============================================================================
# TARJETA DE VIDEOJUEGO DE BIBLIOTECA (STEEL & DARK GLASS - PROPORCIÓN 0.96:1)
# ==============================================================================
class LibraryGameCard(AcrylicGlassCard):
    def __init__(self, game: dict, parent=None):
        super().__init__(
            parent,
            border_radius=22,
            is_interactive=True,
            glow_color=QColor(39, 189, 231, 70),
            glow_radius=12,
            border_color=QColor(166, 176, 184, 85),
            inner_padding=0,
        )
        self.game = game
        self.setFixedSize(268, 296)
        self.setCursor(Qt.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # 1. Contenedor de Carátula (248 x 198 px, ratio ~4:3) con botón discreto de Favorito
        cover_container = QWidget()
        cover_container.setFixedSize(248, 198)
        c_lay = QVBoxLayout(cover_container)
        c_lay.setContentsMargins(0, 0, 0, 0)

        self.cover_label = QLabel(cover_container)
        self.cover_label.setFixedSize(248, 198)
        self.cover_label.setStyleSheet("border-radius: 14px; background: rgba(0, 0, 0, 70);")

        pix = resolve_game_cover(game)
        if pix and not pix.isNull():
            self.cover_label.setPixmap(get_rounded_pixmap(pix, 248, 198, 14))

        # Botón Favorito (♡) discreto en esquina superior derecha
        self.fav_btn = QPushButton("♡", cover_container)
        self.fav_btn.setFixedSize(28, 28)
        self.fav_btn.move(248 - 28 - 6, 6)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 30, 120);
                border: 1px solid rgba(255, 255, 255, 140);
                border-radius: 14px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 180);
                color: #102638;
            }
        """)
        self.is_fav = False

        def toggle_fav():
            self.is_fav = not self.is_fav
            if self.is_fav:
                self.fav_btn.setText("♥")
                self.fav_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(255, 255, 255, 220);
                        border: 1px solid #ffffff;
                        border-radius: 14px;
                        color: #102638;
                        font-size: 14px;
                        font-weight: 700;
                    }
                """)
            else:
                self.fav_btn.setText("♡")
                self.fav_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(10, 20, 30, 120);
                        border: 1px solid rgba(255, 255, 255, 140);
                        border-radius: 14px;
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 700;
                    }
                """)

        self.fav_btn.clicked.connect(toggle_fav)
        lay.addWidget(cover_container)

        # 2. Textos: Título Semibold y Subtítulo con FPS
        txt_box = QVBoxLayout()
        txt_box.setSpacing(2)
        txt_box.setContentsMargins(4, 2, 4, 0)

        title = game.get("title", "Game")
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #f4f6f8;")
        self.title_lbl.setFixedHeight(20)
        txt_box.addWidget(self.title_lbl)

        # Subtítulo con icono de mando + "C.C.I. • 60 FPS"
        sub_row = QHBoxLayout()
        sub_row.setSpacing(6)
        sub_row.setContentsMargins(0, 0, 0, 0)

        ico = QLabel()
        c_ico_path = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not c_ico_path.exists():
            c_ico_path = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if c_ico_path.exists():
            ico.setPixmap(QPixmap(str(c_ico_path)).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        sub_row.addWidget(ico)

        fps_val = game.get("fps", 60)
        if game.get("on_demand"):
            sub_lbl = QLabel(f"☁ En la nube  •  {game.get('size', 'Descargar')}")
            sub_lbl.setStyleSheet("font-size: 13px; color: #56c9e9; font-weight: 600;")
        else:
            sub_lbl = QLabel(f"C.C.I.  •  {fps_val} FPS")
            sub_lbl.setStyleSheet("font-size: 13px; color: #bdd1df; font-weight: 500;")
        sub_row.addWidget(sub_lbl)
        sub_row.addStretch(1)

        txt_box.addLayout(sub_row)
        lay.addLayout(txt_box)
        lay.addStretch(1)


# ==============================================================================
# 2. VISTA DE BIBLIOTECA OFICIAL C.C.I. (REDISEÑO DARK GLASS & STEEL)
# ==============================================================================
class LibraryView(QWidget):
    open_game = Signal(dict)
    back_home = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.grid_cards: list[LibraryGameCard] = []
        self.grid_games: list[dict] = []
        self.selected_idx = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(44, 12, 44, 20)
        layout.setSpacing(20)

        # 1. Barra Lateral Izquierda de Cristal Oscuro (Sidebar: 338 x 718 px)
        self.sidebar = AcrylicGlassCard(
            self,
            border_radius=30,
            border_color=QColor(166, 176, 184, 100),
            glow_color=QColor(0, 0, 0, 70),
            glow_radius=12
        )
        self.sidebar.setFixedSize(338, 718)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(12)

        # Botón Home en forma de píldora translúcida (298 x 48 px)
        back_btn = QPushButton("   Home")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(48)
        ip = ROOT / "assets_omnidash" / "icons" / "home.png"
        if ip.exists():
            back_btn.setIcon(QIcon(str(ip)))
            back_btn.setIconSize(QSize(18, 18))
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(32, 52, 68, 0.7);
                border: 1.5px solid rgba(166, 176, 184, 0.35);
                border-radius: 24px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
                padding-left: 10px;
                text-align: center;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.4);
                border: 1.5px solid #27bde7;
            }
        """)
        back_btn.clicked.connect(self.back_home.emit)
        side_layout.addWidget(back_btn)

        # Widget Storage: "Storage: 72% usado", "128 GB libres de 512 GB" (298 x 95 px)
        storage_box = QFrame()
        storage_box.setFixedHeight(95)
        storage_box.setStyleSheet("""
            QFrame {
                background: rgba(20, 38, 54, 0.55);
                border: 1.5px solid rgba(166, 176, 184, 0.3);
                border-radius: 20px;
            }
        """)
        st_lay = QVBoxLayout(storage_box)
        st_lay.setContentsMargins(14, 12, 14, 12)
        st_lay.setSpacing(8)

        st_top = QHBoxLayout()
        st_top.setSpacing(10)
        hd_ico = QLabel()
        hd_ico.setFixedSize(26, 26)
        hd_ico.setStyleSheet("border: none; background: transparent;")
        hd_path = ROOT / "assets_omnidash" / "icons" / "hard_drive.png"
        if hd_path.exists():
            hd_ico.setPixmap(QPixmap(str(hd_path)).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        st_top.addWidget(hd_ico)

        st_txt = QVBoxLayout()
        st_txt.setSpacing(2)
        st_title = QLabel("Storage: 72% usado")
        st_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff; border: none; background: transparent;")
        st_sub = QLabel("128 GB libres de 512 GB")
        st_sub.setStyleSheet("font-size: 11px; color: #bdd1df; border: none; background: transparent;")
        st_txt.addWidget(st_title)
        st_txt.addWidget(st_sub)
        st_top.addLayout(st_txt)
        st_top.addStretch(1)
        st_lay.addLayout(st_top)

        # Barra de progreso estilizada
        self.storage_bar = QProgressBar()
        self.storage_bar.setRange(0, 100)
        self.storage_bar.setValue(72)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setFixedHeight(6)
        self.storage_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.15);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: #56c9e9;
                border-radius: 3px;
            }
        """)
        st_lay.addWidget(self.storage_bar)
        side_layout.addWidget(storage_box)

        # Buscador interactivo con lupa (298 x 46 px)
        search_box = QFrame()
        search_box.setStyleSheet("""
            QFrame {
                background: rgba(16, 32, 48, 0.65);
                border: 1.5px solid rgba(166, 176, 184, 0.35);
                border-radius: 23px;
            }
        """)
        search_box.setFixedHeight(46)
        s_box_lay = QHBoxLayout(search_box)
        s_box_lay.setContentsMargins(14, 0, 14, 0)
        s_box_lay.setSpacing(8)

        s_ico = QLabel()
        s_ico_path = ROOT / "assets_omnidash" / "icons" / "search.png"
        if s_ico_path.exists():
            s_ico.setPixmap(QPixmap(str(s_ico_path)).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        s_ico.setStyleSheet("border: none; background: transparent;")
        s_box_lay.addWidget(s_ico)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar juegos...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 14px;
            }
        """)
        self.search_input.textChanged.connect(self._filter_games)
        s_box_lay.addWidget(self.search_input)
        side_layout.addWidget(search_box)

        # Título "CATEGORÍAS"
        cat_title = QLabel("CATEGORÍAS")
        cat_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff; padding: 6px 0px 4px 6px; letter-spacing: 0.8px;")
        side_layout.addWidget(cat_title)

        # Filtros por consola con iconos oficiales
        self.current_plat_name = "Todas"
        self.current_plat_code = "todas"

        platforms = [
            (f"Todas ({len(ALL_GAMES)})", "todas", "apps_grid.png"),
            ("Super Nintendo", "snes", "controller_outline.png"),
            ("Arcade MAME", "arcade", "arcade_cabinet.png"),
            ("Nintendo 64", "n64", "xbox_controller.png"),
            ("PlayStation 1", "ps1", "disc_ps.png"),
            ("Nintendo DS", "nds", "nds_dual.png"),
            ("Neo-Geo", "neo", "games.png"),
            ("Game Boy Advance", "gba", "desktop.png"),
            ("C.C.I.", "cci", "controller_outline.png"),
        ]

        self.cat_buttons = []
        for name, code, icon_file in platforms:
            b = QPushButton(f"  {name}")
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(36)
            ipath = ROOT / "assets_omnidash" / "icons" / icon_file
            if not ipath.exists():
                ipath = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
            if ipath.exists():
                b.setIcon(QIcon(str(ipath)))
                b.setIconSize(QSize(18, 18))
            b.clicked.connect(lambda _, n=name, c=code: self._set_platform(n, c))
            side_layout.addWidget(b)
            self.cat_buttons.append((b, code))

        self._update_cat_button_styles()
        side_layout.addStretch(1)
        layout.addWidget(self.sidebar)

        # 2. Panel Principal de Juegos (Content Panel: 1215 x 715 px)
        self.content_panel = AcrylicGlassCard(
            self,
            border_radius=30,
            border_color=QColor(166, 176, 184, 110),
            glow_color=QColor(0, 0, 0, 80),
            glow_radius=14
        )
        self.content_panel.setFixedHeight(718)
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(24, 18, 18, 16)
        content_layout.setSpacing(14)

        # Cabecera de contenido: Icono Joystick + Título + Selector Cuadrícula/Lista
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        gp_ico = QLabel()
        gp_path = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not gp_path.exists():
            gp_path = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if gp_path.exists():
            gp_ico.setPixmap(QPixmap(str(gp_path)).scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        header_row.addWidget(gp_ico)

        self.count_label = QLabel(f"Todas ({len(ALL_GAMES)} disponibles)")
        self.count_label.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")
        header_row.addWidget(self.count_label)
        header_row.addStretch(1)

        # Selector de Vista Cuadrícula / Lista en cápsula compacta de cristal
        view_toggle_frame = QFrame()
        view_toggle_frame.setStyleSheet("""
            QFrame {
                background: rgba(16, 30, 44, 0.7);
                border: 1.5px solid rgba(166, 176, 184, 0.35);
                border-radius: 21px;
            }
        """)
        view_toggle_frame.setFixedSize(94, 42)
        vt_lay = QHBoxLayout(view_toggle_frame)
        vt_lay.setContentsMargins(4, 3, 4, 3)
        vt_lay.setSpacing(4)

        self.grid_mode_btn = QPushButton()
        self.grid_mode_btn.setFixedSize(36, 34)
        self.grid_mode_btn.setCursor(Qt.PointingHandCursor)
        grid_ico_path = ROOT / "assets_omnidash" / "icons" / "apps_grid.png"
        if not grid_ico_path.exists():
            grid_ico_path = ROOT / "assets_omnidash" / "icons" / "grid.png"
        if grid_ico_path.exists():
            self.grid_mode_btn.setIcon(QIcon(str(grid_ico_path)))
            self.grid_mode_btn.setIconSize(QSize(18, 18))
        self.grid_mode_btn.setStyleSheet("""
            QPushButton {
                background: rgba(39, 189, 231, 0.45);
                border: 1.5px solid #27bde7;
                border-radius: 17px;
            }
        """)

        self.list_mode_btn = QPushButton()
        self.list_mode_btn.setFixedSize(36, 34)
        self.list_mode_btn.setCursor(Qt.PointingHandCursor)
        list_ico_path = ROOT / "assets_omnidash" / "icons" / "apps_list.png"
        if list_ico_path.exists():
            self.list_mode_btn.setIcon(QIcon(str(list_ico_path)))
            self.list_mode_btn.setIconSize(QSize(18, 18))
        self.list_mode_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 17px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 25);
            }
        """)

        vt_lay.addWidget(self.grid_mode_btn)
        vt_lay.addWidget(self.list_mode_btn)
        header_row.addWidget(view_toggle_frame)
        content_layout.addLayout(header_row)

        # Scroll Area transparente (4 columnas x 2 filas completas en resolución base)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:horizontal {
                height: 0px;
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(166, 176, 184, 0.4);
                min-height: 40px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(39, 189, 231, 0.85);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setHorizontalSpacing(20)
        self.grid.setVerticalSpacing(18)
        self.grid.setContentsMargins(6, 4, 12, 6)
        self.scroll.setWidget(self.scroll_content)
        content_layout.addWidget(self.scroll)

        layout.addWidget(self.content_panel, 1)

        # Inicializar tarjetas persistentes en el scroll area
        self.all_cards: list[LibraryGameCard] = []
        prioritized = self._get_prioritized_games(ALL_GAMES)
        for g in prioritized:
            card = LibraryGameCard(g, self.scroll_content)
            card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
            self.all_cards.append(card)

        self._filter_games()

    def _get_prioritized_games(self, games: list[dict]) -> list[dict]:
        """Ordena los 8 juegos emblemáticos en la cuadrícula 4x2 inicial según la referencia."""
        def match_game(target: str, g: dict) -> bool:
            t = g.get("title", "").lower().replace("-", " ")
            if target == "da vinci": return "da vinci" in t
            if target == "asteroids": return "asteroids" in t
            if target == "mario": return "super mario" in t and "kart" not in t and "64" not in t and "world" not in t and "collection" not in t
            if target == "zelda": return "zelda" in t
            if target == "pacman": return "pac man" in t or "pacman" in t
            if target == "tetris": return "tetris" in t
            if target == "space invaders": return "space invader" in t
            if target == "metal slug": return "metal slug" in t
            return False

        top_targets = [
            "da vinci",
            "asteroids",
            "mario",
            "zelda",
            "pacman",
            "tetris",
            "space invaders",
            "metal slug"
        ]
        priority_games = []
        remaining_games = []
        for target in top_targets:
            found = next((g for g in games if match_game(target, g) and g not in priority_games), None)
            if found:
                priority_games.append(found)
        for g in games:
            if g not in priority_games:
                remaining_games.append(g)
        return priority_games + remaining_games

    def _update_cat_button_styles(self):
        for b, code in self.cat_buttons:
            if code == self.current_plat_code:
                b.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 14px;
                        border: 1.5px solid #27bde7;
                        border-radius: 14px;
                        background: rgba(39, 189, 231, 0.22);
                        color: #ffffff;
                        font-size: 13px;
                        font-weight: 700;
                    }
                """)
            else:
                b.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 14px;
                        border: 1px solid transparent;
                        border-radius: 14px;
                        background: transparent;
                        color: rgba(244, 246, 248, 0.85);
                        font-size: 13px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.08);
                        color: #ffffff;
                    }
                """)

    def _set_platform(self, name: str, code: str):
        clean_name = name.split("(")[0].strip()
        self.current_plat_name = clean_name
        self.current_plat_code = code
        self._update_cat_button_styles()
        self._filter_games()

    def _filter_games(self):
        raw_query = self.search_input.text().lower().strip()
        query = (
            raw_query.replace("simpsom", "simpson")
            .replace("gow", "god of war")
            .replace("kratos", "god of war")
            .replace("brats", "bratz")
        )
        code = self.current_plat_code
        matching_cards = []

        for card in self.all_cards:
            g = card.game
            title = g.get("title", "").lower()
            console = g.get("console", "").lower()
            badge = g.get("badge", "").lower()
            desc = g.get("desc", "").lower()

            if not code or code == "todas":
                plat_match = True
            elif code == "snes":
                plat_match = ("super" in console or "snes" in console or badge == "snes")
            elif code == "arcade":
                plat_match = ("arcade" in console or "mame" in console or badge == "arcade")
            elif code == "n64":
                plat_match = ("64" in console or badge == "n64")
            elif code == "ps1":
                plat_match = ("playstation" in console or "ps1" in console or "ps2" in console or "psp" in console or badge in ("ps1", "ps2", "psp"))
            elif code == "nds":
                plat_match = ("ds" in console or badge == "nds")
            elif code == "neo":
                plat_match = ("neo" in console or badge == "neo-geo")
            elif code == "gba":
                plat_match = ("gba" in console or "advance" in console or badge == "gba")
            elif code == "cci":
                plat_match = ("c.c.i" in console or badge == "cci")
            else:
                plat_match = (code in console or code in badge)

            query_match = (
                not query
                or (query in title)
                or (query in console)
                or (query in desc)
                or (query in badge)
                or (raw_query in title)
            )

            if query:
                if query_match:
                    matching_cards.append(card)
            else:
                if plat_match:
                    matching_cards.append(card)

        self.count_label.setText(f"{self.current_plat_name} ({len(matching_cards)} disponibles)")

        # Remover del layout y ocultar todas
        for card in self.all_cards:
            self.grid.removeWidget(card)
            card.hide()

        # Añadir y mostrar solo las tarjetas activas
        cols = 4
        self.grid_cards = matching_cards
        self.grid_games = [c.game for c in matching_cards]
        for idx, card in enumerate(matching_cards):
            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)
            card.show()

        self.selected_idx = 0
        self._update_card_focus()

    def _update_card_focus(self):
        for idx, card in enumerate(self.grid_cards):
            card.set_focused(idx == self.selected_idx)

    def handle_key(self, key: int) -> bool:
        if not self.grid_cards:
            return False
        cols = 4
        total = len(self.grid_cards)

        if key in (Qt.Key_Left, Qt.Key_A):
            if self.selected_idx > 0:
                self.selected_idx -= 1
                self._update_card_focus()
                self._ensure_visible()
            return True
        elif key in (Qt.Key_Right, Qt.Key_D):
            if self.selected_idx < total - 1:
                self.selected_idx += 1
                self._update_card_focus()
                self._ensure_visible()
            return True
        elif key in (Qt.Key_Up, Qt.Key_W):
            if self.selected_idx - cols >= 0:
                self.selected_idx -= cols
                self._update_card_focus()
                self._ensure_visible()
            return True
        elif key in (Qt.Key_Down, Qt.Key_S):
            if self.selected_idx + cols < total:
                self.selected_idx += cols
                self._update_card_focus()
                self._ensure_visible()
            return True
        elif key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if 0 <= self.selected_idx < len(self.grid_games):
                self.open_game.emit(self.grid_games[self.selected_idx])
            return True
        return False

    def _ensure_visible(self):
        if 0 <= self.selected_idx < len(self.grid_cards):
            card = self.grid_cards[self.selected_idx]
            self.scroll.ensureWidgetVisible(card, 50, 50)

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
            card = LibraryGameCard(g, self.scroll_content)
            card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
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
# 4. VISTA DE AJUSTES (SETTINGS - 1:1 REDISEÑO FRUTIGER AERO / DARK GLASS)
# ==============================================================================
class WallpaperThumbnailCard(QFrame):
    clicked = Signal()

    def __init__(self, card_id: str, title: str, image_path: Path | None, is_picker: bool = False, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.title = title
        self.image_path = image_path
        self.is_picker = is_picker
        self.is_selected = False
        self.is_hovered = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(116)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_Hover, True)

        self._pixmap = None
        if image_path and image_path.exists():
            self._pixmap = QPixmap(str(image_path))

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(16)
        self.shadow.setColor(QColor(53, 204, 245, 0))
        self.setGraphicsEffect(self.shadow)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.shadow.setColor(QColor(53, 204, 245, 170))
            self.shadow.setBlurRadius(20)
        else:
            self.shadow.setColor(QColor(0, 0, 0, 50))
            self.shadow.setBlurRadius(10)
        self.update()

    def enterEvent(self, event):
        self.is_hovered = True
        if not self.is_selected:
            self.shadow.setColor(QColor(255, 255, 255, 60))
            self.shadow.setBlurRadius(14)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        if not self.is_selected:
            self.shadow.setColor(QColor(0, 0, 0, 50))
            self.shadow.setBlurRadius(10)
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        w = self.width()
        h = self.height()
        radius = 20

        clip_path = QPainterPath()
        clip_path.addRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        if self.is_picker:
            bg_col = QColor(25, 42, 60, 200) if self.is_hovered else QColor(16, 28, 42, 170)
            p.fillPath(clip_path, QBrush(bg_col))

            ico_path = ROOT / "assets_omnidash" / "icons" / "image_picker.png"
            if not ico_path.exists():
                ico_path = ROOT / "assets_omnidash" / "icons" / "image.png"
            if ico_path.exists():
                ico = QPixmap(str(ico_path)).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p.drawPixmap((w - 30) // 2, (h - 56) // 2, ico)

            p.setPen(QColor(255, 255, 255, 240))
            p.setFont(QFont("Helvetica Neue", 12, QFont.Bold))
            p.drawText(0, h // 2 + 12, w, 24, Qt.AlignHCenter | Qt.AlignVCenter, self.title)
        else:
            p.save()
            p.setClipPath(clip_path)
            if self._pixmap and not self._pixmap.isNull():
                scaled = self._pixmap.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                sx = max(0, (scaled.width() - w) // 2)
                sy = max(0, (scaled.height() - h) // 2)
                p.drawPixmap(0, 0, scaled, sx, sy, w, h)
            else:
                p.fillRect(0, 0, w, h, QColor(30, 45, 60))
            p.restore()

            if self.is_selected:
                chk_path = ROOT / "assets_omnidash" / "icons" / "check_circle_cyan.png"
                if chk_path.exists():
                    chk_pix = QPixmap(str(chk_path)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    p.drawPixmap(w - 34, 10, chk_pix)
                else:
                    p.setPen(QPen(QColor(53, 204, 245), 2))
                    p.setBrush(QBrush(QColor(10, 24, 38, 200)))
                    p.drawEllipse(w - 34, 10, 24, 24)
                    p.drawLine(w - 28, 22, w - 24, 26)
                    p.drawLine(w - 24, 26, w - 16, 17)

        if self.is_selected:
            p.setPen(QPen(QColor(53, 204, 245), 2.2))
        elif self.is_hovered:
            p.setPen(QPen(QColor(255, 255, 255, 140), 1.5))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 38), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, radius, radius)


class SettingsView(QWidget):
    wallpaper_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(44, 12, 44, 20)
        layout.setSpacing(20)

        # 1. Panel Lateral Izquierdo: Ajustes (354 x 718 px)
        self.sidebar = AcrylicGlassCard(
            self,
            border_radius=30,
            border_color=QColor(166, 176, 184, 100),
            glow_color=QColor(0, 0, 0, 70),
            glow_radius=12
        )
        self.sidebar.setFixedWidth(354)
        self.sidebar.setFixedHeight(718)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(10)

        # Cabecera del Sidebar: Icono Gear + Título + Subtítulo
        s_hdr = QHBoxLayout()
        s_hdr.setSpacing(14)
        gear_lbl = QLabel()
        gear_path = ROOT / "assets_omnidash" / "icons" / "settings.png"
        if gear_path.exists():
            gear_lbl.setPixmap(QPixmap(str(gear_path)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        s_hdr.addWidget(gear_lbl)

        s_text_lay = QVBoxLayout()
        s_text_lay.setSpacing(2)
        s_title = QLabel("Ajustes")
        s_title.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff;")
        s_sub = QLabel("Personalizá tu consola")
        s_sub.setStyleSheet("font-size: 13px; color: #8da2b5; font-weight: 500;")
        s_text_lay.addWidget(s_title)
        s_text_lay.addWidget(s_sub)
        s_hdr.addLayout(s_text_lay)
        s_hdr.addStretch(1)
        side_layout.addLayout(s_hdr)
        side_layout.addSpacing(6)

        # 8 Botones de Categorías
        categories = [
            ("Apariencia", "display_monitor"),
            ("Pantalla y sonido", "speaker_2"),
            ("Controles y accesorios", "xbox_controller"),
            ("Notificaciones", "alert"),
            ("Biblioteca y emulación", "games"),
            ("Perfil y sistema", "person"),
            ("Accesibilidad", "accessibility"),
            ("Sistema", "desktop"),
        ]

        self.cat_btns = []
        for i, (name, icon_name) in enumerate(categories):
            btn = QPushButton(f"   {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(54)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            ip = ROOT / "assets_omnidash" / "icons" / f"{icon_name}.png"
            if ip.exists():
                btn.setIcon(QIcon(str(ip)))
                btn.setIconSize(QSize(22, 22))

            if i == 0:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        border: 1.5px solid #35CCF5;
                        border-radius: 20px;
                        background: rgba(14, 45, 68, 0.85);
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 700;
                    }
                """)
                btn_glow = QGraphicsDropShadowEffect(btn)
                btn_glow.setOffset(0, 0)
                btn_glow.setColor(QColor(53, 204, 245, 110))
                btn_glow.setBlurRadius(14)
                btn.setGraphicsEffect(btn_glow)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 20px;
                        background: rgba(20, 32, 45, 0.5);
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        border: 1px solid rgba(255, 255, 255, 0.3);
                        background: rgba(28, 48, 68, 0.7);
                    }
                """)
            btn.clicked.connect(lambda _, idx=i: self._on_cat_clicked(idx))
            side_layout.addWidget(btn)
            self.cat_btns.append(btn)

        side_layout.addStretch(1)
        layout.addWidget(self.sidebar)

        # 2. Panel Principal de Configuración: Perfil y Apariencia
        self.content_panel = AcrylicGlassCard(
            self,
            border_radius=30,
            border_color=QColor(166, 176, 184, 100),
            glow_color=QColor(0, 0, 0, 80),
            glow_radius=14
        )
        self.content_panel.setFixedHeight(718)
        content_lay = QVBoxLayout(self.content_panel)
        content_lay.setContentsMargins(28, 22, 28, 22)
        content_lay.setSpacing(16)

        # Cabecera: Icono Paleta + Perfil y Apariencia + Subtítulo
        c_hdr = QHBoxLayout()
        c_hdr.setSpacing(14)
        pal_lbl = QLabel()
        pal_path = ROOT / "assets_omnidash" / "icons" / "palette_outline.png"
        if pal_path.exists():
            pal_lbl.setPixmap(QPixmap(str(pal_path)).scaled(44, 44, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        c_hdr.addWidget(pal_lbl)

        c_text_lay = QVBoxLayout()
        c_text_lay.setSpacing(2)
        c_title = QLabel("Perfil y Apariencia")
        c_title.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff;")
        c_sub = QLabel("Configurá el aspecto de tu C.C.I.")
        c_sub.setStyleSheet("font-size: 13px; color: #8da2b5; font-weight: 500;")
        c_text_lay.addWidget(c_title)
        c_text_lay.addWidget(c_sub)
        c_hdr.addLayout(c_text_lay)
        c_hdr.addStretch(1)
        content_lay.addLayout(c_hdr)

        # Contenedor de Galería de Fondos de Pantalla
        wp_container = AcrylicGlassCard(
            self,
            border_radius=24,
            border_color=QColor(255, 255, 255, 30),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10
        )
        wp_container.setFixedHeight(186)
        wp_box_lay = QVBoxLayout(wp_container)
        wp_box_lay.setContentsMargins(20, 12, 20, 14)
        wp_box_lay.setSpacing(10)

        # Fila de Título del Fondo
        wp_title_row = QHBoxLayout()
        wp_ico = QLabel()
        wp_ico_p = ROOT / "assets_omnidash" / "icons" / "image.png"
        if wp_ico_p.exists():
            wp_ico.setPixmap(QPixmap(str(wp_ico_p)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        wp_title_row.addWidget(wp_ico)

        wp_t_lbl = QLabel("Fondo de pantalla de la consola")
        wp_t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        wp_title_row.addWidget(wp_t_lbl)
        wp_title_row.addStretch(1)

        self.wp_current_lbl = QLabel("Spider-Man (background.jpg)")
        self.wp_current_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #a5d8ff;")
        wp_title_row.addWidget(self.wp_current_lbl)
        wp_box_lay.addLayout(wp_title_row)

        # Fila de 4 Tarjetas de Wallpapers
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.cards: list[WallpaperThumbnailCard] = []

        # Card 1: Spider-Man
        c1 = WallpaperThumbnailCard(
            "spidey",
            "Spider-Man",
            ROOT / "assets_omnidash" / "wallpapers" / "thumb_spidey_clean.jpg"
        )
        c1.set_selected(True)
        c1.clicked.connect(lambda: self._select_wallpaper(ROOT / "background.jpg", "Spider-Man (background.jpg)", "spidey"))
        cards_row.addWidget(c1)
        self.cards.append(c1)

        # Card 2: Sunset City
        c2 = WallpaperThumbnailCard(
            "sunset",
            "Sunset City",
            ROOT / "assets_omnidash" / "wallpapers" / "thumb_sunset_exact.jpg"
        )
        c2.clicked.connect(lambda: self._select_wallpaper(ROOT / "assets_omnidash" / "wallpapers" / "sunset_city.jpg", "Sunset City (sunset_city.jpg)", "sunset"))
        cards_row.addWidget(c2)
        self.cards.append(c2)

        # Card 3: Night Moon
        c3 = WallpaperThumbnailCard(
            "moon",
            "Night Moon",
            ROOT / "assets_omnidash" / "wallpapers" / "thumb_moon_exact.jpg"
        )
        c3.clicked.connect(lambda: self._select_wallpaper(ROOT / "assets_omnidash" / "wallpapers" / "night_moon.jpg", "Night Moon (night_moon.jpg)", "moon"))
        cards_row.addWidget(c3)
        self.cards.append(c3)

        # Card 4: Cambiar fondo...
        c4 = WallpaperThumbnailCard("picker", "Cambiar fondo...", None, is_picker=True)
        c4.clicked.connect(self._browse_wallpaper)
        cards_row.addWidget(c4)
        self.cards.append(c4)

        wp_box_lay.addLayout(cards_row)
        content_lay.addWidget(wp_container)

        # 4 Filas de Configuración Interactivas de Cristal
        settings_rows = [
            ("person", "Active Player", "Alex (18,450 G, Frutiger Master)"),
            ("trophy", "Total Gamerscore", "18,450 G acumulados en 7 plataformas"),
            ("layers_stack", "Libretro Framebuffer", "V-Sync 60 FPS | Hardware Glitched = OFF"),
            ("sound_wave", "Audio Sink", "Qt Multimedia Core Stereo (44.1 kHz 16-bit)"),
        ]

        for icon_id, title, val in settings_rows:
            row_frame = AcrylicGlassCard(
                self,
                border_radius=22,
                border_color=QColor(255, 255, 255, 24),
                glow_color=QColor(0, 0, 0, 40),
                is_interactive=True
            )
            row_frame.setFixedHeight(64)
            r_lay = QHBoxLayout(row_frame)
            r_lay.setContentsMargins(20, 0, 20, 0)
            r_lay.setSpacing(14)

            # Icono Izquierdo
            ico_lbl = QLabel()
            ico_p = ROOT / "assets_omnidash" / "icons" / f"{icon_id}.png"
            if ico_p.exists():
                ico_lbl.setPixmap(QPixmap(str(ico_p)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            r_lay.addWidget(ico_lbl)

            # Título de Opción
            t_lbl = QLabel(title)
            t_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
            r_lay.addWidget(t_lbl)

            r_lay.addStretch(1)

            # Valor a la derecha
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("font-size: 14px; color: #a5d8ff; font-weight: 500;")
            r_lay.addWidget(v_lbl)

            # Flecha Chevron >
            chev_lbl = QLabel()
            chev_p = ROOT / "assets_omnidash" / "icons" / "chevron_right.png"
            if chev_p.exists():
                chev_lbl.setPixmap(QPixmap(str(chev_p)).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                chev_lbl.setText(">")
                chev_lbl.setStyleSheet("font-size: 16px; color: rgba(255, 255, 255, 0.4);")
            r_lay.addWidget(chev_lbl)

            content_lay.addWidget(row_frame)

        content_lay.addStretch(1)
        layout.addWidget(self.content_panel, 1)

    def _on_cat_clicked(self, active_idx: int):
        for i, btn in enumerate(self.cat_btns):
            if i == active_idx:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        border: 1.5px solid #35CCF5;
                        border-radius: 20px;
                        background: rgba(14, 45, 68, 0.85);
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 700;
                    }
                """)
                btn_glow = QGraphicsDropShadowEffect(btn)
                btn_glow.setOffset(0, 0)
                btn_glow.setColor(QColor(53, 204, 245, 110))
                btn_glow.setBlurRadius(14)
                btn.setGraphicsEffect(btn_glow)
            else:
                btn.setGraphicsEffect(None)
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 18px;
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 20px;
                        background: rgba(20, 32, 45, 0.5);
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        border: 1px solid rgba(255, 255, 255, 0.3);
                        background: rgba(28, 48, 68, 0.7);
                    }
                """)

    def _select_wallpaper(self, path, label: str, card_id: str = "custom"):
        p = Path(path).resolve()
        if p.exists():
            self.wp_current_lbl.setText(label)
            for c in self.cards:
                c.set_selected(c.card_id == card_id)
            self.wallpaper_changed.emit(str(p))

    def _browse_wallpaper(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Fondo de Pantalla",
            str(ROOT),
            "Imágenes (*.png *.jpg *.jpeg *.webp *.bmp *.tif)"
        )
        if file_path:
            p = Path(file_path).resolve()
            for c in self.cards:
                c.set_selected(False)
            self._select_wallpaper(p, p.name, "custom")


# ==============================================================================
# 5. VISTA DE COMUNIDADES Y AMIGOS (COMMUNITIES / FRIENDS - 1:1 DISCORD-LIKE DARK GLASS)
# ==============================================================================
class ServerRailItem(QPushButton):
    def __init__(self, icon_path: Path, is_active: bool = False, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.is_active = is_active
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self._pixmap = None
        if icon_path.exists():
            self._pixmap = QPixmap(str(icon_path))

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(14)
        if is_active:
            self.shadow.setColor(QColor(53, 200, 241, 180))
        else:
            self.shadow.setColor(QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self.shadow)

    def set_active(self, active: bool):
        self.is_active = active
        if active:
            self.shadow.setColor(QColor(53, 200, 241, 180))
        else:
            self.shadow.setColor(QColor(0, 0, 0, 0))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        radius = 16 if self.is_active else 23

        path = QPainterPath()
        path.addRoundedRect(1, 1, w - 2, h - 2, radius, radius)

        bg = QColor(18, 38, 56, 220) if self.is_active else QColor(14, 28, 40, 160)
        p.fillPath(path, QBrush(bg))

        if self._pixmap and not self._pixmap.isNull():
            ico_size = 26 if self.is_active else 24
            scaled = self._pixmap.scaled(ico_size, ico_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((w - ico_size) // 2, (h - ico_size) // 2, scaled)

        if self.is_active:
            p.setPen(QPen(QColor(53, 200, 241), 2.2))
        else:
            p.setPen(QPen(QColor(145, 165, 179, 70), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, radius, radius)


class ServerRail(QWidget):
    community_selected = Signal(str)
    explore_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(58)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignHCenter)

        plus_p = ROOT / "assets_omnidash" / "communities" / "rail_plus.png"
        self.add_btn = ServerRailItem(plus_p, tooltip="Explorar / Crear Comunidad")
        self.add_btn.clicked.connect(self.explore_clicked.emit)
        layout.addWidget(self.add_btn)

        self.items: list[ServerRailItem] = []

        servers = [
            ("seeker-hub", "rail_seeker.png", True, "Seeker Hub Central"),
            ("night-raid", "rail_skull.png", False, "Night Raid Elite"),
            ("pixel-squad", "rail_alien.png", False, "Pixel Squad"),
            ("retro-preservation", "rail_triforce.png", False, "Retro Preservation Society"),
            ("ps-classics", "rail_ps.png", False, "PlayStation Classics"),
        ]

        for s_id, s_icon, active, tooltip in servers:
            icon_p = ROOT / "assets_omnidash" / "communities" / s_icon
            if not icon_p.exists():
                icon_p = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
            item = ServerRailItem(icon_p, is_active=active, tooltip=tooltip)
            item.clicked.connect(lambda _, sid=s_id, it=item: self._select_server(sid, it))
            layout.addWidget(item)
            self.items.append(item)

        layout.addStretch(1)

        more_p = ROOT / "assets_omnidash" / "communities" / "rail_more.png"
        self.more_btn = ServerRailItem(more_p, tooltip="Más opciones")
        layout.addWidget(self.more_btn)

    def _select_server(self, server_id: str, item: ServerRailItem):
        for it in self.items:
            it.set_active(it == item)
        self.community_selected.emit(server_id)


class ChannelSidebar(AcrylicGlassCard):
    channel_selected = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            border_radius=22,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10
        )
        self.setFixedWidth(306)
        self.active_channel = "general"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.banner_frame = QFrame()
        self.banner_frame.setFixedHeight(120)
        b_lay = QVBoxLayout(self.banner_frame)
        b_lay.setContentsMargins(12, 12, 12, 10)
        b_lay.setSpacing(2)

        banner_path = ROOT / "assets_omnidash" / "communities" / "banner_seeker_hub.jpg"
        if not banner_path.exists():
            banner_path = ROOT / "assets_omnidash" / "wallpapers" / "sunset_city.jpg"

        self.banner_frame.setStyleSheet(f"""
            QFrame {{
                background-image: url("{str(banner_path)}");
                background-position: center;
                border-radius: 14px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)

        t_row = QHBoxLayout()
        self.c_name_lbl = QLabel("Seeker Hub Central")
        self.c_name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff; background: transparent;")
        t_row.addWidget(self.c_name_lbl)
        t_row.addStretch(1)

        chev = QLabel("∨")
        chev.setStyleSheet("font-size: 12px; font-weight: 800; color: #ffffff; background: transparent;")
        t_row.addWidget(chev)
        b_lay.addLayout(t_row)

        self.c_members_lbl = QLabel("● 14 en línea · 42 miembros")
        self.c_members_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #a5d8ff; background: transparent;")
        b_lay.addWidget(self.c_members_lbl)
        b_lay.addStretch(1)

        layout.addWidget(self.banner_frame)

        home_btn = QPushButton("  Inicio")
        home_btn.setCursor(Qt.PointingHandCursor)
        home_btn.setFixedHeight(36)
        h_ico = ROOT / "assets_omnidash" / "icons" / "home.png"
        if h_ico.exists():
            home_btn.setIcon(QIcon(str(h_ico)))
            home_btn.setIconSize(QSize(16, 16))
        home_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 12px;
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #ffffff;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(home_btn)

        t_sec = QHBoxLayout()
        t_sec_lbl = QLabel("∨  Canales de texto")
        t_sec_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #BDD4E4;")
        t_sec.addWidget(t_sec_lbl)
        t_sec.addStretch(1)
        add_t_btn = QLabel("+")
        add_t_btn.setStyleSheet("font-size: 14px; font-weight: 700; color: #BDD4E4;")
        t_sec.addWidget(add_t_btn)
        layout.addLayout(t_sec)

        self.text_buttons: dict[str, QPushButton] = {}
        text_channels = ["general", "juegos", "torneos", "clips-y-streams", "off-topic", "memes"]

        for ch in text_channels:
            btn = QPushButton(f" #  {ch}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda _, c=ch: self._set_active_text_channel(c))
            layout.addWidget(btn)
            self.text_buttons[ch] = btn

        self._style_text_channels()

        layout.addSpacing(6)
        v_sec = QHBoxLayout()
        v_sec_lbl = QLabel("∨  Canales de voz")
        v_sec_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #BDD4E4;")
        v_sec.addWidget(v_sec_lbl)
        v_sec.addStretch(1)
        add_v_btn = QLabel("+")
        add_v_btn.setStyleSheet("font-size: 14px; font-weight: 700; color: #BDD4E4;")
        v_sec.addWidget(add_v_btn)
        layout.addLayout(v_sec)

        voice_channels = [
            ("Lobby General", "speaker_2", "14"),
            ("Gaming 1", "speaker_2", "4"),
            ("Gaming 2", "speaker_2", None),
            ("Streaming", "sound_wave", None),
        ]

        for v_name, v_ico, badge in voice_channels:
            v_btn = QPushButton(f"    {v_name}")
            v_btn.setCursor(Qt.PointingHandCursor)
            v_btn.setFixedHeight(32)
            vip = ROOT / "assets_omnidash" / "icons" / f"{v_ico}.png"
            if vip.exists():
                v_btn.setIcon(QIcon(str(vip)))
                v_btn.setIconSize(QSize(15, 15))
            v_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 10px;
                    background: transparent;
                    border: none;
                    border-radius: 8px;
                    color: #BDD4E4;
                    font-size: 13px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.08);
                    color: #ffffff;
                }
            """)
            if badge:
                row = QHBoxLayout(v_btn)
                row.setContentsMargins(0, 0, 10, 0)
                row.addStretch(1)
                b_lbl = QLabel(badge)
                b_lbl.setStyleSheet("background: rgba(255, 255, 255, 0.15); border-radius: 8px; padding: 1px 6px; font-size: 11px; font-weight: 700; color: #ffffff;")
                row.addWidget(b_lbl)
            layout.addWidget(v_btn)

        layout.addStretch(1)

    def _set_active_text_channel(self, ch_name: str):
        self.active_channel = ch_name
        self._style_text_channels()
        self.channel_selected.emit(ch_name, "text")

    def _style_text_channels(self):
        for name, btn in self.text_buttons.items():
            if name == self.active_channel:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 12px;
                        background: rgba(27, 48, 64, 0.95);
                        border: 1px solid rgba(53, 200, 241, 0.6);
                        border-radius: 8px;
                        color: #ffffff;
                        font-size: 13px;
                        font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left;
                        padding-left: 12px;
                        background: transparent;
                        border: none;
                        border-radius: 8px;
                        color: #BDD4E4;
                        font-size: 13px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.06);
                        color: #ffffff;
                    }
                """)


class StreamCard(AcrylicGlassCard):
    play_stream = Signal(str)

    def __init__(self, title: str, streamer: str, viewers: int, thumb_path: Path, parent=None):
        super().__init__(
            parent,
            border_radius=18,
            border_color=QColor(93, 116, 131, 90),
            glow_color=QColor(0, 0, 0, 60),
            glow_radius=12
        )
        self.setFixedHeight(142)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 16, 10)
        layout.setSpacing(16)

        self.thumb_frame = QFrame()
        self.thumb_frame.setFixedSize(210, 120)
        t_lay = QVBoxLayout(self.thumb_frame)
        t_lay.setContentsMargins(8, 8, 8, 8)

        b_row = QHBoxLayout()
        live_lbl = QLabel("EN VIVO")
        live_lbl.setStyleSheet("background: #E94B56; color: #ffffff; font-size: 10px; font-weight: 800; border-radius: 4px; padding: 2px 6px;")
        b_row.addWidget(live_lbl)
        b_row.addStretch(1)

        v_lbl = QLabel(f"👁 {viewers}")
        v_lbl.setStyleSheet("background: rgba(0, 0, 0, 0.6); color: #ffffff; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 2px 6px;")
        b_row.addWidget(v_lbl)
        t_lay.addLayout(b_row)
        t_lay.addStretch(1)

        self.thumb_frame.setStyleSheet(f"""
            QFrame {{
                background-image: url("{str(thumb_path)}");
                background-position: center;
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 0.25);
            }}
        """)
        layout.addWidget(self.thumb_frame)

        info_lay = QVBoxLayout()
        info_lay.setContentsMargins(0, 6, 0, 6)
        info_lay.setSpacing(4)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")
        info_lay.addWidget(title_lbl)

        st_row = QHBoxLayout()
        st_row.setSpacing(6)
        av_lbl = QLabel()
        av_p = ROOT / "assets_omnidash" / "communities" / "avatar_miku.png"
        if av_p.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(av_p)), 20, 20, 10))
        st_row.addWidget(av_lbl)

        name_lbl = QLabel(streamer)
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #BDD4E4;")
        st_row.addWidget(name_lbl)
        st_row.addStretch(1)
        info_lay.addLayout(st_row)

        info_lay.addStretch(1)

        act_row = QHBoxLayout()
        act_row.setSpacing(10)

        play_btn = QPushButton(" ▶  Ver stream")
        play_btn.setCursor(Qt.PointingHandCursor)
        play_btn.setFixedHeight(34)
        play_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                border: 1.5px solid rgba(255, 255, 255, 0.35);
                border-radius: 12px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(53, 200, 241, 0.3);
                border: 1.5px solid #35C8F1;
            }
        """)
        play_btn.clicked.connect(lambda: self.play_stream.emit(title))
        act_row.addWidget(play_btn)

        pop_btn = QPushButton(" ↗ ")
        pop_btn.setCursor(Qt.PointingHandCursor)
        pop_btn.setFixedSize(34, 34)
        pop_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 10px;
                color: #ffffff;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.18);
            }
        """)
        act_row.addWidget(pop_btn)
        act_row.addStretch(1)
        info_lay.addLayout(act_row)

        layout.addLayout(info_lay, 1)


class ChatMessageWidget(QWidget):
    def __init__(self, author: str, time_str: str, text: str, avatar_path: Path, has_crown: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        av_lbl = QLabel()
        av_lbl.setFixedSize(36, 36)
        if avatar_path.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(avatar_path)), 36, 36, 18))
        layout.addWidget(av_lbl, 0, Qt.AlignTop)

        content_lay = QVBoxLayout()
        content_lay.setSpacing(3)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(6)

        name_lbl = QLabel(author)
        name_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff;")
        hdr_row.addWidget(name_lbl)

        if has_crown:
            cr_lbl = QLabel()
            cr_p = ROOT / "assets_omnidash" / "icons" / "crown.png"
            if cr_p.exists():
                cr_lbl.setPixmap(QPixmap(str(cr_p)).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            hdr_row.addWidget(cr_lbl)

        t_lbl = QLabel(time_str)
        t_lbl.setStyleSheet("font-size: 11px; color: #7f95a6; font-weight: 500;")
        hdr_row.addWidget(t_lbl)
        hdr_row.addStretch(1)
        content_lay.addLayout(hdr_row)

        txt_lbl = QLabel(text)
        txt_lbl.setStyleSheet("font-size: 13px; color: #F4F6F8; line-height: 1.4;")
        txt_lbl.setWordWrap(True)
        content_lay.addWidget(txt_lbl)

        layout.addLayout(content_lay, 1)


class CentralChatWidget(QWidget):
    message_sent = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 4)
        layout.setSpacing(8)

        c_hdr = QHBoxLayout()
        c_hdr.setContentsMargins(8, 4, 8, 8)
        c_hdr.setSpacing(10)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        self.c_title = QLabel("# general")
        self.c_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")
        self.c_topic = QLabel("Conversación general de la comunidad.")
        self.c_topic.setStyleSheet("font-size: 12px; color: #BDD4E4;")
        t_box.addWidget(self.c_title)
        t_box.addWidget(self.c_topic)
        c_hdr.addLayout(t_box)
        c_hdr.addStretch(1)

        for ico_name in ["bell_badge", "pin", "friends_duo", "more_horizontal"]:
            b = QPushButton()
            b.setFixedSize(30, 30)
            b.setCursor(Qt.PointingHandCursor)
            ip = ROOT / "assets_omnidash" / "icons" / f"{ico_name}.png"
            if ip.exists():
                b.setIcon(QIcon(str(ip)))
                b.setIconSize(QSize(16, 16))
            b.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
            """)
            c_hdr.addWidget(b)

        layout.addLayout(c_hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(145, 165, 179, 0.2);")
        layout.addWidget(sep)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.msgs_container = QWidget()
        self.msgs_layout = QVBoxLayout(self.msgs_container)
        self.msgs_layout.setContentsMargins(6, 10, 6, 10)
        self.msgs_layout.setSpacing(10)

        self._load_initial_messages()

        self.msgs_layout.addStretch(1)
        self.scroll.setWidget(self.msgs_container)
        layout.addWidget(self.scroll, 1)

        comp_frame = QFrame()
        comp_frame.setFixedHeight(55)
        comp_frame.setStyleSheet("""
            QFrame {
                background: rgba(18, 38, 56, 0.85);
                border: 1.5px solid rgba(145, 165, 179, 0.35);
                border-radius: 14px;
            }
        """)
        comp_lay = QHBoxLayout(comp_frame)
        comp_lay.setContentsMargins(10, 0, 10, 0)
        comp_lay.setSpacing(8)

        add_b = QPushButton("+")
        add_b.setFixedSize(28, 28)
        add_b.setCursor(Qt.PointingHandCursor)
        add_b.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                font-size: 16px;
                font-weight: 700;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.25);
            }
        """)
        comp_lay.addWidget(add_b)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Enviar mensaje a #general...")
        self.msg_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 13px;
            }
        """)
        self.msg_input.returnPressed.connect(self._send_current_message)
        comp_lay.addWidget(self.msg_input, 1)

        emojis = [("smile", "😊"), ("image", "🖼️"), ("gift", "🎁")]
        for _, em_char in emojis:
            eb = QPushButton(em_char)
            eb.setFixedSize(28, 28)
            eb.setCursor(Qt.PointingHandCursor)
            eb.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; } QPushButton:hover { background: rgba(255, 255, 255, 0.1); border-radius: 6px; }")
            comp_lay.addWidget(eb)

        send_b = QPushButton()
        send_b.setFixedSize(30, 30)
        send_b.setCursor(Qt.PointingHandCursor)
        send_p = ROOT / "assets_omnidash" / "icons" / "paper_plane.png"
        if send_p.exists():
            send_b.setIcon(QIcon(str(send_p)))
            send_b.setIconSize(QSize(15, 15))
        send_b.setStyleSheet("""
            QPushButton {
                background: #35C8F1;
                border-radius: 15px;
                border: none;
            }
            QPushButton:hover {
                background: #60d7f7;
            }
        """)
        send_b.clicked.connect(self._send_current_message)
        comp_lay.addWidget(send_b)

        layout.addWidget(comp_frame)

    def _load_initial_messages(self):
        m1 = ChatMessageWidget(
            "Enni", "Hoy a las 21:12",
            "¿Alguien se suma para una partida de Metal Slug 2? 👀",
            ROOT / "assets_omnidash" / "communities" / "avatar_enni.png",
            has_crown=True
        )
        self.msgs_layout.addWidget(m1)

        m2 = ChatMessageWidget(
            "Alex", "Hoy a las 21:15",
            "¡Yo me prendo! ¿Armamos sala? 🎮",
            ROOT / "assets_omnidash" / "spidey_avatar.png"
        )
        self.msgs_layout.addWidget(m2)

        m3 = ChatMessageWidget(
            "Miku", "Hoy a las 21:20",
            "Estoy en stream ahora, pasen a ver 👾",
            ROOT / "assets_omnidash" / "communities" / "avatar_miku.png"
        )
        self.msgs_layout.addWidget(m3)

        thumb_p = ROOT / "assets_omnidash" / "communities" / "stream_mslug2_preview.jpg"
        if not thumb_p.exists():
            thumb_p = ROOT / "assets_omnidash" / "covers" / "arcade_mslug.png"
        self.stream_card = StreamCard("Metal Slug 2 - Arcade Run", "Miku", 12, thumb_p)
        self.msgs_layout.addWidget(self.stream_card)

        m4 = ChatMessageWidget(
            "Lau", "Hoy a las 21:28",
            "¡Qué partida! 🔥",
            ROOT / "assets_omnidash" / "communities" / "avatar_lau.png"
        )
        self.msgs_layout.addWidget(m4)

    def _send_current_message(self):
        txt = self.msg_input.text().strip()
        if not txt:
            return
        self.msg_input.clear()
        m = ChatMessageWidget("Alex", "Ahora", txt, ROOT / "assets_omnidash" / "spidey_avatar.png")
        count = self.msgs_layout.count()
        self.msgs_layout.insertWidget(count - 1, m)
        try:
            repo = CommunitiesRepository.get_instance()
            comm = repo.get_community_by_slug("seeker-hub")
            if comm:
                chans = repo.list_channels(comm["id"])
                g_ch = [c for c in chans if c["name"] == "general"]
                if g_ch:
                    repo.create_message(g_ch[0]["id"], "u_alex", txt)
        except Exception:
            pass
        self.message_sent.emit(txt)


class MemberItemWidget(QWidget):
    def __init__(self, name: str, status_text: str, is_online: bool, avatar_path: Path, has_crown: bool = False, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        av_container = QFrame()
        av_container.setFixedSize(32, 32)
        av_lay = QVBoxLayout(av_container)
        av_lay.setContentsMargins(0, 0, 0, 0)

        av_lbl = QLabel()
        if avatar_path.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(avatar_path)), 30, 30, 15))
        av_lay.addWidget(av_lbl)

        layout.addWidget(av_container)

        info = QVBoxLayout()
        info.setSpacing(1)

        n_row = QHBoxLayout()
        n_row.setSpacing(4)
        nl = QLabel(name)
        nl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        n_row.addWidget(nl)

        if has_crown:
            cr = QLabel()
            cr_p = ROOT / "assets_omnidash" / "icons" / "crown.png"
            if cr_p.exists():
                cr.setPixmap(QPixmap(str(cr_p)).scaled(13, 13, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            n_row.addWidget(cr)

        n_row.addStretch(1)
        info.addLayout(n_row)

        st = QLabel(status_text)
        if "stream" in status_text.lower() or "transmitiendo" in status_text.lower():
            st_color = "#A77AE4"
        elif "jugando" in status_text.lower() or "partida" in status_text.lower():
            st_color = "#32D875"
        else:
            st_color = "#7f95a6"
        st.setStyleSheet(f"font-size: 11px; color: {st_color};")
        info.addWidget(st)

        layout.addLayout(info, 1)


class RightPanel(QWidget):
    voice_toggled = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(305)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 6)
        layout.setSpacing(10)

        m_scroll = QScrollArea()
        m_scroll.setWidgetResizable(True)
        m_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        m_container = QWidget()
        m_lay = QVBoxLayout(m_container)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_lay.setSpacing(4)

        on_hdr = QLabel("●  En línea — 14")
        on_hdr.setStyleSheet("font-size: 12px; font-weight: 800; color: #32D875; padding: 4px 6px;")
        m_lay.addWidget(on_hdr)

        online_members = [
            ("Alex", "Jugando: Metal Slug 2", ROOT / "assets_omnidash" / "spidey_avatar.png", False),
            ("Enni", "En stream", ROOT / "assets_omnidash" / "communities" / "avatar_enni.png", True),
            ("Miku", "Transmitiendo", ROOT / "assets_omnidash" / "communities" / "avatar_miku.png", False),
            ("Lau", "Jugando: Tetris", ROOT / "assets_omnidash" / "communities" / "avatar_lau.png", False),
            ("Rami", "En partida", ROOT / "assets_omnidash" / "communities" / "avatar_rami.png", False),
        ]
        for name, st, av, crown in online_members:
            m_lay.addWidget(MemberItemWidget(name, st, True, av, has_crown=crown))

        m_lay.addSpacing(10)

        off_hdr = QLabel("●  Búsqueda — 28")
        off_hdr.setStyleSheet("font-size: 12px; font-weight: 800; color: #7f95a6; padding: 4px 6px;")
        m_lay.addWidget(off_hdr)

        offline_members = [
            ("Tomi", "Desconectado", ROOT / "assets_omnidash" / "communities" / "avatar_tomi.png"),
            ("Vale", "Desconectado", ROOT / "assets_omnidash" / "communities" / "avatar_vale.png"),
        ]
        for name, st, av in offline_members:
            m_lay.addWidget(MemberItemWidget(name, st, False, av))

        m_lay.addStretch(1)
        m_scroll.setWidget(m_container)
        layout.addWidget(m_scroll, 1)

        self.voice_panel = AcrylicGlassCard(
            self,
            border_radius=18,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10
        )
        self.voice_panel.setFixedHeight(175)
        v_lay = QVBoxLayout(self.voice_panel)
        v_lay.setContentsMargins(14, 14, 14, 14)
        v_lay.setSpacing(12)

        v_hdr = QHBoxLayout()
        v_hdr.setSpacing(8)

        v_wave = QLabel()
        wave_p = ROOT / "assets_omnidash" / "icons" / "sound_wave.png"
        if wave_p.exists():
            v_wave.setPixmap(QPixmap(str(wave_p)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v_hdr.addWidget(v_wave)

        v_titles = QVBoxLayout()
        v_titles.setSpacing(1)
        v_st = QLabel("Voz conectada")
        v_st.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff;")
        v_chan = QLabel("Lobby General")
        v_chan.setStyleSheet("font-size: 12px; font-weight: 600; color: #BDD4E4;")
        v_titles.addWidget(v_st)
        v_titles.addWidget(v_chan)
        v_hdr.addLayout(v_titles)
        v_hdr.addStretch(1)

        user_ico = QLabel()
        u_p = ROOT / "assets_omnidash" / "icons" / "person.png"
        if u_p.exists():
            user_ico.setPixmap(QPixmap(str(u_p)).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v_hdr.addWidget(user_ico)

        v_lay.addLayout(v_hdr)

        ctrls_row = QHBoxLayout()
        ctrls_row.setSpacing(10)

        self.mic_btn = QPushButton()
        self.mic_btn.setFixedSize(42, 42)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_muted = False
        self._update_mic_style()
        self.mic_btn.clicked.connect(self._toggle_mic)
        ctrls_row.addWidget(self.mic_btn)

        self.headset_btn = QPushButton()
        self.headset_btn.setFixedSize(42, 42)
        self.headset_btn.setCursor(Qt.PointingHandCursor)
        self.headset_muted = False
        self._update_headset_style()
        self.headset_btn.clicked.connect(self._toggle_headset)
        ctrls_row.addWidget(self.headset_btn)

        self.screen_btn = QPushButton()
        self.screen_btn.setFixedSize(42, 42)
        self.screen_btn.setCursor(Qt.PointingHandCursor)
        self.screen_active = False
        self._update_screen_style()
        self.screen_btn.clicked.connect(self._toggle_screen)
        ctrls_row.addWidget(self.screen_btn)

        self.dc_btn = QPushButton()
        self.dc_btn.setFixedSize(42, 42)
        self.dc_btn.setCursor(Qt.PointingHandCursor)
        dc_p = ROOT / "assets_omnidash" / "icons" / "phone_disconnect.png"
        if dc_p.exists():
            self.dc_btn.setIcon(QIcon(str(dc_p)))
            self.dc_btn.setIconSize(QSize(20, 20))
        self.dc_btn.setStyleSheet("""
            QPushButton {
                background: #E94B56;
                border-radius: 21px;
                border: none;
            }
            QPushButton:hover {
                background: #ff606c;
            }
        """)
        self.dc_btn.clicked.connect(self._disconnect_voice)
        ctrls_row.addWidget(self.dc_btn)

        v_lay.addLayout(ctrls_row)
        layout.addWidget(self.voice_panel)

    def _toggle_mic(self):
        self.mic_muted = not self.mic_muted
        self._update_mic_style()
        self.voice_toggled.emit("mic", not self.mic_muted)

    def _update_mic_style(self):
        mic_p = ROOT / "assets_omnidash" / "icons" / "microphone.png"
        if mic_p.exists():
            self.mic_btn.setIcon(QIcon(str(mic_p)))
            self.mic_btn.setIconSize(QSize(18, 18))
        if self.mic_muted:
            self.mic_btn.setStyleSheet("QPushButton { background: rgba(233, 75, 86, 0.85); border: 1.5px solid #E94B56; border-radius: 19px; }")
        else:
            self.mic_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 19px; } QPushButton:hover { background: rgba(255, 255, 255, 0.25); }")

    def _toggle_headset(self):
        self.headset_muted = not self.headset_muted
        self._update_headset_style()
        self.voice_toggled.emit("headset", not self.headset_muted)

    def _update_headset_style(self):
        hs_p = ROOT / "assets_omnidash" / "icons" / "headset.png"
        if hs_p.exists():
            self.headset_btn.setIcon(QIcon(str(hs_p)))
            self.headset_btn.setIconSize(QSize(18, 18))
        if self.headset_muted:
            self.headset_btn.setStyleSheet("QPushButton { background: rgba(120, 120, 120, 0.6); border: 1.5px solid #888888; border-radius: 19px; }")
        else:
            self.headset_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 19px; } QPushButton:hover { background: rgba(255, 255, 255, 0.25); }")

    def _toggle_screen(self):
        self.screen_active = not self.screen_active
        self._update_screen_style()
        self.voice_toggled.emit("screen", self.screen_active)

    def _update_screen_style(self):
        sc_p = ROOT / "assets_omnidash" / "icons" / "screen_share.png"
        if sc_p.exists():
            self.screen_btn.setIcon(QIcon(str(sc_p)))
            self.screen_btn.setIconSize(QSize(18, 18))
        if self.screen_active:
            self.screen_btn.setStyleSheet("QPushButton { background: rgba(53, 200, 241, 0.3); border: 1.5px solid #35C8F1; border-radius: 19px; }")
        else:
            self.screen_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 19px; } QPushButton:hover { background: rgba(255, 255, 255, 0.2); }")

    def _disconnect_voice(self):
        self.voice_panel.hide()
        self.voice_toggled.emit("disconnect", False)


class CommunityInteriorView(AcrylicGlassCard):
    back_to_explore = Signal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            border_radius=30,
            border_color=QColor(145, 165, 179, 85),
            glow_color=QColor(0, 0, 0, 75),
            glow_radius=14
        )
        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(20, 16, 20, 18)
        main_lay.setSpacing(12)

        hdr_row = QHBoxLayout()
        hdr_row.setContentsMargins(4, 0, 4, 4)
        hdr_row.setSpacing(12)

        logo_box = QHBoxLayout()
        logo_box.setSpacing(10)

        ico_lbl = QLabel()
        ico_p = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not ico_p.exists():
            ico_p = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if ico_p.exists():
            ico_lbl.setPixmap(QPixmap(str(ico_p)).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_box.addWidget(ico_lbl)

        txt_v = QVBoxLayout()
        txt_v.setSpacing(0)
        t_cci = QLabel("C.C.I.")
        t_cci.setStyleSheet("font-size: 20px; font-weight: 900; color: #ffffff; letter-spacing: 1.5px;")
        t_com = QLabel("Communities")
        t_com.setStyleSheet("font-size: 11px; font-weight: 800; color: #35C8F1; letter-spacing: 1px;")
        txt_v.addWidget(t_cci)
        txt_v.addWidget(t_com)
        logo_box.addLayout(txt_v)
        hdr_row.addLayout(logo_box)

        sep = QLabel("|")
        sep.setStyleSheet("color: rgba(255, 255, 255, 60); font-size: 26px; font-weight: 200; margin: 0 4px;")
        hdr_row.addWidget(sep)

        desc_v = QVBoxLayout()
        desc_v.setSpacing(2)
        m_title = QLabel("Gaming Communities & Friends")
        m_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        m_desc = QLabel("Crea comunidades, juega, conversa y transmite con tu gente.")
        m_desc.setStyleSheet("font-size: 12px; color: #BDD4E4;")
        desc_v.addWidget(m_title)
        desc_v.addWidget(m_desc)
        hdr_row.addLayout(desc_v)

        hdr_row.addStretch(1)

        search_frame = QFrame()
        search_frame.setFixedHeight(38)
        search_frame.setFixedWidth(220)
        search_frame.setStyleSheet("""
            QFrame {
                background: rgba(14, 28, 42, 0.7);
                border: 1px solid rgba(145, 165, 179, 0.3);
                border-radius: 19px;
            }
        """)
        s_lay = QHBoxLayout(search_frame)
        s_lay.setContentsMargins(12, 0, 12, 0)
        s_lay.setSpacing(8)

        s_ico = QLabel()
        s_p = ROOT / "assets_omnidash" / "icons" / "search.png"
        if s_p.exists():
            s_ico.setPixmap(QPixmap(str(s_p)).scaled(14, 14, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        s_lay.addWidget(s_ico)

        s_inp = QLineEdit()
        s_inp.setPlaceholderText("Buscar en C.C.I...")
        s_inp.setStyleSheet("background: transparent; border: none; color: #ffffff; font-size: 12px;")
        s_lay.addWidget(s_inp)
        hdr_row.addWidget(search_frame)

        add_comm_btn = QPushButton("+")
        add_comm_btn.setFixedSize(38, 38)
        add_comm_btn.setCursor(Qt.PointingHandCursor)
        add_comm_btn.setToolTip("Crear Comunidad")
        add_comm_btn.setStyleSheet("""
            QPushButton {
                background: rgba(18, 38, 56, 0.75);
                border: 1px solid rgba(145, 165, 179, 0.4);
                border-radius: 19px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(53, 200, 241, 0.25);
                border: 1.5px solid #35C8F1;
            }
        """)
        hdr_row.addWidget(add_comm_btn)

        invite_btn = QPushButton()
        invite_btn.setFixedSize(38, 38)
        invite_btn.setCursor(Qt.PointingHandCursor)
        invite_btn.setToolTip("Invitar Amigos")
        inv_p = ROOT / "assets_omnidash" / "icons" / "person_add.png"
        if not inv_p.exists():
            inv_p = ROOT / "assets_omnidash" / "icons" / "people.png"
        if inv_p.exists():
            invite_btn.setIcon(QIcon(str(inv_p)))
            invite_btn.setIconSize(QSize(18, 18))
        invite_btn.setStyleSheet("""
            QPushButton {
                background: rgba(18, 38, 56, 0.75);
                border: 1px solid rgba(145, 165, 179, 0.4);
                border-radius: 19px;
            }
            QPushButton:hover {
                background: rgba(53, 200, 241, 0.25);
                border: 1.5px solid #35C8F1;
            }
        """)
        hdr_row.addWidget(invite_btn)

        main_lay.addLayout(hdr_row)

        body_row = QHBoxLayout()
        body_row.setSpacing(12)

        self.rail = ServerRail(self)
        self.rail.explore_clicked.connect(self.back_to_explore.emit)
        body_row.addWidget(self.rail)

        self.channel_sidebar = ChannelSidebar(self)
        body_row.addWidget(self.channel_sidebar)

        self.chat_area = CentralChatWidget(self)
        body_row.addWidget(self.chat_area, 1)

        self.right_panel = RightPanel(self)
        body_row.addWidget(self.right_panel)

        main_lay.addLayout(body_row, 1)


class CommunityExploreView(QWidget):
    open_community_requested = Signal(str)

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

        try:
            repo = CommunitiesRepository.get_instance()
            service = CommunitiesService(repo)
            rooms = service.list_rooms()
        except Exception:
            rooms = []

        if not rooms:
            rooms = [
                {"id": "seeker-hub", "name": "Seeker Hub Central", "description": "3 friends playing Metal Slug 2", "members_count": 14},
                {"id": "night-raid", "name": "Night Raid Elite", "description": "Street Fighter II Turbo Tournament", "members_count": 8},
                {"id": "retro-preservation", "name": "Retro Preservation Society", "description": "Castlevania Symphony of the Night Party", "members_count": 22},
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
            join_btn.clicked.connect(lambda _, cid=r.get("id"): self.open_community_requested.emit(cid))
            c_lay.addWidget(join_btn)

            p_lay.addWidget(card)

        p_lay.addStretch(1)
        layout.addWidget(self.panel)


class CommunitiesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 12, 44, 20)

        self.internal_stack = QStackedWidget(self)
        layout.addWidget(self.internal_stack)

        self.explore_view = CommunityExploreView(self)
        self.interior_view = CommunityInteriorView(self)

        self.internal_stack.addWidget(self.explore_view)   # Index 0: Catálogo / Explorar
        self.internal_stack.addWidget(self.interior_view)  # Index 1: Interior de Comunidad (1:1 Imagen 2)

        # Conectar navegación
        self.explore_view.open_community_requested.connect(self.show_interior)
        self.interior_view.back_to_explore.connect(self.show_explore)

        # Mostrar interior por defecto para alineación con Imagen 2
        self.internal_stack.setCurrentIndex(1)

    def show_interior(self, community_id: str = "seeker-hub"):
        self.internal_stack.setCurrentIndex(1)

    def show_explore(self):
        self.internal_stack.setCurrentIndex(0)


# Alias para retrocompatibilidad
FriendsView = CommunityExploreView



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
        self.resize(1672, 941)
        self.setMinimumSize(1280, 720)

        # Cargar fondo predeterminado (prioriza background.jpg subido por el usuario)
        self.bg_pixmap = None
        self.bg_path = ROOT / "background.jpg"
        if not self.bg_path.exists():
            self.bg_path = ROOT / "assets_omnidash" / "aero-background.webp"
        if self.bg_path.exists():
            self.bg_pixmap = QPixmap(str(self.bg_path))
            update_global_blurred_wallpaper(self.bg_path, (1672, 941))

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
        self.communities_view = CommunitiesView(self)
        self.friends_view = self.communities_view.explore_view
        self.profile_view = ProfileView(self)

        # Registrar en stack
        self.stack.addWidget(self.home_view)          # 0: HOME
        self.stack.addWidget(self.library_view)       # 1: LIBRARY
        self.stack.addWidget(self.details_view)       # 2: DETAILS
        self.stack.addWidget(self.settings_view)      # 3: SETTINGS
        self.stack.addWidget(self.communities_view)   # 4: COMMUNITY / COMMUNITIES / FRIENDS
        self.stack.addWidget(self.profile_view)       # 5: PROFILE

        # Conectar señales
        self.home_view.navigate_to.connect(self.switch_view)
        self.home_view.open_details.connect(self.show_details)
        self.home_view.launch_game.connect(self.launch_game)

        self.library_view.open_game.connect(self.show_details)
        self.library_view.back_home.connect(lambda: self.switch_view("HOME"))

        self.details_view.back_to_library.connect(lambda: self.switch_view("LIBRARY"))
        self.details_view.launch_game.connect(self.launch_game)

        self.settings_view.wallpaper_changed.connect(self.set_wallpaper)

        # Conectar Stream Card para lanzar juego en directo
        self.communities_view.interior_view.chat_area.stream_card.play_stream.connect(
            lambda _: self.launch_game({
                "title": "Metal Slug 2",
                "core": "cores/fbneo_libretro.dylib",
                "rom": "roms/arcade/mslug2.zip"
            })
        )

    def set_wallpaper(self, path: str):
        p = Path(path).resolve()
        if p.exists():
            self.bg_path = p
            self.bg_pixmap = QPixmap(str(p))
            self._cached_bg = None
            update_global_blurred_wallpaper(p, (self.width(), self.height()))
            self.update()
            for child in self.findChildren(AcrylicGlassCard):
                child.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._cached_bg = None
        if hasattr(self, "bg_path") and self.bg_path:
            update_global_blurred_wallpaper(self.bg_path, (self.width(), self.height()))
            self.update()
            for child in self.findChildren(AcrylicGlassCard):
                child.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.bg_pixmap and not self.bg_pixmap.isNull():
            # Renderizado nativo 4K Ultra-HD para pantallas Retina HiDPI
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else float(self.devicePixelRatio())
            pw = max(100, int(self.width() * dpr))
            ph = max(100, int(self.height() * dpr))

            if (
                not hasattr(self, "_cached_bg")
                or self._cached_bg is None
                or getattr(self, "_cached_bg_size", None) != (pw, ph)
                or getattr(self, "_cached_bg_path", None) != self.bg_path
            ):
                scaled = self.bg_pixmap.scaled(
                    pw, ph, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
                scaled.setDevicePixelRatio(dpr)
                self._cached_bg = scaled
                self._cached_bg_size = (pw, ph)
                self._cached_bg_path = self.bg_path

            painter.drawPixmap(0, 0, self._cached_bg)
        else:
            painter.fillRect(self.rect(), QColor(10, 45, 80))

    def switch_view(self, view_id: str):
        mapping = {
            "HOME": 0,
            "LIBRARY": 1,
            "DETAILS": 2,
            "SETTINGS": 3,
            "COMMUNITY": 4,
            "COMMUNITIES": 4,
            "FRIENDS": 4,
            "PROFILE": 5,
        }
        idx = mapping.get(view_id, 0)
        self.stack.setCurrentIndex(idx)
        if view_id == "FRIENDS":
            self.communities_view.show_explore()
        elif view_id in ("COMMUNITY", "COMMUNITIES"):
            self.communities_view.show_interior()
        self.nav_bar.set_active_view(view_id)

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
