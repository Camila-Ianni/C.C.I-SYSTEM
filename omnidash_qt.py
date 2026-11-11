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
import re
import sqlite3
from pathlib import Path
from datetime import datetime

os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from PySide6.QtCore import (
    Qt, QSize, QTimer, QRectF, QPropertyAnimation, QEasingCurve, Signal, Slot, QPoint, QPointF, QByteArray, QProcess
)
from PySide6.QtGui import (
    QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap, QLinearGradient, QRadialGradient, QBrush, QPen, QImage, QPalette
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QLineEdit, QScrollArea, QGridLayout, QFrame, QSizePolicy,
    QProgressBar, QSlider, QFileDialog, QGraphicsDropShadowEffect, QDialog, QMessageBox,
    QComboBox, QMenu, QCheckBox, QInputDialog
)

from cci_console import CATALOG, UserData
from cci_users import UserManager
from retro_core_runner import LibretroRunner
from backend.communities.desktop_client import CommunityApiError, CommunityController, CommunitySession
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
    font-family: "Helvetica Neue", "Segoe UI", Arial;
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
        inner_aura: QColor | None = None,
        aura_strength: float = 1.0,
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
        self.inner_aura = inner_aura
        self.aura_strength = aura_strength
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

        # 2.8 Aura luminosa interior temática (difuminación centrada + halo suave en bordes)
        if self.inner_aura and self.inner_aura.alpha() > 0:
            r_col, g_col, b_col, base_a = (
                self.inner_aura.red(),
                self.inner_aura.green(),
                self.inner_aura.blue(),
                self.inner_aura.alpha(),
            )
            strength = max(0.25, self.aura_strength * (1.20 if active else 1.0))

            # Sutil profundidad periférica para que el brillo nazca en el centro del cristal
            edge_vig = QRadialGradient(w * 0.5, h * 0.44, max(w, h) * 0.64)
            edge_vig.setColorAt(0.0, QColor(0, 0, 0, 0))
            edge_vig.setColorAt(0.55, QColor(5, 12, 22, 18))
            edge_vig.setColorAt(1.0, QColor(4, 10, 20, 72))
            painter.fillRect(0, 0, w, h, QBrush(edge_vig))

            # Difuminación radial suave centrada detrás del icono y el título
            rad = max(w, h) * 0.52
            aura_rad = QRadialGradient(w * 0.5, h * 0.42, rad)
            core_r = min(255, int(r_col * 0.85 + 255 * 0.15))
            core_g = min(255, int(g_col * 0.85 + 255 * 0.15))
            core_b = min(255, int(b_col * 0.85 + 255 * 0.15))
            aura_rad.setColorAt(0.0, QColor(core_r, core_g, core_b, min(235, int(base_a * 1.20 * strength))))
            aura_rad.setColorAt(0.36, QColor(r_col, g_col, b_col, min(190, int(base_a * 0.74 * strength))))
            aura_rad.setColorAt(0.72, QColor(r_col, g_col, b_col, min(95, int(base_a * 0.24 * strength))))
            aura_rad.setColorAt(1.0, QColor(r_col, g_col, b_col, 0))
            painter.fillRect(0, 0, w, h, QBrush(aura_rad))

            # Halo interior suave mezclado hacia blanco para fundir el borde sin línea marcada
            rim_r = min(255, int(r_col * 0.45 + 255 * 0.55))
            rim_g = min(255, int(g_col * 0.45 + 255 * 0.55))
            rim_b = min(255, int(b_col * 0.45 + 255 * 0.55))
            for pen_w, mult in ((14.0, 0.08), (7.5, 0.15), (3.0, 0.26)):
                painter.setPen(QPen(QColor(rim_r, rim_g, rim_b, min(195, int(base_a * mult * strength))), pen_w))
                painter.drawPath(path)

        # 3. Reflejo especular Liquid Glass (curva o gradiente superior sobre todo el cristal)
        if self.show_specular:
            spec_h = int(h * 0.42)
            if spec_h > 8:
                spec_grad = QLinearGradient(0, 0, 0, spec_h)
                spec_grad.setColorAt(0.0, QColor(255, 255, 255, 58 if active else 30))
                spec_grad.setColorAt(0.38, QColor(255, 255, 255, 12))
                spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.fillRect(0, 0, w, spec_h, QBrush(spec_grad))

        # 4. Línea de brillo inset superior (hairline de cristal líquido)
        painter.setPen(QColor(255, 255, 255, 190 if active else 125))
        painter.drawLine(self.border_radius, 1, w - self.border_radius, 1)

        painter.restore()

        # 5. Borde luminoso suave integrado con el aura exterior e interior
        if self.inner_aura:
            b_col = self.border_color if self.border_color else self.inner_aura
            br, bg, bb = b_col.red(), b_col.green(), b_col.blue()
            top_c = QColor(
                min(255, int(br * 0.30 + 255 * 0.70)),
                min(255, int(bg * 0.30 + 255 * 0.70)),
                min(255, int(bb * 0.30 + 255 * 0.70)),
                245 if active else 225,
            )
            mid_c = QColor(
                min(255, int(br * 0.62 + 255 * 0.38)),
                min(255, int(bg * 0.62 + 255 * 0.38)),
                min(255, int(bb * 0.62 + 255 * 0.38)),
                215 if active else 185,
            )
            bot_c = QColor(
                min(255, int(br * 0.48 + 255 * 0.52)),
                min(255, int(bg * 0.48 + 255 * 0.52)),
                min(255, int(bb * 0.48 + 255 * 0.52)),
                235 if active else 205,
            )
            rim_grad = QLinearGradient(0, 0, 0, h)
            rim_grad.setColorAt(0.0, top_c)
            rim_grad.setColorAt(0.45, mid_c)
            rim_grad.setColorAt(1.0, bot_c)
            # Halo sutil sobre el propio borde para eliminar aspecto de trazo plano
            painter.setPen(QPen(QColor(mid_c.red(), mid_c.green(), mid_c.blue(), 80), 3.0))
            painter.drawPath(path)
            painter.setPen(QPen(QBrush(rim_grad), 1.45 if active else 1.25))
            painter.drawPath(path)
        elif self.border_color:
            painter.setPen(QPen(self.border_color, 2.2 if active else 1.8))
            painter.drawPath(path)
        elif active:
            painter.setPen(QPen(QColor(0, 210, 255, 230), 1.6))
            painter.drawPath(path)
        else:
            painter.setPen(QPen(QColor(255, 255, 255, 130), 1.3))
            painter.drawPath(path)


# ==============================================================================
# BARRA SUPERIOR DE NAVEGACIÓN DOCK (C.C.I. SYSTEM + LIQUID DOCK + STATUS)
# ==============================================================================
class OmniDashNavBar(QWidget):
    navigate = Signal(str)
    notifications_clicked = Signal()

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
        self.left_stack.setFixedWidth(248)

        # Index 0: Brand Logo C.C.I. SYSTEM (Escala visual destacada 1:1 con Imagen B)
        brand_widget = QWidget()
        brand_box = QHBoxLayout(brand_widget)
        brand_box.setContentsMargins(0, 0, 0, 0)
        brand_box.setSpacing(12)

        ico_lbl = QLabel()
        ico_p = ROOT / "assets_omnidash" / "icons" / "controller_outline.png"
        if not ico_p.exists():
            ico_p = ROOT / "assets_omnidash" / "icons" / "xbox_controller.png"
        if ico_p.exists():
            ico_lbl.setPixmap(QPixmap(str(ico_p)).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_box.addWidget(ico_lbl)

        txt_v = QVBoxLayout()
        txt_v.setSpacing(0)
        t_cci = QLabel("C.C.I.")
        t_cci.setStyleSheet("font-size: 24px; font-weight: 900; color: #ffffff; letter-spacing: 2px;")
        t_sys = QLabel("SYSTEM")
        t_sys.setStyleSheet("font-size: 11px; font-weight: 800; color: #00d2ff; letter-spacing: 3px;")
        txt_v.addWidget(t_cci)
        txt_v.addWidget(t_sys)
        brand_box.addLayout(txt_v)
        brand_box.addStretch(1)
        self.left_stack.addWidget(brand_widget)

        # Index 1: Cápsula de Perfil de Jugador para Comunidades (sincronizada con sesión real)
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
        self.profile_pill.setMinimumWidth(190)
        self.profile_pill.setFixedHeight(44)
        pp_lay = QHBoxLayout(self.profile_pill)
        pp_lay.setContentsMargins(6, 4, 14, 4)
        pp_lay.setSpacing(8)

        av_l = QLabel()
        av_p = ROOT / "assets_omnidash" / "spidey_avatar.png"
        if av_p.exists():
            av_l.setPixmap(get_rounded_pixmap(QPixmap(str(av_p)), 32, 32, 16))
        pp_lay.addWidget(av_l)

        self.nav_player_lbl = QLabel("Invitado  <span style='color: #7f95a6;'>●</span>  Sin sesión")
        self.nav_player_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        pp_lay.addWidget(self.nav_player_lbl)
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
        status_widget = QWidget()
        status_widget.setFixedWidth(248)
        status_box = QHBoxLayout(status_widget)
        status_box.setContentsMargins(0, 0, 0, 0)
        status_box.setSpacing(14)
        status_box.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Campana interactiva con badge real de menciones/notificaciones (sin "1" hardcodeado)
        bell_wrap = QWidget()
        bell_wrap.setFixedSize(32, 30)
        self.bell_btn = QPushButton(bell_wrap)
        self.bell_btn.setGeometry(0, 2, 26, 26)
        self.bell_btn.setCursor(Qt.PointingHandCursor)
        self.bell_btn.setToolTip("Notificaciones y menciones")
        self.bell_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.12); border-radius: 13px; }")
        bell_p = ROOT / "assets_omnidash" / "icons" / "alert.png"
        if not bell_p.exists():
            bell_p = ROOT / "assets_omnidash" / "icons" / "bell_badge.png"
        if bell_p.exists():
            self.bell_btn.setIcon(QIcon(str(bell_p)))
            self.bell_btn.setIconSize(QSize(22, 22))
        else:
            self.bell_btn.setText("🔔")
        self.bell_btn.clicked.connect(self.notifications_clicked.emit)

        self.bell_badge = QLabel("", bell_wrap)
        self.bell_badge.setGeometry(16, 0, 15, 15)
        self.bell_badge.setAlignment(Qt.AlignCenter)
        self.bell_badge.setStyleSheet(
            "background: #E94B56; color: #ffffff; font-size: 9px; font-weight: 800; border-radius: 7.5px;"
        )
        self.bell_badge.setVisible(False)
        status_box.addWidget(bell_wrap)

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

        layout.addWidget(status_widget)

        # Timer para reloj en vivo
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def set_session_user(self, username: Optional[str]):
        if not hasattr(self, "nav_player_lbl"):
            return
        if username:
            import html as _html
            safe_u = _html.escape(str(username))
            self.nav_player_lbl.setText(f"@{safe_u}  <span style='color: #32D875;'>●</span>  En línea")
        else:
            self.nav_player_lbl.setText("Invitado  <span style='color: #7f95a6;'>●</span>  Sin sesión")

    def set_unread_notifications(self, count: int):
        if count and count > 0:
            self.bell_badge.setText(str(count) if count < 10 else "9+")
            self.bell_badge.setVisible(True)
        else:
            self.bell_badge.setVisible(False)

    def set_active_view(self, view_id: str):
        self.current_view = view_id
        if hasattr(self, "left_stack"):
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
# 1. VISTA DE INICIO (HOME REDESIGN - PERSONAL DASHBOARD & RECENT ACTIVITY)
# ==============================================================================
class HomeView(QWidget):
    launch_game = Signal(dict)
    open_details = Signal(dict)
    navigate_to = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Cargar fondo local para renderizado con proporción de aspecto perfecta (sin estirar Spider-Man)
        self.bg_path = ROOT / "background.jpg"
        if not self.bg_path.exists():
            self.bg_path = ROOT / "assets_omnidash" / "aero-background.webp"
        self.bg_pixmap = QPixmap(str(self.bg_path)) if self.bg_path.exists() else None
        self._cached_home_bg = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(52, 10, 52, 26)
        self.layout.setSpacing(14)

        # ----------------------------------------------------------------------
        # 1. SECCIÓN DE ENCABEZADO: PERFIL ALEX + SALUDO (1:1 con Referencia)
        # ----------------------------------------------------------------------
        header_v = QVBoxLayout()
        header_v.setContentsMargins(0, 0, 0, 0)
        header_v.setSpacing(14)

        # 1.1 Cápsula de Perfil de Alex (Fila 1: Alex ●, Fila 2: 18,450 G)
        self.profile_pill = AcrylicGlassCard(
            self,
            border_radius=25,
            is_interactive=True,
            glow_color=QColor(0, 217, 255, 60),
            glow_radius=12,
            border_color=QColor(145, 165, 179, 120),
        )
        self.profile_pill.setFixedSize(210, 50)
        self.profile_pill.setCursor(Qt.PointingHandCursor)
        self.profile_pill.mousePressEvent = lambda _: self.navigate_to.emit("PROFILE")

        pp_lay = QHBoxLayout(self.profile_pill)
        pp_lay.setContentsMargins(8, 4, 14, 4)
        pp_lay.setSpacing(10)

        self.avatar_lbl = QLabel()
        av_p = ROOT / "assets_omnidash" / "spidey_avatar.png"
        if not av_p.exists():
            av_p = ROOT / "assets_omnidash" / "avatar.png"
        if av_p.exists():
            self.avatar_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(av_p)), 40, 40, 20))
        pp_lay.addWidget(self.avatar_lbl)

        txt_v_pill = QVBoxLayout()
        txt_v_pill.setContentsMargins(0, 0, 0, 0)
        txt_v_pill.setSpacing(1)

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)
        name_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.pill_name_lbl = QLabel("Invitado")
        self.pill_name_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #FFFFFF;")
        name_row.addWidget(self.pill_name_lbl)

        self.pill_dot_lbl = QLabel("●")
        self.pill_dot_lbl.setStyleSheet("font-size: 9px; color: #7f95a6; margin-top: 1px;")
        name_row.addWidget(self.pill_dot_lbl)
        txt_v_pill.addLayout(name_row)

        self.pill_score_lbl = QLabel("Sin sesión")
        self.pill_score_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #A8C4D8;")
        txt_v_pill.addWidget(self.pill_score_lbl)

        pp_lay.addLayout(txt_v_pill, 1)

        header_v.addWidget(self.profile_pill, alignment=Qt.AlignLeft)

        # 1.2 Saludo y Bienvenida
        greet_row = QHBoxLayout()
        greet_row.setContentsMargins(0, 0, 0, 0)
        greet_row.setSpacing(14)
        greet_row.setAlignment(Qt.AlignVCenter)

        # Barra vertical cyan luminosa
        self.cyan_bar = QFrame()
        self.cyan_bar.setFixedSize(4, 52)
        self.cyan_bar.setStyleSheet("""
            background: #00D9FF;
            border-radius: 2px;
        """)
        bar_glow = QGraphicsDropShadowEffect(self.cyan_bar)
        bar_glow.setColor(QColor(0, 217, 255, 240))
        bar_glow.setBlurRadius(18)
        bar_glow.setOffset(0, 0)
        self.cyan_bar.setGraphicsEffect(bar_glow)
        greet_row.addWidget(self.cyan_bar)

        # Textos de saludo dinámico
        greet_v = QVBoxLayout()
        greet_v.setSpacing(3)
        greet_v.setContentsMargins(0, 0, 0, 0)

        self.title_lbl = QLabel("¡Bienvenido a C.C.I.!")
        self.title_lbl.setStyleSheet("font-size: 34px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")

        self.sub_lbl = QLabel("Tu centro de juegos, comunidades y amigos.")
        self.sub_lbl.setStyleSheet("font-size: 15px; font-weight: 500; color: #BDD4E4;")

        greet_v.addWidget(self.title_lbl)
        greet_v.addWidget(self.sub_lbl)
        greet_row.addLayout(greet_v)
        greet_row.addStretch(1)

        header_v.addLayout(greet_row)
        self.layout.addLayout(header_v)

        # ----------------------------------------------------------------------
        # 2. CUATRO WIDGETS PRINCIPALES (Row 1)
        # ----------------------------------------------------------------------
        main_widgets_row = QHBoxLayout()
        main_widgets_row.setSpacing(18)

        widgets_data = [
            (
                "Mis juegos y apps",
                f"{len(ALL_GAMES)} juegos listos para jugar",
                "LIBRARY",
                "controller_outline_white.png",
                QColor(55, 215, 255, 195),
                QColor(0, 190, 255, 225),
                QColor(0, 185, 255, 128),
            ),
            (
                "Amigos",
                "Inicia sesión para ver comunidades",
                "COMMUNITY",
                "friends_duo_white.png",
                QColor(180, 222, 250, 205),
                QColor(135, 200, 245, 180),
                QColor(110, 185, 235, 82),
            ),
            (
                "GAME PASS",
                "Descubre cientos de juegos",
                "LIBRARY",
                "xbox_gamepass_white.png",
                QColor(50, 235, 160, 200),
                QColor(0, 220, 130, 230),
                QColor(0, 210, 125, 138),
            ),
            (
                "Logros",
                "18,450 G • 110 trofeos",
                "PROFILE",
                "trophy_white.png",
                QColor(190, 125, 255, 200),
                QColor(165, 85, 255, 230),
                QColor(160, 80, 255, 138),
            ),
        ]

        self.main_cards = []
        for title, subtitle, dest, icon_file, border_c, glow_c, aura_c in widgets_data:
            c = AcrylicGlassCard(
                self,
                border_radius=28,
                is_interactive=True,
                glow_color=glow_c,
                glow_radius=32,
                border_color=border_c,
                inner_aura=aura_c,
                aura_strength=1.0,
            )
            c._orig_border_color = border_c
            c._orig_glow_color = glow_c
            c._orig_glow_radius = 32
            c._orig_inner_aura = aura_c
            c.setFixedHeight(175)

            c_lay = QHBoxLayout(c)
            c_lay.setContentsMargins(16, 18, 16, 18)
            c_lay.setSpacing(0)

            # Espaciador izquierdo balanceador para centrado perfecto de textos
            dummy_l = QWidget()
            dummy_l.setFixedWidth(24)
            c_lay.addWidget(dummy_l)

            # Columna central con Icono, Título y Subtítulo centrados
            center_v = QVBoxLayout()
            center_v.setContentsMargins(0, 0, 0, 0)
            center_v.setSpacing(8)
            center_v.setAlignment(Qt.AlignCenter)

            ico_l = QLabel()
            ico_l.setAlignment(Qt.AlignCenter)
            ico_p = ROOT / "assets_omnidash" / "icons" / "dashboard" / icon_file
            if not ico_p.exists():
                ico_p = ROOT / "assets_omnidash" / "icons" / "grid.png"
            if ico_p.exists():
                ico_l.setPixmap(QPixmap(str(ico_p)).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            center_v.addWidget(ico_l)

            t_l = QLabel(title)
            t_l.setAlignment(Qt.AlignCenter)
            t_l.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
            center_v.addWidget(t_l)

            s_l = QLabel(subtitle)
            s_l.setAlignment(Qt.AlignCenter)
            s_l.setStyleSheet("font-size: 13px; font-weight: 500; color: #BDD4E4;")
            center_v.addWidget(s_l)
            c._subtitle_lbl = s_l

            c_lay.addLayout(center_v, 1)

            # Chevron indicador a la derecha
            chev_l = QLabel("›")
            chev_l.setFixedWidth(24)
            chev_l.setAlignment(Qt.AlignCenter)
            chev_l.setStyleSheet("font-size: 26px; font-weight: 600; color: #BDD4E4;")
            c_lay.addWidget(chev_l)

            c.mousePressEvent = lambda _, d=dest: self.navigate_to.emit(d)
            c.setCursor(Qt.PointingHandCursor)
            self.main_cards.append(c)
            main_widgets_row.addWidget(c, 1)

        self.layout.addLayout(main_widgets_row)

        # ----------------------------------------------------------------------
        # 3. ACTIVIDAD RECIENTE (Header + Carrusel de 3 Tarjetas + Paginación)
        # ----------------------------------------------------------------------
        # Header
        act_header = QHBoxLayout()
        act_header.setContentsMargins(0, 6, 0, 2)
        act_header.setSpacing(10)
        act_header.setAlignment(Qt.AlignVCenter)

        clock_ico = QLabel()
        clock_p = ROOT / "assets_omnidash" / "icons" / "dashboard" / "clock_outline.png"
        if clock_p.exists():
            clock_ico.setPixmap(QPixmap(str(clock_p)).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        act_header.addWidget(clock_ico)

        act_title = QLabel("Actividad reciente")
        act_title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        act_header.addWidget(act_title)
        act_header.addStretch(1)
        self.layout.addLayout(act_header)

        # Fila de carrusel: Flecha Izq + 3 Tarjetas + Flecha Der
        recent_row = QHBoxLayout()
        recent_row.setSpacing(14)
        recent_row.setAlignment(Qt.AlignCenter)

        self.left_arrow = QPushButton("<")
        self.left_arrow.setFixedSize(42, 42)
        self.left_arrow.setCursor(Qt.PointingHandCursor)
        self.left_arrow.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 35, 150);
                border: 1.6px solid rgba(255, 255, 255, 140);
                border-radius: 21px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(0, 217, 255, 160);
                border: 1.6px solid #00D9FF;
            }
        """)
        recent_row.addWidget(self.left_arrow)

        # Datos de juegos recientes modernos en 3 páginas
        self.recent_pages_data = [
            # Página 0 (Destacados actuales)
            [
                ("God of War Ragnarök", "PlayStation 5 • 103 GB", "fotos juegos/33_god_of_war_ragnar_k.jpg", "ps5_god_of_war_ragnarok", True),
                ("Mario Kart 8 Deluxe", "Nintendo Switch • 6.8 GB", "fotos juegos/43_mario_kart_8_deluxe.png", "switch_mario_kart_8_deluxe", False),
                ("Minecraft", "PS3 • Instalado local", "fotos juegos/03_minecraft.jpg", "ps3_minecraft", False),
            ],
            # Página 1
            [
                ("ASTRO BOT", "PlayStation 5 • 37.9 GB", "fotos juegos/34_astro_bot.jpg", "ps5_astro_bot", False),
                ("Gran Turismo Sport", "PlayStation 4 • 40 GB", "fotos juegos/12_gran_turismo_sport.png", "ps4_gran_turismo_sport", False),
                ("Hollow Knight", "Nintendo Switch • 3.6 GB", "fotos juegos/55_hollow_knight.jpg", "switch_hollow_knight", False),
            ],
            # Página 2
            [
                ("Grand Theft Auto V", "PlayStation 5 • 84.4 GB", "fotos juegos/32_grand_theft_auto_v.jpg", "ps5_grand_theft_auto_v", False),
                ("God of War (2018)", "PlayStation 4 • 36 GB", "fotos juegos/15_god_of_war_2018.jpg", "ps4_god_of_war_2018", False),
                ("Resident Evil 4", "Nintendo Switch • 12.1 GB", "fotos juegos/72_resident_evil_4.jpg", "switch_resident_evil_4", False),
            ]
        ]

        self.recent_page = 0
        self.recent_cards_widgets = []

        for slot_idx in range(3):
            is_first = (slot_idx == 0)
            b_col = QColor(45, 220, 255, 205) if is_first else QColor(165, 195, 215, 135)
            g_col = QColor(0, 200, 255, 215) if is_first else QColor(90, 155, 205, 105)
            a_col = QColor(0, 195, 255, 115) if is_first else QColor(105, 175, 225, 42)
            g_rad = 30 if is_first else 18
            c = AcrylicGlassCard(
                self,
                border_radius=24,
                is_interactive=True,
                glow_color=g_col,
                glow_radius=g_rad,
                border_color=b_col,
                inner_aura=a_col,
            )
            c._orig_border_color = b_col
            c._orig_glow_color = g_col
            c._orig_glow_radius = g_rad
            c._orig_inner_aura = a_col
            c.setFixedHeight(138)

            c_lay = QHBoxLayout(c)
            c_lay.setContentsMargins(14, 12, 18, 12)
            c_lay.setSpacing(16)

            # Miniatura de portada redondeada
            thumb_l = QLabel()
            thumb_l.setFixedSize(100, 100)
            c_lay.addWidget(thumb_l)

            # VBox Textos
            txt_v = QVBoxLayout()
            txt_v.setContentsMargins(0, 0, 0, 0)
            txt_v.setSpacing(4)
            txt_v.setAlignment(Qt.AlignVCenter)

            title_l = QLabel()
            title_l.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
            sub_l = QLabel()
            sub_l.setStyleSheet("font-size: 13px; font-weight: 500; color: #BDD4E4;")

            txt_v.addWidget(title_l)
            txt_v.addWidget(sub_l)
            c_lay.addLayout(txt_v, 1)

            # Botón circular de reproducción ▶
            play_btn = QPushButton("▶")
            play_btn.setFixedSize(44, 44)
            play_btn.setCursor(Qt.PointingHandCursor)
            play_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(10, 25, 45, 180);
                    border: 1.5px solid rgba(255, 255, 255, 160);
                    border-radius: 22px;
                    color: #FFFFFF;
                    font-size: 14px;
                    padding-left: 2px;
                }
                QPushButton:hover {
                    background: rgba(0, 217, 255, 180);
                    border: 1.5px solid #00D9FF;
                    color: #FFFFFF;
                }
            """)
            c_lay.addWidget(play_btn)

            slot_data = {
                "card": c,
                "thumb_lbl": thumb_l,
                "title_lbl": title_l,
                "sub_lbl": sub_l,
                "play_btn": play_btn,
                "game": None
            }
            self.recent_cards_widgets.append(slot_data)
            recent_row.addWidget(c, 1)

        self.right_arrow = QPushButton(">")
        self.right_arrow.setFixedSize(42, 42)
        self.right_arrow.setCursor(Qt.PointingHandCursor)
        self.right_arrow.setStyleSheet("""
            QPushButton {
                background: rgba(10, 20, 35, 150);
                border: 1.6px solid rgba(255, 255, 255, 140);
                border-radius: 21px;
                color: #ffffff;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(0, 217, 255, 160);
                border: 1.6px solid #00D9FF;
            }
        """)
        recent_row.addWidget(self.right_arrow)

        self.layout.addLayout(recent_row)

        # Indicadores de página de Actividad reciente (Pills & Dots)
        dots_box = QHBoxLayout()
        dots_box.setContentsMargins(0, 2, 0, 5)
        dots_box.setSpacing(8)
        dots_box.setAlignment(Qt.AlignCenter)
        self.dots = []
        for i in range(3):
            dot = QLabel()
            if i == 0:
                dot.setFixedSize(30, 6)
                dot.setStyleSheet("background: #00D9FF; border-radius: 3px;")
            else:
                dot.setFixedSize(6, 6)
                dot.setStyleSheet("background: rgba(145, 165, 179, 120); border-radius: 3px;")
            dots_box.addWidget(dot)
            self.dots.append(dot)
        self.layout.addLayout(dots_box)

        # Conectar flechas de carrusel
        self.left_arrow.clicked.connect(lambda: self.set_recent_page(self.recent_page - 1))
        self.right_arrow.clicked.connect(lambda: self.set_recent_page(self.recent_page + 1))

        # Poblar slots de la página actual
        self._update_recent_slots()

        # ----------------------------------------------------------------------
        # 4. TRES WIDGETS INFERIORES DE NOVEDADES
        # ----------------------------------------------------------------------
        news_row = QHBoxLayout()
        news_row.setSpacing(18)

        news_data = [
            (
                "Novedades en C.C.I.",
                "Actualizaciones, eventos y comunidad",
                "COMMUNITY",
                "megaphone_outline.png",
                False
            ),
            (
                "Eventos y torneos",
                "Participa y compite con la comunidad",
                "COMMUNITY",
                "calendar_outline.png",
                False
            ),
            (
                "Transmisiones en vivo",
                "Sin transmisiones activas",
                "COMMUNITY",
                "live_signal.png",
                True  # Etiqueta roja EN VIVO (solo visible si hay transmisiones reales > 0)
            ),
        ]

        self.news_cards = []
        for title, subtitle, dest, icon_file, is_live in news_data:
            b_col = QColor(155, 195, 225, 140)
            g_col = QColor(80, 160, 225, 115)
            a_col = QColor(90, 170, 230, 48)
            c = AcrylicGlassCard(
                self,
                border_radius=24,
                is_interactive=True,
                glow_color=g_col,
                glow_radius=20,
                border_color=b_col,
                inner_aura=a_col,
            )
            c._orig_border_color = b_col
            c._orig_glow_color = g_col
            c._orig_glow_radius = 20
            c._orig_inner_aura = a_col
            c.setFixedHeight(114)

            c_lay = QHBoxLayout(c)
            c_lay.setContentsMargins(20, 14, 22, 14)
            c_lay.setSpacing(16)

            # Icono a la izquierda
            ico_l = QLabel()
            ico_p = ROOT / "assets_omnidash" / "icons" / "dashboard" / icon_file
            if ico_p.exists():
                ico_l.setPixmap(QPixmap(str(ico_p)).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            c_lay.addWidget(ico_l)

            # Columna de texto
            txt_v = QVBoxLayout()
            txt_v.setContentsMargins(0, 0, 0, 0)
            txt_v.setSpacing(3)
            txt_v.setAlignment(Qt.AlignVCenter)

            if is_live:
                t_row = QHBoxLayout()
                t_row.setContentsMargins(0, 0, 0, 0)
                t_row.setSpacing(8)
                t_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

                t_lbl = QLabel(title)
                t_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
                t_row.addWidget(t_lbl)

                live_badge = QLabel("EN VIVO")
                live_badge.setStyleSheet("""
                    background: #E94B56;
                    color: #FFFFFF;
                    font-size: 10px;
                    font-weight: 800;
                    border-radius: 6px;
                    padding: 2px 7px;
                """)
                live_badge.setVisible(False)
                self._home_live_badge = live_badge
                t_row.addWidget(live_badge)
                txt_v.addLayout(t_row)
            else:
                t_lbl = QLabel(title)
                t_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
                txt_v.addWidget(t_lbl)

            s_lbl = QLabel(subtitle)
            s_lbl.setStyleSheet("font-size: 12px; font-weight: 500; color: #BDD4E4;")
            txt_v.addWidget(s_lbl)
            if is_live:
                self._home_live_subtitle = s_lbl

            c_lay.addLayout(txt_v, 1)

            # Chevron indicador a la derecha
            chev_l = QLabel("›")
            chev_l.setStyleSheet("font-size: 24px; font-weight: 600; color: #BDD4E4;")
            c_lay.addWidget(chev_l)

            c.mousePressEvent = lambda _, d=dest: self.navigate_to.emit(d)
            c.setCursor(Qt.PointingHandCursor)
            self.news_cards.append(c)
            news_row.addWidget(c, 1)

        self.layout.addLayout(news_row)
        self.layout.addStretch(1)

        # Sistema de foco por teclado unificado
        self.focus_idx = 0
        self.nav_items = []
        for c in self.main_cards:
            self.nav_items.append((c, lambda card=c: card.mousePressEvent(None)))
        for slot in self.recent_cards_widgets:
            self.nav_items.append((slot["card"], lambda s=slot: self.launch_game.emit(s["game"]) if s["game"] else None))
        for c in self.news_cards:
            self.nav_items.append((c, lambda card=c: card.mousePressEvent(None)))

        self._update_focus()

    def set_session_state(
        self,
        username: Optional[str],
        communities_count: int = 0,
        active_streams_count: int = 0,
    ):
        """Actualiza HomeView con la cuenta autenticada real y métricas sin datos ficticios."""
        if username:
            self.pill_name_lbl.setText(username)
            self.pill_dot_lbl.setStyleSheet("font-size: 9px; color: #00E676; margin-top: 1px;")
            self.pill_score_lbl.setText("Cuenta conectada")
            self.title_lbl.setText(f"¡Hola, {username}!")
            if len(self.main_cards) > 1 and hasattr(self.main_cards[1], "_subtitle_lbl"):
                self.main_cards[1]._subtitle_lbl.setText(
                    f"{communities_count} comunidades" if communities_count else "Sin comunidades aún"
                )
        else:
            self.pill_name_lbl.setText("Invitado")
            self.pill_dot_lbl.setStyleSheet("font-size: 9px; color: #7f95a6; margin-top: 1px;")
            self.pill_score_lbl.setText("Sin sesión")
            self.title_lbl.setText("¡Bienvenido a C.C.I.!")
            if len(self.main_cards) > 1 and hasattr(self.main_cards[1], "_subtitle_lbl"):
                self.main_cards[1]._subtitle_lbl.setText("Inicia sesión para ver comunidades")

        if hasattr(self, "_home_live_badge"):
            self._home_live_badge.setVisible(active_streams_count > 0)
        if hasattr(self, "_home_live_subtitle"):
            self._home_live_subtitle.setText(
                f"{active_streams_count} transmisiones activas"
                if active_streams_count > 0
                else "Sin transmisiones activas"
            )

    def _update_bg_cache(self):
        """Calcula el escalado y centrado del fondo Spider-Man preservando exactamente su aspecto 16:9 sin estiramiento."""
        if not hasattr(self, "bg_pixmap") or not self.bg_pixmap or self.bg_pixmap.isNull():
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return

        win = self.window()
        ww = win.width() if win else w
        wh = win.height() if win else (h + 76)
        dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else float(self.devicePixelRatio())

        bw, bh = self.bg_pixmap.width(), self.bg_pixmap.height()
        scale = max(ww / bw, wh / bh)
        nw, nh = max(10, int(bw * scale * dpr)), max(10, int(bh * scale * dpr))

        scaled = self.bg_pixmap.scaled(nw, nh, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Centrar Spider-Man y la luna en el espacio global de la ventana
        ox = max(0, (nw - int(ww * dpr)) // 2)
        oy = max(0, (nh - int(wh * dpr)) // 2)

        # Posición local de HomeView respecto de la ventana (para alinear con el fondo de la barra de navegación)
        pt = self.mapTo(win, QPoint(0, 0)) if win else QPoint(0, 76)
        gx = int(pt.x() * dpr)
        gy = int(pt.y() * dpr)

        cw = int(w * dpr)
        ch = int(h * dpr)

        rx = min(max(0, ox + gx), max(0, scaled.width() - cw))
        ry = min(max(0, oy + gy), max(0, scaled.height() - ch))

        crop = scaled.copy(rx, ry, cw, ch)
        crop.setDevicePixelRatio(dpr)
        self._cached_home_bg = crop

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if getattr(self, "_cached_home_bg", None) and not self._cached_home_bg.isNull():
            painter.drawPixmap(0, 0, self._cached_home_bg)

        # Halo luminoso exterior real alrededor de cada tarjeta sobre el fondo
        cards = []
        if hasattr(self, "main_cards"):
            cards.extend((c, 1.0) for c in self.main_cards)
        if hasattr(self, "recent_cards_widgets"):
            cards.extend((s["card"], 1.0 if s["card"].is_focused or (s["card"].glow_color and s["card"].glow_color.alpha() > 160) else 0.55) for s in self.recent_cards_widgets)
        if hasattr(self, "news_cards"):
            cards.extend((c, 0.55) for c in self.news_cards)

        painter.save()
        painter.setBrush(Qt.NoBrush)
        for card, base_strength in cards:
            if not card.isVisible() or not card.glow_color or card.glow_color.alpha() <= 0:
                continue
            r = card.geometry()
            if r.width() <= 0 or r.height() <= 0:
                continue
            gc = card.glow_color
            strength = base_strength * (1.28 if (card.is_focused or card.is_hovered) else 1.0)
            gr, gg, gb, ga = gc.red(), gc.green(), gc.blue(), gc.alpha()
            br = card.border_radius
            rf = QRectF(r)
            for expand, pen_w, mult, white_mix in (
                (10.0, 14.0, 0.05, 0.10),
                (6.5, 10.0, 0.09, 0.18),
                (3.8, 7.0, 0.14, 0.28),
                (1.8, 4.5, 0.21, 0.40),
                (0.5, 2.5, 0.30, 0.54),
            ):
                cr = min(255, int(gr * (1.0 - white_mix) + 255 * white_mix))
                cg = min(255, int(gg * (1.0 - white_mix) + 255 * white_mix))
                cb = min(255, int(gb * (1.0 - white_mix) + 255 * white_mix))
                alpha = min(195, int(ga * mult * strength))
                if alpha <= 1:
                    continue
                halo_rect = rf.adjusted(-expand, -expand, expand, expand)
                halo_rad = br + expand * 0.72
                painter.setPen(QPen(QColor(cr, cg, cb, alpha), pen_w))
                painter.drawRoundedRect(halo_rect, halo_rad, halo_rad)
        painter.restore()

        super().paintEvent(event)

    def set_recent_page(self, page: int):
        self.recent_page = page % len(self.recent_pages_data)
        for i, dot in enumerate(self.dots):
            if i == self.recent_page:
                dot.setFixedSize(30, 6)
                dot.setStyleSheet("background: #00D9FF; border-radius: 3px;")
            else:
                dot.setFixedSize(6, 6)
                dot.setStyleSheet("background: rgba(145, 165, 179, 120); border-radius: 3px;")
        self._update_recent_slots()

    def _update_recent_slots(self):
        page_items = self.recent_pages_data[self.recent_page]
        for slot_idx, (title, sub, img_rel, game_id, is_active) in enumerate(page_items):
            slot = self.recent_cards_widgets[slot_idx]
            slot["title_lbl"].setText(title)
            slot["sub_lbl"].setText(sub)

            # Buscar juego real en ALL_GAMES
            matched = next((g for g in ALL_GAMES if g.get("id") == game_id), None)
            if not matched:
                matched = next((g for g in ALL_GAMES if title.lower() in g.get("title", "").lower()), None)
            if not matched:
                matched = {"title": title, "console": "PlayStation 5", "badge": "PS5", "cover": img_rel, "on_demand": True}
            slot["game"] = matched

            # Cargar imagen redondeada adaptada al tamaño del slot
            img_p = ROOT / img_rel
            raw = QPixmap(str(img_p)) if img_p.exists() else resolve_game_cover(matched)
            if raw and not raw.isNull():
                ts = slot["thumb_lbl"].width() if slot["thumb_lbl"].width() > 10 else 96
                slot["thumb_lbl"].setPixmap(get_rounded_pixmap(raw, ts, ts, 16))

            # Conectar tarjeta a detalles y botón ▶ al lanzamiento / aviso nube
            slot["card"].mousePressEvent = lambda _, gm=matched: self.open_details.emit(gm)
            if slot.get("connected"):
                try:
                    slot["play_btn"].clicked.disconnect()
                except Exception:
                    pass
            slot["play_btn"].clicked.connect(lambda _, gm=matched: self.launch_game.emit(gm))
            slot["connected"] = True

            # Aura y borde activo de la primera tarjeta en la página 0
            if slot_idx == 0 and self.recent_page == 0:
                slot["card"].border_color = QColor(45, 220, 255, 205)
                slot["card"].inner_aura = QColor(0, 195, 255, 115)
                slot["card"].set_glow(QColor(0, 200, 255, 215), 30)
            else:
                slot["card"].border_color = QColor(165, 195, 215, 135)
                slot["card"].inner_aura = QColor(105, 175, 225, 42)
                slot["card"].set_glow(QColor(90, 155, 205, 105), 18)
            slot["card"].update()

    def _update_focus(self):
        for idx, (card, _) in enumerate(self.nav_items):
            is_active = (idx == self.focus_idx)
            card.set_focused(is_active)
            if hasattr(card, "_orig_border_color"):
                if is_active:
                    orig_aura = getattr(card, "_orig_inner_aura", None)
                    card.border_color = QColor(55, 220, 255, 215) if idx != 0 else card._orig_border_color
                    card.inner_aura = orig_aura if (orig_aura and idx == 0) else (orig_aura or QColor(0, 190, 255, 120))
                    card.set_glow(
                        card._orig_glow_color if idx == 0 else QColor(0, 200, 255, 225),
                        max(32, getattr(card, "_orig_glow_radius", 28) + 4),
                    )
                else:
                    card.border_color = card._orig_border_color
                    card.inner_aura = getattr(card, "_orig_inner_aura", None)
                    card.set_glow(card._orig_glow_color, card._orig_glow_radius)
            card.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0:
            return

        # Factor de escala responsive considerando ancho y altura de ventana real
        sw = w / 1536.0
        sh = h / 884.0
        s = min(max(0.80, min(sw, sh * 1.05)), 1.25)

        for c in self.main_cards:
            c.setFixedHeight(int(175 * s))

        recent_h = int(138 * s)
        thumb_s = int(100 * s)
        for slot in self.recent_cards_widgets:
            slot["card"].setFixedHeight(recent_h)
            slot["thumb_lbl"].setFixedSize(thumb_s, thumb_s)

        for c in self.news_cards:
            c.setFixedHeight(int(114 * s))

        side_margin = max(38, int(52 * sw))
        top_margin = max(8, int(12 * sh))
        bottom_margin = max(14, int(22 * sh))
        spacing = max(9, int(13 * sh))
        self.layout.setContentsMargins(side_margin, top_margin, side_margin, bottom_margin)
        self.layout.setSpacing(spacing)

        self._update_bg_cache()
        self._update_recent_slots()

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
            if self.focus_idx < 4:
                # Salto de fila 1 (0..3) a fila 2 (4..6)
                self.focus_idx = min(6, 4 + (self.focus_idx * 3 // 4))
                self._update_focus()
                return True
            elif 4 <= self.focus_idx < 7:
                # Salto de fila 2 (4..6) a fila 3 (7..9)
                self.focus_idx = min(9, 7 + (self.focus_idx - 4))
                self._update_focus()
                return True
        elif key in (Qt.Key_Up, Qt.Key_W):
            if 7 <= self.focus_idx <= 9:
                self.focus_idx = 4 + (self.focus_idx - 7)
                self._update_focus()
                return True
            elif 4 <= self.focus_idx <= 6:
                self.focus_idx = (self.focus_idx - 4) * 4 // 3
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
    # 1. Carátula oficial registrada por ID
    gid = game.get("id")
    if gid and gid in OFFICIAL_GAME_COVERS:
        cand = ROOT / OFFICIAL_GAME_COVERS[gid]
        if cand.exists():
            pm = QPixmap(str(cand))
            if not pm.isNull():
                return pm

    # 2. Carátula oficial asignada directamente (si no es fallback genérico)
    cov = game.get("cover")
    is_fallback = game.get("cover_is_fallback", False)
    if cov and not is_fallback and not str(cov).startswith("fotos web/") and not str(cov).startswith("assets_omnidash/covers/"):
        if (ROOT / cov).exists():
            pm = QPixmap(str(ROOT / cov))
            if not pm.isNull():
                return pm

    # 3. Búsqueda normalizada inteligente en fotos juegos/
    fj_dir = ROOT / "fotos juegos"
    if fj_dir.exists():
        import unicodedata, re

        def _norm(s: str) -> str:
            t = unicodedata.normalize("NFKD", s or "").encode("ASCII", "ignore").decode("utf-8")
            return re.sub(r"[^a-z0-9]", "", t.lower())

        candidates = [
            _norm(game.get("title") or ""),
            _norm(game.get("clean_title") or ""),
            _norm(gid or ""),
        ]
        target_norms = [c for c in candidates if c]

        all_files = list(fj_dir.glob("*.*"))
        for cand in all_files:
            c_norm = _norm(cand.stem)
            if c_norm in target_norms:
                pm = QPixmap(str(cand))
                if not pm.isNull():
                    return pm

        for cand in all_files:
            c_norm = _norm(cand.stem)
            for tn in target_norms:
                if len(c_norm) >= 5 and len(tn) >= 5 and (c_norm in tn or tn in c_norm):
                    pm = QPixmap(str(cand))
                    if not pm.isNull():
                        return pm

    # 4. Asignación directa como recurso existente (incluso si era fallback)
    if cov and (ROOT / cov).exists():
        pm = QPixmap(str(ROOT / cov))
        if not pm.isNull():
            return pm

    # 5. Fallbacks modernos si un archivo directo faltara
    title = (game.get("title") or "").lower()
    priority_map = [
        ("god of war", ROOT / "fotos juegos" / "33_god_of_war_ragnar_k.jpg"),
        ("mario kart", ROOT / "fotos juegos" / "43_mario_kart_8_deluxe.png"),
        ("minecraft", ROOT / "fotos juegos" / "03_minecraft.jpg"),
        ("astro bot", ROOT / "fotos juegos" / "34_astro_bot.jpg"),
        ("grand theft auto", ROOT / "fotos juegos" / "32_grand_theft_auto_v.jpg"),
        ("hollow knight", ROOT / "fotos juegos" / "55_hollow_knight.jpg"),
        ("resident evil", ROOT / "fotos juegos" / "72_resident_evil_4.jpg"),
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
        self.sub_lbl = QLabel("")
        sub_row.addWidget(self.sub_lbl)
        sub_row.addStretch(1)
        if not hasattr(LibraryGameCard, "refresh_game_state"):
            def _refresh_game_state(card_self, g_data: dict):
                card_self.game = g_data
                f_val = g_data.get("fps", 60)
                sz = g_data.get("size", "Descargar")
                if g_data.get("on_demand"):
                    if g_data.get("has_saved_data"):
                        card_self.sub_lbl.setText(f"☁ Nube • {sz} • 💾 Progreso")
                        card_self.sub_lbl.setStyleSheet("font-size: 12px; color: #56f0c8; font-weight: 700;")
                    else:
                        card_self.sub_lbl.setText(f"☁ En la nube  •  {sz}")
                        card_self.sub_lbl.setStyleSheet("font-size: 13px; color: #56c9e9; font-weight: 600;")
                else:
                    card_self.sub_lbl.setText(f"💾 Instalado  •  {sz}" if sz else f"C.C.I.  •  {f_val} FPS")
                    card_self.sub_lbl.setStyleSheet("font-size: 13px; color: #7ef29d; font-weight: 600;")
            LibraryGameCard.refresh_game_state = _refresh_game_state
        self.refresh_game_state(game)

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

        # Widget Storage: Almacenamiento de consola en tiempo real + gestor tipo PS5
        storage_box = QFrame()
        storage_box.setFixedHeight(120)
        storage_box.setStyleSheet("""
            QFrame {
                background: rgba(20, 38, 54, 0.55);
                border: 1.5px solid rgba(166, 176, 184, 0.3);
                border-radius: 20px;
            }
        """)
        st_lay = QVBoxLayout(storage_box)
        st_lay.setContentsMargins(14, 10, 14, 10)
        st_lay.setSpacing(6)

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
        self.st_title_lbl = st_title
        self.st_sub_lbl = st_sub
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

        self.manage_storage_btn = QPushButton("💾  Gestionar almacenamiento")
        self.manage_storage_btn.setFixedHeight(24)
        self.manage_storage_btn.setCursor(Qt.PointingHandCursor)
        self.manage_storage_btn.setStyleSheet("""
            QPushButton {
                background: rgba(39, 189, 231, 0.18);
                border: 1px solid rgba(39, 189, 231, 0.55);
                border-radius: 8px;
                color: #d8f3ff;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.35);
                border: 1px solid #27bde7;
                color: #ffffff;
            }
        """)
        self.manage_storage_btn.clicked.connect(self.open_storage_manager)
        st_lay.addWidget(self.manage_storage_btn)
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
            ("PlayStation 5", "ps5", "disc_ps.png"),
            ("PlayStation 4", "ps4", "disc_ps.png"),
            ("Nintendo Switch", "switch", "controller_outline.png"),
            ("PlayStation 3", "ps3", "disc_ps.png"),
            ("Instalados locales", "installed", "games.png"),
            ("En la nube", "cloud", "desktop.png"),
            ("Clásicos PS1 / PS2", "ps_classic", "disc_ps.png"),
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
                background: rgba(10, 20, 32, 0.4);
                width: 10px;
                margin: 4px 2px 4px 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(166, 176, 184, 0.65);
                min-height: 48px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(39, 189, 231, 0.95);
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

        self.refresh_storage_indicator()
        self._filter_games()

    def refresh_storage_indicator(self):
        try:
            from backend.games.storage_manager import GameStorageManager
            from backend.games.scanner_service import GameLibraryScannerService

            summary = GameStorageManager.get_instance().get_storage_summary(
                GameLibraryScannerService.get_instance()
            )
            used_pct = int(summary.get("used_pct", 0))
            inst_cnt = int(summary.get("installed_count", 0))
            inst_lbl = summary.get("installed_label", "0 B")
            free_lbl = summary.get("disk_free_label", "—")
            self.storage_bar.setValue(used_pct)
            self.st_title_lbl.setText(f"Juegos: {inst_lbl} ({inst_cnt} inst.)")
            self.st_sub_lbl.setText(f"{free_lbl} libres · {used_pct}% disco")
        except Exception:
            pass

    def reload_library(self):
        """Re-escanea el catálogo tras instalar/desinstalar y actualiza tarjetas y contadores en vivo."""
        try:
            from backend.games.scanner_service import GameLibraryScannerService

            scanner = GameLibraryScannerService.get_instance()
            fresh_games = scanner.refresh()
            ALL_GAMES[:] = fresh_games
            prioritized = self._get_prioritized_games(ALL_GAMES)
            by_id = {str(c.game.get("id") or ""): c for c in self.all_cards}
            new_cards: list[LibraryGameCard] = []
            for g in prioritized:
                gid = str(g.get("id") or "")
                card = by_id.get(gid)
                if card is not None:
                    card.refresh_game_state(g)
                    card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
                    new_cards.append(card)
                else:
                    card = LibraryGameCard(g, self.scroll_content)
                    card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
                    new_cards.append(card)
            self.all_cards = new_cards
            if self.cat_buttons:
                first_btn, first_code = self.cat_buttons[0]
                if first_code == "todas":
                    first_btn.setText(f"Todas ({len(ALL_GAMES)})")
            self.refresh_storage_indicator()
            self._filter_games()
        except Exception as exc:
            print(f"[OmniDash-Qt] Error recargando biblioteca: {exc}")

    def open_storage_manager(self):
        dlg = StorageManagerDialog(self, on_changed=self.reload_library)
        dlg.exec()

    def wheelEvent(self, event):
        self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().value() - event.angleDelta().y()
        )
        event.accept()

    def _get_prioritized_games(self, games: list[dict]) -> list[dict]:
        """Ordena la biblioteca moderna destacando lanzamientos insignia e instalados primero."""
        def match_game(target: str, g: dict) -> bool:
            gid = (g.get("id") or "").lower()
            t = (g.get("title") or "").lower()
            if target == "ps3_minecraft":
                return gid == "ps3_minecraft"
            if target == "ragnarok":
                return "ragnarök" in t or "ragnarok" in t
            if target == "astro":
                return "astro bot" in t
            if target == "mk8":
                return "mario kart 8" in t
            if target == "gtav":
                return gid == "ps5_grand_theft_auto_v"
            if target == "gtsport":
                return "gran turismo sport" in t
            if target == "sparking":
                return "sparking! zero" in t
            if target == "hollow":
                return "hollow knight" in t
            return False

        top_targets = [
            "ps3_minecraft",
            "ragnarok",
            "astro",
            "mk8",
            "gtav",
            "gtsport",
            "sparking",
            "hollow",
        ]
        priority_games = []
        for target in top_targets:
            found = next((g for g in games if match_game(target, g) and g not in priority_games), None)
            if found:
                priority_games.append(found)
        remaining = [g for g in games if g not in priority_games]
        return priority_games + remaining

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
            elif code == "ps5":
                plat_match = (badge == "ps5" or "playstation 5" in console)
            elif code == "ps4":
                plat_match = (badge == "ps4" or "playstation 4" in console)
            elif code == "switch":
                plat_match = ("switch" in badge or "switch" in console)
            elif code == "ps3":
                plat_match = (badge == "ps3" or "playstation 3" in console)
            elif code == "installed":
                plat_match = bool(g.get("installed")) and not bool(g.get("on_demand"))
            elif code == "cloud":
                plat_match = bool(g.get("on_demand"))
            elif code == "ps_classic":
                plat_match = badge in ("ps1", "ps2") or "playstation 1" in console or "playstation 2" in console
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
# 3. VISTA DE DETALLES DEL JUEGO (GAME DETAILS - GAMING CONSOLE PREMIUM)
# ==============================================================================
class ScreenshotPreviewDialog(QDialog):
    """Visualizador cinematográfico de capturas a pantalla ampliada."""
    def __init__(self, pixmap: QPixmap, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Captura: {title}")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(960, 580)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)

        panel = AcrylicGlassCard(self, border_radius=22, glow_color=QColor(39, 189, 231, 100), glow_radius=20)
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(18, 14, 18, 14)
        p_lay.setSpacing(10)

        top_row = QHBoxLayout()
        t_lbl = QLabel(f"Captura del juego — {title}")
        t_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        top_row.addWidget(t_lbl)
        top_row.addStretch(1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.12);
                border: 1px solid rgba(255, 255, 255, 0.25);
                border-radius: 16px;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.4);
                border-color: #27bde7;
            }
        """)
        close_btn.clicked.connect(self.close)
        top_row.addWidget(close_btn)
        p_lay.addLayout(top_row)

        img_lbl = QLabel()
        img_lbl.setAlignment(Qt.AlignCenter)
        if not pixmap.isNull():
            img_lbl.setPixmap(pixmap.scaled(910, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        p_lay.addWidget(img_lbl, 1)

        lay.addWidget(panel)

    def mousePressEvent(self, event):
        self.close()


def _render_cyan_svg_icon(svg_markup: str, size_px: int = 21) -> QPixmap:
    """Renderiza icono SVG vectorial lineal en alta densidad (Retina @2x)."""
    dpr = 2
    target = size_px * dpr
    pix = QPixmap(target, target)
    pix.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg_markup.encode("utf-8")))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(float(dpr))
    return pix


class ClickableCaptureCard(QFrame):
    """Tarjeta interactiva compacta 16:9 para capturas de gameplay con apertura en modal."""
    clicked = Signal(QPixmap)

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        sp = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setSizePolicy(sp)
        self.setMinimumSize(168, 95)
        self.setMaximumSize(310, 166)
        self.setFixedHeight(99)
        self.setCursor(Qt.PointingHandCursor)
        self._is_hovered = False
        self.setAttribute(Qt.WA_Hover, True)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        target_h = max(95, min(166, int(self.width() * 9 / 16)))
        if self.height() != target_h:
            self.setFixedHeight(target_h)

    def sizeHint(self):
        return QSize(175, 99)

    def enterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, w - 2.0, h - 2.0, 10, 10)

        painter.save()
        painter.setClipPath(path)
        painter.fillRect(0, 0, w, h, QColor(8, 20, 30))
        if self.pixmap and not self.pixmap.isNull():
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
            scaled = self.pixmap.scaled(
                int(w * dpr), int(h * dpr),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - int(w * dpr)) // 2)
            sy = max(0, (scaled.height() - int(h * dpr)) // 2)
            painter.drawPixmap(QRectF(0, 0, w, h), scaled, QRectF(sx, sy, w * dpr, h * dpr))
        painter.restore()

        pen_color = QColor(39, 189, 231) if self._is_hovered else QColor(166, 176, 184, 85)
        painter.setPen(QPen(pen_color, 1.3))
        painter.drawRoundedRect(1.0, 1.0, w - 2.0, h - 2.0, 10, 10)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap and not self.pixmap.isNull():
            self.clicked.emit(self.pixmap)
        super().mousePressEvent(event)


class BoxArtCoverLabel(QFrame):
    """Carátula vertical con recorte suave y borde nítido dibujado por QPainter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap: QPixmap | None = None
        self.setFixedSize(148, 188)

    def set_cover_pixmap(self, pix: QPixmap | None):
        self.pixmap = pix
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()
        r = 12.0
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, w - 2.0, h - 2.0, r, r)

        painter.save()
        painter.setClipPath(path)
        painter.fillRect(0, 0, w, h, QColor(8, 16, 24))
        if self.pixmap and not self.pixmap.isNull():
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
            scaled = self.pixmap.scaled(
                int(w * dpr), int(h * dpr),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - int(w * dpr)) // 2)
            sy = max(0, (scaled.height() - int(h * dpr)) // 2)
            painter.drawPixmap(QRectF(0, 0, w, h), scaled, QRectF(sx, sy, w * dpr, h * dpr))
        painter.restore()

        painter.setPen(QPen(QColor(255, 255, 255, 115), 1.6))
        painter.drawRoundedRect(1.0, 1.0, w - 2.0, h - 2.0, r, r)


class GameDetailsHeroCard(QFrame):
    """Banner cinematográfico panorámico del Hero (30% texto | 52% ilustración | 18% carátula)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(222)
        self.hero_pixmap: QPixmap | None = None
        self.box_zone_width = 172
        self.border_radius = 18
        self.setStyleSheet("background: transparent;")

    def set_hero_image(self, pix: QPixmap | None):
        self.hero_pixmap = pix
        self.update()

    def set_box_zone_width(self, width_px: int):
        self.box_zone_width = max(165, width_px)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, w - 1, h - 1, self.border_radius, self.border_radius)

        painter.save()
        painter.setClipPath(path)

        # 1. Backdrop Blur real (Glassmorphism consistente con Home y Biblioteca)
        drawn_blur = False
        if GLOBAL_BLURRED_BG and not GLOBAL_BLURRED_BG.isNull():
            try:
                win = self.window()
                pt = self.mapTo(win, QPoint(0, 0))
                bw, bh = GLOBAL_BLURRED_BG.width(), GLOBAL_BLURRED_BG.height()
                rx = max(0, min(pt.x(), max(0, bw - 1)))
                ry = max(0, min(pt.y(), max(0, bh - 1)))
                rw = max(1, min(w, bw - rx))
                rh = max(1, min(h, bh - ry))
                patch = GLOBAL_BLURRED_BG.copy(rx, ry, rw, rh)
                if not patch.isNull():
                    painter.drawPixmap(0, 0, w, h, patch)
                    drawn_blur = True
            except Exception:
                pass
        if not drawn_blur:
            painter.fillRect(0, 0, w, h, QColor(10, 18, 28, 215))
        else:
            painter.fillRect(0, 0, w, h, QColor(6, 14, 22, 165))

        # 2. Ilustración panorámica central (~52% ancho útil entre texto izquierdo y carátula derecha)
        if self.hero_pixmap and not self.hero_pixmap.isNull():
            dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0
            pano_start = int(w * 0.27)
            pano_end = w - self.box_zone_width + 6
            pano_w = max(240, pano_end - pano_start)

            scaled = self.hero_pixmap.scaled(
                int(pano_w * dpr), int(h * dpr),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            sx = max(0, (scaled.width() - int(pano_w * dpr)) // 2)
            sy = max(0, int((scaled.height() - int(h * dpr)) * 0.34))

            painter.drawPixmap(
                QRectF(pano_start, 0, pano_w, h),
                scaled,
                QRectF(sx, sy, pano_w * dpr, h * dpr),
            )

            # Degradado protector izquierdo exactamente desde pano_start hacia zona texto (30%)
            fade_w = max(110, int(pano_w * 0.36))
            grad_left = QLinearGradient(pano_start, 0, pano_start + fade_w, 0)
            grad_left.setColorAt(0.0, QColor(8, 16, 26, 245))
            grad_left.setColorAt(0.35, QColor(8, 16, 26, 215))
            grad_left.setColorAt(0.75, QColor(8, 16, 26, 95))
            grad_left.setColorAt(1.0, QColor(8, 16, 26, 0))
            painter.fillRect(0, 0, pano_start, h, QColor(8, 16, 26, 215))
            painter.fillRect(pano_start, 0, fade_w, h, grad_left)

            # Separación discreta detrás de la carátula derecha (18%)
            sep_start = pano_end - 36
            grad_right = QLinearGradient(sep_start, 0, pano_end + 4, 0)
            grad_right.setColorAt(0.0, QColor(8, 16, 26, 0))
            grad_right.setColorAt(1.0, QColor(8, 16, 26, 225))
            painter.fillRect(sep_start, 0, w - sep_start, h, grad_right)

        # 3. Viñeta vertical sutil
        vignette = QLinearGradient(0, 0, 0, h)
        vignette.setColorAt(0.0, QColor(0, 0, 0, 35))
        vignette.setColorAt(0.5, QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QColor(0, 0, 0, 70))
        painter.fillRect(0, 0, w, h, vignette)

        painter.restore()

        # 4. Brillo hairline superior y borde cristalizado
        painter.setPen(QColor(255, 255, 255, 110))
        painter.drawLine(self.border_radius, 1, w - self.border_radius, 1)
        painter.setPen(QPen(QColor(166, 176, 184, 115), 1.5))
        painter.drawRoundedRect(0.5, 0.5, w - 1, h - 1, self.border_radius, self.border_radius)


class GameDetailsGlassShell(AcrylicGlassCard):
    """Contenedor cuadrado redondeado semi-opaco (Glassmorphism estilo Biblioteca) para Game Details."""
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        path = QPainterPath()
        path.addRoundedRect(1.0, 1.0, w - 2.0, h - 2.0, self.border_radius, self.border_radius)
        painter.setClipPath(path)
        # Capa frosted semi-opaca: deja entrever suavemente el desenfoque del wallpaper sin verse transparente ni plano
        painter.fillRect(0, 0, w, h, QColor(7, 15, 26, 115))
        # Bisel luminoso superior extra sutil sobre el velo semi-opaco
        spec_pen = QPen(QColor(255, 255, 255, 110), 1.0)
        painter.setPen(spec_pen)
        painter.drawLine(self.border_radius, 1, max(self.border_radius, w - self.border_radius), 1)


class StorageManagerDialog(QDialog):
    """Gestor de almacenamiento estilo consola PS5: permite liberar espacio desinstalando juegos sin perder su progreso."""

    def __init__(self, parent=None, on_changed=None):
        super().__init__(parent)
        self.on_changed = on_changed
        self.setWindowTitle("C.C.I. SYSTEM — Gestión de Almacenamiento de Consola")
        self.setMinimumSize(680, 480)
        self.setStyleSheet("""
            QDialog {
                background: #0b1826;
                color: #ffffff;
            }
            QLabel {
                color: #e4f2fc;
            }
        """)
        self.main_lay = QVBoxLayout(self)
        self.main_lay.setContentsMargins(24, 20, 24, 20)
        self.main_lay.setSpacing(14)

        hdr = QLabel("💾  Almacenamiento de Consola y Datos Guardados")
        hdr.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        self.main_lay.addWidget(hdr)

        sub = QLabel(
            "Igual que en PlayStation, podés desinstalar juegos descargados para liberar espacio en disco "
            "sin perder tus partidas guardadas ni tu progreso. Los juegos permanecen en tu Biblioteca listos para re-descargar."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #9fc5e0;")
        self.main_lay.addWidget(sub)

        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #56c9e9;")
        self.main_lay.addWidget(self.summary_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setFixedHeight(10)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.14);
                border-radius: 5px;
                border: none;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d9bf0, stop:1 #56f0c8);
                border-radius: 5px;
            }
        """)
        self.main_lay.addWidget(self.bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { background: rgba(14, 28, 44, 0.75); border: 1px solid rgba(86, 201, 233, 0.25); border-radius: 12px; }")
        self.list_container = QWidget()
        self.list_lay = QVBoxLayout(self.list_container)
        self.list_lay.setContentsMargins(14, 14, 14, 14)
        self.list_lay.setSpacing(10)
        self.scroll.setWidget(self.list_container)
        self.main_lay.addWidget(self.scroll, 1)

        bottom_row = QHBoxLayout()
        close_btn = QPushButton("Cerrar")
        close_btn.setFixedSize(110, 34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(39, 189, 231, 0.22);
                border: 1.5px solid #27bde7;
                border-radius: 10px;
                color: #ffffff;
                font-weight: 700;
            }
        """)
        close_btn.clicked.connect(self.accept)
        bottom_row.addStretch(1)
        bottom_row.addWidget(close_btn)
        self.main_lay.addLayout(bottom_row)

        self.refresh_list()

    def refresh_list(self):
        while self.list_lay.count():
            item = self.list_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        from backend.games.storage_manager import GameStorageManager
        from backend.games.scanner_service import GameLibraryScannerService

        scanner = GameLibraryScannerService.get_instance()
        mgr = GameStorageManager.get_instance()
        summary = mgr.get_storage_summary(scanner)

        self.bar.setValue(int(summary.get("used_pct", 0)))
        self.summary_lbl.setText(
            f"Juegos instalados: {summary['installed_count']} ({summary['installed_label']})   •   "
            f"En la nube: {summary['cloud_count']}   •   "
            f"Espacio libre en disco: {summary['disk_free_label']} de {summary['disk_total_label']}"
        )

        items = summary.get("installed_items") or []
        if not items:
            empty_lbl = QLabel("No hay juegos instalados localmente en este momento. Todos tus juegos y partidas siguen disponibles en tu Biblioteca.")
            empty_lbl.setWordWrap(True)
            empty_lbl.setStyleSheet("font-size: 13px; color: #9fc5e0; padding: 18px;")
            self.list_lay.addWidget(empty_lbl)
        else:
            for item in items:
                row_frame = QFrame()
                row_frame.setStyleSheet("""
                    QFrame {
                        background: rgba(20, 40, 60, 0.85);
                        border: 1px solid rgba(166, 176, 184, 0.25);
                        border-radius: 10px;
                    }
                """)
                rlay = QHBoxLayout(row_frame)
                rlay.setContentsMargins(14, 10, 14, 10)

                info_v = QVBoxLayout()
                t_lbl = QLabel(f"{item['title']}  ({item['badge']})")
                t_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #ffffff; border: none;")
                s_lbl = QLabel(
                    f"Tamaño en disco: {item['size_label']}   •   "
                    f"Datos guardados: {item['save_slots']} slot(s)   •   "
                    f"Tiempo jugado: {item['play_time_label']}"
                )
                s_lbl.setStyleSheet("font-size: 12px; color: #9fc5e0; border: none;")
                info_v.addWidget(t_lbl)
                info_v.addWidget(s_lbl)
                rlay.addLayout(info_v, 1)

                uninst_btn = QPushButton("🗑 Desinstalar (conservar progreso)")
                uninst_btn.setFixedHeight(32)
                uninst_btn.setCursor(Qt.PointingHandCursor)
                uninst_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(235, 87, 87, 0.20);
                        border: 1px solid rgba(235, 87, 87, 0.70);
                        border-radius: 8px;
                        color: #ffd6d6;
                        font-size: 12px;
                        font-weight: 700;
                        padding: 0 12px;
                    }
                    QPushButton:hover {
                        background: rgba(235, 87, 87, 0.42);
                        color: #ffffff;
                    }
                """)
                gid = str(item["id"])
                uninst_btn.clicked.connect(lambda _, g_id=gid: self._handle_uninstall(g_id))
                rlay.addWidget(uninst_btn)
                self.list_lay.addWidget(row_frame)

        self.list_lay.addStretch(1)

    def _handle_uninstall(self, game_id: str):
        from backend.games.storage_manager import GameStorageManager
        from backend.games.scanner_service import GameLibraryScannerService

        scanner = GameLibraryScannerService.get_instance()
        mgr = GameStorageManager.get_instance()
        ok, msg, _ = mgr.uninstall_game(game_id, scanner=scanner)
        if callable(self.on_changed):
            self.on_changed()
        self.refresh_list()
        if not ok:
            QMessageBox.warning(self, "Desinstalación", msg)


class GameDetailsView(QWidget):
    launch_game = Signal(dict)
    back_to_library = Signal()
    uninstall_requested = Signal(dict)
    install_package_requested = Signal(dict)

    # Iconografía SVG lineal cian consistente con la referencia
    _SVG_HISTORY = '<svg viewBox="0 0 24 24" fill="none" stroke="#29d4ee" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></svg>'
    _SVG_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="#29d4ee" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>'
    _SVG_SAVES = '<svg viewBox="0 0 24 24" fill="none" stroke="#29d4ee" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4.2l2 2H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7z"/><rect x="8.5" y="10.5" width="7" height="5.5" rx="1"/><path d="M10.5 13h3"/></svg>'
    _SVG_PROGRESS = '<svg viewBox="0 0 24 24" fill="none" stroke="#29d4ee" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a9 9 0 1 1-6.36 2.64"/><path d="M9 12.2l2.1 2.1 4.2-4.4"/></svg>'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game = {}
        self.is_fav = False
        self._current_cover_pix: QPixmap | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 12, 44, 20)
        layout.setSpacing(0)

        self.main_panel = GameDetailsGlassShell(
            self,
            border_radius=28,
            is_interactive=False,
            glow_color=QColor(0, 0, 0, 85),
            glow_radius=14,
            border_color=QColor(166, 176, 184, 115),
            show_specular=True,
        )
        panel_lay = QVBoxLayout(self.main_panel)
        panel_lay.setContentsMargins(20, 18, 20, 16)
        panel_lay.setSpacing(0)
        layout.addWidget(self.main_panel)

        self.scroll = QScrollArea(self.main_panel)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(10, 20, 32, 0.4);
                width: 8px;
                margin: 4px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(166, 176, 184, 0.6);
                min-height: 40px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #27bde7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(self.scroll_content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(18)

        # ======================================================================
        # A. HERO PANORÁMICO (30% texto | 52% ilustración | 18% carátula)
        # ======================================================================
        self.hero_card = GameDetailsHeroCard(self.scroll_content)
        hero_inner = QHBoxLayout(self.hero_card)
        hero_inner.setContentsMargins(24, 16, 22, 16)
        hero_inner.setSpacing(16)

        hero_left = QVBoxLayout()
        hero_left.setSpacing(5)

        top_back_row = QHBoxLayout()
        self.back_btn = QPushButton("  Volver")
        self.back_btn.setFixedSize(90, 28)
        self.back_btn.setCursor(Qt.PointingHandCursor)
        ip = ROOT / "assets_omnidash" / "icons" / "home.png"
        if ip.exists():
            self.back_btn.setIcon(QIcon(str(ip)))
            self.back_btn.setIconSize(QSize(14, 14))
        self.back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 32, 48, 0.78);
                border: 1.5px solid rgba(166, 176, 184, 0.4);
                border-radius: 14px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
                padding-left: 2px;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.35);
                border: 1.5px solid #27bde7;
            }
        """)
        self.back_btn.clicked.connect(self.back_to_library.emit)
        top_back_row.addWidget(self.back_btn)
        top_back_row.addStretch(1)
        hero_left.addLayout(top_back_row)

        hero_left.addSpacing(4)

        self.title_lbl = QLabel("SUPER MARIO\nALL\u2011STARS")
        self.title_lbl.setMaximumWidth(310)
        self.title_lbl.setStyleSheet("font-size: 33px; font-weight: 900; color: #ffffff; letter-spacing: 0.4px; line-height: 1.04;")
        self.title_lbl.setWordWrap(True)
        hero_left.addWidget(self.title_lbl)

        self.meta_lbl = QLabel("Super Nintendo · Nintendo EAD · 1992")
        self.meta_lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #a4c9e4;")
        hero_left.addWidget(self.meta_lbl)

        hero_left.addSpacing(8)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.play_btn = QPushButton("▶  JUGAR")
        self.play_btn.setFixedSize(134, 40)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00f0ff, stop:1 #00cce6);
                border: none;
                border-radius: 10px;
                color: #05131e;
                font-size: 13px;
                font-weight: 900;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #33f3ff, stop:1 #00daf5);
            }
            QPushButton:pressed {
                background: #00b4cc;
            }
        """)
        play_shadow = QGraphicsDropShadowEffect(self.play_btn)
        play_shadow.setColor(QColor(0, 240, 255, 130))
        play_shadow.setBlurRadius(14)
        play_shadow.setOffset(0, 0)
        self.play_btn.setGraphicsEffect(play_shadow)
        self.play_btn.clicked.connect(lambda: self.launch_game.emit(self.game))
        action_row.addWidget(self.play_btn)

        self.fav_btn = QPushButton("♡  FAVORITO")
        self.fav_btn.setFixedSize(134, 40)
        self.fav_btn.setCursor(Qt.PointingHandCursor)
        self.fav_btn.setStyleSheet("""
            QPushButton {
                background: rgba(16, 32, 48, 0.78);
                border: 1.5px solid rgba(166, 176, 184, 0.45);
                border-radius: 10px;
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.25);
                border-color: #27bde7;
                color: #27bde7;
            }
        """)
        self.fav_btn.clicked.connect(self._toggle_favorite)
        action_row.addWidget(self.fav_btn)
        action_row.addStretch(1)

        hero_left.addLayout(action_row)

        storage_action_row = QHBoxLayout()
        storage_action_row.setSpacing(8)

        self.install_pkg_btn = QPushButton("⬇  INSTALAR EN CONSOLA")
        self.install_pkg_btn.setFixedSize(176, 32)
        self.install_pkg_btn.setCursor(Qt.PointingHandCursor)
        self.install_pkg_btn.setStyleSheet("""
            QPushButton {
                background: rgba(39, 189, 231, 0.28);
                border: 1.5px solid #27bde7;
                border-radius: 9px;
                color: #ffffff;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.48);
                color: #ffffff;
            }
        """)
        self.install_pkg_btn.clicked.connect(lambda: self.install_package_requested.emit(self.game))
        storage_action_row.addWidget(self.install_pkg_btn)

        self.uninstall_btn = QPushButton("🗑  LIBERAR ESPACIO")
        self.uninstall_btn.setFixedSize(156, 32)
        self.uninstall_btn.setCursor(Qt.PointingHandCursor)
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background: rgba(235, 87, 87, 0.20);
                border: 1.5px solid rgba(235, 87, 87, 0.65);
                border-radius: 9px;
                color: #ffd6d6;
                font-size: 11px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: rgba(235, 87, 87, 0.38);
                color: #ffffff;
            }
        """)
        self.uninstall_btn.clicked.connect(lambda: self.uninstall_requested.emit(self.game))
        storage_action_row.addWidget(self.uninstall_btn)
        storage_action_row.addStretch(1)
        hero_left.addLayout(storage_action_row)

        # Barra de instalación integrada en consola (sin popups de Finder/Explorer)
        self.install_progress_box = QWidget()
        ip_lay = QVBoxLayout(self.install_progress_box)
        ip_lay.setContentsMargins(0, 2, 0, 0)
        ip_lay.setSpacing(3)
        self.install_status_lbl = QLabel("")
        self.install_status_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #56f0c8;")
        self.install_progress_bar = QProgressBar()
        self.install_progress_bar.setRange(0, 100)
        self.install_progress_bar.setValue(0)
        self.install_progress_bar.setFixedSize(260, 7)
        self.install_progress_bar.setTextVisible(False)
        self.install_progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 0.16);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #27bde7, stop:1 #56f0c8);
                border-radius: 3px;
            }
        """)
        ip_lay.addWidget(self.install_status_lbl)
        ip_lay.addWidget(self.install_progress_bar)
        self.install_progress_box.hide()
        hero_left.addWidget(self.install_progress_box)

        hero_left.addStretch(1)

        hero_inner.addLayout(hero_left, 30)
        hero_inner.addStretch(52)

        self.box_art_lbl = BoxArtCoverLabel(self.hero_card)
        self.box_art_lbl.setFixedSize(148, 188)
        hero_inner.addWidget(self.box_art_lbl, 0, Qt.AlignRight | Qt.AlignVCenter)

        c_lay.addWidget(self.hero_card)

        # ======================================================================
        # B & C. GRID DE DOS COLUMNAS (Separación 32px)
        # ======================================================================
        middle_row = QHBoxLayout()
        middle_row.setSpacing(32)

        # COLUMNA IZQUIERDA: INFORMACIÓN (~36% ancho)
        info_col = QVBoxLayout()
        info_col.setSpacing(9)

        info_title = QLabel("Información")
        info_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        info_col.addWidget(info_title)

        self.info_card = AcrylicGlassCard(
            self.scroll_content,
            border_radius=16,
            is_interactive=False,
            glow_color=QColor(0, 0, 0, 75),
            glow_radius=14,
            border_color=QColor(166, 176, 184, 110),
            show_specular=True,
        )
        info_card_lay = QVBoxLayout(self.info_card)
        info_card_lay.setContentsMargins(18, 18, 18, 18)
        info_card_lay.setSpacing(13)

        self.desc_lbl = QLabel("Clásico legendario preservado para C.C.I. SYSTEM a 60 FPS estables.")
        self.desc_lbl.setStyleSheet("font-size: 13px; color: #d0e6f7; line-height: 1.42; border: none; background: transparent;")
        self.desc_lbl.setWordWrap(True)
        info_card_lay.addWidget(self.desc_lbl)

        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(166, 176, 184, 0.20); border: none;")
        info_card_lay.addWidget(div)

        grid = QGridLayout()
        grid.setVerticalSpacing(10)
        grid.setHorizontalSpacing(14)

        def make_row(lbl_text: str, row_idx: int) -> tuple[QLabel, QLabel]:
            k = QLabel(lbl_text)
            k.setStyleSheet("font-size: 12.5px; color: #8eaec7; font-weight: 500; border: none; background: transparent;")
            v = QLabel("—")
            v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            v.setStyleSheet("font-size: 12.5px; color: #ffffff; font-weight: 700; border: none; background: transparent;")
            grid.addWidget(k, row_idx, 0)
            grid.addWidget(v, row_idx, 1)
            return k, v

        self.lbl_genre, self.val_genre = make_row("Género", 0)
        self.lbl_platform, self.val_platform = make_row("Plataforma", 1)
        self.lbl_developer, self.val_developer = make_row("Desarrollador", 2)
        self.lbl_year, self.val_year = make_row("Lanzamiento", 3)
        self.lbl_players, self.val_players = make_row("Jugadores", 4)

        info_card_lay.addLayout(grid)
        info_col.addWidget(self.info_card)
        info_col.addStretch(1)
        middle_row.addLayout(info_col, 4)

        # COLUMNA DERECHA: TU ACTIVIDAD + CAPTURAS DEL JUEGO (~64% ancho)
        act_col = QVBoxLayout()
        act_col.setSpacing(9)

        act_title = QLabel("Tu actividad")
        act_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        act_col.addWidget(act_title)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)

        def make_stat_box(svg_markup: str, label_text: str, default_val: str) -> tuple[AcrylicGlassCard, QLabel]:
            box = AcrylicGlassCard(
                self.scroll_content,
                border_radius=12,
                is_interactive=False,
                glow_color=QColor(0, 0, 0, 75),
                glow_radius=12,
                border_color=QColor(175, 192, 205, 130),
                show_specular=True,
            )
            box.setFixedHeight(52)
            box.setMinimumWidth(148)
            box.setMaximumWidth(265)
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            b_lay = QHBoxLayout(box)
            b_lay.setContentsMargins(11, 6, 11, 6)
            b_lay.setSpacing(9)

            ico_lbl = QLabel()
            ico_lbl.setFixedSize(22, 22)
            ico_lbl.setAlignment(Qt.AlignCenter)
            ico_lbl.setStyleSheet("background: transparent; border: none;")
            ico_lbl.setPixmap(_render_cyan_svg_icon(svg_markup, 22))
            b_lay.addWidget(ico_lbl)

            t_lay = QVBoxLayout()
            t_lay.setSpacing(1)
            l = QLabel(label_text)
            l.setStyleSheet("font-size: 9.5px; color: #c4d8e8; font-weight: 500; border: none; background: transparent;")
            v = QLabel(default_val)
            v.setStyleSheet("font-size: 13.5px; color: #ffffff; font-weight: 800; border: none; background: transparent;")
            t_lay.addWidget(l)
            t_lay.addWidget(v)
            b_lay.addLayout(t_lay)
            return box, v

        box_last, self.val_last_played = make_stat_box(self._SVG_HISTORY, "Última vez jugado:", "Ayer")
        box_time, self.val_play_time = make_stat_box(self._SVG_CLOCK, "Tiempo jugado:", "12h 45m")
        box_saves, self.val_saves = make_stat_box(self._SVG_SAVES, "Partidas guardadas:", "3 slots")
        box_prog, self.val_progress = make_stat_box(self._SVG_PROGRESS, "Progreso:", "85%")

        stats_row.addWidget(box_last, 1)
        stats_row.addWidget(box_time, 1)
        stats_row.addWidget(box_saves, 1)
        stats_row.addWidget(box_prog, 1)
        act_col.addLayout(stats_row)

        act_col.addSpacing(9)

        self.captures_header = QLabel("Capturas del juego")
        self.captures_header.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff;")
        act_col.addWidget(self.captures_header)

        self.captures_container = QWidget()
        self.captures_lay = QHBoxLayout(self.captures_container)
        self.captures_lay.setContentsMargins(0, 0, 0, 0)
        self.captures_lay.setSpacing(10)
        act_col.addWidget(self.captures_container)
        act_col.addStretch(1)

        middle_row.addLayout(act_col, 7)
        c_lay.addLayout(middle_row)

        # ======================================================================
        # D. SECCIÓN PLEGABLE: INFORMACIÓN TÉCNICA
        # ======================================================================
        tech_btn_row = QHBoxLayout()
        tech_btn_row.addStretch(1)

        self.tech_btn = QPushButton("▼  Información técnica")
        self.tech_btn.setFixedSize(206, 34)
        self.tech_btn.setCursor(Qt.PointingHandCursor)
        self.tech_btn.setStyleSheet("""
            QPushButton {
                background: rgba(14, 30, 44, 0.85);
                border: 1.2px solid rgba(166, 176, 184, 0.35);
                border-radius: 10px;
                color: #b4cde0;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(39, 189, 231, 0.25);
                border-color: #27bde7;
                color: #ffffff;
            }
        """)
        self.tech_btn.clicked.connect(self._toggle_tech_info)
        tech_btn_row.addWidget(self.tech_btn)
        tech_btn_row.addStretch(1)
        c_lay.addLayout(tech_btn_row)

        self.tech_card = AcrylicGlassCard(
            self.scroll_content,
            border_radius=14,
            is_interactive=False,
            glow_color=QColor(0, 0, 0, 75),
            glow_radius=12,
            border_color=QColor(166, 176, 184, 110),
            show_specular=True,
        )
        self.tech_card.setVisible(False)
        tech_card_lay = QVBoxLayout(self.tech_card)
        tech_card_lay.setContentsMargins(20, 16, 20, 16)
        tech_card_lay.setSpacing(10)

        t_grid = QGridLayout()
        t_grid.setVerticalSpacing(8)
        t_grid.setHorizontalSpacing(18)

        def make_tech_row(label: str, row_i: int) -> QLabel:
            k = QLabel(label)
            k.setStyleSheet("font-size: 12px; color: #8eaec7; font-weight: 600; border: none; background: transparent;")
            v = QLabel("—")
            v.setStyleSheet("font-size: 12px; color: #e1f0fc; font-weight: 700; border: none; background: transparent;")
            t_grid.addWidget(k, row_i, 0)
            t_grid.addWidget(v, row_i, 1)
            return v

        self.val_tech_core = make_tech_row("Emulador / Core Libretro", 0)
        self.val_tech_rom = make_tech_row("Ruta del archivo ROM", 1)
        self.val_tech_format = make_tech_row("Formato y Región", 2)
        self.val_tech_status = make_tech_row("Estado de disponibilidad", 3)
        self.val_tech_cert = make_tech_row("Certificación de rendimiento", 4)

        tech_card_lay.addLayout(t_grid)
        c_lay.addWidget(self.tech_card)
        c_lay.addStretch(1)

        self.scroll.setWidget(self.scroll_content)
        panel_lay.addWidget(self.scroll)

    def _update_title_typography(self, avail_w: int | None = None):
        if avail_w is None:
            avail_w = max(640, self.width() - 128)
        base_px = max(30, min(38, int(avail_w * 0.031)))
        raw_title = (self.game.get("title") or self.title_lbl.text() or "").strip()
        n = len(raw_title)
        if n > 28:
            title_px = max(20, base_px - 11)
        elif n > 21:
            title_px = max(23, base_px - 7)
        else:
            title_px = base_px
        self.title_lbl.setMaximumWidth(max(260, int(avail_w * 0.32)))
        self.title_lbl.setStyleSheet(
            f"font-size: {title_px}px; font-weight: 900; color: #ffffff; letter-spacing: 0.4px; line-height: 1.05;"
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        avail_w = max(640, self.width() - 128)
        hero_h = max(214, min(280, int(avail_w * 0.195)))
        self.hero_card.setFixedHeight(hero_h)

        box_h = hero_h - 34
        box_w = int(box_h * 150 / 190)
        self.box_art_lbl.setFixedSize(box_w, box_h)
        self.hero_card.set_box_zone_width(box_w + 34)

        self._update_title_typography(avail_w)

        if self._current_cover_pix and not self._current_cover_pix.isNull():
            self.box_art_lbl.set_cover_pixmap(self._current_cover_pix)

    def _toggle_favorite(self):
        self.is_fav = not self.is_fav
        self.game["is_favorite"] = self.is_fav
        if self.is_fav:
            self.fav_btn.setText("♥  FAVORITO")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(39, 189, 231, 0.35);
                    border: 1.5px solid #27bde7;
                    border-radius: 10px;
                    color: #27bde7;
                    font-size: 12px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background: rgba(39, 189, 231, 0.45);
                }
            """)
        else:
            self.fav_btn.setText("♡  FAVORITO")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 32, 48, 0.78);
                    border: 1.5px solid rgba(166, 176, 184, 0.45);
                    border-radius: 10px;
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    background: rgba(39, 189, 231, 0.25);
                    border-color: #27bde7;
                    color: #27bde7;
                }
            """)

    def _toggle_tech_info(self):
        is_vis = not self.tech_card.isVisible()
        self.tech_card.setVisible(is_vis)
        self.tech_btn.setText("▲  Información técnica" if is_vis else "▼  Información técnica")

    def _open_capture_preview(self, pixmap: QPixmap):
        dialog = ScreenshotPreviewDialog(pixmap, self.game.get("title", "Juego"), self)
        dialog.exec()

    def load_game(self, game: dict):
        self.game = game
        self.scroll.verticalScrollBar().setValue(0)
        title = game.get("title", "Juego")
        console = game.get("console", "Retro")
        developer = game.get("developer", "Official")
        year = str(game.get("year", "—"))

        self.title_lbl.setText(title.upper().replace("ALL-STARS", "ALL\u2011STARS"))
        self._update_title_typography()
        self.meta_lbl.setText(f"{console}  ·  {developer}  ·  {year}")
        self.desc_lbl.setText(game.get("desc", "Clásico legendario preservado para C.C.I. SYSTEM a 60 FPS estables."))

        genre, players = self._infer_genre_and_players(game)
        self.val_genre.setText(genre)
        self.val_platform.setText(console)
        self.val_developer.setText(developer)
        self.val_year.setText(year)
        if players:
            self.val_players.setText(players)
            self.lbl_players.show()
            self.val_players.show()
        else:
            self.lbl_players.hide()
            self.val_players.hide()

        self.is_fav = bool(game.get("is_favorite", False))
        if self.is_fav:
            self.fav_btn.setText("♥  FAVORITO")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(39, 189, 231, 0.35);
                    border: 1.5px solid #27bde7;
                    border-radius: 10px;
                    color: #27bde7;
                    font-size: 12px;
                    font-weight: 800;
                }
            """)
        else:
            self.fav_btn.setText("♡  FAVORITO")
            self.fav_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(16, 32, 48, 0.78);
                    border: 1.5px solid rgba(166, 176, 184, 0.45);
                    border-radius: 10px;
                    color: #ffffff;
                    font-size: 12px;
                    font-weight: 700;
                }
            """)

        try:
            from backend.games.storage_manager import GameStorageManager

            prog = GameStorageManager.get_instance().get_progress(str(game.get("id") or ""))
        except Exception:
            prog = {
                "has_progress": False,
                "last_played": "Hoy" if game.get("installed") else "Sin registrar aún",
                "play_time_label": "0h 0m",
                "saves_label": "Nube C.C.I." if game.get("on_demand") else "Local",
                "progress_pct": 0,
                "progress_label": "0%",
                "save_slots": 0,
            }

        self.val_last_played.setText(
            prog["last_played"] if prog.get("has_progress") else ("Hoy" if game.get("installed") else "Sin registrar aún")
        )
        self.val_play_time.setText(prog.get("play_time_label", "0h 0m"))
        if prog.get("has_progress"):
            self.val_saves.setText(f"{prog['saves_label']} (Conservados)")
        else:
            self.val_saves.setText("Nube C.C.I." if game.get("on_demand") else "Consola Local")

        sz_display = game.get("size", "—")
        if prog.get("progress_pct", 0) > 0:
            self.val_progress.setText(f"{prog['progress_label']} · {sz_display}")
        else:
            self.val_progress.setText(sz_display)

        cover_pix = resolve_game_cover(game)

        if game.get("on_demand"):
            sz_txt = game.get("size") or "Nube"
            self.play_btn.setText(f"⬇  INSTALAR · {sz_txt}")
            self.play_btn.setFixedWidth(max(162, min(220, 118 + len(sz_txt) * 8)))
            self.install_pkg_btn.show()
            self.uninstall_btn.hide()
        else:
            self.play_btn.setText("▶  JUGAR")
            self.play_btn.setFixedWidth(134)
            self.install_pkg_btn.hide()
            self.uninstall_btn.show()
            self.install_progress_box.hide()

        self._current_cover_pix = cover_pix
        if cover_pix and not cover_pix.isNull():
            self.box_art_lbl.set_cover_pixmap(cover_pix)
        else:
            self.box_art_lbl.set_cover_pixmap(None)

        hero_pix = self._resolve_hero_banner_pixmap(game, cover_pix)
        self.hero_card.set_hero_image(hero_pix)

        self._populate_captures(game)

        core_disp = str(game.get("core") or "")
        if core_disp.startswith("external:"):
            core_disp = f"Emulador externo ({core_disp.split(':', 1)[1].upper()})"
        elif not core_disp:
            core_disp = "Nube / Sin emulador local"
        self.val_tech_core.setText(core_disp)
        self.val_tech_rom.setText(game.get("rom") or f"Nube On-Demand ({game.get('size', '—')})")
        self.val_tech_format.setText(f"{game.get('format', 'PKG')} · {game.get('region', 'Global')}")
        if game.get("on_demand"):
            self.val_tech_status.setText(f"☁ Disponible en la nube ({game.get('size', '—')})")
            self.val_tech_cert.setText(
                "Descarga manual/externa requerida en roms/" + str(game.get("platform_key", "ps3"))
            )
        else:
            self.val_tech_status.setText("✓ ROM descargada e instalada localmente")
            self.val_tech_cert.setText("✓ Verificado en biblioteca C.C.I. SYSTEM")

    def _infer_genre_and_players(self, game: dict) -> tuple[str, str]:
        if game.get("genre"):
            return str(game["genre"]), str(game.get("players") or "1-2 Jugadores")
        title = (game.get("title") or "").lower()
        if "mario kart" in title or "hot wheels" in title or "f1 " in title or "gran turismo" in title or "wrc" in title or "need for speed" in title:
            return "Carreras", "1-4 Jugadores"
        elif "mortal kombat" in title or "dragon ball" in title or "jojo" in title:
            return "Lucha", "1-2 Jugadores"
        elif "resident evil" in title or "silent hill" in title:
            return "Survival Horror", "1 Jugador"
        elif "god of war" in title or "spider-man" in title or "star wars" in title:
            return "Acción / Aventura", "1 Jugador"
        elif "fifa" in title or "fc " in title or "pro evolution" in title:
            return "Deportes / Fútbol", "1-4 Jugadores"
        elif "just dance" in title:
            return "Música / Baile", "1-6 Jugadores"
        elif "hollow knight" in title or "cuphead" in title:
            return "Indie / Acción", "1-2 Jugadores"
        return "Acción / Aventura", "1-2 Jugadores"

    def _resolve_hero_banner_pixmap(self, game: dict, fallback_cover: QPixmap | None) -> QPixmap | None:
        if fallback_cover and not fallback_cover.isNull():
            return fallback_cover
        return None

    def _populate_captures(self, game: dict):
        while self.captures_lay.count():
            item = self.captures_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        caps = []
        cover = resolve_game_cover(game)
        if cover and not cover.isNull():
            caps.append(cover)

        if caps:
            self.captures_header.show()
            self.captures_container.show()
            for pix in caps:
                card = ClickableCaptureCard(pix, self.captures_container)
                card.clicked.connect(self._open_capture_preview)
                self.captures_lay.addWidget(card, 1)
            self.captures_lay.addStretch(2)
        else:
            self.captures_header.hide()
            self.captures_container.hide()

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
            ("person", "Active Player", "Sin sesión activa (Invitado)"),
            ("trophy", "Local Runtime", "OmniDash Frutiger Aero + Communities"),
            ("layers_stack", "Libretro Framebuffer", "V-Sync 60 FPS | Hardware Glitched = OFF"),
            ("sound_wave", "Audio Sink", "Qt Multimedia Core Stereo (44.1 kHz 16-bit)"),
        ]

        self._settings_value_labels = {}
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
            self._settings_value_labels[title] = v_lbl

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
def _format_message_time(ts: Any) -> str:
    try:
        val = float(ts)
        if val > 0:
            return datetime.fromtimestamp(val).strftime("%H:%M")
    except Exception:
        pass
    return "Ahora"


def _clear_layout_widgets(lay: QVBoxLayout | QHBoxLayout, keep_trailing_stretch: bool = False) -> None:
    limit = 1 if keep_trailing_stretch else 0
    while lay.count() > limit:
        item = lay.takeAt(0)
        if item is None:
            break
        w = item.widget()
        if w is not None:
            w.deleteLater()


class ServerRailItem(QPushButton):
    def __init__(
        self,
        icon_path: Optional[Path] = None,
        is_active: bool = False,
        tooltip: str = "",
        badge_text: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.is_active = is_active
        self.badge_text = badge_text.upper()[:2]
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip)
        self._pixmap = None
        if icon_path and icon_path.exists():
            self._pixmap = QPixmap(str(icon_path))

        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(14)
        self.shadow.setColor(QColor(53, 200, 241, 180) if is_active else QColor(0, 0, 0, 0))
        self.setGraphicsEffect(self.shadow)

    def set_active(self, active: bool):
        self.is_active = active
        self.shadow.setColor(QColor(53, 200, 241, 180) if active else QColor(0, 0, 0, 0))
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
        elif self.badge_text:
            p.setPen(QColor("#ffffff"))
            p.setFont(QFont("Helvetica Neue", 13, QFont.Bold))
            p.drawText(self.rect(), Qt.AlignCenter, self.badge_text)

        p.setPen(QPen(QColor(53, 200, 241), 2.2) if self.is_active else QPen(QColor(145, 165, 179, 70), 1.0))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, w - 2, h - 2, radius, radius)


class ServerRail(QWidget):
    community_selected = Signal(str)
    explore_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(58)
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(4, 4, 4, 8)
        self._root_layout.setSpacing(10)
        self._root_layout.setAlignment(Qt.AlignHCenter)

        plus_p = ROOT / "assets_omnidash" / "communities" / "rail_plus.png"
        self.add_btn = ServerRailItem(plus_p if plus_p.exists() else None, tooltip="Explorar / Crear Comunidad", badge_text="+")
        self.add_btn.clicked.connect(self.explore_clicked.emit)
        self._root_layout.addWidget(self.add_btn)

        self._items_container = QWidget(self)
        self._items_layout = QVBoxLayout(self._items_container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(10)
        self._items_layout.setAlignment(Qt.AlignHCenter)
        self._root_layout.addWidget(self._items_container)
        self._root_layout.addStretch(1)

        self.items: dict[str, ServerRailItem] = {}

    def set_communities(self, communities: list[dict], active_community_id: Optional[str] = None):
        self.items.clear()
        _clear_layout_widgets(self._items_layout)
        for comm in communities or []:
            cid = str(comm.get("id") or "")
            name = str(comm.get("name") or "Comunidad")
            initials = "".join(part[0] for part in name.split()[:2] if part) or name[:2]
            item = ServerRailItem(
                icon_path=None,
                is_active=(cid == active_community_id),
                tooltip=name,
                badge_text=initials,
                parent=self._items_container,
            )
            item.clicked.connect(lambda _, s=cid: self.community_selected.emit(s))
            self._items_layout.addWidget(item)
            self.items[cid] = item

    def set_active_community(self, community_id: str):
        for cid, it in self.items.items():
            it.set_active(cid == community_id)


class ChannelSidebar(AcrylicGlassCard):
    channel_selected = Signal(str, str)       # channel_id, type
    create_channel_requested = Signal(str)    # "text" | "voice"
    edit_channel_requested = Signal(str)      # channel_id
    delete_channel_requested = Signal(str)    # channel_id
    leave_community_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            border_radius=22,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10
        )
        self.setFixedWidth(306)
        self.active_channel_id: Optional[str] = None
        self.active_voice_id: Optional[str] = None
        self.text_buttons: dict[str, QPushButton] = {}
        self.voice_buttons: dict[str, QPushButton] = {}
        self._voice_names: dict[str, str] = {}
        self._live_channel_ids: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.banner_frame = QFrame()
        self.banner_frame.setFixedHeight(124)
        b_lay = QVBoxLayout(self.banner_frame)
        b_lay.setContentsMargins(0, 0, 0, 8)
        b_lay.setSpacing(6)

        banner_path = ROOT / "assets_omnidash" / "communities" / "banner_moon_skyline_2x.png"
        if not banner_path.exists():
            banner_path = ROOT / "assets_omnidash" / "communities" / "banner_seeker_hub.jpg"

        img_lbl = QLabel()
        img_lbl.setFixedHeight(68)
        if banner_path.exists():
            bpm = QPixmap(str(banner_path)).scaled(282, 68, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            img_lbl.setPixmap(get_rounded_pixmap(bpm, 282, 68, 14))
        b_lay.addWidget(img_lbl)

        info_box = QVBoxLayout()
        info_box.setContentsMargins(12, 0, 12, 0)
        info_box.setSpacing(2)

        t_row = QHBoxLayout()
        self.c_name_lbl = QLabel("Sin comunidad")
        self.c_name_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #ffffff;")
        t_row.addWidget(self.c_name_lbl)
        t_row.addStretch(1)

        self.c_vis_lbl = QLabel("")
        self.c_vis_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #BDD4E4;")
        t_row.addWidget(self.c_vis_lbl)
        info_box.addLayout(t_row)

        self.c_members_lbl = QLabel("0 miembros")
        self.c_members_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #35C8F1;")
        info_box.addWidget(self.c_members_lbl)
        b_lay.addLayout(info_box)

        self.banner_frame.setStyleSheet("""
            QFrame {
                background: rgba(14, 28, 44, 0.75);
                border-radius: 14px;
                border: 1px solid rgba(145, 165, 179, 0.3);
            }
        """)
        layout.addWidget(self.banner_frame)

        t_sec = QHBoxLayout()
        t_sec_lbl = QLabel("∨  Canales de texto")
        t_sec_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #BDD4E4;")
        t_sec.addWidget(t_sec_lbl)
        t_sec.addStretch(1)
        self.add_text_btn = QPushButton("+")
        self.add_text_btn.setFixedSize(24, 24)
        self.add_text_btn.setCursor(Qt.PointingHandCursor)
        self.add_text_btn.setToolTip("Crear canal de texto")
        self.add_text_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 15px; font-weight: 800; color: #BDD4E4; border-radius: 6px; } QPushButton:hover { background: rgba(255,255,255,0.12); color: #ffffff; }")
        self.add_text_btn.clicked.connect(lambda: self.create_channel_requested.emit("text"))
        t_sec.addWidget(self.add_text_btn)
        layout.addLayout(t_sec)

        self._text_list_layout = QVBoxLayout()
        self._text_list_layout.setSpacing(4)
        layout.addLayout(self._text_list_layout)

        layout.addSpacing(6)
        v_sec = QHBoxLayout()
        v_sec_lbl = QLabel("∨  Canales de voz")
        v_sec_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #BDD4E4;")
        v_sec.addWidget(v_sec_lbl)
        v_sec.addStretch(1)
        self.add_voice_btn = QPushButton("+")
        self.add_voice_btn.setFixedSize(24, 24)
        self.add_voice_btn.setCursor(Qt.PointingHandCursor)
        self.add_voice_btn.setToolTip("Crear canal de voz")
        self.add_voice_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 15px; font-weight: 800; color: #BDD4E4; border-radius: 6px; } QPushButton:hover { background: rgba(255,255,255,0.12); color: #ffffff; }")
        self.add_voice_btn.clicked.connect(lambda: self.create_channel_requested.emit("voice"))
        v_sec.addWidget(self.add_voice_btn)
        layout.addLayout(v_sec)

        self._voice_list_layout = QVBoxLayout()
        self._voice_list_layout.setSpacing(4)
        layout.addLayout(self._voice_list_layout)

        layout.addStretch(1)

        self.leave_btn = QPushButton("Salir de la comunidad")
        self.leave_btn.setCursor(Qt.PointingHandCursor)
        self.leave_btn.setFixedHeight(32)
        self.leave_btn.setStyleSheet("""
            QPushButton {
                background: rgba(233, 75, 86, 0.16);
                border: 1px solid rgba(233, 75, 86, 0.45);
                border-radius: 10px;
                color: #ffb3b8;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(233, 75, 86, 0.34);
                color: #ffffff;
            }
        """)
        self.leave_btn.clicked.connect(self.leave_community_requested.emit)
        layout.addWidget(self.leave_btn)

    def set_community_data(
        self,
        community: Optional[dict],
        channels: list[dict],
        member_count: int = 0,
        online_count: int = 0,
        active_text_id: Optional[str] = None,
        active_voice_id: Optional[str] = None,
    ):
        if community:
            self.c_name_lbl.setText(str(community.get("name") or "Comunidad"))
            vis = "Pública" if community.get("visibility") == "public" else "Privada"
            self.c_vis_lbl.setText(vis)
            self.c_members_lbl.setText(f"●  {online_count} en línea  •  {member_count} miembros")
        else:
            self.c_name_lbl.setText("Sin comunidad")
            self.c_vis_lbl.setText("")
            self.c_members_lbl.setText("0 miembros")

        self.text_buttons.clear()
        self.voice_buttons.clear()
        self._voice_names.clear()
        _clear_layout_widgets(self._text_list_layout)
        _clear_layout_widgets(self._voice_list_layout)

        self.active_channel_id = active_text_id
        self.active_voice_id = active_voice_id

        text_channels = [c for c in (channels or []) if c.get("type") == "text"]
        voice_channels = [c for c in (channels or []) if c.get("type") in ("voice", "stream")]

        if not text_channels:
            empty_t = QLabel("Sin canales de texto")
            empty_t.setStyleSheet("font-size: 12px; color: #7f95a6; padding-left: 10px;")
            self._text_list_layout.addWidget(empty_t)
        else:
            for ch in text_channels:
                cid = str(ch["id"])
                btn = QPushButton(f" #  {ch.get('name', 'canal')}")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(32)
                btn.clicked.connect(lambda _, c=cid: self._on_channel_click(c, "text"))
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, b=btn, c=cid: self._show_channel_context_menu(c, b.mapToGlobal(pos))
                )
                self._text_list_layout.addWidget(btn)
                self.text_buttons[cid] = btn
            if not self.active_channel_id:
                self.active_channel_id = str(text_channels[0]["id"])

        vip = ROOT / "assets_omnidash" / "icons" / "speaker_2.png"
        if not voice_channels:
            empty_v = QLabel("Sin canales de voz")
            empty_v.setStyleSheet("font-size: 12px; color: #7f95a6; padding-left: 10px;")
            self._voice_list_layout.addWidget(empty_v)
        else:
            for ch in voice_channels:
                cid = str(ch["id"])
                base_name = str(ch.get("name", "voz"))
                self._voice_names[cid] = base_name
                label = f"  {base_name}  ● LIVE" if cid in self._live_channel_ids else f"  {base_name}"
                btn = QPushButton(label)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(32)
                if vip.exists():
                    btn.setIcon(QIcon(str(vip)))
                    btn.setIconSize(QSize(15, 15))
                btn.clicked.connect(lambda _, c=cid: self._on_channel_click(c, "voice"))
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(
                    lambda pos, b=btn, c=cid: self._show_channel_context_menu(c, b.mapToGlobal(pos))
                )
                self._voice_list_layout.addWidget(btn)
                self.voice_buttons[cid] = btn

        self._style_channels()

    def set_live_channels(self, channel_ids: list[str]):
        self._live_channel_ids = {str(cid) for cid in (channel_ids or []) if cid}
        for cid, btn in self.voice_buttons.items():
            base_name = self._voice_names.get(cid, "voz")
            btn.setText(f"  {base_name}  ● LIVE" if cid in self._live_channel_ids else f"  {base_name}")
        self._style_channels()

    def set_active_text_channel(self, channel_id: str):
        self.active_channel_id = channel_id
        self._style_channels()

    def set_active_voice_channel(self, channel_id: Optional[str]):
        self.active_voice_id = channel_id
        self._style_channels()

    def _on_channel_click(self, channel_id: str, ch_type: str):
        if ch_type == "text":
            self.active_channel_id = channel_id
        self._style_channels()
        self.channel_selected.emit(channel_id, ch_type)

    def _show_channel_context_menu(self, channel_id: str, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #102438; color: #ffffff; border: 1px solid rgba(53,200,241,0.45); } QMenu::item:selected { background: rgba(53,200,241,0.3); }")
        edit_act = menu.addAction("Editar canal")
        del_act = menu.addAction("Eliminar canal")
        chosen = menu.exec(global_pos)
        if chosen == edit_act:
            self.edit_channel_requested.emit(channel_id)
        elif chosen == del_act:
            self.delete_channel_requested.emit(channel_id)

    def _style_channels(self):
        for cid, btn in self.text_buttons.items():
            if cid == self.active_channel_id:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 12px;
                        background: rgba(27, 48, 64, 0.95);
                        border: 1px solid rgba(53, 200, 241, 0.6);
                        border-radius: 8px; color: #ffffff;
                        font-size: 13px; font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 12px;
                        background: transparent; border: none; border-radius: 8px;
                        color: #BDD4E4; font-size: 13px; font-weight: 600;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.06); color: #ffffff; }
                """)
        for cid, btn in self.voice_buttons.items():
            if cid == self.active_voice_id:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 10px;
                        background: rgba(50, 216, 117, 0.16);
                        border: 1px solid rgba(50, 216, 117, 0.55);
                        border-radius: 8px; color: #ffffff;
                        font-size: 13px; font-weight: 700;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        text-align: left; padding-left: 10px;
                        background: transparent; border: none; border-radius: 8px;
                        color: #BDD4E4; font-size: 13px; font-weight: 600;
                    }
                    QPushButton:hover { background: rgba(255, 255, 255, 0.08); color: #ffffff; }
                """)


class ChatMessageWidget(QWidget):
    reply_requested = Signal(str, str, str)      # message_id, author, snippet
    edit_requested = Signal(str, str)            # message_id, current_text
    delete_requested = Signal(str)               # message_id
    reaction_toggled = Signal(str, str)          # message_id, emoji

    def __init__(
        self,
        message_id: str,
        author: str,
        time_str: str,
        text: str,
        avatar_path: Optional[Path] = None,
        is_self: bool = False,
        edited: bool = False,
        reply_preview: Optional[dict] = None,
        reactions: Optional[list] = None,
        attachments: Optional[list] = None,
        image_loader=None,
        can_moderate: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.message_id = message_id
        self.author = author
        self.current_text = text
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(14)

        av_lbl = QLabel()
        av_lbl.setFixedSize(44, 44)
        av_lbl.setAlignment(Qt.AlignCenter)
        if avatar_path and avatar_path.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(avatar_path)), 44, 44, 22))
        else:
            initial = (author[:1] or "?").upper()
            av_lbl.setText(initial)
            bg = "rgba(53, 200, 241, 0.35)" if is_self else "rgba(255, 255, 255, 0.12)"
            av_lbl.setStyleSheet(
                f"background: {bg}; border: 1px solid rgba(255,255,255,0.28); border-radius: 22px; color: #ffffff; font-size: 16px; font-weight: 800;"
            )
        layout.addWidget(av_lbl, 0, Qt.AlignTop)

        content_lay = QVBoxLayout()
        content_lay.setSpacing(4)

        hdr_row = QHBoxLayout()
        hdr_row.setSpacing(6)

        self.name_lbl = QLabel(author)
        name_color = "#35C8F1" if is_self else "#ffffff"
        self.name_lbl.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {name_color};")
        hdr_row.addWidget(self.name_lbl)

        self.time_lbl = QLabel(f"{time_str} (editado)" if edited else time_str)
        self.time_lbl.setStyleSheet("font-size: 11px; color: #BDD4E4; font-weight: 600;")
        hdr_row.addWidget(self.time_lbl)
        hdr_row.addStretch(1)

        act_style = (
            "QPushButton { background: rgba(255,255,255,0.06); border: none; border-radius: 6px; "
            "color: #BDD4E4; font-size: 11px; padding: 2px 6px; } "
            "QPushButton:hover { background: rgba(53,200,241,0.24); color: #ffffff; }"
        )
        reply_btn = QPushButton("↩")
        reply_btn.setToolTip("Responder")
        reply_btn.setCursor(Qt.PointingHandCursor)
        reply_btn.setStyleSheet(act_style)
        reply_btn.clicked.connect(
            lambda: self.reply_requested.emit(self.message_id, self.author, self.current_text[:60])
        )
        hdr_row.addWidget(reply_btn)

        for emo in ("👍", "🔥", "🎮"):
            eb = QPushButton(emo)
            eb.setCursor(Qt.PointingHandCursor)
            eb.setStyleSheet(act_style)
            eb.clicked.connect(lambda _, e=emo: self.reaction_toggled.emit(self.message_id, e))
            hdr_row.addWidget(eb)

        if is_self:
            edit_btn = QPushButton("✎")
            edit_btn.setToolTip("Editar")
            edit_btn.setCursor(Qt.PointingHandCursor)
            edit_btn.setStyleSheet(act_style)
            edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.message_id, self.current_text))
            hdr_row.addWidget(edit_btn)

        if is_self or can_moderate:
            del_btn = QPushButton("🗑")
            del_btn.setToolTip("Eliminar")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setStyleSheet(act_style)
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self.message_id))
            hdr_row.addWidget(del_btn)

        content_lay.addLayout(hdr_row)

        if isinstance(reply_preview, dict) and reply_preview.get("id"):
            r_auth = str(reply_preview.get("author_name") or reply_preview.get("author_id") or "Usuario")
            r_txt = str(reply_preview.get("content") or "")[:72]
            rep_lbl = QLabel(f"↩ Respuesta a @{r_auth}: {r_txt}")
            rep_lbl.setStyleSheet(
                "font-size: 11px; color: #a5d8ff; padding: 3px 8px; "
                "background: rgba(53,200,241,0.12); border-left: 2px solid #35C8F1; border-radius: 4px;"
            )
            content_lay.addWidget(rep_lbl)

        self.txt_lbl = QLabel(text)
        self.txt_lbl.setStyleSheet("font-size: 14px; font-weight: 500; color: #F4F6F8;")
        self.txt_lbl.setWordWrap(True)
        self.txt_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.txt_lbl.setVisible(bool(text))
        content_lay.addWidget(self.txt_lbl)

        if attachments:
            att_row = QHBoxLayout()
            att_row.setSpacing(8)
            for att in attachments:
                aid = str(att.get("id") or "")
                fname = str(att.get("filename") or "imagen")
                raw = image_loader(aid) if (image_loader and aid) else None
                if raw:
                    pm = QPixmap()
                    if pm.loadFromData(raw):
                        img_lbl = QLabel()
                        img_lbl.setPixmap(pm.scaled(220, 140, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        img_lbl.setStyleSheet("border: 1px solid rgba(255,255,255,0.22); border-radius: 8px; padding: 2px;")
                        att_row.addWidget(img_lbl)
                        continue
                pill = QLabel(f"🖼 {fname}")
                pill.setStyleSheet("font-size: 11px; color: #cbe6ff; background: rgba(255,255,255,0.08); padding: 4px 8px; border-radius: 6px;")
                att_row.addWidget(pill)
            att_row.addStretch(1)
            content_lay.addLayout(att_row)

        self.reactions_row = QHBoxLayout()
        self.reactions_row.setSpacing(6)
        self.reactions_wrap = QWidget()
        self.reactions_wrap.setLayout(self.reactions_row)
        self.reactions_wrap.setVisible(False)
        content_lay.addWidget(self.reactions_wrap)
        self.update_reactions(reactions or [])

        layout.addLayout(content_lay, 1)

    def update_content(self, new_text: str, edited: bool = True):
        self.current_text = new_text
        self.txt_lbl.setText(new_text)
        self.txt_lbl.setVisible(bool(new_text))
        if edited and "(editado)" not in self.time_lbl.text():
            self.time_lbl.setText(f"{self.time_lbl.text()} (editado)")

    def update_reactions(self, reactions: list):
        _clear_layout_widgets(self.reactions_row)
        if not reactions:
            self.reactions_wrap.setVisible(False)
            return
        for r in reactions:
            emo = str(r.get("emoji") or "")
            cnt = int(r.get("count") or 0)
            if not emo or cnt <= 0:
                continue
            chip = QPushButton(f"{emo} {cnt}")
            chip.setCursor(Qt.PointingHandCursor)
            chip.setStyleSheet(
                "QPushButton { background: rgba(53,200,241,0.16); border: 1px solid rgba(53,200,241,0.4); "
                "border-radius: 10px; color: #ffffff; font-size: 11px; font-weight: 700; padding: 2px 8px; } "
                "QPushButton:hover { background: rgba(53,200,241,0.34); }"
            )
            chip.clicked.connect(lambda _, e=emo: self.reaction_toggled.emit(self.message_id, e))
            self.reactions_row.addWidget(chip)
        self.reactions_row.addStretch(1)
        self.reactions_wrap.setVisible(True)


class StreamStageWidget(QFrame):
    """Visor WebRTC real de pantalla / juego (LiveKit SOURCE_SCREENSHARE + preview)."""

    stop_requested = Signal()
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        self.frames_rendered: int = 0
        self.last_frame_size: tuple[int, int] = (0, 0)
        self.last_frame_rgba: Optional[bytes] = None
        self._is_broadcaster: bool = False

        self.setStyleSheet("""
            StreamStageWidget {
                background: rgba(7, 16, 26, 0.92);
                border: 1px solid rgba(53, 200, 241, 0.45);
                border-radius: 14px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        self.live_badge = QLabel("● LIVE")
        self.live_badge.setStyleSheet(
            "background: #E94B56; color: #ffffff; font-size: 11px; font-weight: 800; "
            "padding: 2px 8px; border-radius: 8px;"
        )
        hdr.addWidget(self.live_badge)

        self.title_lbl = QLabel("Transmisión en vivo")
        self.title_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #ffffff;")
        hdr.addWidget(self.title_lbl, 1)

        self.meta_lbl = QLabel("")
        self.meta_lbl.setStyleSheet("font-size: 11px; color: #8ad8f0;")
        hdr.addWidget(self.meta_lbl)

        self.action_btn = QPushButton("Cerrar")
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.setStyleSheet(
            "QPushButton { background: rgba(233, 75, 86, 0.25); border: 1px solid #E94B56; "
            "border-radius: 8px; color: #ffffff; font-size: 11px; font-weight: 700; padding: 3px 10px; } "
            "QPushButton:hover { background: #E94B56; }"
        )
        self.action_btn.clicked.connect(self._on_action_clicked)
        hdr.addWidget(self.action_btn)
        lay.addLayout(hdr)

        self.video_lbl = QLabel("Esperando video WebRTC de LiveKit...")
        self.video_lbl.setAlignment(Qt.AlignCenter)
        self.video_lbl.setMinimumHeight(180)
        self.video_lbl.setMaximumHeight(320)
        self.video_lbl.setStyleSheet(
            "background: #040b12; border-radius: 10px; color: #7f95a6; font-size: 12px; font-weight: 600;"
        )
        lay.addWidget(self.video_lbl)

    def _on_action_clicked(self):
        if self._is_broadcaster:
            self.stop_requested.emit()
        else:
            self.close_requested.emit()

    def set_stream_session(self, info: Optional[dict], is_broadcaster: bool = False):
        if not info or (not info.get("live") and not info.get("watching")):
            self.clear_stream()
            return
        self._is_broadcaster = bool(is_broadcaster or info.get("live"))
        sess = info.get("session") or {}
        title = str(sess.get("title") or info.get("title") or "Pantalla compartida")
        username = str(sess.get("username") or "")
        res = str(sess.get("resolution") or f"{info.get('width') or ''}x{info.get('height') or ''}")
        fps = info.get("fps") or sess.get("fps") or 30
        self.title_lbl.setText(f"{username} — {title}" if username else title)
        self.meta_lbl.setText(f"{res} · {fps} fps")
        self.live_badge.setVisible(True)
        self.action_btn.setText("Dejar de compartir" if self._is_broadcaster else "Cerrar visor")
        self.setVisible(True)

    def update_rgba_frame(self, width: int, height: int, rgba: bytes):
        if width <= 0 or height <= 0 or not rgba:
            return
        expected = int(width) * int(height) * 4
        if len(rgba) < expected:
            return
        img = QImage(rgba, int(width), int(height), int(width) * 4, QImage.Format_RGBA8888).copy()
        pm = QPixmap.fromImage(img)
        target_w = max(320, self.video_lbl.width() or 560)
        target_h = max(180, self.video_lbl.height() or 280)
        self.video_lbl.setPixmap(pm.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.last_frame_size = (int(width), int(height))
        self.last_frame_rgba = bytes(rgba[:expected])
        self.frames_rendered += 1
        self.meta_lbl.setText(f"{width}x{height} · {self.frames_rendered} frames")
        if not self.isVisible():
            self.setVisible(True)

    def clear_stream(self):
        self.frames_rendered = 0
        self.last_frame_size = (0, 0)
        self.last_frame_rgba = None
        self._is_broadcaster = False
        self.video_lbl.clear()
        self.video_lbl.setText("Esperando video WebRTC de LiveKit...")
        self.meta_lbl.setText("")
        self.setVisible(False)


class CentralChatWidget(AcrylicGlassCard):
    message_submit_requested = Signal(str)
    refresh_requested = Signal()
    older_messages_requested = Signal(str)        # oldest_message_id
    message_edit_requested = Signal(str, str)     # message_id, new_text
    message_delete_requested = Signal(str)        # message_id
    reaction_toggle_requested = Signal(str, str)  # message_id, emoji
    attachment_upload_requested = Signal(str)     # local_path
    typing_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            border_radius=22,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10,
        )
        self._msg_widgets: dict[str, ChatMessageWidget] = {}
        self._msg_order: list[str] = []
        self._current_user_id: str = ""
        self._can_moderate: bool = False
        self._image_loader = None
        self._reply_to_id: Optional[str] = None
        self._editing_msg_id: Optional[str] = None
        self._pending_attachments: list[dict] = []
        self._last_typing_emit = 0.0
        self._typing_peers: dict[str, str] = {}

        self._typing_clear_timer = QTimer(self)
        self._typing_clear_timer.setSingleShot(True)
        self._typing_clear_timer.setInterval(3500)
        self._typing_clear_timer.timeout.connect(self._clear_typing_indicator)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(8)

        c_hdr = QHBoxLayout()
        c_hdr.setContentsMargins(4, 2, 4, 6)
        c_hdr.setSpacing(10)

        t_box = QVBoxLayout()
        t_box.setSpacing(2)
        self.c_title = QLabel("# Seleccioná un canal")
        self.c_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        self.c_topic = QLabel("Mensajería persistida y en tiempo real.")
        self.c_topic.setStyleSheet("font-size: 12px; color: #BDD4E4;")
        t_box.addWidget(self.c_title)
        t_box.addWidget(self.c_topic)
        c_hdr.addLayout(t_box)
        c_hdr.addStretch(1)

        self.load_older_btn = QPushButton("↑ Anteriores")
        self.load_older_btn.setCursor(Qt.PointingHandCursor)
        self.load_older_btn.setVisible(False)
        self.load_older_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18); "
            "border-radius: 8px; color: #BDD4E4; font-size: 11px; font-weight: 700; padding: 4px 10px; } "
            "QPushButton:hover { background: rgba(53,200,241,0.22); color: #ffffff; }"
        )
        self.load_older_btn.clicked.connect(self._on_load_older_clicked)
        c_hdr.addWidget(self.load_older_btn)

        self.rt_badge = QLabel("● Offline")
        self.rt_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #7f95a6; padding: 4px 10px; background: rgba(255,255,255,0.06); border-radius: 10px;")
        c_hdr.addWidget(self.rt_badge)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedSize(32, 32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Recargar mensajes")
        self.refresh_btn.setStyleSheet("QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.16); border-radius: 8px; color: #ffffff; font-size: 15px; font-weight: 700; } QPushButton:hover { background: rgba(255,255,255,0.12); }")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        c_hdr.addWidget(self.refresh_btn)

        layout.addLayout(c_hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(145, 165, 179, 0.22);")
        layout.addWidget(sep)

        self.error_banner = QLabel("")
        self.error_banner.setWordWrap(True)
        self.error_banner.setVisible(False)
        self.error_banner.setStyleSheet(
            "background: rgba(233, 75, 86, 0.22); border: 1px solid rgba(233, 75, 86, 0.65); "
            "border-radius: 10px; color: #ffd6d9; font-size: 12px; font-weight: 600; padding: 8px 12px;"
        )
        layout.addWidget(self.error_banner)

        self.stream_stage = StreamStageWidget(self)
        layout.addWidget(self.stream_stage)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; }
            QScrollBar:vertical { background: rgba(10, 20, 30, 0.3); width: 6px; margin: 0px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: rgba(145, 165, 179, 0.4); min-height: 24px; border-radius: 3px; }
            QScrollBar::handle:vertical:hover { background: rgba(53, 200, 241, 0.7); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.scroll.viewport().setStyleSheet("background: transparent;")
        self.scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        self.scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        pal = self.scroll.viewport().palette()
        pal.setColor(QPalette.Base, Qt.transparent)
        pal.setColor(QPalette.Window, Qt.transparent)
        self.scroll.viewport().setPalette(pal)

        self.msgs_container = QWidget()
        self.msgs_container.setStyleSheet("background: transparent;")
        self.msgs_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.msgs_layout = QVBoxLayout(self.msgs_container)
        self.msgs_layout.setContentsMargins(4, 8, 4, 8)
        self.msgs_layout.setSpacing(10)

        self.empty_lbl = QLabel("No hay mensajes en este canal todavía.")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet("font-size: 13px; color: #8da4b8; padding: 24px;")
        self.msgs_layout.addWidget(self.empty_lbl)
        self.msgs_layout.addStretch(1)

        self.scroll.setWidget(self.msgs_container)
        layout.addWidget(self.scroll, 1)

        self.typing_lbl = QLabel("")
        self.typing_lbl.setVisible(False)
        self.typing_lbl.setStyleSheet("font-size: 11px; color: #35C8F1; font-style: italic; padding-left: 8px;")
        layout.addWidget(self.typing_lbl)

        self.context_bar = QFrame()
        self.context_bar.setVisible(False)
        self.context_bar.setStyleSheet(
            "QFrame { background: rgba(53,200,241,0.14); border: 1px solid rgba(53,200,241,0.35); border-radius: 10px; }"
        )
        ctx_lay = QHBoxLayout(self.context_bar)
        ctx_lay.setContentsMargins(10, 4, 8, 4)
        self.context_lbl = QLabel("")
        self.context_lbl.setStyleSheet("font-size: 11px; color: #dff5ff; border: none; background: transparent;")
        ctx_cancel = QPushButton("✕")
        ctx_cancel.setFixedSize(22, 22)
        ctx_cancel.setCursor(Qt.PointingHandCursor)
        ctx_cancel.setStyleSheet("background: transparent; border: none; color: #ffffff; font-weight: 800;")
        ctx_cancel.clicked.connect(self.clear_compose_context)
        ctx_lay.addWidget(self.context_lbl, 1)
        ctx_lay.addWidget(ctx_cancel)
        layout.addWidget(self.context_bar)

        comp_frame = QFrame()
        comp_frame.setFixedHeight(52)
        comp_frame.setStyleSheet("""
            QFrame {
                background: rgba(14, 28, 42, 0.75);
                border: 1.5px solid rgba(145, 165, 179, 0.35);
                border-radius: 26px;
            }
        """)
        comp_lay = QHBoxLayout(comp_frame)
        comp_lay.setContentsMargins(12, 0, 12, 0)
        comp_lay.setSpacing(8)

        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(32, 32)
        self.attach_btn.setCursor(Qt.PointingHandCursor)
        self.attach_btn.setToolTip("Adjuntar imagen (PNG/JPEG/WEBP/GIF)")
        self.attach_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: none; border-radius: 16px; color: #BDD4E4; font-size: 14px; } "
            "QPushButton:hover { background: rgba(53,200,241,0.28); color: #ffffff; }"
        )
        self.attach_btn.clicked.connect(self._on_pick_attachment)
        comp_lay.addWidget(self.attach_btn)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Enviar mensaje...")
        self.msg_input.setStyleSheet("QLineEdit { background: transparent; border: none; color: #ffffff; font-size: 13px; padding-left: 4px; }")
        self.msg_input.returnPressed.connect(self._on_submit)
        self.msg_input.textChanged.connect(self._on_input_text_changed)
        comp_lay.addWidget(self.msg_input, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(34, 34)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton { background: rgba(53, 200, 241, 0.2); border: 1.5px solid #35C8F1; border-radius: 17px; font-size: 14px; color: #35C8F1; }
            QPushButton:hover { background: rgba(53, 200, 241, 0.45); }
        """)
        self.send_btn.clicked.connect(self._on_submit)
        comp_lay.addWidget(self.send_btn)

        layout.addWidget(comp_frame)

    def set_attachment_loader(self, loader):
        self._image_loader = loader

    def set_can_moderate(self, can_mod: bool):
        self._can_moderate = bool(can_mod)

    def set_realtime_status(self, connected: bool, detail: str = ""):
        if connected:
            self.rt_badge.setText("● Realtime")
            self.rt_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #32D875; padding: 4px 10px; background: rgba(50,216,117,0.14); border-radius: 10px;")
            self.rt_badge.setToolTip(detail or "Socket.IO conectado")
        else:
            self.rt_badge.setText("● Sin realtime")
            self.rt_badge.setStyleSheet("font-size: 11px; font-weight: 700; color: #ffd166; padding: 4px 10px; background: rgba(255,209,102,0.12); border-radius: 10px;")
            self.rt_badge.setToolTip(detail or "Desconectado")

    def show_error(self, message: str):
        if message:
            self.error_banner.setText(message)
            self.error_banner.setVisible(True)
        else:
            self.error_banner.setVisible(False)

    def set_channel(self, channel: Optional[dict]):
        self.show_error("")
        self.clear_compose_context()
        self._typing_peers.clear()
        self._clear_typing_indicator()
        if channel:
            name = str(channel.get("name") or "general")
            self.c_title.setText(f"# {name}")
            self.c_topic.setText(str(channel.get("topic") or "Canal de comunidad"))
            self.msg_input.setPlaceholderText(f"Enviar mensaje a #{name}...")
            self.msg_input.setEnabled(True)
            self.send_btn.setEnabled(True)
            self.attach_btn.setEnabled(True)
        else:
            self.c_title.setText("# Sin canal")
            self.c_topic.setText("No hay canales disponibles")
            self.msg_input.setPlaceholderText("Seleccioná un canal...")
            self.msg_input.setEnabled(False)
            self.send_btn.setEnabled(False)
            self.attach_btn.setEnabled(False)
            self.load_older_btn.setVisible(False)

    def _build_msg_widget(self, msg: dict, current_user_id: str) -> ChatMessageWidget:
        mid = str(msg.get("id") or "")
        author_id = str(msg.get("author_id") or "")
        author_name = str(msg.get("author_name") or author_id or "Usuario")
        time_str = _format_message_time(msg.get("created_at"))
        w = ChatMessageWidget(
            message_id=mid,
            author=author_name,
            time_str=time_str,
            text=str(msg.get("content") or ""),
            is_self=(bool(current_user_id) and author_id == str(current_user_id)),
            edited=bool(msg.get("edited_at")),
            reply_preview=msg.get("reply_preview"),
            reactions=msg.get("reactions"),
            attachments=msg.get("attachments"),
            image_loader=self._image_loader,
            can_moderate=self._can_moderate,
            parent=self.msgs_container,
        )
        w.reply_requested.connect(self._set_reply_target)
        w.edit_requested.connect(self._start_edit_message)
        w.delete_requested.connect(self.message_delete_requested.emit)
        w.reaction_toggled.connect(self.reaction_toggle_requested.emit)
        return w

    def set_messages(self, messages: list[dict], current_user_id: str = ""):
        self._current_user_id = current_user_id
        self._msg_widgets.clear()
        self._msg_order.clear()
        _clear_layout_widgets(self.msgs_layout, keep_trailing_stretch=True)

        self.empty_lbl = QLabel("No hay mensajes en este canal todavía.")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.empty_lbl.setStyleSheet("font-size: 13px; color: #8da4b8; padding: 24px;")
        self.msgs_layout.insertWidget(0, self.empty_lbl)

        for m in messages or []:
            self.append_or_update_message(m, current_user_id=current_user_id, scroll_to_bottom=False)
        self.empty_lbl.setVisible(len(self._msg_widgets) == 0)
        self.load_older_btn.setVisible(len(self._msg_order) >= 20)
        QTimer.singleShot(20, self._scroll_bottom)

    def prepend_messages(self, older_messages: list[dict], current_user_id: str = ""):
        if not older_messages:
            self.load_older_btn.setVisible(False)
            return
        added = 0
        # Insert after empty_lbl (index 1)
        pos = 1
        for m in older_messages:
            mid = str(m.get("id") or "")
            if not mid or mid in self._msg_widgets:
                continue
            w = self._build_msg_widget(m, current_user_id or self._current_user_id)
            self._msg_widgets[mid] = w
            self._msg_order.insert(added, mid)
            self.msgs_layout.insertWidget(pos, w)
            pos += 1
            added += 1
        if added == 0:
            self.load_older_btn.setVisible(False)
        self.empty_lbl.setVisible(len(self._msg_widgets) == 0)

    def sync_new_messages(self, missed_messages: list[dict], current_user_id: str = ""):
        """Sincroniza mensajes perdidos tras reconexión sin duplicar IDs ya renderizados."""
        for m in missed_messages or []:
            self.append_or_update_message(m, current_user_id=current_user_id or self._current_user_id, scroll_to_bottom=False)
        if missed_messages:
            QTimer.singleShot(20, self._scroll_bottom)

    def append_or_update_message(self, msg: dict, current_user_id: str = "", scroll_to_bottom: bool = True):
        mid = str(msg.get("id") or "")
        if not mid:
            return
        if current_user_id:
            self._current_user_id = current_user_id
        content = str(msg.get("content") or "")
        edited = bool(msg.get("edited_at"))
        if mid in self._msg_widgets:
            self._msg_widgets[mid].update_content(content, edited=edited)
            if "reactions" in msg:
                self._msg_widgets[mid].update_reactions(msg.get("reactions") or [])
            return

        w = self._build_msg_widget(msg, self._current_user_id)
        self._msg_widgets[mid] = w
        self._msg_order.append(mid)
        self.empty_lbl.setVisible(False)
        insert_idx = max(0, self.msgs_layout.count() - 1)
        self.msgs_layout.insertWidget(insert_idx, w)
        if scroll_to_bottom:
            QTimer.singleShot(20, self._scroll_bottom)

    def update_message_reactions(self, message_id: str, reactions: list):
        w = self._msg_widgets.get(str(message_id))
        if w is not None:
            w.update_reactions(reactions or [])

    def remove_message(self, message_id: str):
        mid = str(message_id)
        w = self._msg_widgets.pop(mid, None)
        if mid in self._msg_order:
            self._msg_order.remove(mid)
        if w is not None:
            self.msgs_layout.removeWidget(w)
            w.deleteLater()
        self.empty_lbl.setVisible(len(self._msg_widgets) == 0)

    def show_typing_peer(self, user_id: str, username: str, typing: bool):
        if str(user_id) == str(self._current_user_id):
            return
        if typing:
            self._typing_peers[str(user_id)] = username or "Alguien"
        else:
            self._typing_peers.pop(str(user_id), None)
        self._refresh_typing_label()
        if self._typing_peers:
            self._typing_clear_timer.start()

    def _clear_typing_indicator(self):
        self._typing_peers.clear()
        self._refresh_typing_label()

    def _refresh_typing_label(self):
        names = list(self._typing_peers.values())
        if not names:
            self.typing_lbl.setVisible(False)
            self.typing_lbl.setText("")
        elif len(names) == 1:
            self.typing_lbl.setText(f"{names[0]} está escribiendo...")
            self.typing_lbl.setVisible(True)
        else:
            self.typing_lbl.setText(f"{', '.join(names[:3])} están escribiendo...")
            self.typing_lbl.setVisible(True)

    def _set_reply_target(self, message_id: str, author: str, snippet: str):
        self._editing_msg_id = None
        self._reply_to_id = message_id
        self._refresh_context_bar(f"↩ Respondiendo a @{author}: {snippet}")
        self.msg_input.setFocus()

    def _start_edit_message(self, message_id: str, current_text: str):
        self._reply_to_id = None
        self._editing_msg_id = message_id
        self.msg_input.setText(current_text)
        self.msg_input.setFocus()
        self._refresh_context_bar("✎ Editando tu mensaje (Enter para guardar)")

    def add_uploaded_attachment(self, att: dict):
        if att and att.get("id"):
            self._pending_attachments.append(att)
            names = ", ".join(str(a.get("filename") or "imagen") for a in self._pending_attachments)
            self._refresh_context_bar(f"📎 Adjuntos ({len(self._pending_attachments)}): {names}")

    def consume_compose_meta(self) -> tuple[Optional[str], list[str]]:
        reply_id = self._reply_to_id
        att_ids = [str(a["id"]) for a in self._pending_attachments if a.get("id")]
        self.clear_compose_context()
        return reply_id, att_ids

    def clear_compose_context(self):
        self._reply_to_id = None
        self._editing_msg_id = None
        self._pending_attachments.clear()
        self.context_bar.setVisible(False)
        self.context_lbl.setText("")

    def _refresh_context_bar(self, text: str):
        self.context_lbl.setText(text)
        self.context_bar.setVisible(True)

    def _on_pick_attachment(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Adjuntar imagen",
            str(ROOT),
            "Imágenes (*.png *.jpg *.jpeg *.webp *.gif)",
        )
        if path:
            self.attachment_upload_requested.emit(path)

    def _on_load_older_clicked(self):
        if self._msg_order:
            self.older_messages_requested.emit(self._msg_order[0])

    def _on_input_text_changed(self, txt: str):
        now = time.monotonic()
        if txt.strip() and now - self._last_typing_emit >= 2.0:
            self._last_typing_emit = now
            self.typing_changed.emit(True)

    def _scroll_bottom(self):
        bar = self.scroll.verticalScrollBar()
        if bar:
            bar.setValue(bar.maximum())

    def _on_submit(self):
        txt = self.msg_input.text().strip()
        if self._editing_msg_id:
            if not txt:
                return
            mid = self._editing_msg_id
            self.clear_compose_context()
            self.msg_input.clear()
            self.message_edit_requested.emit(mid, txt)
            return
        if not txt and not self._pending_attachments:
            return
        self.show_error("")
        self.message_submit_requested.emit(txt)


class MemberItemWidget(QWidget):
    moderation_requested = Signal(str, str)  # user_id, action

    def __init__(
        self,
        name: str,
        status_text: str,
        is_online: bool,
        avatar_path: Optional[Path] = None,
        has_crown: bool = False,
        user_id: str = "",
        presence_status: str = "offline",
        is_muted: bool = False,
        can_moderate: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.user_id = user_id
        self.is_muted = is_muted
        self.can_moderate = can_moderate and bool(user_id)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        if self.can_moderate:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
            self.customContextMenuRequested.connect(self._show_mod_menu)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 5, 4, 5)
        layout.setSpacing(12)

        av_container = QWidget()
        av_container.setFixedSize(46, 46)
        av_container.setAttribute(Qt.WA_TranslucentBackground, True)
        av_container.setStyleSheet("background: transparent;")

        av_lbl = QLabel(av_container)
        av_lbl.setGeometry(0, 0, 42, 42)
        av_lbl.setAlignment(Qt.AlignCenter)
        if avatar_path and avatar_path.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(avatar_path)), 42, 42, 21))
        else:
            av_lbl.setText((name[:1] or "?").upper())
            bg = "rgba(53, 200, 241, 0.32)" if is_online else "rgba(255, 255, 255, 0.1)"
            av_lbl.setStyleSheet(
                f"background: {bg}; border: 1px solid rgba(255,255,255,0.25); "
                "border-radius: 21px; color: #ffffff; font-size: 15px; font-weight: 800;"
            )

        dot = QLabel(av_container)
        dot.setGeometry(30, 30, 13, 13)
        st_low = (presence_status or "").lower()
        if not is_online or st_low in ("offline", "invisible"):
            dot_col = "#7f95a6"
        elif "jugando" in status_text.lower():
            dot_col = "#A77AE4"
        elif st_low in ("idle", "away"):
            dot_col = "#FFD166"
        elif st_low in ("dnd", "busy"):
            dot_col = "#E94B56"
        else:
            dot_col = "#32D875"
        dot.setStyleSheet(f"background: {dot_col}; border: 2.2px solid #102638; border-radius: 6.5px;")

        layout.addWidget(av_container)

        info = QVBoxLayout()
        info.setSpacing(2)

        n_row = QHBoxLayout()
        n_row.setSpacing(5)
        nl = QLabel(f"{name} 🔇" if is_muted else name)
        nl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {'#ffffff' if is_online else '#91A5B3'};")
        n_row.addWidget(nl)

        if has_crown:
            cr = QLabel("👑")
            cr.setStyleSheet("font-size: 13px; color: #ffd700;")
            n_row.addWidget(cr)

        n_row.addStretch(1)
        info.addLayout(n_row)

        st = QLabel(status_text)
        if not is_online:
            st_color = "#657C8D"
        elif "jugando" in status_text.lower():
            st_color = "#32D875"
        elif st_low in ("idle", "away"):
            st_color = "#FFD166"
        elif st_low in ("dnd", "busy"):
            st_color = "#ffb3b8"
        else:
            st_color = "#7f95a6"
        st.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {st_color};")
        info.addWidget(st)

        layout.addLayout(info, 1)

    def _show_mod_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background: #102438; color: #ffffff; border: 1px solid rgba(53,200,241,0.45); } QMenu::item:selected { background: rgba(53,200,241,0.3); }")
        mute_act = menu.addAction("Quitar silencio" if self.is_muted else "Silenciar (10 min)")
        kick_act = menu.addAction("Expulsar de la comunidad")
        ban_act = menu.addAction("Banear permanentemente")
        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen == mute_act:
            self.moderation_requested.emit(self.user_id, "unmute" if self.is_muted else "mute")
        elif chosen == kick_act:
            self.moderation_requested.emit(self.user_id, "kick")
        elif chosen == ban_act:
            self.moderation_requested.emit(self.user_id, "ban")


class RightPanel(QWidget):
    voice_toggled = Signal(str, bool)
    self_presence_changed = Signal(str, str)       # status, activity_visibility
    member_moderation_requested = Signal(str, str)  # user_id, action
    soundboard_play_requested = Signal(str)         # sound_id
    soundboard_stop_requested = Signal()
    soundboard_upload_requested = Signal(str)       # file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(305)
        self._media_ready = False
        self._can_moderate = False
        self._self_user_id = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Contenedor de Miembros en Dark Glass (100% desde backend)
        self.members_card = AcrylicGlassCard(
            self,
            border_radius=20,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 45),
            glow_radius=10,
        )
        mem_lay = QVBoxLayout(self.members_card)
        mem_lay.setContentsMargins(12, 12, 12, 12)
        mem_lay.setSpacing(6)

        pres_box = QVBoxLayout()
        pres_box.setSpacing(4)
        self.status_combo = QComboBox()
        self.status_combo.addItem("🟢 En línea", "online")
        self.status_combo.addItem("🌙 Ausente", "idle")
        self.status_combo.addItem("⛔ No molestar", "dnd")
        self.status_combo.addItem("👻 Invisible", "invisible")
        self.status_combo.setFixedHeight(28)
        self.status_combo.setStyleSheet(
            "QComboBox { background: rgba(14, 28, 44, 0.8); border: 1px solid rgba(145,165,179,0.35); "
            "border-radius: 8px; color: #ffffff; font-size: 12px; padding: 2px 8px; }"
        )
        self.status_combo.currentIndexChanged.connect(self._on_self_presence_ui_changed)
        pres_box.addWidget(self.status_combo)

        self.share_game_chk = QCheckBox("Mostrar juego activo")
        self.share_game_chk.setChecked(True)
        self.share_game_chk.setStyleSheet("font-size: 11px; color: #BDD4E4;")
        self.share_game_chk.toggled.connect(self._on_self_presence_ui_changed)
        pres_box.addWidget(self.share_game_chk)
        mem_lay.addLayout(pres_box)

        m_scroll = QScrollArea()
        m_scroll.setWidgetResizable(True)
        m_scroll.setStyleSheet("""
            QScrollArea, QScrollArea > QWidget > QWidget {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(10, 20, 30, 0.3);
                width: 6px;
                margin: 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(145, 165, 179, 0.4);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        m_scroll.viewport().setStyleSheet("background: transparent;")
        m_scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)
        m_scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        pal_m = m_scroll.viewport().palette()
        pal_m.setColor(QPalette.Base, Qt.transparent)
        pal_m.setColor(QPalette.Window, Qt.transparent)
        m_scroll.viewport().setPalette(pal_m)

        self.m_container = QWidget()
        self.m_container.setStyleSheet("background: transparent;")
        self.m_container.setAttribute(Qt.WA_TranslucentBackground, True)
        self.m_lay = QVBoxLayout(self.m_container)
        self.m_lay.setContentsMargins(0, 0, 0, 0)
        self.m_lay.setSpacing(6)
        self.m_lay.addStretch(1)

        m_scroll.setWidget(self.m_container)
        mem_lay.addWidget(m_scroll)
        layout.addWidget(self.members_card, 1)

        # Panel de Voz / Señalización LiveKit (oculto hasta intentar o conectar a canal de voz)
        self.voice_panel = AcrylicGlassCard(
            self,
            border_radius=18,
            border_color=QColor(93, 116, 131, 80),
            glow_color=QColor(0, 0, 0, 50),
            glow_radius=10
        )
        self.voice_panel.setMinimumHeight(185)
        v_lay = QVBoxLayout(self.voice_panel)
        v_lay.setContentsMargins(14, 14, 14, 14)
        v_lay.setSpacing(10)

        v_hdr = QHBoxLayout()
        v_hdr.setSpacing(8)

        v_wave = QLabel()
        wave_p = ROOT / "assets_omnidash" / "icons" / "sound_wave.png"
        if wave_p.exists():
            v_wave.setPixmap(QPixmap(str(wave_p)).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v_hdr.addWidget(v_wave)

        v_titles = QVBoxLayout()
        v_titles.setSpacing(1)
        self.v_st = QLabel("Voz desconectada")
        self.v_st.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffffff;")
        self.v_chan = QLabel("Sin canal")
        self.v_chan.setStyleSheet("font-size: 12px; font-weight: 600; color: #BDD4E4;")
        v_titles.addWidget(self.v_st)
        v_titles.addWidget(self.v_chan)
        v_hdr.addLayout(v_titles)
        v_hdr.addStretch(1)

        self.v_live_badge = QLabel("● LIVE")
        self.v_live_badge.setVisible(False)
        self.v_live_badge.setStyleSheet(
            "background: #E94B56; color: #ffffff; font-size: 10px; font-weight: 800; "
            "padding: 2px 7px; border-radius: 7px;"
        )
        v_hdr.addWidget(self.v_live_badge)

        user_ico = QLabel()
        u_p = ROOT / "assets_omnidash" / "icons" / "person.png"
        if u_p.exists():
            user_ico.setPixmap(QPixmap(str(u_p)).scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        v_hdr.addWidget(user_ico)

        v_lay.addLayout(v_hdr)

        self.v_media_lbl = QLabel("Sin transporte multimedia activo.")
        self.v_media_lbl.setWordWrap(True)
        self.v_media_lbl.setStyleSheet("font-size: 11px; color: #ffd166;")
        v_lay.addWidget(self.v_media_lbl)

        src_row = QHBoxLayout()
        src_row.setSpacing(6)
        self.screen_source_combo = QComboBox()
        self.screen_source_combo.addItem("Pantalla principal", "screen:0")
        self.screen_source_combo.addItem("Ventana OmniDash", "window:omnidash")
        self.screen_source_combo.setStyleSheet(
            "QComboBox { background: rgba(10, 22, 34, 0.72); border: 1px solid rgba(145,165,179,0.28); "
            "border-radius: 7px; padding: 3px 8px; color: #BDD4E4; font-size: 11px; }"
        )
        src_row.addWidget(self.screen_source_combo, 1)

        self.screen_res_combo = QComboBox()
        self.screen_res_combo.addItem("720p 30fps", ("720p", 30, 2500))
        self.screen_res_combo.addItem("1080p 60fps", ("1080p", 60, 4500))
        self.screen_res_combo.addItem("1440p 60fps", ("1440p", 60, 7500))
        self.screen_res_combo.setStyleSheet(
            "QComboBox { background: rgba(10, 22, 34, 0.72); border: 1px solid rgba(145,165,179,0.28); "
            "border-radius: 7px; padding: 3px 6px; color: #BDD4E4; font-size: 11px; }"
        )
        src_row.addWidget(self.screen_res_combo)
        v_lay.addLayout(src_row)

        ctrls_row = QHBoxLayout()
        ctrls_row.setSpacing(8)

        self.mic_btn = QPushButton()
        self.mic_btn.setFixedSize(40, 40)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_muted = False
        self._update_mic_style()
        self.mic_btn.clicked.connect(self._toggle_mic)
        ctrls_row.addWidget(self.mic_btn)

        self.headset_btn = QPushButton()
        self.headset_btn.setFixedSize(40, 40)
        self.headset_btn.setCursor(Qt.PointingHandCursor)
        self.headset_muted = False
        self._update_headset_style()
        self.headset_btn.clicked.connect(self._toggle_headset)
        ctrls_row.addWidget(self.headset_btn)

        self.screen_btn = QPushButton()
        self.screen_btn.setFixedSize(40, 40)
        self.screen_btn.setCursor(Qt.PointingHandCursor)
        self.screen_btn.setToolTip("Compartir pantalla o ventana en vivo (LiveKit WebRTC)")
        self.screen_active = False
        self._update_screen_style()
        self.screen_btn.clicked.connect(self._toggle_screen)
        ctrls_row.addWidget(self.screen_btn)

        self.soundboard_btn = QPushButton("🔊")
        self.soundboard_btn.setFixedSize(40, 40)
        self.soundboard_btn.setCursor(Qt.PointingHandCursor)
        self.soundboard_btn.setToolTip("Abrir Soundboard RTC")
        self.soundboard_btn.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); "
            "border-radius: 20px; color: #ffffff; font-size: 15px; } "
            "QPushButton:hover { background: rgba(53, 200, 241, 0.25); }"
        )
        self.soundboard_btn.clicked.connect(self._toggle_soundboard_drawer)
        ctrls_row.addWidget(self.soundboard_btn)

        self.dc_btn = QPushButton()
        self.dc_btn.setFixedSize(40, 40)
        self.dc_btn.setCursor(Qt.PointingHandCursor)
        dc_p = ROOT / "assets_omnidash" / "icons" / "phone_disconnect.png"
        if dc_p.exists():
            self.dc_btn.setIcon(QIcon(str(dc_p)))
            self.dc_btn.setIconSize(QSize(18, 18))
        self.dc_btn.setStyleSheet("""
            QPushButton {
                background: #E94B56;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background: #ff606c;
            }
        """)
        self.dc_btn.clicked.connect(self._disconnect_voice)
        ctrls_row.addWidget(self.dc_btn)

        v_lay.addLayout(ctrls_row)

        # Drawer colapsable de Soundboard RTC (P1-C)
        self.soundboard_drawer = QFrame()
        self.soundboard_drawer.setStyleSheet(
            "QFrame { background: rgba(8, 18, 28, 0.78); border: 1px solid rgba(145,165,179,0.22); "
            "border-radius: 12px; }"
        )
        sb_lay = QVBoxLayout(self.soundboard_drawer)
        sb_lay.setContentsMargins(8, 8, 8, 8)
        sb_lay.setSpacing(6)

        sb_hdr = QHBoxLayout()
        sb_hdr.setSpacing(4)
        sb_title = QLabel("Soundboard RTC")
        sb_title.setStyleSheet("font-size: 11px; font-weight: 800; color: #35C8F1; border: none;")
        sb_hdr.addWidget(sb_title)
        sb_hdr.addStretch(1)

        self.sb_stop_btn = QPushButton("Detener")
        self.sb_stop_btn.setCursor(Qt.PointingHandCursor)
        self.sb_stop_btn.setStyleSheet(
            "QPushButton { background: rgba(233,75,86,0.22); border: 1px solid rgba(233,75,86,0.5); "
            "border-radius: 6px; color: #ffd6d9; font-size: 10px; font-weight: 700; padding: 2px 6px; }"
        )
        self.sb_stop_btn.clicked.connect(self.soundboard_stop_requested.emit)
        sb_hdr.addWidget(self.sb_stop_btn)

        self.sb_upload_btn = QPushButton("+ MP3")
        self.sb_upload_btn.setCursor(Qt.PointingHandCursor)
        self.sb_upload_btn.setStyleSheet(
            "QPushButton { background: rgba(53,200,241,0.18); border: 1px solid rgba(53,200,241,0.45); "
            "border-radius: 6px; color: #BDD4E4; font-size: 10px; font-weight: 700; padding: 2px 6px; }"
        )
        self.sb_upload_btn.clicked.connect(self._on_sb_upload_clicked)
        sb_hdr.addWidget(self.sb_upload_btn)
        sb_lay.addLayout(sb_hdr)

        self.sb_grid = QGridLayout()
        self.sb_grid.setSpacing(5)
        sb_lay.addLayout(self.sb_grid)

        self.sb_status_lbl = QLabel("Listo para transmitir efectos por voz RTC.")
        self.sb_status_lbl.setWordWrap(True)
        self.sb_status_lbl.setStyleSheet("font-size: 10px; color: #9fc2d8; border: none;")
        sb_lay.addWidget(self.sb_status_lbl)

        self.soundboard_drawer.setVisible(False)
        v_lay.addWidget(self.soundboard_drawer)

        layout.addWidget(self.voice_panel)
        self.voice_panel.setVisible(False)
        self.set_soundboard_sounds([])
        self.set_members([])

    def set_members(self, members: list[dict], presence: Optional[dict[str, dict]] = None):
        _clear_layout_widgets(self.m_lay, keep_trailing_stretch=True)
        presence = presence or {}

        online_items = []
        offline_items = []
        for m in members or []:
            uid = str(m.get("user_id") or "")
            name = str(m.get("username") or uid or "Miembro")
            role = str(m.get("role") or "member").lower()
            pinfo = presence.get(uid) or {}
            p_status = str(m.get("presence_status") or m.get("presence") or pinfo.get("status") or "offline").lower()
            is_online = p_status in ("online", "idle", "dnd", "away", "busy", "playing", "in_game")
            game = m.get("activity_title") or m.get("custom_status") or pinfo.get("game")
            if is_online and game:
                st_text = f"🎮 Jugando: {game}"
            elif p_status in ("idle", "away"):
                st_text = "Ausente"
            elif p_status in ("dnd", "busy"):
                st_text = "No molestar"
            elif is_online:
                st_text = "En línea" if role not in ("owner", "admin") else f"En línea • {role}"
            else:
                st_text = "Desconectado"
            entry = (
                uid,
                name,
                st_text,
                is_online,
                role in ("owner", "admin"),
                p_status,
                bool(m.get("is_muted")),
                bool(self._can_moderate and uid and uid != self._self_user_id and role != "owner"),
            )
            if is_online:
                online_items.append(entry)
            else:
                offline_items.append(entry)

        insert_pos = 0
        on_hdr = QLabel(f"●  En línea — {len(online_items)}")
        on_hdr.setStyleSheet("font-size: 12px; font-weight: 800; color: #32D875; padding: 4px 6px;")
        self.m_lay.insertWidget(insert_pos, on_hdr)
        insert_pos += 1

        def _make_member_widget(ent):
            m_uid, m_name, m_st, m_on, m_crown, m_pstat, m_muted, m_mod = ent
            mw = MemberItemWidget(
                m_name,
                m_st,
                m_on,
                has_crown=m_crown,
                user_id=m_uid,
                presence_status=m_pstat,
                is_muted=m_muted,
                can_moderate=m_mod,
            )
            mw.moderation_requested.connect(self.member_moderation_requested.emit)
            return mw

        if online_items:
            for ent in online_items:
                self.m_lay.insertWidget(insert_pos, _make_member_widget(ent))
                insert_pos += 1
        else:
            none_on = QLabel("Nadie en línea todavía.")
            none_on.setStyleSheet("font-size: 12px; color: #7f95a6; padding: 4px 8px;")
            self.m_lay.insertWidget(insert_pos, none_on)
            insert_pos += 1

        off_hdr = QLabel(f"●  Desconectados — {len(offline_items)}")
        off_hdr.setStyleSheet("font-size: 12px; font-weight: 800; color: #7f95a6; padding: 10px 6px 4px 6px;")
        self.m_lay.insertWidget(insert_pos, off_hdr)
        insert_pos += 1

        for ent in offline_items:
            self.m_lay.insertWidget(insert_pos, _make_member_widget(ent))
            insert_pos += 1

    def set_moderation_context(self, self_user_id: str, can_moderate: bool):
        self._self_user_id = str(self_user_id or "")
        self._can_moderate = bool(can_moderate)

    def sync_self_presence_ui(self, status: str, visibility: str):
        self.status_combo.blockSignals(True)
        self.share_game_chk.blockSignals(True)
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.share_game_chk.setChecked(visibility != "private")
        self.status_combo.blockSignals(False)
        self.share_game_chk.blockSignals(False)

    def _on_self_presence_ui_changed(self):
        status = str(self.status_combo.currentData() or "online")
        vis = "communities" if self.share_game_chk.isChecked() else "private"
        self.self_presence_changed.emit(status, vis)

    def set_voice_state(self, state: dict):
        connected = bool(state.get("connected"))
        self._media_ready = bool(state.get("media_ready"))
        ch_obj = state.get("channel")
        channel_name = str(
            (ch_obj.get("name") if isinstance(ch_obj, dict) else "")
            or state.get("channel_name")
            or ""
        )
        status_text = str(state.get("status_text") or "")

        if not connected and not channel_name and not status_text:
            self.voice_panel.setVisible(False)
            return

        if "is_muted" in state:
            self.mic_muted = bool(state.get("is_muted"))
            self._update_mic_style()
        if "is_deafened" in state:
            self.headset_muted = bool(state.get("is_deafened"))
            self._update_headset_style()

        participants = state.get("participants")
        p_count = len(participants) if isinstance(participants, list) else 0

        self.voice_panel.setVisible(True)
        self.v_chan.setText(channel_name or "Canal de voz")
        if self._media_ready:
            cnt_txt = f" · {p_count} en sala" if p_count > 0 else ""
            self.v_st.setText(f"Voz conectada{cnt_txt}")
            self.v_st.setStyleSheet("font-size: 13px; font-weight: 800; color: #32D875;")
            self.v_media_lbl.setText(status_text or "Audio WebRTC activo.")
            self.v_media_lbl.setStyleSheet("font-size: 11px; color: #BDD4E4;")
        elif connected:
            self.v_st.setText("Señalización LiveKit lista")
            self.v_st.setStyleSheet("font-size: 13px; font-weight: 800; color: #35C8F1;")
            self.v_media_lbl.setText(
                status_text or "Token emitido; audio/pantalla WebRTC no integrado en escritorio."
            )
            self.v_media_lbl.setStyleSheet("font-size: 11px; color: #ffd166;")
        else:
            self.v_st.setText("Voz no disponible")
            self.v_st.setStyleSheet("font-size: 13px; font-weight: 800; color: #ffb3b8;")
            self.v_media_lbl.setText(status_text or "No se pudo iniciar la señalización de voz.")
            self.v_media_lbl.setStyleSheet("font-size: 11px; color: #ffd6d9;")

        self.screen_active = bool(state.get("screen_live")) and self._media_ready
        self.v_live_badge.setVisible(self.screen_active)
        self._update_screen_style()

    def set_capture_sources(self, sources: dict):
        screens = list((sources or {}).get("screens") or [])
        cur = self.screen_source_combo.currentData()
        self.screen_source_combo.blockSignals(True)
        self.screen_source_combo.clear()
        for scr in screens:
            self.screen_source_combo.addItem(
                f"{scr.get('name', 'Pantalla')} ({scr.get('width', '')}x{scr.get('height', '')})",
                str(scr.get("id") or "screen:0"),
            )
        if not screens:
            self.screen_source_combo.addItem("Pantalla principal", "screen:0")
        self.screen_source_combo.addItem("Ventana OmniDash", "window:omnidash")
        idx = self.screen_source_combo.findData(cur)
        if idx >= 0:
            self.screen_source_combo.setCurrentIndex(idx)
        self.screen_source_combo.blockSignals(False)

    def get_selected_stream_config(self) -> tuple[str, str, int, int]:
        source_id = str(self.screen_source_combo.currentData() or "screen:0")
        res_data = self.screen_res_combo.currentData() or ("720p", 30, 2500)
        res, fps, bitrate = res_data
        return source_id, str(res), int(fps), int(bitrate)

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
            self.mic_btn.setStyleSheet("QPushButton { background: rgba(233, 75, 86, 0.85); border: 1.5px solid #E94B56; border-radius: 20px; }")
        else:
            self.mic_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 20px; } QPushButton:hover { background: rgba(255, 255, 255, 0.25); }")

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
            self.headset_btn.setStyleSheet("QPushButton { background: rgba(120, 120, 120, 0.6); border: 1.5px solid #888888; border-radius: 20px; }")
        else:
            self.headset_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.12); border: 1.5px solid rgba(255, 255, 255, 0.25); border-radius: 20px; } QPushButton:hover { background: rgba(255, 255, 255, 0.25); }")

    def _toggle_screen(self):
        if not self._media_ready:
            self.screen_active = False
            self.v_live_badge.setVisible(False)
            self._update_screen_style()
            self.v_media_lbl.setText(
                "Compartir pantalla requiere captura + WebRTC LiveKit nativo activo."
            )
            self.voice_toggled.emit("screen_unavailable", False)
            return
        # El estado LIVE nunca se simula aquí: solo cambia tras confirmar publicación en LiveKit SFU.
        if self.screen_active:
            self.voice_toggled.emit("screen_stop", False)
        else:
            self.v_media_lbl.setText("Publicando pista WebRTC de pantalla en LiveKit SFU...")
            self.voice_toggled.emit("screen_start", True)

    def _update_screen_style(self):
        sc_p = ROOT / "assets_omnidash" / "icons" / "screen_share.png"
        if sc_p.exists():
            self.screen_btn.setIcon(QIcon(str(sc_p)))
            self.screen_btn.setIconSize(QSize(18, 18))
        if self.screen_active and self._media_ready:
            self.screen_btn.setStyleSheet("QPushButton { background: rgba(53, 200, 241, 0.3); border: 1.5px solid #35C8F1; border-radius: 20px; }")
        else:
            self.screen_btn.setStyleSheet("QPushButton { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 20px; } QPushButton:hover { background: rgba(255, 255, 255, 0.2); }")

    def _disconnect_voice(self):
        self.soundboard_drawer.setVisible(False)
        self.voice_panel.hide()
        self.voice_toggled.emit("disconnect", False)

    def _toggle_soundboard_drawer(self):
        vis = not self.soundboard_drawer.isVisible()
        self.soundboard_drawer.setVisible(vis)

    def set_soundboard_sounds(self, sounds: list[dict]):
        while self.sb_grid.count():
            item = self.sb_grid.takeAt(0)
            w = item.widget() if item else None
            if w is not None:
                w.deleteLater()

        items = list(sounds or [])
        if not items:
            from backend.communities.sound_audio import SOUNDBOARD_PRESETS
            items = [dict(p) for p in SOUNDBOARD_PRESETS]

        for idx, snd in enumerate(items[:8]):
            sid = str(snd.get("id") or "")
            icon = str(snd.get("icon") or "🔊")
            title = str(snd.get("title") or sid)
            btn = QPushButton(f"{icon} {title}")
            btn.setProperty("sound_id", sid)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(145,165,179,0.28); "
                "border-radius: 7px; color: #ffffff; font-size: 11px; font-weight: 700; padding: 2px 6px; } "
                "QPushButton:hover { background: rgba(53,200,241,0.26); border-color: #35C8F1; }"
            )
            btn.clicked.connect(self._on_sb_pad_clicked)
            self.sb_grid.addWidget(btn, idx // 2, idx % 2)

    def _on_sb_pad_clicked(self):
        sender = self.sender()
        sid = str(sender.property("sound_id") or "") if sender is not None else ""
        if sid:
            self.soundboard_play_requested.emit(sid)

    def _on_sb_upload_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Subir efecto MP3 al Soundboard",
            "",
            "Audio MP3 (*.mp3)",
        )
        if path:
            self.soundboard_upload_requested.emit(path)

    def set_soundboard_feedback(self, text: str, is_error: bool = False):
        color = "#ffb3b8" if is_error else "#32D875"
        self.sb_status_lbl.setStyleSheet(f"font-size: 10px; color: {color}; border: none;")
        self.sb_status_lbl.setText(text)


def _styled_input(placeholder: str = "", password: bool = False) -> QLineEdit:
    inp = QLineEdit()
    inp.setPlaceholderText(placeholder)
    if password:
        inp.setEchoMode(QLineEdit.Password)
    inp.setFixedHeight(40)
    inp.setStyleSheet("""
        QLineEdit {
            background: rgba(12, 26, 40, 0.85);
            border: 1px solid rgba(145, 165, 179, 0.45);
            border-radius: 10px;
            color: #ffffff;
            font-size: 13px;
            padding: 0 12px;
        }
        QLineEdit:focus {
            border: 1.5px solid #35C8F1;
        }
    """)
    return inp


def _make_auth_vector_icon(kind: str, size: int = 22, color: QColor = QColor(255, 255, 255)) -> QPixmap:
    """Dibuja íconos vectoriales nítidos para la pantalla de inicio de sesión de C.C.I. Communities."""
    pm = QPixmap(size * 2, size * 2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    s = float(size * 2)
    pen = QPen(color, max(2.2, s * 0.075), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "chat_dots":
        r = QRectF(s * 0.16, s * 0.18, s * 0.68, s * 0.50)
        path = QPainterPath()
        path.addRoundedRect(r, s * 0.12, s * 0.12)
        p.drawPath(path)
        tail = QPainterPath()
        tail.moveTo(s * 0.34, s * 0.68)
        tail.lineTo(s * 0.26, s * 0.84)
        tail.lineTo(s * 0.48, s * 0.68)
        p.drawPath(tail)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(s * 0.40, s * 0.43), s * 0.045, s * 0.045)
        p.drawEllipse(QPointF(s * 0.58, s * 0.43), s * 0.045, s * 0.045)
    elif kind == "mic":
        p.drawRoundedRect(QRectF(s * 0.36, s * 0.14, s * 0.28, s * 0.44), s * 0.14, s * 0.14)
        p.drawArc(QRectF(s * 0.24, s * 0.28, s * 0.52, s * 0.44), 180 * 16, 180 * 16)
        p.drawLine(QPointF(s * 0.50, s * 0.72), QPointF(s * 0.50, s * 0.86))
        p.drawLine(QPointF(s * 0.36, s * 0.86), QPointF(s * 0.64, s * 0.86))
    elif kind == "stream_tv":
        p.drawRoundedRect(QRectF(s * 0.14, s * 0.18, s * 0.72, s * 0.52), s * 0.09, s * 0.09)
        p.drawLine(QPointF(s * 0.34, s * 0.82), QPointF(s * 0.66, s * 0.82))
        p.drawLine(QPointF(s * 0.50, s * 0.70), QPointF(s * 0.50, s * 0.82))
        tri = QPainterPath()
        tri.moveTo(s * 0.44, s * 0.34)
        tri.lineTo(s * 0.60, s * 0.44)
        tri.lineTo(s * 0.44, s * 0.54)
        tri.closeSubpath()
        p.setBrush(color)
        p.drawPath(tri)
    elif kind == "live_waves":
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.07, s * 0.07)
        p.setBrush(Qt.NoBrush)
        p.setPen(pen)
        r1 = QRectF(s * 0.30, s * 0.30, s * 0.40, s * 0.40)
        p.drawArc(r1, -45 * 16, 90 * 16)
        p.drawArc(r1, 135 * 16, 90 * 16)
        r2 = QRectF(s * 0.14, s * 0.14, s * 0.72, s * 0.72)
        p.drawArc(r2, -45 * 16, 90 * 16)
        p.drawArc(r2, 135 * 16, 90 * 16)
    elif kind == "mail":
        p.drawRoundedRect(QRectF(s * 0.14, s * 0.24, s * 0.72, s * 0.52), s * 0.08, s * 0.08)
        flap = QPainterPath()
        flap.moveTo(s * 0.17, s * 0.28)
        flap.lineTo(s * 0.50, s * 0.52)
        flap.lineTo(s * 0.83, s * 0.28)
        p.drawPath(flap)
    elif kind == "lock":
        p.drawRoundedRect(QRectF(s * 0.22, s * 0.44, s * 0.56, s * 0.42), s * 0.09, s * 0.09)
        p.drawArc(QRectF(s * 0.32, s * 0.18, s * 0.36, s * 0.46), 0, 180 * 16)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(s * 0.50, s * 0.63), s * 0.05, s * 0.05)
    elif kind == "eye":
        path = QPainterPath()
        path.moveTo(s * 0.12, s * 0.50)
        path.quadTo(s * 0.50, s * 0.20, s * 0.88, s * 0.50)
        path.quadTo(s * 0.50, s * 0.80, s * 0.12, s * 0.50)
        p.drawPath(path)
        p.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.12, s * 0.12)
    elif kind == "login_enter":
        door = QPainterPath()
        door.moveTo(s * 0.46, s * 0.20)
        door.lineTo(s * 0.78, s * 0.20)
        door.lineTo(s * 0.78, s * 0.80)
        door.lineTo(s * 0.46, s * 0.80)
        p.drawPath(door)
        p.drawLine(QPointF(s * 0.18, s * 0.50), QPointF(s * 0.60, s * 0.50))
        p.drawLine(QPointF(s * 0.46, s * 0.36), QPointF(s * 0.60, s * 0.50))
        p.drawLine(QPointF(s * 0.46, s * 0.64), QPointF(s * 0.60, s * 0.50))
    elif kind == "user_plus":
        p.drawEllipse(QPointF(s * 0.42, s * 0.34), s * 0.15, s * 0.15)
        p_arc = QRectF(s * 0.18, s * 0.54, s * 0.48, s * 0.38)
        p.drawArc(p_arc, 0, 180 * 16)
        p.drawLine(QPointF(s * 0.76, s * 0.36), QPointF(s * 0.76, s * 0.60))
        p.drawLine(QPointF(s * 0.64, s * 0.48), QPointF(s * 0.88, s * 0.48))
    elif kind == "gamepad":
        p.drawRoundedRect(QRectF(s * 0.14, s * 0.28, s * 0.72, s * 0.44), s * 0.18, s * 0.18)
        p.drawLine(QPointF(s * 0.30, s * 0.50), QPointF(s * 0.42, s * 0.50))
        p.drawLine(QPointF(s * 0.36, s * 0.44), QPointF(s * 0.36, s * 0.56))
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        p.drawEllipse(QPointF(s * 0.64, s * 0.45), s * 0.04, s * 0.04)
        p.drawEllipse(QPointF(s * 0.72, s * 0.54), s * 0.04, s * 0.04)
    elif kind == "spotify":
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(30, 215, 96))
        p.drawEllipse(QPointF(s * 0.50, s * 0.50), s * 0.40, s * 0.40)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(6, 22, 34), max(2.2, s * 0.075), Qt.SolidLine, Qt.RoundCap))
        p.drawArc(QRectF(s * 0.26, s * 0.34, s * 0.48, s * 0.26), 25 * 16, 130 * 16)
        p.drawArc(QRectF(s * 0.30, s * 0.47, s * 0.40, s * 0.22), 25 * 16, 130 * 16)
        p.drawArc(QRectF(s * 0.34, s * 0.60, s * 0.32, s * 0.18), 25 * 16, 130 * 16)

    p.end()
    return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class _AuthFeatureCard(QFrame):
    """Tarjeta de funcionalidad (Grupos y chat, Salas de voz, Streaming, Actividad) con borde neón cian activo."""
    clicked = Signal()

    def __init__(self, icon_kind: str, title: str, subtitle: str, active: bool = False, parent=None):
        super().__init__(parent)
        self._icon_kind = icon_kind
        self._active = active
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(138)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 14, 12, 14)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignCenter)

        self.icon_box = QLabel()
        self.icon_box.setFixedSize(44, 40)
        self.icon_box.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.icon_box, 0, Qt.AlignHCenter)

        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #FFFFFF; background: transparent;")
        lay.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        self.sub_lbl.setWordWrap(True)
        self.sub_lbl.setStyleSheet("font-size: 11px; font-weight: 500; color: rgba(200, 224, 240, 0.88); background: transparent;")
        lay.addWidget(self.sub_lbl)

        self.set_active(active)

    def set_active(self, active: bool):
        self._active = active
        ico_col = QColor(42, 236, 255) if active else QColor(225, 242, 252)
        self.icon_box.setPixmap(_make_auth_vector_icon(self._icon_kind, 24, ico_col))
        if active:
            self.icon_box.setStyleSheet(
                "background: rgba(34, 218, 255, 0.18); border: 1.4px solid rgba(62, 238, 255, 0.85); border-radius: 11px;"
            )
        else:
            self.icon_box.setStyleSheet("background: transparent; border: none;")
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 16.0, 16.0)

        if self._active:
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            grad.setColorAt(0.0, QColor(18, 72, 98, 210))
            grad.setColorAt(1.0, QColor(10, 38, 56, 225))
            p.fillPath(path, grad)
            p.setPen(QPen(QColor(38, 232, 255, 95), 4.0))
            p.drawPath(path)
            p.setPen(QPen(QColor(56, 242, 255, 245), 1.8))
            p.drawPath(path)
        else:
            grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            grad.setColorAt(0.0, QColor(14, 34, 50, 185))
            grad.setColorAt(1.0, QColor(9, 24, 37, 200))
            p.fillPath(path, grad)
            p.setPen(QPen(QColor(120, 175, 205, 78), 1.1))
            p.drawPath(path)
        p.end()


class _AuthActivityCard(QFrame):
    """Tarjeta inferior de actividad en vivo (Luca / Mortal Kombat 1, Sofi / Daft Punk, Mateo / En vivo)."""

    def __init__(
        self,
        badge_kind: str,
        line1_html: str,
        line2_html: str,
        art_rel_path: str,
        highlight_border: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._highlight = highlight_border
        self._art_pm: Optional[QPixmap] = None
        art_p = ROOT / art_rel_path
        if art_p.exists():
            self._art_pm = QPixmap(str(art_p))

        self.setFixedHeight(78)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        ico_lbl = QLabel()
        ico_lbl.setFixedSize(20, 18)
        ico_col = QColor(42, 234, 255) if badge_kind == "gamepad" else QColor(230, 245, 255)
        ico_lbl.setPixmap(_make_auth_vector_icon(badge_kind, 17, ico_col))
        ico_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(ico_lbl, 0, Qt.AlignLeft)

        lay.addStretch(1)

        l1 = QLabel(line1_html)
        l1.setStyleSheet("font-size: 11.5px; color: rgba(230, 244, 255, 0.95); background: transparent;")
        lay.addWidget(l1)

        l2 = QLabel(line2_html)
        l2.setStyleSheet("font-size: 12px; font-weight: 800; color: #FFFFFF; background: transparent;")
        lay.addWidget(l2)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14.0, 14.0)

        p.save()
        p.setClipPath(path)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor(13, 33, 49, 220))
        grad.setColorAt(1.0, QColor(8, 21, 34, 235))
        p.fillPath(path, grad)

        if self._art_pm and not self._art_pm.isNull():
            art_w = int(rect.height() * 1.18)
            art_rect = QRectF(rect.right() - art_w, rect.top(), art_w, rect.height())
            scaled = self._art_pm.scaled(
                int(art_rect.width()),
                int(art_rect.height()),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            p.drawPixmap(int(art_rect.left()), int(art_rect.top()), scaled)
        p.restore()

        if self._highlight:
            p.setPen(QPen(QColor(64, 218, 245, 170), 1.5))
        else:
            p.setPen(QPen(QColor(115, 175, 205, 80), 1.1))
        p.drawPath(path)
        p.end()


class _CyanVerticalAccentBar(QWidget):
    """Barra vertical cian luminosa junto al título C.C.I. Communities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 88)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        glow_r = QRectF(1.0, 2.0, 8.0, self.height() - 4.0)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(38, 236, 255, 85))
        p.drawRoundedRect(glow_r, 4.0, 4.0)

        core_r = QRectF(2.5, 4.0, 5.0, self.height() - 8.0)
        grad = QLinearGradient(core_r.topLeft(), core_r.bottomLeft())
        grad.setColorAt(0.0, QColor(82, 248, 255))
        grad.setColorAt(1.0, QColor(18, 198, 242))
        p.setBrush(grad)
        p.drawRoundedRect(core_r, 2.5, 2.5)
        p.end()


def _build_icon_input_capsule(
    line_edit: QLineEdit,
    icon_kind: str,
    trailing_widget: Optional[QWidget] = None,
) -> QFrame:
    """Envuelve un QLineEdit dentro de una cápsula oscura traslúcida con ícono a la izquierda."""
    wrap = QFrame()
    wrap.setFixedHeight(44)
    wrap.setStyleSheet("""
        QFrame {
            background: rgba(7, 20, 32, 0.78);
            border: 1px solid rgba(110, 175, 210, 0.36);
            border-radius: 11px;
        }
        QFrame:focus-within {
            border: 1.5px solid #29E8FF;
            background: rgba(9, 25, 40, 0.90);
        }
    """)
    h = QHBoxLayout(wrap)
    h.setContentsMargins(13, 0, 10, 0)
    h.setSpacing(10)

    ico = QLabel()
    ico.setFixedSize(18, 18)
    ico.setPixmap(_make_auth_vector_icon(icon_kind, 17, QColor(175, 210, 232)))
    ico.setStyleSheet("border: none; background: transparent;")
    h.addWidget(ico)

    line_edit.setFixedHeight(40)
    line_edit.setStyleSheet("""
        QLineEdit {
            background: transparent;
            border: none;
            color: #FFFFFF;
            font-size: 13px;
            font-weight: 500;
            padding: 0px;
        }
    """)
    h.addWidget(line_edit, 1)

    if trailing_widget is not None:
        h.addWidget(trailing_widget)

    return wrap


class CommunityAuthView(AcrylicGlassCard):
    """Pantalla real de autenticación JWT para C.C.I. Communities con diseño Frutiger Aero 1:1."""

    def __init__(self, controller: CommunityController, parent=None):
        super().__init__(
            parent,
            border_radius=26,
            border_color=QColor(78, 182, 222, 115),
            glow_color=QColor(0, 0, 0, 85),
            glow_radius=14,
        )
        self.controller = controller
        self._mode = "login"
        self._pwd_visible = False

        bg_path = ROOT / "assets_omnidash" / "communities" / "auth_hero_bg.png"
        self._hero_bg = QPixmap(str(bg_path)) if bg_path.exists() else QPixmap()

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 18, 34, 22)
        root.setSpacing(10)

        # ── 1. FILA SUPERIOR: Cápsula de Jugador (Izquierda) ──
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.player_pill = QFrame(self)
        self.player_pill.setFixedHeight(40)
        self.player_pill.setStyleSheet("""
            QFrame {
                background: rgba(9, 26, 42, 0.78);
                border: 1px solid rgba(110, 182, 220, 0.36);
                border-radius: 20px;
            }
        """)
        pp_lay = QHBoxLayout(self.player_pill)
        pp_lay.setContentsMargins(5, 4, 14, 4)
        pp_lay.setSpacing(8)

        av_lbl = QLabel()
        av_p = ROOT / "assets_omnidash" / "spidey_avatar.png"
        if av_p.exists():
            av_lbl.setPixmap(get_rounded_pixmap(QPixmap(str(av_p)), 30, 30, 15))
        av_lbl.setStyleSheet("border: none; background: transparent;")
        pp_lay.addWidget(av_lbl)

        self.auth_player_lbl = QLabel("Alex  <span style='color:#23E4FF;'>●</span>  <b>18,450 G</b>")
        self.auth_player_lbl.setStyleSheet("border: none; background: transparent; color: #FFFFFF; font-size: 12.5px; font-weight: 700;")
        pp_lay.addWidget(self.auth_player_lbl)

        top_bar.addWidget(self.player_pill, 0, Qt.AlignLeft)
        top_bar.addStretch(1)
        root.addLayout(top_bar)

        # ── 2. CUERPO DE DOS COLUMNAS (Showcase Izquierda + Tarjeta Auth Derecha) ──
        body_row = QHBoxLayout()
        body_row.setContentsMargins(4, 4, 4, 4)
        body_row.setSpacing(28)

        # ================== COLUMNA IZQUIERDA ==================
        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 18, 0, 0)
        left_col.setSpacing(14)

        hero_title_row = QHBoxLayout()
        hero_title_row.setContentsMargins(0, 0, 0, 0)
        hero_title_row.setSpacing(14)

        accent_bar = _CyanVerticalAccentBar(self)
        hero_title_row.addWidget(accent_bar, 0, Qt.AlignTop)

        title_stack = QVBoxLayout()
        title_stack.setContentsMargins(0, 0, 0, 0)
        title_stack.setSpacing(0)

        lbl_cci = QLabel("C.C.I.")
        lbl_cci.setStyleSheet(
            "font-size: 44px; font-weight: 900; font-style: italic; color: #FFFFFF; "
            "letter-spacing: 1px; line-height: 0.95; background: transparent;"
        )
        lbl_comm = QLabel("Communities")
        lbl_comm.setStyleSheet(
            "font-size: 42px; font-weight: 900; font-style: italic; color: #FFFFFF; "
            "letter-spacing: 0.5px; line-height: 0.95; background: transparent;"
        )
        title_stack.addWidget(lbl_cci)
        title_stack.addWidget(lbl_comm)
        hero_title_row.addLayout(title_stack)
        hero_title_row.addStretch(1)
        left_col.addLayout(hero_title_row)

        hero_sub = QLabel("Conecta con jugadores, crea grupos,\nconversa, transmite y comparte tu experiencia.")
        hero_sub.setStyleSheet(
            "font-size: 15px; font-weight: 500; color: rgba(224, 240, 252, 0.92); "
            "line-height: 1.35; background: transparent;"
        )
        left_col.addWidget(hero_sub)
        left_col.addSpacing(6)

        feat_row = QHBoxLayout()
        feat_row.setContentsMargins(0, 0, 0, 0)
        feat_row.setSpacing(12)

        features_spec = [
            ("chat_dots", "Grupos y chat", "Conversaciones por\ntexto con tu comunidad.", True),
            ("mic", "Salas de voz", "Habla en tiempo real\ncon tu equipo.", False),
            ("stream_tv", "Streaming", "Comparte tu juego\nen vivo.", False),
            ("live_waves", "Actividad", "Descubre qué están\njugando tus amigos.", False),
        ]
        self._feature_cards: list[_AuthFeatureCard] = []
        for idx, (ikind, ftitle, fsub, is_act) in enumerate(features_spec):
            fc = _AuthFeatureCard(ikind, ftitle, fsub, active=is_act, parent=self)
            fc.clicked.connect(lambda i=idx: self._select_feature_card(i))
            feat_row.addWidget(fc, 1)
            self._feature_cards.append(fc)

        left_col.addLayout(feat_row)

        dot_lbl = QLabel("●")
        dot_lbl.setStyleSheet("color: #36EEFF; font-size: 7px; padding-left: 14px; background: transparent;")
        left_col.addWidget(dot_lbl)

        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 0, 0, 0)
        act_row.setSpacing(12)

        act1 = _AuthActivityCard(
            "gamepad",
            "<b>Luca</b> está jugando",
            "Mortal Kombat 1",
            "assets_omnidash/communities/act_mk1.png",
            highlight_border=True,
            parent=self,
        )
        act2 = _AuthActivityCard(
            "spotify",
            "<b>Sofi</b> está escuchando",
            "Daft Punk",
            "assets_omnidash/communities/act_daftpunk.png",
            highlight_border=False,
            parent=self,
        )
        act3 = _AuthActivityCard(
            "live_waves",
            "<b>Mateo</b> está en vivo",
            "(12 espectadores)",
            "assets_omnidash/communities/act_stream_racing.png",
            highlight_border=False,
            parent=self,
        )
        act_row.addWidget(act1, 1)
        act_row.addWidget(act2, 1)
        act_row.addWidget(act3, 1)
        left_col.addLayout(act_row)
        left_col.addStretch(1)

        body_row.addLayout(left_col, 1)

        # ================== COLUMNA DERECHA (TARJETA CRISTAL LOGIN / REGISTRO) ==================
        card = AcrylicGlassCard(
            self,
            border_radius=24,
            border_color=QColor(72, 204, 242, 130),
            glow_color=QColor(0, 0, 0, 110),
            glow_radius=18,
            inner_aura=QColor(18, 92, 130),
        )
        card.setFixedWidth(404)
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(26, 24, 26, 20)
        c_lay.setSpacing(13)

        tabs_capsule = QFrame(card)
        tabs_capsule.setFixedHeight(44)
        tabs_capsule.setStyleSheet("""
            QFrame {
                background: rgba(6, 18, 29, 0.72);
                border: 1px solid rgba(105, 175, 212, 0.30);
                border-radius: 22px;
            }
        """)
        tabs = QHBoxLayout(tabs_capsule)
        tabs.setContentsMargins(3, 3, 3, 3)
        tabs.setSpacing(4)

        self.tab_login_btn = QPushButton("  Iniciar sesión")
        self.tab_login_btn.setIcon(QIcon(_make_auth_vector_icon("login_enter", 16, QColor(255, 255, 255))))
        self.tab_login_btn.setIconSize(QSize(16, 16))

        self.tab_reg_btn = QPushButton("  Crear cuenta")
        self.tab_reg_btn.setIcon(QIcon(_make_auth_vector_icon("user_plus", 16, QColor(210, 232, 248))))
        self.tab_reg_btn.setIconSize(QSize(16, 16))

        for btn, mode in ((self.tab_login_btn, "login"), (self.tab_reg_btn, "register")):
            btn.setFixedHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, m=mode: self.set_mode(m))
            tabs.addWidget(btn, 1)

        c_lay.addWidget(tabs_capsule)
        c_lay.addSpacing(2)

        self.form_title_lbl = QLabel("Iniciar sesión")
        self.form_title_lbl.setStyleSheet("font-size: 25px; font-weight: 800; color: #FFFFFF; background: transparent;")
        self.form_sub_lbl = QLabel("Accede a tu cuenta de C.C.I. SYSTEM.")
        self.form_sub_lbl.setStyleSheet("font-size: 12.5px; color: rgba(195, 222, 240, 0.88); background: transparent;")
        c_lay.addWidget(self.form_title_lbl)
        c_lay.addWidget(self.form_sub_lbl)
        c_lay.addSpacing(2)

        self.form_stack = QStackedWidget()

        # ── Tab 0: Login ──
        login_w = QWidget()
        login_l = QVBoxLayout(login_w)
        login_l.setContentsMargins(0, 2, 0, 0)
        login_l.setSpacing(12)

        self.login_identifier = _styled_input("Usuario o correo")
        self.login_password = _styled_input("Contraseña", password=True)
        self.login_password.returnPressed.connect(self._do_login)

        self.pwd_eye_btn = QPushButton()
        self.pwd_eye_btn.setFixedSize(28, 28)
        self.pwd_eye_btn.setCursor(Qt.PointingHandCursor)
        self.pwd_eye_btn.setIcon(QIcon(_make_auth_vector_icon("eye", 17, QColor(180, 212, 232))))
        self.pwd_eye_btn.setIconSize(QSize(17, 17))
        self.pwd_eye_btn.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,0.08); border-radius: 14px; }")
        self.pwd_eye_btn.clicked.connect(self._toggle_pwd_visibility)

        ident_capsule = _build_icon_input_capsule(self.login_identifier, "mail")
        pwd_capsule = _build_icon_input_capsule(self.login_password, "lock", trailing_widget=self.pwd_eye_btn)

        login_l.addWidget(ident_capsule)
        login_l.addWidget(pwd_capsule)

        opts_row = QHBoxLayout()
        opts_row.setContentsMargins(2, 2, 2, 2)
        chk_on = (ROOT / "assets_omnidash" / "communities" / "chk_checked.png").as_posix()
        chk_off = (ROOT / "assets_omnidash" / "communities" / "chk_unchecked.png").as_posix()
        self.remember_chk = QCheckBox("Recordar sesión")
        self.remember_chk.setChecked(True)
        self.remember_chk.setCursor(Qt.PointingHandCursor)
        self.remember_chk.setStyleSheet(f"""
            QCheckBox {{
                color: rgba(230, 244, 255, 0.95);
                font-size: 12px;
                font-weight: 600;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                image: url("{chk_off}");
            }}
            QCheckBox::indicator:checked {{
                image: url("{chk_on}");
            }}
        """)
        opts_row.addWidget(self.remember_chk)
        opts_row.addStretch(1)

        self.forgot_btn = QPushButton("¿Olvidaste tu contraseña?")
        self.forgot_btn.setCursor(Qt.PointingHandCursor)
        self.forgot_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #29E4FF;
                font-size: 12px;
                font-weight: 600;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #7CF4FF;
            }
        """)
        self.forgot_btn.clicked.connect(
            lambda: self.show_error("Para recuperar tu acceso local, registrá o restablecé tu cuenta desde el panel.")
        )
        opts_row.addWidget(self.forgot_btn)
        login_l.addLayout(opts_row)

        self.login_btn = QPushButton("  Entrar a Comunidades")
        self.login_btn.setIcon(QIcon(_make_auth_vector_icon("login_enter", 18, QColor(4, 22, 36))))
        self.login_btn.setIconSize(QSize(18, 18))
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #14D4FF, stop:0.5 #2CEEFF, stop:1 #16D8FA);
                border: 1px solid rgba(180, 252, 255, 0.85);
                border-radius: 23px;
                color: #041827;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3CE0FF, stop:0.5 #68F4FF, stop:1 #3CE0FF);
            }
        """)
        self.login_btn.clicked.connect(self._do_login)
        login_l.addSpacing(4)
        login_l.addWidget(self.login_btn)
        self.form_stack.addWidget(login_w)

        # ── Tab 1: Register ──
        reg_w = QWidget()
        reg_l = QVBoxLayout(reg_w)
        reg_l.setContentsMargins(0, 2, 0, 0)
        reg_l.setSpacing(10)

        self.reg_email = _styled_input("Correo electrónico")
        self.reg_username = _styled_input("Nombre de usuario (único)")
        self.reg_password = _styled_input("Contraseña (mín. 8 caracteres)", password=True)
        self.reg_password.returnPressed.connect(self._do_register)

        reg_l.addWidget(_build_icon_input_capsule(self.reg_email, "mail"))
        reg_l.addWidget(_build_icon_input_capsule(self.reg_username, "user_plus"))
        reg_l.addWidget(_build_icon_input_capsule(self.reg_password, "lock"))

        self.reg_btn = QPushButton("  Registrar cuenta")
        self.reg_btn.setIcon(QIcon(_make_auth_vector_icon("user_plus", 18, QColor(4, 22, 36))))
        self.reg_btn.setIconSize(QSize(18, 18))
        self.reg_btn.setFixedHeight(46)
        self.reg_btn.setCursor(Qt.PointingHandCursor)
        self.reg_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #14D4FF, stop:0.5 #2CEEFF, stop:1 #16D8FA);
                border: 1px solid rgba(180, 252, 255, 0.85);
                border-radius: 23px;
                color: #041827;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3CE0FF, stop:0.5 #68F4FF, stop:1 #3CE0FF);
            }
        """)
        self.reg_btn.clicked.connect(self._do_register)
        reg_l.addSpacing(4)
        reg_l.addWidget(self.reg_btn)
        self.form_stack.addWidget(reg_w)

        c_lay.addWidget(self.form_stack)

        self.error_lbl = QLabel("")
        self.error_lbl.setWordWrap(True)
        self.error_lbl.setVisible(False)
        self.error_lbl.setStyleSheet(
            "background: rgba(233, 75, 86, 0.22); border: 1px solid rgba(233, 75, 86, 0.65); "
            "border-radius: 10px; color: #ffd6d9; font-size: 12px; font-weight: 600; padding: 7px 10px;"
        )
        c_lay.addWidget(self.error_lbl)
        c_lay.addStretch(1)

        footer_row = QHBoxLayout()
        footer_row.setContentsMargins(0, 6, 0, 0)
        footer_row.setSpacing(8)

        line_l = QFrame()
        line_l.setFixedHeight(1)
        line_l.setStyleSheet("background: rgba(110, 178, 215, 0.22); border: none;")
        line_r = QFrame()
        line_r.setFixedHeight(1)
        line_r.setStyleSheet("background: rgba(110, 178, 215, 0.22); border: none;")

        self.backend_lbl = QLabel("● Servidor conectado")
        self.backend_lbl.setAlignment(Qt.AlignCenter)
        self.backend_lbl.setStyleSheet("font-size: 12px; font-weight: 700; color: #32D875; background: transparent;")

        self.retry_btn = QPushButton("↻")
        self.retry_btn.setFixedSize(22, 22)
        self.retry_btn.setCursor(Qt.PointingHandCursor)
        self.retry_btn.setToolTip("Reintentar conexión con el servidor")
        self.retry_btn.setVisible(False)
        self.retry_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.2); "
            "border-radius: 11px; color: #ffffff; font-size: 11px; font-weight: 800; }"
        )
        self.retry_btn.clicked.connect(lambda: self.controller.check_backend_async(auto_start=True))

        footer_row.addWidget(line_l, 1)
        footer_row.addWidget(self.backend_lbl)
        footer_row.addWidget(self.retry_btn)
        footer_row.addWidget(line_r, 1)
        c_lay.addLayout(footer_row)

        right_wrap = QVBoxLayout()
        right_wrap.setContentsMargins(0, 14, 10, 0)
        right_wrap.addWidget(card, 0, Qt.AlignTop)
        right_wrap.addStretch(1)
        body_row.addLayout(right_wrap, 0)
        root.addLayout(body_row, 1)

        self.controller.backend_status_changed.connect(self.set_backend_status)
        self.set_mode("login")

    def _select_feature_card(self, active_idx: int):
        for i, fc in enumerate(self._feature_cards):
            fc.set_active(i == active_idx)

    def _toggle_pwd_visibility(self):
        self._pwd_visible = not self._pwd_visible
        self.login_password.setEchoMode(QLineEdit.Normal if self._pwd_visible else QLineEdit.Password)

    def paintEvent(self, event):
        if not self._hero_bg.isNull():
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            rect = QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0)
            clip = QPainterPath()
            clip.addRoundedRect(rect, 26.0, 26.0)
            p.save()
            p.setClipPath(clip)
            scaled = self._hero_bg.scaled(
                int(rect.width()),
                int(rect.height()),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            p.drawPixmap(int(rect.left()), int(rect.top()), scaled)
            p.restore()
            p.setPen(QPen(QColor(82, 195, 235, 115), 1.4))
            p.drawPath(clip)
            p.end()
        else:
            super().paintEvent(event)

    def set_mode(self, mode: str):
        self._mode = "register" if mode == "register" else "login"
        self.form_stack.setCurrentIndex(1 if self._mode == "register" else 0)
        self.show_error("")
        if self._mode == "login":
            self.form_title_lbl.setText("Iniciar sesión")
            self.form_sub_lbl.setText("Accede a tu cuenta de C.C.I. SYSTEM.")
        else:
            self.form_title_lbl.setText("Crear cuenta")
            self.form_sub_lbl.setText("Registra tu cuenta en C.C.I. SYSTEM.")

        active_css = (
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
            "stop:0 rgba(25, 185, 232, 0.36), stop:1 rgba(18, 132, 185, 0.28)); "
            "border: 1.6px solid #2AE8FF; border-radius: 18px; color: #ffffff; font-size: 13px; font-weight: 800; }"
        )
        idle_css = (
            "QPushButton { background: transparent; border: 1px solid transparent; "
            "border-radius: 18px; color: rgba(205, 228, 245, 0.85); font-size: 13px; font-weight: 700; }"
            "QPushButton:hover { color: #ffffff; background: rgba(255,255,255,0.05); }"
        )
        self.tab_login_btn.setStyleSheet(active_css if self._mode == "login" else idle_css)
        self.tab_reg_btn.setStyleSheet(active_css if self._mode == "register" else idle_css)

    def set_backend_status(self, online: bool, detail: str = ""):
        if online:
            self.backend_lbl.setText("● Servidor conectado")
            self.backend_lbl.setStyleSheet(
                "font-size: 12px; font-weight: 700; color: #32D875; background: transparent;"
            )
            self.backend_lbl.setToolTip(detail or self.controller.api_url)
            self.retry_btn.setVisible(False)
        else:
            self.backend_lbl.setText("● Servidor sin conexión")
            self.backend_lbl.setStyleSheet(
                "font-size: 12px; font-weight: 700; color: #ff858d; background: transparent;"
            )
            self.backend_lbl.setToolTip(detail or "Backend no accesible")
            self.retry_btn.setVisible(True)

    def show_error(self, message: str):
        if message:
            self.error_lbl.setText(message)
            self.error_lbl.setVisible(True)
        else:
            self.error_lbl.setVisible(False)

    def _set_auth_loading(self, busy: bool, mode: str = "login"):
        self.login_btn.setEnabled(not busy)
        self.reg_btn.setEnabled(not busy)
        if busy:
            if mode == "register":
                self.reg_btn.setText("  Registrando...")
            else:
                self.login_btn.setText("  Entrando...")
        else:
            self.login_btn.setText("  Entrar a Comunidades")
            self.reg_btn.setText("  Registrar cuenta")

    def _do_login(self):
        ident = self.login_identifier.text().strip()
        pw = self.login_password.text()
        if not ident or not pw:
            self.show_error("Completá tu usuario/email y contraseña.")
            return
        self.show_error("")
        self._set_auth_loading(True, "login")

        def _ok(_sess):
            self._set_auth_loading(False, "login")
            self.login_password.clear()

        def _err(exc: CommunityApiError):
            self._set_auth_loading(False, "login")
            self.show_error(exc.message)

        self.controller.login_async(ident, pw, on_success=_ok, on_error=_err)

    def _do_register(self):
        email = self.reg_email.text().strip()
        username = self.reg_username.text().strip()
        pw = self.reg_password.text()
        if not email or not username or not pw:
            self.show_error("Completá email, nombre de usuario y contraseña.")
            return
        self.show_error("")
        self._set_auth_loading(True, "register")

        def _ok(_sess):
            self._set_auth_loading(False, "register")
            self.reg_password.clear()

        def _err(exc: CommunityApiError):
            self._set_auth_loading(False, "register")
            self.show_error(exc.message)

        self.controller.register_async(email=email, username=username, password=pw, on_success=_ok, on_error=_err)


class CommunityInteriorView(AcrylicGlassCard):
    back_to_explore = Signal()

    def __init__(self, controller: Optional[CommunityController] = None, parent=None):
        super().__init__(
            parent,
            border_radius=30,
            border_color=QColor(145, 165, 179, 85),
            glow_color=QColor(0, 0, 0, 75),
            glow_radius=14
        )
        self.controller = controller
        self._all_members: list[dict] = []
        self._presence_map: dict[str, dict] = {}
        self._search_filter: str = ""

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
            ico_lbl.setPixmap(QPixmap(str(ico_p)).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        ico_shadow = QGraphicsDropShadowEffect(ico_lbl)
        ico_shadow.setOffset(0, 0)
        ico_shadow.setBlurRadius(14)
        ico_shadow.setColor(QColor(53, 200, 241, 230))
        ico_lbl.setGraphicsEffect(ico_shadow)
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
        sep.setStyleSheet("color: rgba(255, 255, 255, 60); font-size: 26px; font-weight: 200; margin: 0 6px;")
        hdr_row.addWidget(sep)

        desc_v = QVBoxLayout()
        desc_v.setSpacing(2)
        m_title = QLabel("Gaming Communities & Friends")
        m_title.setStyleSheet("font-size: 18px; font-weight: 800; color: #ffffff;")
        m_desc = QLabel("Comunidades reales persistidas, invitaciones y mensajería Socket.IO.")
        m_desc.setStyleSheet("font-size: 12px; color: #BDD4E4;")
        desc_v.addWidget(m_title)
        desc_v.addWidget(m_desc)
        hdr_row.addLayout(desc_v)

        hdr_row.addStretch(1)

        self.user_chip_lbl = QLabel("@sin_sesion")
        self.user_chip_lbl.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #35C8F1; padding: 6px 12px; "
            "background: rgba(53, 200, 241, 0.14); border: 1px solid rgba(53, 200, 241, 0.4); border-radius: 14px;"
        )
        hdr_row.addWidget(self.user_chip_lbl)

        self.logout_btn = QPushButton("Salir")
        self.logout_btn.setFixedHeight(34)
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.setToolTip("Cerrar sesión de Comunidades")
        self.logout_btn.setStyleSheet(
            "QPushButton { background: rgba(233,75,86,0.18); border: 1px solid rgba(233,75,86,0.45); "
            "border-radius: 14px; color: #ffb3b8; font-size: 12px; font-weight: 700; padding: 0 12px; }"
            "QPushButton:hover { background: rgba(233,75,86,0.35); color: #ffffff; }"
        )
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        hdr_row.addWidget(self.logout_btn)

        search_frame = QFrame()
        search_frame.setFixedHeight(40)
        search_frame.setFixedWidth(220)
        search_frame.setStyleSheet("""
            QFrame {
                background: rgba(14, 28, 44, 0.75);
                border: 1px solid rgba(145, 165, 179, 0.35);
                border-radius: 20px;
            }
        """)
        s_lay = QHBoxLayout(search_frame)
        s_lay.setContentsMargins(14, 0, 14, 0)
        s_lay.setSpacing(8)

        s_ico = QLabel()
        s_p = ROOT / "assets_omnidash" / "icons" / "search.png"
        if s_p.exists():
            s_ico.setPixmap(QPixmap(str(s_p)).scaled(15, 15, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        s_lay.addWidget(s_ico)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar miembros...")
        self.search_input.setStyleSheet("background: transparent; border: none; color: #ffffff; font-size: 13px;")
        self.search_input.textChanged.connect(self._on_search_changed)
        s_lay.addWidget(self.search_input)
        hdr_row.addWidget(search_frame)

        self.add_comm_btn = QPushButton("+")
        self.add_comm_btn.setFixedSize(40, 40)
        self.add_comm_btn.setCursor(Qt.PointingHandCursor)
        self.add_comm_btn.setToolTip("Crear Comunidad")
        self.add_comm_btn.setStyleSheet("""
            QPushButton {
                background: rgba(18, 38, 56, 0.75);
                border: 1px solid rgba(145, 165, 179, 0.4);
                border-radius: 20px;
                color: #ffffff;
                font-size: 19px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(53, 200, 241, 0.25);
                border: 1.5px solid #35C8F1;
            }
        """)
        self.add_comm_btn.clicked.connect(self.open_create_community_dialog)
        hdr_row.addWidget(self.add_comm_btn)

        self.invite_btn = QPushButton()
        self.invite_btn.setFixedSize(40, 40)
        self.invite_btn.setCursor(Qt.PointingHandCursor)
        self.invite_btn.setToolTip("Generar enlace de invitación")
        inv_p = ROOT / "assets_omnidash" / "icons" / "person_add.png"
        if not inv_p.exists():
            inv_p = ROOT / "assets_omnidash" / "icons" / "people.png"
        if inv_p.exists():
            self.invite_btn.setIcon(QIcon(str(inv_p)))
            self.invite_btn.setIconSize(QSize(20, 20))
        self.invite_btn.setStyleSheet("""
            QPushButton {
                background: rgba(18, 38, 56, 0.75);
                border: 1px solid rgba(145, 165, 179, 0.4);
                border-radius: 20px;
            }
            QPushButton:hover {
                background: rgba(53, 200, 241, 0.25);
                border: 1.5px solid #35C8F1;
            }
        """)
        self.invite_btn.clicked.connect(self.open_invite_dialog)
        hdr_row.addWidget(self.invite_btn)

        main_lay.addLayout(hdr_row)

        body_row = QHBoxLayout()
        body_row.setSpacing(12)

        self.rail = ServerRail(self)
        self.rail.explore_clicked.connect(self.back_to_explore.emit)
        self.rail.community_selected.connect(self._on_community_selected)
        body_row.addWidget(self.rail)

        self.channel_sidebar = ChannelSidebar(self)
        self.channel_sidebar.channel_selected.connect(self._on_channel_selected)
        self.channel_sidebar.create_channel_requested.connect(self.open_create_channel_dialog)
        self.channel_sidebar.edit_channel_requested.connect(self._on_edit_channel_requested)
        self.channel_sidebar.delete_channel_requested.connect(self._on_delete_channel_requested)
        self.channel_sidebar.leave_community_requested.connect(self._on_leave_community)
        body_row.addWidget(self.channel_sidebar)

        self.chat_area = CentralChatWidget(self)
        self.chat_area.message_submit_requested.connect(self._on_send_message)
        self.chat_area.refresh_requested.connect(self._on_refresh_messages)
        self.chat_area.older_messages_requested.connect(self._on_load_older_messages)
        self.chat_area.message_edit_requested.connect(self._on_edit_message)
        self.chat_area.message_delete_requested.connect(self._on_delete_message)
        self.chat_area.reaction_toggle_requested.connect(self._on_toggle_reaction)
        self.chat_area.attachment_upload_requested.connect(self._on_upload_attachment)
        self.chat_area.typing_changed.connect(self._on_local_typing)
        self.chat_area.stream_stage.stop_requested.connect(lambda: self._on_voice_toggled("screen_stop", False))
        self.chat_area.stream_stage.close_requested.connect(self._on_close_stream_viewer)
        if self.controller:
            self.chat_area.set_attachment_loader(self._load_attachment_bytes)
        body_row.addWidget(self.chat_area, 1)

        self._screen_capture_source_id: str = "screen:0"
        self._screen_capture_dims: tuple[int, int] = (1280, 720)
        self._screen_capture_timer = QTimer(self)
        self._screen_capture_timer.setInterval(33)
        self._screen_capture_timer.timeout.connect(self._on_screen_capture_tick)

        self.right_panel = RightPanel(self)
        self.right_panel.voice_toggled.connect(self._on_voice_toggled)
        self.right_panel.self_presence_changed.connect(self._on_self_presence_changed)
        self.right_panel.member_moderation_requested.connect(self._on_member_moderation_requested)
        self.right_panel.soundboard_play_requested.connect(self._on_soundboard_play_requested)
        self.right_panel.soundboard_stop_requested.connect(self._on_soundboard_stop_requested)
        self.right_panel.soundboard_upload_requested.connect(self._on_soundboard_upload_requested)
        body_row.addWidget(self.right_panel)

        main_lay.addLayout(body_row, 1)

        if self.controller:
            self._bind_controller(self.controller)

    def _bind_controller(self, ctrl: CommunityController):
        ctrl.session_changed.connect(self._on_session_changed)
        ctrl.communities_updated.connect(self._on_communities_updated)
        ctrl.community_opened.connect(self._on_community_opened)
        ctrl.channel_messages_loaded.connect(self._on_messages_loaded)
        ctrl.messages_synced.connect(self._on_messages_synced)
        ctrl.message_received.connect(self._on_message_received)
        ctrl.message_updated.connect(self._on_message_updated)
        ctrl.message_deleted.connect(self._on_message_deleted)
        ctrl.reaction_updated.connect(self._on_reaction_updated)
        ctrl.typing_updated.connect(self._on_typing_updated)
        ctrl.members_updated.connect(self._on_members_updated)
        ctrl.presence_self_changed.connect(self.right_panel.sync_self_presence_ui)
        ctrl.voice_state_changed.connect(self._on_voice_state_changed)
        ctrl.stream_state_changed.connect(self._on_stream_state_changed)
        ctrl.remote_video_frame_received.connect(self._on_remote_video_frame)
        ctrl.remote_stream_ended.connect(self._on_remote_stream_ended)
        ctrl.active_streams_updated.connect(self._on_active_streams_updated)
        ctrl.soundboard_loaded.connect(self.right_panel.set_soundboard_sounds)
        ctrl.soundboard_event.connect(self._on_soundboard_event)
        ctrl.realtime_status_changed.connect(self.chat_area.set_realtime_status)
        ctrl.error_occurred.connect(self.chat_area.show_error)
        if getattr(ctrl, "active_voice_channel", None):
            self._on_voice_state_changed(
                ctrl._build_voice_state(
                    ctrl.active_voice_channel,
                    getattr(ctrl, "_active_voice_cred", None),
                    bool(getattr(ctrl, "_active_voice_reachable", False)),
                )
            )

    def _load_attachment_bytes(self, attachment_id: str) -> Optional[bytes]:
        if not self.controller or not self.controller.session:
            return None
        try:
            return self.controller.api.download_attachment_bytes(attachment_id)
        except Exception:
            return None

    def _current_user_id(self) -> str:
        return str(self.controller.session.user_id) if (self.controller and self.controller.session) else ""

    def _on_communities_updated(self, mine: list, _pub: list):
        self.rail.set_communities(mine)

    def _on_session_changed(self, sess):
        if sess is None:
            self._screen_capture_timer.stop()
            self.chat_area.stream_stage.clear_stream()
            self.user_chip_lbl.setText("@sin_sesion")
            self.rail.set_communities([])
            self.channel_sidebar.set_live_channels([])
            self.channel_sidebar.set_community_data(None, [])
            self.chat_area.set_channel(None)
            self.chat_area.set_messages([], "")
            self._all_members = []
            self.right_panel.set_members([])
            self.right_panel.set_voice_state({"connected": False})
        else:
            self.user_chip_lbl.setText(f"@{sess.username}")

    def _on_logout_clicked(self):
        if self.controller:
            self.controller.logout()

    def _on_community_selected(self, community_id: str):
        if not self.controller:
            return
        self.controller.open_community_async(
            community_id,
            on_error=lambda exc: self.chat_area.show_error(exc.message),
        )

    def _on_community_opened(self, payload: dict):
        comm = payload.get("community")
        channels = list(payload.get("channels") or [])
        members = list(payload.get("members") or [])
        if comm:
            self.rail.set_active_community(str(comm["id"]))
        self._all_members = members
        my_uid = self._current_user_id()
        my_role = next(
            (str(m.get("role") or "member").lower() for m in members if str(m.get("user_id")) == my_uid),
            "member",
        )
        can_mod = my_role in ("owner", "admin", "moderator")
        self.chat_area.set_can_moderate(can_mod)
        self.right_panel.set_moderation_context(my_uid, can_mod)
        online_count = sum(
            1 for m in members
            if str(m.get("presence_status") or m.get("presence") or "").lower()
            in ("online", "idle", "dnd", "away", "busy", "playing", "in_game")
        )
        active_text_id = (
            str(self.controller.active_channel["id"])
            if self.controller and self.controller.active_channel
            else None
        )
        active_voice_id = (
            str(self.controller.active_voice_channel["id"])
            if self.controller and self.controller.active_voice_channel
            else None
        )
        self.channel_sidebar.set_community_data(
            comm,
            channels,
            member_count=len(members),
            online_count=online_count,
            active_text_id=active_text_id,
            active_voice_id=active_voice_id,
        )
        streams = list(payload.get("streams") or (self.controller.active_streams if self.controller else []))
        self.channel_sidebar.set_live_channels(
            [str(s.get("channel_id")) for s in streams if s.get("channel_id")]
        )
        self._apply_member_filter()

    def _on_channel_selected(self, channel_id: str, ch_type: str):
        if not self.controller:
            return
        if ch_type == "voice":
            self.controller.join_voice_channel_async(
                channel_id,
                on_error=lambda exc: self.chat_area.show_error(exc.message),
            )
        else:
            self.controller.select_channel_async(
                channel_id,
                on_error=lambda exc: self.chat_area.show_error(exc.message),
            )

    def _on_messages_loaded(self, channel_id: str, messages: list):
        if self.controller and self.controller.active_channel:
            self.chat_area.set_channel(self.controller.active_channel)
            self.channel_sidebar.set_active_text_channel(str(self.controller.active_channel["id"]))
        else:
            self.chat_area.set_channel(None)
        self.chat_area.set_messages(messages, current_user_id=self._current_user_id())

    def _on_messages_synced(self, channel_id: str, missed_messages: list):
        active_id = str(self.controller.active_channel["id"]) if (self.controller and self.controller.active_channel) else ""
        if active_id and str(channel_id) == active_id:
            self.chat_area.sync_new_messages(missed_messages, current_user_id=self._current_user_id())

    def _on_message_received(self, msg: dict):
        active_id = str(self.controller.active_channel["id"]) if (self.controller and self.controller.active_channel) else ""
        if active_id and str(msg.get("channel_id") or "") == active_id:
            self.chat_area.append_or_update_message(msg, current_user_id=self._current_user_id())

    def _on_message_updated(self, msg: dict):
        active_id = str(self.controller.active_channel["id"]) if (self.controller and self.controller.active_channel) else ""
        if active_id and str(msg.get("channel_id") or "") == active_id:
            self.chat_area.append_or_update_message(msg, current_user_id=self._current_user_id(), scroll_to_bottom=False)

    def _on_message_deleted(self, payload: dict):
        mid = str(payload.get("id") or payload.get("message_id") or "")
        if mid:
            self.chat_area.remove_message(mid)

    def _on_reaction_updated(self, payload: dict):
        mid = str(payload.get("message_id") or "")
        if mid:
            self.chat_area.update_message_reactions(mid, payload.get("reactions") or [])

    def _on_typing_updated(self, payload: dict):
        self.chat_area.show_typing_peer(
            str(payload.get("user_id") or ""),
            str(payload.get("username") or "Alguien"),
            bool(payload.get("typing", True)),
        )

    def _on_members_updated(self, members: list):
        self._all_members = list(members or [])
        self._apply_member_filter()

    def _on_search_changed(self, text: str):
        self._search_filter = text.strip().lower()
        self._apply_member_filter()

    def _apply_member_filter(self):
        if not self._search_filter:
            self.right_panel.set_members(self._all_members)
            return
        filtered = [
            m for m in self._all_members
            if self._search_filter in str(m.get("username") or m.get("user_id") or "").lower()
        ]
        self.right_panel.set_members(filtered)

    def _on_send_message(self, text: str):
        if not self.controller:
            return
        reply_id, att_ids = self.chat_area.consume_compose_meta()
        self.chat_area.msg_input.clear()

        def _done(msg: dict):
            self.chat_area.append_or_update_message(msg, current_user_id=self._current_user_id())

        self.controller.send_message_async(
            text,
            reply_to_id=reply_id,
            attachment_ids=att_ids or None,
            on_done=_done,
            on_error=lambda exc: self.chat_area.show_error(exc.message),
        )

    def _on_load_older_messages(self, before_id: str):
        if not self.controller:
            return
        self.controller.load_older_messages_async(
            before_id,
            limit=40,
            on_done=lambda older: self.chat_area.prepend_messages(older, current_user_id=self._current_user_id()),
            on_error=lambda exc: self.chat_area.show_error(exc.message),
        )

    def _on_edit_message(self, message_id: str, new_text: str):
        if not self.controller:
            return
        try:
            msg = self.controller.edit_message(message_id, new_text)
            self.chat_area.append_or_update_message(msg, current_user_id=self._current_user_id(), scroll_to_bottom=False)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_delete_message(self, message_id: str):
        if not self.controller:
            return
        try:
            self.controller.delete_message(message_id)
            self.chat_area.remove_message(message_id)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_toggle_reaction(self, message_id: str, emoji: str):
        if not self.controller:
            return
        try:
            res = self.controller.toggle_reaction(message_id, emoji)
            self.chat_area.update_message_reactions(message_id, res.get("reactions") or [])
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_upload_attachment(self, file_path: str):
        if not self.controller:
            return
        try:
            att = self.controller.upload_attachment(file_path)
            self.chat_area.add_uploaded_attachment(att)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_local_typing(self, typing: bool):
        if self.controller:
            self.controller.emit_typing(typing=typing)

    def _on_edit_channel_requested(self, channel_id: str):
        if not self.controller:
            return
        ch = next((c for c in self.controller.active_channels if c["id"] == channel_id), None)
        if not ch:
            return
        new_name, ok = QInputDialog.getText(self, "Editar canal", "Nuevo nombre del canal:", text=str(ch.get("name") or ""))
        if not ok or not new_name.strip():
            return
        try:
            self.controller.update_channel(channel_id, name=new_name.strip())
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_delete_channel_requested(self, channel_id: str):
        if not self.controller:
            return
        try:
            self.controller.delete_channel(channel_id)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_self_presence_changed(self, status: str, visibility: str):
        if not self.controller:
            return
        try:
            self.controller.set_status(status=status, activity_visibility=visibility)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_member_moderation_requested(self, user_id: str, action: str):
        if not self.controller or not self.controller.active_community:
            return
        cid = str(self.controller.active_community["id"])
        dur = 600 if action == "mute" else None
        try:
            self.controller.moderate_member(cid, user_id, action, duration_seconds=dur)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_refresh_messages(self):
        if self.controller and self.controller.active_channel:
            self.controller.select_channel_async(
                str(self.controller.active_channel["id"]),
                on_error=lambda exc: self.chat_area.show_error(exc.message),
            )

    def _on_leave_community(self):
        if not self.controller or not self.controller.active_community:
            return
        cid = str(self.controller.active_community["id"])
        try:
            self.controller.leave_community(cid)
            self.back_to_explore.emit()
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)

    def _on_voice_state_changed(self, state: dict):
        self.right_panel.set_voice_state(state)
        ch = state.get("channel")
        ch_id = str(ch["id"]) if isinstance(ch, dict) and ch.get("id") else None
        self.channel_sidebar.set_active_voice_channel(ch_id)
        if not state.get("connected"):
            self._screen_capture_timer.stop()
            self.chat_area.stream_stage.clear_stream()
            return
        if self.controller and ch_id:
            if not getattr(self, "_sources_loaded_for_voice", False):
                self._sources_loaded_for_voice = True
                try:
                    self.right_panel.set_capture_sources(self.controller.get_stream_sources())
                except Exception:
                    pass
                try:
                    self.controller.load_soundboard_async(
                        community_id=(self.controller.active_community or {}).get("id"),
                        on_error=lambda _e: None,
                    )
                except Exception:
                    pass
            active_s = next(
                (s for s in self.controller.active_streams if str(s.get("channel_id")) == ch_id),
                None,
            )
            if active_s and not state.get("screen_live"):
                self.chat_area.stream_stage.set_stream_session(
                    {"watching": True, "session": active_s},
                    is_broadcaster=False,
                )

    def _on_screen_capture_tick(self):
        if not self.controller or not self.controller.voice_engine.is_screen_sharing:
            self._screen_capture_timer.stop()
            return
        from backend.communities.stream_adapter import capture_source_rgba
        tw, th = self._screen_capture_dims
        frame = capture_source_rgba(
            source_id=self._screen_capture_source_id,
            target_width=tw,
            target_height=th,
            window_widget=self.window(),
        )
        if frame is not None:
            fw, fh, rgba = frame
            self.controller.push_screen_video_frame(fw, fh, rgba)
            self.chat_area.stream_stage.update_rgba_frame(fw, fh, rgba)

    def _on_stream_state_changed(self, state: dict):
        is_live = bool(state.get("live"))
        is_watching = bool(state.get("watching"))
        if is_live:
            fps = max(1, int(state.get("fps") or 30))
            self._screen_capture_timer.setInterval(max(16, int(1000 / fps)))
            if not self._screen_capture_timer.isActive():
                self._screen_capture_timer.start()
            self.chat_area.stream_stage.set_stream_session(state, is_broadcaster=True)
        elif is_watching:
            self._screen_capture_timer.stop()
            self.chat_area.stream_stage.set_stream_session(state, is_broadcaster=False)
        else:
            self._screen_capture_timer.stop()
            self.chat_area.stream_stage.clear_stream()

    def _on_remote_video_frame(self, participant_id: str, width: int, height: int, rgba: bytes):
        self.chat_area.stream_stage.update_rgba_frame(width, height, rgba)

    def _on_remote_stream_ended(self, _participant_or_channel: str):
        if not (self.controller and self.controller.voice_engine.is_screen_sharing):
            self.chat_area.stream_stage.clear_stream()

    def _on_active_streams_updated(self, streams: list):
        self.channel_sidebar.set_live_channels(
            [str(s.get("channel_id")) for s in (streams or []) if s.get("channel_id")]
        )

    def _on_close_stream_viewer(self):
        if self.controller:
            self.controller.stop_watching_stream()
        self.chat_area.stream_stage.clear_stream()

    def _on_voice_toggled(self, action: str, enabled: bool):
        if not self.controller:
            return
        if action == "mic":
            self.controller.set_voice_mute(not enabled)
        elif action == "headset":
            self.controller.set_voice_deafen(not enabled)
        elif action == "disconnect":
            self._screen_capture_timer.stop()
            self.controller.leave_voice_channel()
        elif action == "screen_start":
            from backend.communities.stream_adapter import parse_resolution_dimensions
            source_id, res, fps, bitrate = self.right_panel.get_selected_stream_config()
            self._screen_capture_source_id = source_id
            self._screen_capture_dims = parse_resolution_dimensions(res)
            self.controller.start_screen_share_async(
                source_id=source_id,
                resolution=res,
                fps=fps,
                bitrate_kbps=bitrate,
                with_audio=False,
                window_widget=self.window(),
                on_error=lambda exc: self.chat_area.show_error(exc.message),
            )
        elif action == "screen_stop":
            self._screen_capture_timer.stop()
            self.controller.stop_screen_share_async()
        elif action == "screen_unavailable":
            self.chat_area.show_error(
                "Compartir pantalla requiere captura + publicación de video WebRTC LiveKit (P1-B)."
            )

    def _on_soundboard_play_requested(self, sound_id: str):
        if not self.controller:
            return
        self.right_panel.set_soundboard_feedback("Inyectando efecto en audio WebRTC...")
        self.controller.play_soundboard_effect_async(
            sound_id=sound_id,
            on_done=lambda res: self.right_panel.set_soundboard_feedback(
                f"🔊 Transmitiendo por RTC: {res.get('title', sound_id)}"
            ),
            on_error=lambda exc: self.right_panel.set_soundboard_feedback(exc.message, is_error=True),
        )

    def _on_soundboard_stop_requested(self):
        if not self.controller:
            return
        self.controller.stop_soundboard_effect()
        self.right_panel.set_soundboard_feedback("Reproducción soundboard detenida.")

    def _on_soundboard_upload_requested(self, file_path: str):
        if not self.controller:
            return
        self.right_panel.set_soundboard_feedback("Subiendo efecto MP3...")
        self.controller.upload_sound_file_async(
            file_path=file_path,
            on_done=lambda snd: self.right_panel.set_soundboard_feedback(
                f"✅ Efecto agregado: {snd.get('title', 'MP3')}"
            ),
            on_error=lambda exc: self.right_panel.set_soundboard_feedback(exc.message, is_error=True),
        )

    def _on_soundboard_event(self, payload: dict):
        action = str(payload.get("action") or "")
        title = str(payload.get("title") or payload.get("sound_id") or "Efecto")
        if action == "played":
            self.right_panel.set_soundboard_feedback(f"🔊 Sonando en sala RTC: {title}")
        elif action == "stopped":
            self.right_panel.set_soundboard_feedback(f"Efecto detenido: {title}")

    def open_create_community_dialog(self):
        if not self.controller or not self.controller.session:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Crear Comunidad")
        dlg.setFixedWidth(400)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        name_inp = _styled_input("Nombre de la comunidad")
        desc_inp = _styled_input("Descripción corta")
        vis_cb = QComboBox()
        vis_cb.addItem("Privada (por invitación)", "private")
        vis_cb.addItem("Pública (visible en Explorar)", "public")
        vis_cb.setFixedHeight(36)
        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #ffb3b8; font-size: 12px;")
        err_lbl.setVisible(False)

        lay.addWidget(QLabel("Nombre:"))
        lay.addWidget(name_inp)
        lay.addWidget(QLabel("Descripción:"))
        lay.addWidget(desc_inp)
        lay.addWidget(QLabel("Visibilidad:"))
        lay.addWidget(vis_cb)
        lay.addWidget(err_lbl)

        btns = QHBoxLayout()
        cancel_b = QPushButton("Cancelar")
        cancel_b.clicked.connect(dlg.reject)
        create_b = QPushButton("Crear")
        create_b.setStyleSheet("background: #35C8F1; color: #051624; font-weight: 800; padding: 8px 16px; border-radius: 8px;")
        btns.addStretch(1)
        btns.addWidget(cancel_b)
        btns.addWidget(create_b)
        lay.addLayout(btns)

        def submit():
            name = name_inp.text().strip()
            if not name:
                err_lbl.setText("El nombre es obligatorio.")
                err_lbl.setVisible(True)
                return
            try:
                self.controller.create_community(
                    name=name,
                    description=desc_inp.text().strip(),
                    visibility=str(vis_cb.currentData()),
                )
                dlg.accept()
            except CommunityApiError as exc:
                err_lbl.setText(exc.message)
                err_lbl.setVisible(True)

        create_b.clicked.connect(submit)
        dlg.exec()

    def open_create_channel_dialog(self, channel_type: str = "text"):
        if not self.controller or not self.controller.active_community:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Crear Canal")
        dlg.setFixedWidth(380)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        name_inp = _styled_input("Nombre del canal (ej. torneos)")
        topic_inp = _styled_input("Tema opcional")
        type_cb = QComboBox()
        type_cb.addItem("Texto (#)", "text")
        type_cb.addItem("Voz (LiveKit señalización)", "voice")
        type_cb.setCurrentIndex(1 if channel_type == "voice" else 0)
        type_cb.setFixedHeight(36)
        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #ffb3b8; font-size: 12px;")
        err_lbl.setVisible(False)

        lay.addWidget(QLabel("Nombre:"))
        lay.addWidget(name_inp)
        lay.addWidget(QLabel("Tema:"))
        lay.addWidget(topic_inp)
        lay.addWidget(QLabel("Tipo:"))
        lay.addWidget(type_cb)
        lay.addWidget(err_lbl)

        btns = QHBoxLayout()
        cancel_b = QPushButton("Cancelar")
        cancel_b.clicked.connect(dlg.reject)
        create_b = QPushButton("Crear Canal")
        create_b.setStyleSheet("background: #35C8F1; color: #051624; font-weight: 800; padding: 8px 16px; border-radius: 8px;")
        btns.addStretch(1)
        btns.addWidget(cancel_b)
        btns.addWidget(create_b)
        lay.addLayout(btns)

        def submit():
            name = name_inp.text().strip()
            if not name:
                err_lbl.setText("El nombre del canal es obligatorio.")
                err_lbl.setVisible(True)
                return
            try:
                self.controller.create_channel(
                    name=name,
                    channel_type=str(type_cb.currentData()),
                    topic=topic_inp.text().strip(),
                )
                dlg.accept()
            except CommunityApiError as exc:
                err_lbl.setText(exc.message)
                err_lbl.setVisible(True)

        create_b.clicked.connect(submit)
        dlg.exec()

    def open_invite_dialog(self):
        if not self.controller or not self.controller.active_community:
            self.chat_area.show_error("Abrí una comunidad para generar un código de invitación.")
            return
        cid = str(self.controller.active_community["id"])
        try:
            inv = self.controller.create_invitation(cid)
        except CommunityApiError as exc:
            self.chat_area.show_error(exc.message)
            return

        code = str(inv.get("code") or "")
        link = f"cci://invite/{code}" if code else ""
        dlg = QDialog(self)
        dlg.setWindowTitle("Invitaciones de comunidad")
        dlg.setFixedWidth(460)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        lay.addWidget(QLabel(f"Compartí este código o enlace para unirse a {self.controller.active_community.get('name', 'la comunidad')}:"))

        code_box = _styled_input()
        code_box.setReadOnly(True)
        code_box.setText(code)
        link_box = _styled_input()
        link_box.setReadOnly(True)
        link_box.setText(link)
        lay.addWidget(QLabel("Código:"))
        lay.addWidget(code_box)
        lay.addWidget(QLabel("Enlace C.C.I.:"))
        lay.addWidget(link_box)

        inv_list_lbl = QLabel("Invitaciones activas:")
        inv_list_lbl.setStyleSheet("font-weight: 700; color: #35C8F1; margin-top: 6px;")
        lay.addWidget(inv_list_lbl)
        inv_list_box = QVBoxLayout()
        lay.addLayout(inv_list_box)

        def _reload_invites():
            _clear_layout_widgets(inv_list_box)
            try:
                active_invs = self.controller.list_invitations(cid)
            except CommunityApiError:
                active_invs = []
            for item in active_invs[:6]:
                row_w = QWidget()
                row = QHBoxLayout(row_w)
                row.setContentsMargins(0, 2, 0, 2)
                icode = str(item.get("code") or "")
                uses = f"{item.get('uses_count', 0)} usos"
                row.addWidget(QLabel(f"{icode}  ({uses})"), 1)
                rev_b = QPushButton("Revocar")
                rev_b.setStyleSheet("background: rgba(233,75,86,0.28); border: 1px solid #E94B56; border-radius: 6px; padding: 3px 8px; color: #ffd6d9; font-size: 11px;")
                rev_b.clicked.connect(lambda _, c=icode: (_revoke(c)))
                row.addWidget(rev_b)
                inv_list_box.addWidget(row_w)

        def _revoke(icode: str):
            try:
                self.controller.revoke_invitation(cid, icode)
                _reload_invites()
            except CommunityApiError as exc:
                self.chat_area.show_error(exc.message)

        _reload_invites()

        btns = QHBoxLayout()
        copy_b = QPushButton("Copiar código")
        copy_b.clicked.connect(lambda: QApplication.clipboard().setText(code))
        close_b = QPushButton("Cerrar")
        close_b.setStyleSheet("background: #35C8F1; color: #051624; font-weight: 800; padding: 8px 16px; border-radius: 8px;")
        close_b.clicked.connect(dlg.accept)
        btns.addStretch(1)
        btns.addWidget(copy_b)
        btns.addWidget(close_b)
        lay.addLayout(btns)
        dlg.exec()


class CommunityExploreView(QWidget):
    open_community_requested = Signal(str)

    def __init__(self, controller: Optional[CommunityController] = None, parent=None):
        super().__init__(parent)
        self.controller = controller
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 18)

        self.panel = AcrylicGlassCard(self, border_radius=24)
        p_lay = QVBoxLayout(self.panel)
        p_lay.setContentsMargins(28, 22, 28, 22)
        p_lay.setSpacing(14)

        hdr = QHBoxLayout()
        hdr_t = QVBoxLayout()
        hdr_t.setSpacing(3)
        title = QLabel("C.C.I. Gaming Communities & Friends")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        sub = QLabel("Tus comunidades privadas o públicas y catálogo oficial del servidor.")
        sub.setStyleSheet("font-size: 12px; color: #a5d8ff;")
        hdr_t.addWidget(title)
        hdr_t.addWidget(sub)
        hdr.addLayout(hdr_t, 1)

        self.create_btn = QPushButton("+ Crear comunidad")
        self.create_btn.setProperty("class", "glassBtn")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.clicked.connect(self._open_create_dialog)
        hdr.addWidget(self.create_btn)

        self.join_code_btn = QPushButton("Unirse por código")
        self.join_code_btn.setProperty("class", "glassBtn")
        self.join_code_btn.setCursor(Qt.PointingHandCursor)
        self.join_code_btn.clicked.connect(self._open_join_code_dialog)
        hdr.addWidget(self.join_code_btn)

        self.spotify_btn = QPushButton("🎵 Spotify")
        self.spotify_btn.setProperty("class", "glassBtn")
        self.spotify_btn.setCursor(Qt.PointingHandCursor)
        self.spotify_btn.setToolTip("Conectar, configurar o revocar integración opt-in con Spotify")
        self.spotify_btn.clicked.connect(self._open_spotify_dialog)
        hdr.addWidget(self.spotify_btn)

        self.refresh_btn = QPushButton("↻ Actualizar")
        self.refresh_btn.setProperty("class", "glassBtn")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(self.refresh_btn)

        self.logout_btn = QPushButton("Cerrar sesión")
        self.logout_btn.setProperty("class", "glassBtn")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(lambda: self.controller.logout() if self.controller else None)
        hdr.addWidget(self.logout_btn)

        p_lay.addLayout(hdr)

        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.setVisible(False)
        self.status_banner.setStyleSheet(
            "background: rgba(233, 75, 86, 0.22); border: 1px solid rgba(233, 75, 86, 0.65); "
            "border-radius: 10px; color: #ffd6d9; font-size: 12px; font-weight: 600; padding: 8px 12px;"
        )
        p_lay.addWidget(self.status_banner)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { border: none; background: transparent; }")
        self.scroll.viewport().setStyleSheet("background: transparent;")
        self.scroll.viewport().setAttribute(Qt.WA_TranslucentBackground, True)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch(1)
        self.scroll.setWidget(self.cards_container)
        p_lay.addWidget(self.scroll, 1)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(12)

        # Panel real de Amigos (Unificación legacy FriendsService + Communities)
        friends_card = AcrylicGlassCard(self, border_radius=14)
        f_lay = QVBoxLayout(friends_card)
        f_lay.setContentsMargins(14, 12, 14, 12)
        f_lay.setSpacing(8)
        f_hdr = QLabel("Amigos y solicitudes")
        f_hdr.setStyleSheet("font-size: 13px; font-weight: 800; color: #35C8F1;")
        f_lay.addWidget(f_hdr)

        add_f_row = QHBoxLayout()
        self.friend_user_inp = _styled_input("Agregar amigo (@username)")
        self.friend_user_inp.setFixedHeight(32)
        self.add_friend_btn = QPushButton("Agregar")
        self.add_friend_btn.setProperty("class", "glassBtn")
        self.add_friend_btn.setCursor(Qt.PointingHandCursor)
        self.add_friend_btn.clicked.connect(self._on_add_friend_clicked)
        add_f_row.addWidget(self.friend_user_inp, 1)
        add_f_row.addWidget(self.add_friend_btn)
        f_lay.addLayout(add_f_row)

        self.friends_list_box = QVBoxLayout()
        self.friends_list_box.setSpacing(4)
        f_lay.addLayout(self.friends_list_box)
        bottom_row.addWidget(friends_card, 1)

        # Panel real de Actividad reciente (solo eventos persistidos reales)
        act_card = AcrylicGlassCard(self, border_radius=14)
        a_lay = QVBoxLayout(act_card)
        a_lay.setContentsMargins(14, 12, 14, 12)
        a_lay.setSpacing(8)
        a_hdr = QLabel("Actividad reciente")
        a_hdr.setStyleSheet("font-size: 13px; font-weight: 800; color: #32D875;")
        a_lay.addWidget(a_hdr)
        self.activity_list_box = QVBoxLayout()
        self.activity_list_box.setSpacing(4)
        a_lay.addLayout(self.activity_list_box)
        a_lay.addStretch(1)
        bottom_row.addWidget(act_card, 1)

        p_lay.addLayout(bottom_row)

        layout.addWidget(self.panel)

        if self.controller:
            self.controller.communities_updated.connect(self.render_communities)
            self.controller.friends_updated.connect(self.render_friends)
            self.controller.spotify_status_changed.connect(self._render_spotify_button)
            self._render_spotify_button(getattr(self.controller, "spotify_status", {}) or {})
            self.controller.activity_feed_updated.connect(self.render_activity_feed)
            self.controller.session_changed.connect(self._on_session_changed)
            self.render_friends([], [])
            self.render_activity_feed([])

    def show_error(self, message: str):
        if message:
            self.status_banner.setText(message)
            self.status_banner.setVisible(True)
        else:
            self.status_banner.setVisible(False)

    def _on_session_changed(self, sess):
        if sess is None:
            self.render_communities([], [])
            self.render_friends([], [])
            self.render_activity_feed([])

    def refresh(self):
        if not self.controller:
            return
        self.show_error("")
        self.controller.refresh_communities_async(on_error=lambda exc: self.show_error(exc.message))
        self.controller.refresh_friends_async()
        self.controller.refresh_activity_and_notifications_async()

    def _on_add_friend_clicked(self):
        if not self.controller:
            return
        uname = self.friend_user_inp.text().strip().lstrip("@")
        if not uname:
            return
        self.show_error("")
        try:
            self.controller.send_friend_request(uname)
            self.friend_user_inp.clear()
        except CommunityApiError as exc:
            self.show_error(exc.message)

    def render_friends(self, friends: list, incoming_requests: list):
        _clear_layout_widgets(self.friends_list_box)
        for req in (incoming_requests or [])[:4]:
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 2, 0, 2)
            from_id = str(req.get("requester_id") or req.get("from_user_id") or "")
            from_name = str(req.get("username") or from_id)
            row.addWidget(QLabel(f"Solicitud de @{from_name}"), 1)
            acc_b = QPushButton("Aceptar")
            acc_b.setStyleSheet("background: rgba(50,216,117,0.28); border: 1px solid #32D875; border-radius: 6px; padding: 2px 8px; color: #ffffff; font-size: 11px;")
            acc_b.clicked.connect(lambda _, u=from_id: self.controller and self.controller.respond_friend_request(u, True))
            rej_b = QPushButton("Rechazar")
            rej_b.setStyleSheet("background: rgba(233,75,86,0.25); border: 1px solid #E94B56; border-radius: 6px; padding: 2px 8px; color: #ffd6d9; font-size: 11px;")
            rej_b.clicked.connect(lambda _, u=from_id: self.controller and self.controller.respond_friend_request(u, False))
            row.addWidget(acc_b)
            row.addWidget(rej_b)
            self.friends_list_box.addWidget(row_w)

        if friends:
            for f in friends[:6]:
                fname = str(f.get("username") or f.get("friend_id") or f.get("user_id") or "Amigo")
                raw_st = str(
                    f.get("presence")
                    or f.get("presence_status")
                    or ("" if f.get("status") in ("accepted", "pending", "blocked", None, "") else f.get("status"))
                    or "offline"
                ).lower()
                fgame = f.get("current_game") or f.get("activity_title")
                atype = str(f.get("activity_type") or "").lower()
                icon = "🎵" if atype == "listening" else "🎮"
                desc = f"{icon} {fgame}" if fgame else raw_st
                lbl = QLabel(f"● @{fname} — {desc}")
                col = "#32D875" if (fgame or raw_st in ("online", "playing", "in_game")) else "#91A5B3"
                lbl.setStyleSheet(f"font-size: 12px; color: {col};")
                self.friends_list_box.addWidget(lbl)
        elif not incoming_requests:
            empty_f = QLabel("Sin amigos agregados todavía.")
            empty_f.setStyleSheet("font-size: 12px; color: #91A5B3;")
            self.friends_list_box.addWidget(empty_f)

    def render_activity_feed(self, events: list):
        _clear_layout_widgets(self.activity_list_box)
        if not events:
            lbl = QLabel("Sin actividad reciente de juegos.")
            lbl.setStyleSheet("font-size: 12px; color: #91A5B3;")
            self.activity_list_box.addWidget(lbl)
            return
        for ev in events[:6]:
            uname = str(ev.get("username") or ev.get("user_id") or "Jugador")
            title = str(ev.get("game_title") or ev.get("title") or ev.get("game_id") or "Juego")
            etype = str(ev.get("event_type") or "")
            verb = "inició" if "started" in etype else "dejó de jugar"
            lbl = QLabel(f"🎮 @{uname} {verb} {title}")
            lbl.setStyleSheet("font-size: 12px; color: #dff5ff;")
            self.activity_list_box.addWidget(lbl)

    def render_communities(self, my_communities: list, public_communities: list):
        _clear_layout_widgets(self.cards_layout, keep_trailing_stretch=True)
        insert_pos = 0

        def add_section_header(text: str):
            nonlocal insert_pos
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #35C8F1; padding: 6px 2px 2px 2px;")
            self.cards_layout.insertWidget(insert_pos, lbl)
            insert_pos += 1

        def add_card(comm: dict, is_member: bool):
            nonlocal insert_pos
            cid = str(comm.get("id") or "")
            card = AcrylicGlassCard(self, border_radius=12, is_interactive=True)
            card.setFixedHeight(74)
            c_lay = QHBoxLayout(card)
            c_lay.setContentsMargins(18, 10, 18, 10)

            info_box = QVBoxLayout()
            r_name = QLabel(str(comm.get("name") or "Comunidad"))
            r_name.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
            r_desc = QLabel(str(comm.get("description") or "Sin descripción"))
            r_desc.setStyleSheet("font-size: 11px; color: #cbe6ff;")
            info_box.addWidget(r_name)
            info_box.addWidget(r_desc)
            c_lay.addLayout(info_box, 1)

            vis = "Pública" if comm.get("visibility") == "public" else "Privada"
            mcount = comm.get("member_count", 0)
            meta_lbl = QLabel(f"{vis}  •  {mcount} miembros")
            meta_lbl.setStyleSheet("font-size: 12px; color: #BDD4E4; font-weight: 600;")
            c_lay.addWidget(meta_lbl)

            btn = QPushButton("Abrir" if is_member else "Unirse")
            btn.setProperty("class", "glassBtn")
            btn.setCursor(Qt.PointingHandCursor)
            if is_member:
                btn.clicked.connect(lambda _, c=cid: self.open_community_requested.emit(c))
            else:
                btn.clicked.connect(lambda _, c=cid: self._join_public(c))
            c_lay.addWidget(btn)

            self.cards_layout.insertWidget(insert_pos, card)
            insert_pos += 1

        add_section_header("Tus comunidades")
        my_ids = {str(c.get("id")) for c in (my_communities or [])}
        if my_communities:
            for c in my_communities:
                add_card(c, is_member=True)
        else:
            empty_mine = QLabel("Todavía no perteneces a ninguna comunidad. Crea una o únete con un código de invitación.")
            empty_mine.setStyleSheet("font-size: 12px; color: #91A5B3; padding: 8px 4px;")
            self.cards_layout.insertWidget(insert_pos, empty_mine)
            insert_pos += 1

        add_section_header("Comunidades públicas disponibles")
        other_public = [c for c in (public_communities or []) if str(c.get("id")) not in my_ids]
        if other_public:
            for c in other_public:
                add_card(c, is_member=bool(c.get("is_member")))
        else:
            empty_pub = QLabel("No hay comunidades públicas nuevas para explorar.")
            empty_pub.setStyleSheet("font-size: 12px; color: #91A5B3; padding: 8px 4px;")
            self.cards_layout.insertWidget(insert_pos, empty_pub)
            insert_pos += 1

    def _join_public(self, community_id: str):
        if not self.controller:
            return
        try:
            self.controller.join_public_community(community_id)
            self.open_community_requested.emit(community_id)
        except CommunityApiError as exc:
            self.show_error(exc.message)

    def _open_join_code_dialog(self):
        if not self.controller:
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Unirse con código o enlace")
        dlg.setFixedWidth(400)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)
        code_inp = _styled_input("Ej: ABC12345 o cci://invite/ABC12345")
        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #ffb3b8; font-size: 12px;")
        err_lbl.setVisible(False)
        lay.addWidget(QLabel("Código o enlace de invitación:"))
        lay.addWidget(code_inp)
        lay.addWidget(err_lbl)

        btns = QHBoxLayout()
        cancel_b = QPushButton("Cancelar")
        cancel_b.clicked.connect(dlg.reject)
        join_b = QPushButton("Unirse")
        join_b.setStyleSheet("background: #35C8F1; color: #051624; font-weight: 800; padding: 8px 16px; border-radius: 8px;")
        btns.addStretch(1)
        btns.addWidget(cancel_b)
        btns.addWidget(join_b)
        lay.addLayout(btns)

        def submit():
            raw = code_inp.text().strip()
            if not raw:
                err_lbl.setText("Ingresá un código válido.")
                err_lbl.setVisible(True)
                return
            try:
                res = self.controller.join_by_invitation(raw)
                cid = str((res.get("community") or {}).get("id") or "")
                dlg.accept()
                if cid:
                    self.open_community_requested.emit(cid)
            except CommunityApiError as exc:
                err_lbl.setText(exc.message)
                err_lbl.setVisible(True)

        join_b.clicked.connect(submit)
        dlg.exec()

    def _render_spotify_button(self, status: dict):
        st = dict(status or {})
        if isinstance(st.get("spotify"), dict):
            st = dict(st["spotify"])
        connected = bool(st.get("connected"))
        opt_in = bool(st.get("opt_in_enabled"))
        track = st.get("current_track")
        track_title = track.get("title") if isinstance(track, dict) else (str(track or "").strip() or None)
        if connected and opt_in and track_title:
            self.spotify_btn.setText(f"🎵 {str(track_title)[:18]}")
        elif connected:
            self.spotify_btn.setText("🎵 Spotify activo" if opt_in else "🎵 Spotify (pausado)")
        else:
            self.spotify_btn.setText("🎵 Conectar Spotify")

    def _open_spotify_dialog(self):
        if not self.controller:
            return
        try:
            st = self.controller.refresh_spotify_status()
        except Exception:
            st = dict(getattr(self.controller, "spotify_status", {}) or {})
        if isinstance(st.get("spotify"), dict):
            st = dict(st["spotify"])

        dlg = QDialog(self)
        dlg.setWindowTitle("Spotify OAuth (Opt-in & Revocable)")
        dlg.setFixedWidth(440)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        connected = bool(st.get("connected"))
        display_name = st.get("display_name") or st.get("spotify_display_name") or st.get("spotify_user_id") or "Cuenta vinculada"
        track = st.get("current_track")
        track_title = track.get("title") if isinstance(track, dict) else (str(track or "").strip() or None)
        track_artist = track.get("artist") if isinstance(track, dict) else (str(st.get("current_artist") or "").strip() or None)
        track_desc = (
            f"Escuchando: {track_title} — {track_artist or ''}".strip(" —")
            if track_title
            else "Sin reproducción activa detectada."
        )
        summary_lbl = QLabel(
            f"Estado: {'Conectado (' + str(display_name) + ')' if connected else 'No vinculado'}\n"
            f"Almacenamiento seguro local: {getattr(self.controller.token_store, 'backend_name', 'keychain')}\n"
            + (track_desc if connected else "Conecta Spotify solo si deseas compartir lo que escuchas.")
        )
        summary_lbl.setWordWrap(True)
        summary_lbl.setStyleSheet("font-size: 12px; color: #bde6ff;")
        lay.addWidget(summary_lbl)

        share_chk = QCheckBox("Compartir lo que escucho en mi presencia (opt-in)")
        share_chk.setChecked(bool(st.get("share_presence", True)))
        lay.addWidget(share_chk)

        optin_chk = QCheckBox("Mantener sincronización Spotify habilitada")
        optin_chk.setChecked(bool(st.get("opt_in_enabled", True if not connected else False)))
        optin_chk.setVisible(connected)
        lay.addWidget(optin_chk)

        msg_lbl = QLabel("")
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("color: #ffb3b8; font-size: 12px;")
        msg_lbl.setVisible(False)
        lay.addWidget(msg_lbl)

        btns = QHBoxLayout()
        close_b = QPushButton("Cerrar")
        close_b.clicked.connect(dlg.reject)
        btns.addWidget(close_b)
        btns.addStretch(1)

        if not connected:
            conn_b = QPushButton("Conectar con Spotify")
            conn_b.setStyleSheet("background: #1DB954; color: #051624; font-weight: 800; padding: 8px 14px; border-radius: 8px;")

            def _do_connect():
                try:
                    self.controller.connect_spotify_via_loopback(share_presence=share_chk.isChecked())
                    dlg.accept()
                except Exception as exc:
                    msg_lbl.setText(str(exc))
                    msg_lbl.setVisible(True)

            conn_b.clicked.connect(_do_connect)
            btns.addWidget(conn_b)
        else:
            sync_b = QPushButton("Sincronizar")
            save_b = QPushButton("Guardar")
            revoke_b = QPushButton("Revocar")
            revoke_b.setStyleSheet("background: rgba(233,75,86,0.3); border: 1px solid #E94B56; color: #ffd6d9; padding: 6px 12px; border-radius: 8px;")

            def _do_sync():
                try:
                    res = self.controller.sync_spotify_playback()
                    self._render_spotify_button(res)
                    dlg.accept()
                except Exception as exc:
                    msg_lbl.setText(str(exc))
                    msg_lbl.setVisible(True)

            def _do_save():
                try:
                    res = self.controller.set_spotify_preferences(
                        opt_in_enabled=optin_chk.isChecked(),
                        share_presence=share_chk.isChecked(),
                    )
                    self._render_spotify_button(res)
                    dlg.accept()
                except Exception as exc:
                    msg_lbl.setText(str(exc))
                    msg_lbl.setVisible(True)

            def _do_revoke():
                try:
                    res = self.controller.revoke_spotify_connection()
                    self._render_spotify_button(res)
                    dlg.accept()
                except Exception as exc:
                    msg_lbl.setText(str(exc))
                    msg_lbl.setVisible(True)

            sync_b.clicked.connect(_do_sync)
            save_b.clicked.connect(_do_save)
            revoke_b.clicked.connect(_do_revoke)
            btns.addWidget(sync_b)
            btns.addWidget(save_b)
            btns.addWidget(revoke_b)

        lay.addLayout(btns)
        dlg.exec()

    def _open_create_dialog(self):
        parent_comm = self.parent()
        while parent_comm is not None and not hasattr(parent_comm, "interior_view"):
            parent_comm = parent_comm.parent()
        if parent_comm is not None and hasattr(parent_comm, "interior_view"):
            parent_comm.interior_view.open_create_community_dialog()
            if self.controller and self.controller.active_community:
                parent_comm.internal_stack.setCurrentWidget(parent_comm.interior_view)


class CommunitiesView(QWidget):
    def __init__(self, parent=None, controller: Optional[CommunityController] = None, auto_connect: bool = True):
        super().__init__(parent)
        self.controller = controller or CommunityController(parent=self)
        self._auto_connect = auto_connect
        self._bootstrapped = False
        self._prefer_explore = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 8, 36, 18)

        self.internal_stack = QStackedWidget(self)
        layout.addWidget(self.internal_stack)

        self.auth_view = CommunityAuthView(self.controller, self)
        self.explore_view = CommunityExploreView(self.controller, self)
        self.interior_view = CommunityInteriorView(self.controller, self)

        self.internal_stack.addWidget(self.auth_view)      # Index 0: Auth real JWT
        self.internal_stack.addWidget(self.explore_view)   # Index 1: Explorar / Invitaciones
        self.internal_stack.addWidget(self.interior_view)  # Index 2: Interior de Comunidad

        self.explore_view.open_community_requested.connect(self.show_interior)
        self.interior_view.back_to_explore.connect(self.show_explore)
        self.controller.session_changed.connect(self._on_session_changed)
        self.controller.community_opened.connect(self._on_community_opened)

        # Gate estricto: jamás mostrar interior ni comunidades sin sesión autenticada
        self.internal_stack.setCurrentIndex(0)

    def _on_community_opened(self, _payload: dict):
        if self.controller.session is not None:
            self.internal_stack.setCurrentWidget(self.interior_view)

    def _on_session_changed(self, sess):
        if sess is None:
            self.internal_stack.setCurrentWidget(self.auth_view)
            return

        self.internal_stack.setCurrentWidget(self.explore_view)

        def _after_comms(res):
            mine, _pub = res
            if self.controller.session is None:
                return
            if not self._prefer_explore and mine:
                target_id = (
                    str(self.controller.active_community["id"])
                    if self.controller.active_community
                    else str(mine[0]["id"])
                )
                self.controller.open_community_async(
                    target_id,
                    on_error=lambda exc: self.explore_view.show_error(exc.message),
                )
            else:
                self.controller.refresh_friends_async()
                self.controller.refresh_activity_and_notifications_async()

        self.controller.refresh_communities_async(
            on_done=_after_comms,
            on_error=lambda exc: self.explore_view.show_error(exc.message),
        )

    def activate_view(self, for_explore: bool = False):
        self._prefer_explore = for_explore
        if self.controller.session is None:
            if not self._bootstrapped and self._auto_connect:
                self._bootstrapped = True
                self.controller.restore_session_async()
            elif self._auto_connect:
                self.controller.check_backend_async(auto_start=True)
            self.internal_stack.setCurrentWidget(self.auth_view)
            return

        if for_explore:
            self.show_explore()
        else:
            self.show_interior()

    def show_interior(self, community_id: Optional[str] = None):
        if self.controller.session is None:
            self.internal_stack.setCurrentWidget(self.auth_view)
            return
        if community_id:
            self.controller.open_community_async(
                community_id,
                on_error=lambda exc: (
                    self.explore_view.show_error(exc.message),
                    self.internal_stack.setCurrentWidget(self.explore_view),
                ),
            )
            return
        if not self.controller.active_community:
            def _after_mine(res):
                mine, _ = res
                if not mine:
                    self.internal_stack.setCurrentWidget(self.explore_view)
                    return
                self.controller.open_community_async(
                    str(mine[0]["id"]),
                    on_error=lambda exc: self.explore_view.show_error(exc.message),
                )

            self.controller.refresh_communities_async(
                on_done=_after_mine,
                on_error=lambda exc: (
                    self.explore_view.show_error(exc.message),
                    self.internal_stack.setCurrentWidget(self.explore_view),
                ),
            )
            return
        self.internal_stack.setCurrentWidget(self.interior_view)

    def show_explore(self):
        if self.controller.session is None:
            self.internal_stack.setCurrentWidget(self.auth_view)
            return
        self.explore_view.refresh()
        self.internal_stack.setCurrentWidget(self.explore_view)


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
        self.profile_av_lbl = QLabel("?")
        self.profile_av_lbl.setFixedSize(64, 64)
        self.profile_av_lbl.setAlignment(Qt.AlignCenter)
        self.profile_av_lbl.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8cd7f5, stop:1 #06345a);
            border: 2px solid #ffffff;
            border-radius: 32px;
            font-size: 26px;
            font-weight: 800;
            color: #ffffff;
        """)
        head_box.addWidget(self.profile_av_lbl)

        name_box = QVBoxLayout()
        self.profile_name_lbl = QLabel("Invitado  •  Sin sesión en Comunidades")
        self.profile_name_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #ffffff;")
        self.profile_score_lbl = QLabel("Inicia sesión en la pestaña Comunidades para sincronizar tu cuenta.")
        self.profile_score_lbl.setStyleSheet("font-size: 13px; color: #ffd166; font-weight: 700;")
        name_box.addWidget(self.profile_name_lbl)
        name_box.addWidget(self.profile_score_lbl)
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

    def set_session_user(self, username: Optional[str]):
        if username:
            self.profile_av_lbl.setText(username[:1].upper())
            self.profile_name_lbl.setText(f"{username}  •  Cuenta C.C.I. conectada")
            self.profile_score_lbl.setText("Sesión activa en C.C.I. Communities")
        else:
            self.profile_av_lbl.setText("?")
            self.profile_name_lbl.setText("Invitado  •  Sin sesión en Comunidades")
            self.profile_score_lbl.setText("Inicia sesión en la pestaña Comunidades para sincronizar tu cuenta.")


# ==============================================================================
# 7. VENTANA PRINCIPAL OMNIDASH EN PYSIDE6 (OmniDashMainWindow)
# ==============================================================================
class OmniDashMainWindow(QMainWindow):
    def __init__(self, controller: Optional[CommunityController] = None, auto_connect: bool = True):
        super().__init__()
        self.setWindowTitle("C.C.I. SYSTEM — OmniDash Virtual Console (Frutiger Aero)")
        self.resize(1672, 941)
        self.setMinimumSize(1280, 720)
        self._auto_connect = auto_connect and (os.environ.get("CCI_AUTO_START_BACKEND", "1") != "0")
        self.community_controller = controller or CommunityController(parent=self)

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
        self.communities_view = CommunitiesView(
            self,
            controller=self.community_controller,
            auto_connect=self._auto_connect,
        )
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
        self.details_view.uninstall_requested.connect(self.uninstall_game_prompt)
        self.details_view.install_package_requested.connect(self.install_game_package_prompt)

        self.settings_view.wallpaper_changed.connect(self.set_wallpaper)

        self.nav_bar.notifications_clicked.connect(self.open_notifications_dialog)
        self.community_controller.notifications_updated.connect(
            lambda _notifs, unread: self.nav_bar.set_unread_notifications(unread)
        )
        self.community_controller.session_changed.connect(lambda _s: self._sync_session_ui())
        self.community_controller.communities_updated.connect(lambda _m, _p: self._sync_session_ui())
        self._sync_session_ui()
        if self._auto_connect:
            QTimer.singleShot(50, self._restore_community_session)
            QTimer.singleShot(150, self.community_controller.sync_library_games_to_watcher)

    def _restore_community_session(self):
        if self.community_controller.session is None:
            self.community_controller.restore_session_async()

    def _sync_session_ui(self):
        sess = self.community_controller.session
        uname = sess.username if sess else None
        self.nav_bar.set_session_user(uname)
        if hasattr(self.settings_view, "_settings_value_labels") and "Active Player" in self.settings_view._settings_value_labels:
            self.settings_view._settings_value_labels["Active Player"].setText(
                f"@{uname} (Sesión activa)" if uname else "Sin sesión activa (Invitado)"
            )
        self.home_view.set_session_state(
            username=uname,
            communities_count=len(self.community_controller.my_communities),
            active_streams_count=len(self.community_controller.active_streams),
        )
        self.profile_view.set_session_user(uname)

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
            self.communities_view.activate_view(for_explore=True)
        elif view_id in ("COMMUNITY", "COMMUNITIES"):
            self.communities_view.activate_view(for_explore=False)
        self.nav_bar.set_active_view(view_id)

    def open_notifications_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Notificaciones y menciones")
        dlg.setFixedWidth(440)
        dlg.setStyleSheet("QDialog { background: #0e1e2e; color: #ffffff; } QLabel { color: #ffffff; }")
        lay = QVBoxLayout(dlg)
        lay.setSpacing(10)

        if not self.community_controller.session:
            lay.addWidget(QLabel("Iniciá sesión en Comunidades para ver tus notificaciones y @menciones."))
        else:
            self.community_controller.refresh_activity_and_notifications()
            notifs = list(self.community_controller.active_notifications or [])
            if not notifs:
                lay.addWidget(QLabel("No tenés notificaciones pendientes."))
            else:
                for n in notifs[:12]:
                    prefix = "🔵 " if not n.get("is_read") else "• "
                    lbl = QLabel(f"{prefix}{n.get('title', 'Notificación')}: {n.get('body', '')}")
                    lbl.setWordWrap(True)
                    lbl.setStyleSheet("font-size: 12px; color: #dff5ff; padding: 4px; background: rgba(255,255,255,0.06); border-radius: 6px;")
                    lay.addWidget(lbl)

        btns = QHBoxLayout()
        if self.community_controller.session and self.community_controller.unread_notifications_count > 0:
            read_b = QPushButton("Marcar todas como leídas")
            read_b.clicked.connect(lambda: (self.community_controller.mark_all_notifications_read(), dlg.accept()))
            btns.addWidget(read_b)
        btns.addStretch(1)
        close_b = QPushButton("Cerrar")
        close_b.setStyleSheet("background: #35C8F1; color: #051624; font-weight: 800; padding: 8px 16px; border-radius: 8px;")
        close_b.clicked.connect(dlg.accept)
        btns.addWidget(close_b)
        lay.addLayout(btns)
        dlg.exec()

    def closeEvent(self, event):
        if hasattr(self, "community_controller") and self.community_controller:
            self.community_controller.shutdown()
        super().closeEvent(event)

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

    def _start_game_qprocess(
        self,
        title: str,
        game_id: str,
        program: str,
        arguments: list[str],
        rom_path: str | None = None,
        executable_name: str | None = None,
        cmdline_tokens: list[str] | tuple[str, ...] = (),
        warn_on_error: bool = True,
    ):
        """Lanza un juego/emulador vía QProcess y notifica su PID real al watcher de actividad."""
        proc = QProcess(self)
        proc.setWorkingDirectory(str(ROOT))
        proc.setProcessChannelMode(QProcess.MergedChannels)
        self._game_process = proc
        launched_pid: dict[str, int | None] = {"pid": None}
        session_start_ts: dict[str, float] = {"t0": time.monotonic()}

        def _on_started():
            session_start_ts["t0"] = time.monotonic()
            pid_val = int(proc.processId() or 0)
            launched_pid["pid"] = pid_val if pid_val > 0 else None
            try:
                from backend.games.storage_manager import GameStorageManager

                GameStorageManager.get_instance().record_progress(
                    game_id=game_id,
                    title=title,
                    last_played="Hoy",
                )
            except Exception:
                pass
            if hasattr(self, "community_controller") and self.community_controller:
                self.community_controller.notify_game_launched(
                    game_id=game_id,
                    title=title,
                    pid=launched_pid["pid"],
                    rom_path=rom_path,
                    executable=executable_name,
                    cmdline_tokens=cmdline_tokens,
                )

        def _on_finished(exit_code: int, exit_status):
            elapsed_s = max(1, int(time.monotonic() - session_start_ts["t0"]))
            try:
                from backend.games.storage_manager import GameStorageManager

                GameStorageManager.get_instance().record_progress(
                    game_id=game_id,
                    title=title,
                    last_played="Hoy",
                    play_time_delta_s=elapsed_s,
                )
                self.library_view.reload_library()
                if self.details_view.game and str(self.details_view.game.get("id") or "") == str(game_id):
                    from backend.games.scanner_service import GameLibraryScannerService

                    fresh_g = GameLibraryScannerService.get_instance().get_game_by_id(str(game_id))
                    if fresh_g:
                        self.details_view.load_game(fresh_g)
            except Exception:
                pass
            if hasattr(self, "community_controller") and self.community_controller:
                self.community_controller.notify_game_exited(
                    game_id=game_id,
                    title=title,
                    pid=launched_pid["pid"],
                    force=(exit_code != 0),
                )
            raw_out = bytes(proc.readAllStandardOutput()).decode("utf-8", errors="ignore").strip()
            if warn_on_error and exit_code != 0:
                err_line = raw_out.splitlines()[-1] if raw_out else f"Código de salida {exit_code}"
                print(f"[OmniDash-Qt] Error al ejecutar core para {title}: {err_line}")
                QMessageBox.warning(
                    self,
                    f"Error al ejecutar {title}",
                    f"El núcleo Libretro no pudo cargar este juego:\n{err_line}",
                )
            self._game_process = None
            proc.deleteLater()
            self.activateWindow()
            self.raise_()

        def _on_error(proc_err):
            if hasattr(self, "community_controller") and self.community_controller:
                self.community_controller.notify_game_exited(
                    game_id=game_id,
                    title=title,
                    pid=launched_pid["pid"],
                    force=True,
                )
            print(f"[OmniDash-Qt] Error de proceso lanzando {title}: {proc_err}")
            if warn_on_error:
                QMessageBox.warning(
                    self,
                    f"Error al iniciar {title}",
                    "No se pudo iniciar el proceso emulador.",
                )
            self._game_process = None
            proc.deleteLater()

        proc.started.connect(_on_started)
        proc.finished.connect(_on_finished)
        proc.errorOccurred.connect(_on_error)
        proc.start(program, arguments)
        return proc

    def uninstall_game_prompt(self, game: dict, confirm: bool = True) -> bool:
        """Desinstala el archivo del juego liberando espacio sin borrar progreso ni partidas guardadas."""
        gid = str(game.get("id") or "")
        title = game.get("title", "Juego")
        size_txt = game.get("size", "—")
        if not gid:
            return False

        if confirm:
            ans = QMessageBox.question(
                self,
                f"Liberar espacio — {title}",
                f"¿Querés desinstalar '{title}' ({size_txt}) para liberar espacio en disco?\n\n"
                "• Tus partidas guardadas y progreso se conservarán intactos en la consola.\n"
                "• El juego seguirá disponible en tu Biblioteca (En la nube) para volver a instalarlo cuando quieras.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ans != QMessageBox.Yes:
                return False

        from backend.games.storage_manager import GameStorageManager
        from backend.games.scanner_service import GameLibraryScannerService

        scanner = GameLibraryScannerService.get_instance()
        mgr = GameStorageManager.get_instance()
        ok, msg, updated = mgr.uninstall_game(gid, scanner=scanner)
        self.library_view.reload_library()
        if updated:
            self.details_view.load_game(updated)
        if confirm:
            QMessageBox.information(self, "Almacenamiento de consola", msg)
        return ok

    def install_game_package_prompt(
        self,
        game: dict,
        source_path: str | Path | None = None,
        target_os: str | None = None,
    ) -> bool:
        """Instala el juego directamente en la consola según el SO (Windows o macOS) sin abrir explorador de archivos."""
        gid = str(game.get("id") or "")
        title = game.get("title", "Juego")
        if not gid:
            return False

        from backend.games.storage_manager import GameStorageManager
        from backend.games.scanner_service import GameLibraryScannerService

        scanner = GameLibraryScannerService.get_instance()
        mgr = GameStorageManager.get_instance()
        os_prof = mgr.detect_target_os_profile(target_os)

        # Mostrar progreso de instalación nativo dentro de la consola
        if hasattr(self, "details_view") and self.details_view:
            self.details_view.install_progress_box.show()
            for pct_step, step_msg in (
                (25, f"Preparando instalación para {os_prof['os_label']}..."),
                (65, f"Instalando contenedor de consola y {os_prof['graphics_api']}..."),
                (95, "Verificando integridad y datos guardados..."),
            ):
                self.details_view.install_status_lbl.setText(step_msg)
                self.details_view.install_progress_bar.setValue(pct_step)
                QApplication.processEvents()

        if source_path is not None:
            ok, msg, updated = mgr.install_local_package(gid, source_path, scanner=scanner)
        else:
            ok, msg, updated = mgr.install_game_for_current_os(gid, scanner=scanner, target_os=target_os)

        if not ok and "Espacio insuficiente" in msg:
            if hasattr(self, "details_view") and self.details_view:
                self.details_view.install_progress_box.hide()
            ans = QMessageBox.warning(
                self,
                "Almacenamiento insuficiente",
                f"{msg}\n\n¿Querés abrir el Gestor de Almacenamiento para desinstalar otro juego sin perder su progreso?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ans == QMessageBox.Yes:
                self.library_view.open_storage_manager()
            return False

        if hasattr(self, "details_view") and self.details_view:
            self.details_view.install_progress_bar.setValue(100)
            self.details_view.install_status_lbl.setText(f"✓ Listo para jugar en {os_prof['os_label']}")
            QApplication.processEvents()

        self.library_view.reload_library()
        if updated:
            self.details_view.load_game(updated)
        return ok

    def _launch_modern_console_runner(self, game: dict):
        """Ejecuta el juego moderno instalado a 60 FPS en el runtime nativo de consola para macOS o Windows."""
        title = game.get("title", "Juego")
        gid = str(game.get("id") or title)
        console_name = game.get("console", "Consola Moderna")
        badge = game.get("badge", "PS5")
        genre = game.get("genre", "Acción / Aventura")
        cover = str(game.get("cover") or "")
        rom = str(game.get("rom") or "")
        print(f"[OmniDash-Qt] Lanzando runtime moderno C.C.I. 60 FPS para {title} [{badge}]...")
        return self._start_game_qprocess(
            title=title,
            game_id=gid,
            program=sys.executable,
            arguments=[
                str(ROOT / "modern_game_runner.py"),
                "--game-id", gid,
                "--title", title,
                "--console", console_name,
                "--badge", badge,
                "--genre", genre,
                "--cover", cover,
                "--rom", rom,
                "--width", "1280",
                "--height", "720",
            ],
            rom_path=rom,
            executable_name=None,
            cmdline_tokens=(gid, title),
            warn_on_error=True,
        )

    def launch_game(self, game: dict):
        core = game.get("core")
        rom = game.get("rom")
        exe_cmd = game.get("executable") or game.get("exe") or game.get("command")
        title = game.get("title", "Game")
        gid = str(game.get("id") or title)

        if getattr(self, "_game_process", None) and self._game_process.state() != QProcess.NotRunning:
            print(f"[OmniDash-Qt] Ya hay un juego en ejecución; cerralo antes de abrir {title}.")
            return

        if game.get("on_demand"):
            # Instalar directamente en la consola para Windows o macOS y dejarlo listo para jugar
            self.install_game_package_prompt(game)
            return

        if rom:
            rom_path = Path(str(rom)) if Path(str(rom)).is_absolute() else (ROOT / str(rom))
            is_cci_pkg = False
            if rom_path.exists():
                try:
                    with open(rom_path, "rb") as fh:
                        is_cci_pkg = fh.read(10).startswith(b"CCI_PKG_V2")
                except Exception:
                    is_cci_pkg = False

            if is_cci_pkg or not core or str(core).startswith("external:"):
                self._launch_modern_console_runner(game)
                return

        if core and rom:
            # Verificación física de integridad de ROM y núcleo Libretro (.dylib/.dll/.so)
            if game.get("id"):
                from backend.games.scanner_service import GameLibraryScannerService
                scanner = GameLibraryScannerService.get_instance()
                ok, msg = scanner.verify_game_file(str(game["id"]))
                if not ok:
                    print(f"[OmniDash-Qt] Verificación de lanzamiento para {title}: {msg}")
                    QMessageBox.information(self, f"{title} — Requiere emulador", msg)
                    return

            print(f"[OmniDash-Qt] Lanzando emulador Libretro 60 FPS en subproceso aislado: {title} ({core})...")
            self._start_game_qprocess(
                title=title,
                game_id=gid,
                program=sys.executable,
                arguments=[
                    str(ROOT / "retro_core_runner.py"),
                    "--core", str(core),
                    "--rom", str(rom),
                    "--title", f"C.C.I. SYSTEM — {title} (60 FPS)",
                    "--width", "1280",
                    "--height", "720",
                ],
                rom_path=str(rom),
                executable_name=None,
                warn_on_error=True,
            )
        elif exe_cmd:
            if isinstance(exe_cmd, (list, tuple)) and exe_cmd:
                program = str(exe_cmd[0])
                args = [str(a) for a in exe_cmd[1:]]
            else:
                program = str(exe_cmd)
                args = [str(a) for a in (game.get("args") or ())]
            prog_base = Path(program).name.lower().removesuffix(".exe").removesuffix(".app")
            generic_interps = {"python", "python3", "py", "sh", "bash", "zsh", "fish", "cmd", "node", "env"}
            safe_exe = None if prog_base in generic_interps else program
            tokens = tuple(str(t) for t in (game.get("cmdline_tokens") or ()))
            print(f"[OmniDash-Qt] Lanzando juego nativo C.C.I.: {title} ({program})...")
            self._start_game_qprocess(
                title=title,
                game_id=gid,
                program=program,
                arguments=args,
                executable_name=safe_exe,
                cmdline_tokens=tokens,
                warn_on_error=False,
            )
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
