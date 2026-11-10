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
from omnidash_screens import ALL_GAMES

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

        # 1. Brand Logo C.C.I. SYSTEM (Esquina superior izquierda)
        brand_box = QHBoxLayout()
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

        # Separador vertical fino
        sep = QLabel("|")
        sep.setStyleSheet("color: rgba(255, 255, 255, 80); font-size: 24px; font-weight: 200; margin-left: 6px;")
        brand_box.addWidget(sep)

        layout.addLayout(brand_box)
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
            ("Amigos", "people", "COMMUNITY"),
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
                "fotos web/super mario.jpg",
                QColor(0, 210, 255, 190),
                QColor(0, 210, 255, 230),
            ),
            (
                "Metal Slug",
                "grid_metalslug.png",
                "fotos web/metal slug.jpg",
                QColor(255, 159, 28, 190),
                QColor(255, 159, 28, 230),
            ),
            (
                "The Legend Of Zelda",
                "grid_zelda.png",
                "fotos web/The_Legend_of_Zelda_film_logo.jpg",
                QColor(255, 215, 0, 190),
                QColor(255, 215, 0, 230),
            ),
            (
                "Donkey Kong 64",
                "grid_donkeykong.png",
                "fotos web/donkeykong.jpg",
                QColor(46, 204, 113, 190),
                QColor(46, 204, 113, 230),
            ),
            (
                "Castlevania - Symphony of the Night",
                "grid_castlevania.png",
                "fotos web/castlevania.webp",
                QColor(230, 57, 70, 190),
                QColor(230, 57, 70, 230),
            ),
            (
                "Mario Kart DS",
                "grid_mariokart.png",
                "fotos web/super mario.jpg",
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
    """Busca y resuelve la carátula en alta definición para el juego."""
    title = game.get("title", "").lower()

    priority_map = [
        ("da vinci", ROOT / "assets_omnidash" / "covers" / "elden.png"),
        ("asteroids", ROOT / "fotos web" / "asteroids.jpg"),
        ("super mario", ROOT / "fotos web" / "super mario.jpg"),
        ("zelda", ROOT / "fotos web" / "The_Legend_of_Zelda_film_logo.jpg"),
        ("pac-man", ROOT / "fotos web" / "pac man.jpg"),
        ("pacman", ROOT / "fotos web" / "pac man.jpg"),
        ("tetris", ROOT / "fotos web" / "tetris logo .jpg"),
        ("space invaders", ROOT / "fotos web" / "space nvaders.jpg"),
        ("metal slug", ROOT / "fotos web" / "metal slug.jpg"),
        ("donkey", ROOT / "fotos web" / "donkeykong.jpg"),
        ("castlevania", ROOT / "fotos web" / "castlevania.webp"),
        ("doom", ROOT / "fotos web" / "Doom_logo.png"),
        ("flappy", ROOT / "fotos web" / "Flappy_Bird_icon.png"),
        ("dino", ROOT / "fotos web" / "dino.jpg"),
        ("ghostbusters", ROOT / "fotos web" / "ghostbusters.webp"),
        ("street fighter", ROOT / "fotos web" / "Street_Fighter_old_logo.png"),
        ("megaman", ROOT / "fotos web" / "megaman.jpg"),
        ("pokemon", ROOT / "fotos web" / "pokemon.webp"),
        ("bratz", ROOT / "roms/nds/6148 - Bratz Fashion Boutique (U)(frieNDS).jpg"),
        ("lego", ROOT / "roms/nds/1633 - Cover.png"),
        ("star wars", ROOT / "roms/nds/1633 - Cover.png"),
        ("god of war", ROOT / "assets_omnidash/covers/god.png"),
        ("barbie", ROOT / "assets_omnidash/covers/sega.webp"),
        ("disney", ROOT / "assets_omnidash/covers/far-cry.webp"),
        ("simpsons", ROOT / "assets_omnidash/covers/battlefield.webp"),
    ]
    for key, path in priority_map:
        if key in title and path.exists():
            return QPixmap(str(path))

    cov = game.get("cover")
    if cov and (ROOT / cov).exists():
        return QPixmap(str(ROOT / cov))

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
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(scroll_content)
        self.grid.setHorizontalSpacing(20)
        self.grid.setVerticalSpacing(18)
        self.grid.setContentsMargins(6, 4, 12, 6)
        self.scroll.setWidget(scroll_content)
        content_layout.addWidget(self.scroll)

        layout.addWidget(self.content_panel, 1)

        self._populate_grid(self._get_prioritized_games(ALL_GAMES))

    def _get_prioritized_games(self, games: list[dict]) -> list[dict]:
        """Ordena los 8 juegos emblemáticos en la cuadrícula 4x2 inicial según la referencia."""
        top_order = [
            "da vinci",
            "asteroids",
            "super mario",
            "zelda",
            "pac-man",
            "tetris",
            "space invaders",
            "metal slug"
        ]
        priority_games = []
        remaining_games = []
        for target in top_order:
            found = next((g for g in games if target in g.get("title", "").lower() and g not in priority_games), None)
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
        query = self.search_input.text().lower().strip()
        filtered = []
        code = self.current_plat_code
        for g in ALL_GAMES:
            title = g.get("title", "").lower()
            console = g.get("console", "").lower()
            badge = g.get("badge", "").lower()
            if not code or code == "todas":
                plat_match = True
            elif code == "snes":
                plat_match = ("super" in console or "snes" in console or badge == "snes")
            elif code == "arcade":
                plat_match = ("arcade" in console or "mame" in console or badge == "arcade")
            elif code == "n64":
                plat_match = ("64" in console or badge == "n64")
            elif code == "ps1":
                plat_match = ("playstation" in console or "ps1" in console or badge == "ps1")
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

            query_match = not query or (query in title) or (query in console)
            if plat_match and query_match:
                filtered.append(g)

        self.count_label.setText(f"{self.current_plat_name} ({len(filtered)} disponibles)")
        if code == "todas" and not query:
            filtered = self._get_prioritized_games(filtered)
        self._populate_grid(filtered)

    def _populate_grid(self, games: list[dict]):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.grid_cards = []
        self.grid_games = games
        self.selected_idx = 0

        cols = 4
        for idx, g in enumerate(games):
            card = LibraryGameCard(g, self)
            card.mousePressEvent = lambda _, gm=g: self.open_game.emit(gm)
            row = idx // cols
            col = idx % cols
            self.grid.addWidget(card, row, col)
            self.grid_cards.append(card)

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
            card = LibraryGameCard(g, self)
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
            "FRIENDS": 4,
            "PROFILE": 5,
        }
        idx = mapping.get(view_id, 0)
        self.stack.setCurrentIndex(idx)
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
