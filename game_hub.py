"""game_hub.py - Ficha detallada interactiva del juego (PS5-Style Game Hub) para C.C.I. System."""
from __future__ import annotations

import math
import time
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent

# Mapeo exhaustivo de controles reales y tips pro para los 19 juegos del catálogo
GAME_CONTROLS: dict[str, dict[str, str]] = {
    "davinci": {
        "move": "W / A / S / D  o  Flechas",
        "action1": "U / I / O  (Golpes débil / medio / fuerte)",
        "action2": "J / K / L  (Patadas débil / media / fuerte)",
        "pause": "Enter  o  P",
        "tip": "Combos especiales: Abajo + Adelante + Golpe para ataques de poder.",
    },
    "asteroids": {
        "move": "Flecha Arriba (Empuje del propulsor)",
        "action1": "Flechas Izq / Der (Rotar nave espacial)",
        "action2": "Espacio  o  Botón A (Disparar cañón láser)",
        "pause": "Enter  o  ESC",
        "tip": "Aprovecha la inercia en gravedad cero para disparar en retroceso.",
    },
    "mario": {
        "move": "Flechas Izq / Der  (Mover)  ·  Flecha Abajo (Agacharse / Tubos)",
        "action1": "Espacio / Z / Botón A  (Salto / Salto alto)",
        "action2": "X / Shift / Botón B  (Correr rápido / Bola de fuego)",
        "pause": "Enter  o  P",
        "tip": "Mantén presionado correr antes de saltar para cruzar abismos largos.",
    },
    "zelda": {
        "move": "W / A / S / D  o  Flechas Direccionales",
        "action1": "Espacio / J / Botón A  (Ataque con Espada)",
        "action2": "K / E / Botón B  (Objeto secundario: Bumerán, Bombas)",
        "pause": "Enter  o  ESC  (Abrir inventario de Hyrule)",
        "tip": "Explora los límites del mapa y quema arbustos sospechosos.",
    },
    "pacman": {
        "move": "Flechas Direccionales  (Arriba / Abajo / Izq / Der)",
        "action1": "Automático  (Come pac-dots en el laberinto)",
        "action2": "—",
        "pause": "P  o  ESC",
        "tip": "Come las bolas de poder grandes para volver azules a los fantasmas.",
    },
    "tetris": {
        "move": "Flechas Izq / Der (Mover pieza lateralmente)",
        "action1": "Flecha Arriba / Z  (Rotar tetrimino 90°)",
        "action2": "Flecha Abajo / Espacio  (Caída suave / Caída dura)",
        "pause": "P  o  ESC",
        "tip": "Acumula el bloque alargado vertical para limpiar 4 líneas ('Tetris').",
    },
    "space_invaders": {
        "move": "Flechas Izquierda / Derecha  (Mover cañón de defensa)",
        "action1": "Espacio  o  Botón A  (Disparar proyectil defensivo)",
        "action2": "—",
        "pause": "P  o  ESC",
        "tip": "Usa las 4 bases de búnkeres para cubrirte de los disparos alienígenas.",
    },
    "metalslug": {
        "move": "W / A / S / D  o  Flechas Direccionales",
        "action1": "J / Espacio / Botón A  (Disparar ametralladora pesada)",
        "action2": "K (Salto)  ·  L (Lanzar Granada explosiva)",
        "pause": "Enter  o  P",
        "tip": "Súbete a tanques y vehículos SV-001 para duplicar tu potencia de fuego.",
    },
    "doom": {
        "move": "W / A / S / D  (Desplazarse hacia adelante / atrás / strafe)",
        "action1": "Flechas / Ratón  (Girar cámara / Apuntar)",
        "action2": "Espacio / Clic Izq (Disparar)  ·  E (Abrir puertas e interruptores)",
        "pause": "ESC  (Pausa y menú de opciones)",
        "tip": "Mantente en constante movimiento lateral para esquivar bolas de fuego.",
    },
    "flappy": {
        "move": "Espacio / Flecha Arriba / Clic Izquierdo  (Aletear)",
        "action1": "Espacio  (Impulso vertical del ave)",
        "action2": "—",
        "pause": "P  o  ESC",
        "tip": "Mantén toques breves y rítmicos; no spamees para no estrellarte.",
    },
    "dino": {
        "move": "Espacio / Flecha Arriba  (Saltar cactus y pterodáctilos)",
        "action1": "Flecha Abajo  (Agacharse bajo obstáculos aéreos)",
        "action2": "—",
        "pause": "P  o  ESC",
        "tip": "La velocidad se incrementa progresivamente cada 100 metros.",
    },
    "ghostbusters": {
        "move": "Flechas Izq / Der  (Mover cazafantasmas)",
        "action1": "Espacio / Z / Botón A  (Saltar plataformas)",
        "action2": "X (Disparar Rayo de Protones)  ·  C (Lanzar Trampa)",
        "pause": "Enter  o  ESC",
        "tip": "Debilita a los fantasmas con el rayo antes de desplegar la trampa.",
    },
    "cyberpunk": {
        "move": "A / D  o  Flechas  (Mover)  ·  S / Abajo (Agacharse)",
        "action1": "Espacio / Botón A  (Salto / Doble salto)",
        "action2": "J / Clic (Disparo de plasma)  ·  K / Shift (Dash cyberpunk)",
        "pause": "Enter  o  ESC",
        "tip": "Salta contra paredes verticales para realizar wall-jump continuo.",
    },
    "pokemon": {
        "move": "Flechas Direccionales  (Caminar por la hierba y pueblos)",
        "action1": "Z / Espacio / Botón A  (Hablar / Interactuar / Aceptar)",
        "action2": "X / Botón B (Cancelar / Correr)  ·  Enter (Mochila / Menú)",
        "pause": "Enter  (Guardar partida en el menú)",
        "tip": "Guarda tu progreso periódicamente antes de enfrentarte a líderes de gimnasio.",
    },
    "megaman": {
        "move": "Flechas Izquierda / Derecha  (Mover Robot)",
        "action1": "Z / Espacio / Botón A  (Saltar plataformas)",
        "action2": "X / J / Botón B  (Mega Buster / Mantener para tiro cargado)",
        "pause": "Enter  (Pausar y cambiar de arma especial)",
        "tip": "Derrota a los jefes para obtener sus armas y explotar debilidades.",
    },
    "castlevania": {
        "move": "Flechas Izquierda / Derecha  (Mover cazador de vampiros)",
        "action1": "X / Espacio / Botón A  (Saltar escalones y zanjas)",
        "action2": "Z (Látigo Vampire Killer)  ·  Arriba + Z (Arma secundaria)",
        "pause": "Enter  (Pausa)",
        "tip": "Golpea las velas con el látigo para recoger corazones y dagas.",
    },
    "bubblebobble": {
        "move": "Flechas Izq / Der  o  A / D  (Mover dragoncito)",
        "action1": "Espacio / Z / Botón A  (Saltar entre plataformas)",
        "action2": "X / Alt / Botón B  (Lanzar burbujas mágicas)",
        "pause": "Enter  o  P",
        "tip": "Encierra a los monstruos en burbujas y salta sobre ellas para reventarlas.",
    },
    "plantsvszombies": {
        "move": "Ratón / Touchpad  (Mover cursor por el jardín)",
        "action1": "Clic Izquierdo  (Elegir semilla, plantar y recoger soles)",
        "action2": "Clic en la Pala  (Remover plantas indeseadas)",
        "pause": "ESC  o  Botón de Pausa superior derecho",
        "tip": "Coloca dos columnas de Girasoles al inicio para asegurar flujo de sol continuo.",
    },
    "donkeykong": {
        "move": "Flechas Izq / Der (Mover)  ·  Arriba / Abajo (Subir/bajar escaleras)",
        "action1": "Espacio / Botón A  (Saltar barriles rodantes)",
        "action2": "Automático  (Destruir barriles al tomar el martillo)",
        "pause": "Enter  o  ESC",
        "tip": "No intentes saltar mientras estés sobre escaleras; calcula cada salto con anticipación.",
    },
}


class GameHubModal:
    """Modal interactivo tipo PS5 Game Hub que muestra ficha, controles, estadísticas y botón jugar."""

    def __init__(self):
        self.active = False
        self.game: dict | None = None
        self.user_data = None
        self.game_art: pygame.Surface | None = None
        self.font_title: pygame.font.Font | None = None
        self.font_subtitle: pygame.font.Font | None = None
        self.font_body: pygame.font.Font | None = None
        self.font_bold: pygame.font.Font | None = None
        self.font_small: pygame.font.Font | None = None
        self.btn_play_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_fav_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_close_rect = pygame.Rect(0, 0, 0, 0)
        self.anim_time = 0.0

    def open(self, game: dict, user_data, game_art: pygame.Surface | None = None):
        self.active = True
        self.game = game
        self.user_data = user_data
        self.game_art = game_art
        self.anim_time = 0.0

    def close(self):
        self.active = False
        self.game = None

    def is_open(self) -> bool:
        return self.active and self.game is not None

    def _ensure_fonts(self):
        if self.font_title is None:
            self.font_title = pygame.font.SysFont("Helvetica,Arial", 22, bold=True)
            self.font_subtitle = pygame.font.SysFont("Helvetica,Arial", 13)
            self.font_body = pygame.font.SysFont("Helvetica,Arial", 12)
            self.font_bold = pygame.font.SysFont("Helvetica,Arial", 12, bold=True)
            self.font_small = pygame.font.SysFont("Helvetica,Arial", 10)

    def handle_event(self, event: pygame.event.Event) -> str | None:
        """Devuelve 'play', 'favorite', 'close' o None."""
        if not self.is_open():
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return "close"
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return "play"
            if event.key in (pygame.K_f, pygame.K_y):
                return "favorite"

        elif event.type == pygame.JOYBUTTONDOWN:
            if event.button == 0:  # A / Cruz
                return "play"
            if event.button in (1, 6):  # B / Círculo o Back
                self.close()
                return "close"
            if event.button == 3:  # Y / Triángulo
                return "favorite"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.btn_play_rect.collidepoint(pos):
                return "play"
            if self.btn_fav_rect.collidepoint(pos):
                return "favorite"
            if self.btn_close_rect.collidepoint(pos):
                self.close()
                return "close"
            # Clic fuera del modal cierra
            modal_rect = pygame.Rect(140, 50, 1000, 620)
            if not modal_rect.collidepoint(pos):
                self.close()
                return "close"

        return None

    def update(self, dt: float):
        if self.active:
            self.anim_time += dt

    def draw(self, screen: pygame.Surface):
        if not self.is_open():
            return
        self._ensure_fonts()
        sw, sh = screen.get_size()

        # 1. Telón translúcido de fondo
        shade = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shade.fill((3, 5, 8, 220))
        screen.blit(shade, (0, 0))

        # 2. Marco principal estilo PS5 Card
        mw, mh = 980, 610
        mx = (sw - mw) // 2
        my = (sh - mh) // 2
        modal_rect = pygame.Rect(mx, my, mw, mh)

        # Fondo del card con sutil degradado visual
        pygame.draw.rect(screen, (13, 16, 24), modal_rect, border_radius=12)
        # Borde cian PS5 con pulsación suave
        pulse = 1 + int(math.sin(self.anim_time * 4.0) * 1)
        pygame.draw.rect(screen, (0, 229, 255), modal_rect, 2 + pulse, border_radius=12)

        game = self.game
        gid = game.get("id", "")
        title = game.get("title", "JUEGO")
        developer = game.get("developer", "C.C.I. System")
        year = str(game.get("year", "2026"))
        genre = game.get("genre", "Arcade")
        players = str(game.get("players", "1"))
        subtitle = game.get("subtitle", "")

        # 3. Header Hero: Carátula destacada y Título
        header_h = 135
        header_rect = pygame.Rect(mx + 15, my + 15, mw - 30, header_h)
        pygame.draw.rect(screen, (19, 24, 36), header_rect, border_radius=8)
        pygame.draw.rect(screen, (35, 45, 65), header_rect, 1, border_radius=8)

        # Carátula en miniatura
        thumb_rect = pygame.Rect(header_rect.x + 12, header_rect.y + 10, 200, 115)
        pygame.draw.rect(screen, (8, 10, 15), thumb_rect, border_radius=6)
        if self.game_art is not None:
            # Escalar conservando proporción
            gw, gh = self.game_art.get_size()
            scale = min((thumb_rect.w - 4) / gw, (thumb_rect.h - 4) / gh)
            nw, nh = max(1, int(gw * scale)), max(1, int(gh * scale))
            scaled = pygame.transform.smoothscale(self.game_art, (nw, nh))
            screen.blit(scaled, scaled.get_rect(center=thumb_rect.center))
        pygame.draw.rect(screen, (0, 229, 255), thumb_rect, 1, border_radius=6)

        # Datos del Header
        tx = thumb_rect.right + 20
        # Badges superiores
        badge_y = header_rect.y + 14
        badges = [f"AÑO {year}", genre.upper(), f"{players} JUGADOR{'ES' if players != '1' else ''}"]
        bx = tx
        for b in badges:
            b_surf = self.font_small.render(b, True, (0, 229, 255))
            bw = b_surf.get_width() + 12
            b_box = pygame.Rect(bx, badge_y, bw, 20)
            pygame.draw.rect(screen, (10, 28, 48), b_box, border_radius=4)
            pygame.draw.rect(screen, (0, 229, 255), b_box, 1, border_radius=4)
            screen.blit(b_surf, (bx + 6, badge_y + 3))
            bx += bw + 8

        # Badge de favorito si aplica
        is_fav = False
        if self.user_data:
            favorites = self.user_data.data.get("favorites", [])
            is_fav = gid in favorites
        if is_fav:
            fav_surf = self.font_small.render("★ EN FAVORITOS", True, (255, 215, 0))
            fb_w = fav_surf.get_width() + 12
            fb_box = pygame.Rect(bx, badge_y, fb_w, 20)
            pygame.draw.rect(screen, (40, 34, 10), fb_box, border_radius=4)
            pygame.draw.rect(screen, (255, 215, 0), fb_box, 1, border_radius=4)
            screen.blit(fav_surf, (bx + 6, badge_y + 3))

        # Título principal
        title_surf = self.font_title.render(title, True, (246, 247, 249))
        screen.blit(title_surf, (tx, badge_y + 28))

        # Desarrollador y subtítulo
        dev_surf = self.font_subtitle.render(f"Desarrollado por {developer}  ·  C.C.I. Virtual Console Collection", True, (160, 168, 182))
        screen.blit(dev_surf, (tx, badge_y + 62))
        sub_surf = self.font_body.render(f'"{subtitle}"', True, (210, 215, 225))
        screen.blit(sub_surf, (tx, badge_y + 86))

        # 4. Dos Columnas: Controles (Izquierda) y Estadísticas PS5 (Derecha)
        col_y = header_rect.bottom + 15
        col_w = (mw - 45) // 2
        col_h = 360

        # --- COLUMNA IZQUIERDA: CONTROLES / CÓMO JUGAR ---
        left_rect = pygame.Rect(mx + 15, col_y, col_w, col_h)
        pygame.draw.rect(screen, (16, 20, 30), left_rect, border_radius=8)
        pygame.draw.rect(screen, (40, 50, 70), left_rect, 1, border_radius=8)

        # Título sección
        ctrl_title = self.font_bold.render("🎮 GUÍA DE CONTROLES (CÓMO JUGAR)", True, (0, 229, 255))
        screen.blit(ctrl_title, (left_rect.x + 14, left_rect.y + 12))

        # Obtener mapeo de controles
        controls = GAME_CONTROLS.get(gid, {
            "move": "Flechas Direccionales / D-Pad / Stick",
            "action1": "Espacio / Botón A (Acción principal)",
            "action2": "Z / X / Botón B (Acción secundaria)",
            "pause": "Enter / ESC / Start (Pausa)",
            "tip": "Combina movimientos y botones para avanzar.",
        })

        items = [
            ("🕹️ MOVIMIENTO", controls["move"]),
            ("🅰️ ACCIÓN 1", controls["action1"]),
            ("🅱️ ACCIÓN 2", controls["action2"]),
            ("⏸️ MENÚ / PAUSA", controls["pause"]),
        ]

        cy = left_rect.y + 40
        for label, val in items:
            box = pygame.Rect(left_rect.x + 12, cy, left_rect.w - 24, 48)
            pygame.draw.rect(screen, (10, 13, 20), box, border_radius=5)
            pygame.draw.rect(screen, (28, 36, 52), box, 1, border_radius=5)

            lbl_surf = self.font_bold.render(label, True, (0, 229, 255))
            screen.blit(lbl_surf, (box.x + 10, box.y + 6))

            val_surf = self.font_body.render(val, True, (230, 235, 245))
            screen.blit(val_surf, (box.x + 10, box.y + 26))
            cy += 54

        # Caja de Consejo Pro
        tip_box = pygame.Rect(left_rect.x + 12, cy, left_rect.w - 24, 64)
        pygame.draw.rect(screen, (20, 25, 38), tip_box, border_radius=5)
        pygame.draw.rect(screen, (0, 229, 255), tip_box, 1, border_radius=5)
        tip_lbl = self.font_bold.render("💡 CONSEJO PRO:", True, (255, 215, 0))
        screen.blit(tip_lbl, (tip_box.x + 10, tip_box.y + 7))
        tip_text = controls.get("tip", "")
        # wrap
        words = tip_text.split()
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if self.font_small.size(test)[0] < tip_box.w - 20:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        for i, l in enumerate(lines[:2]):
            s = self.font_small.render(l, True, (210, 215, 225))
            screen.blit(s, (tip_box.x + 10, tip_box.y + 26 + i * 16))

        # --- COLUMNA DERECHA: ESTADÍSTICAS PS5 & LOGROS ---
        right_rect = pygame.Rect(left_rect.right + 15, col_y, col_w, col_h)
        pygame.draw.rect(screen, (16, 20, 30), right_rect, border_radius=8)
        pygame.draw.rect(screen, (40, 50, 70), right_rect, 1, border_radius=8)

        stat_title = self.font_bold.render("🏆 ESTADÍSTICAS DEL JUGADOR (PS5 HUB)", True, (0, 229, 255))
        screen.blit(stat_title, (right_rect.x + 14, right_rect.y + 12))

        # Datos reales del usuario
        stats = {}
        if self.user_data:
            stats = self.user_data.data.get("game_stats", {}).get(gid, {})
        seconds = int(stats.get("seconds", 0))
        h, m = divmod(seconds // 60, 60)
        launches = int(stats.get("launches", 0))
        progress = int(stats.get("progress", 0))
        last_played = stats.get("last_played", "Nunca")

        stat_boxes = [
            ("⏱️ TIEMPO JUGADO", f"{h:02d}h {m:02d}m acumulados"),
            ("🎮 PARTIDAS INICIADAS", f"{launches} sesiones registradas"),
            ("📅 ÚLTIMA SESIÓN", str(last_played).replace("T", " ")),
        ]

        sy = right_rect.y + 40
        for label, val in stat_boxes:
            box = pygame.Rect(right_rect.x + 12, sy, right_rect.w - 24, 48)
            pygame.draw.rect(screen, (10, 13, 20), box, border_radius=5)
            pygame.draw.rect(screen, (28, 36, 52), box, 1, border_radius=5)

            lbl_surf = self.font_bold.render(label, True, (0, 229, 255))
            screen.blit(lbl_surf, (box.x + 10, box.y + 6))

            val_surf = self.font_body.render(val, True, (230, 235, 245))
            screen.blit(val_surf, (box.x + 10, box.y + 26))
            sy += 54

        # Caja de Progreso y Trofeos
        prog_box = pygame.Rect(right_rect.x + 12, sy, right_rect.w - 24, 120)
        pygame.draw.rect(screen, (10, 13, 20), prog_box, border_radius=5)
        pygame.draw.rect(screen, (28, 36, 52), prog_box, 1, border_radius=5)

        # Logros de este juego
        game_ach_unlocked = 0
        game_ach_total = 5
        if self.user_data:
            for item in self.user_data.achievement_rows():
                if item.get("game_id") == gid:
                    if item.get("unlocked"):
                        game_ach_unlocked += 1

        p_lbl = self.font_bold.render("🥇 PROGRESO DE TROFEOS Y MAESTRÍA", True, (0, 229, 255))
        screen.blit(p_lbl, (prog_box.x + 10, prog_box.y + 10))

        trophy_stat = self.font_body.render(f"{game_ach_unlocked} de {game_ach_total} Logros desbloqueados ({int(game_ach_unlocked / game_ach_total * 100)}%)", True, (240, 240, 240))
        screen.blit(trophy_stat, (prog_box.x + 10, prog_box.y + 34))

        # Barra de progreso estética con gradiente cian
        bar_w = prog_box.w - 20
        bar_rect = pygame.Rect(prog_box.x + 10, prog_box.y + 60, bar_w, 14)
        pygame.draw.rect(screen, (20, 24, 34), bar_rect, border_radius=7)
        fill_w = int(bar_w * (game_ach_unlocked / game_ach_total))
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.h)
            pygame.draw.rect(screen, (0, 229, 255), fill_rect, border_radius=7)
        pygame.draw.rect(screen, (80, 95, 115), bar_rect, 1, border_radius=7)

        # Meta de 4 Horas
        meta_surf = self.font_small.render(f"Meta de Dominio (4 Horas): {progress}% completado", True, (150, 160, 175))
        screen.blit(meta_surf, (prog_box.x + 10, prog_box.y + 86))

        # 5. Barra de Acciones Inferior (Footer)
        footer_y = my + mh - 68
        # Botón JUGAR AHORA
        self.btn_play_rect = pygame.Rect(mx + 25, footer_y, 240, 48)
        pygame.draw.rect(screen, (0, 200, 235), self.btn_play_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 255, 255), self.btn_play_rect, 2, border_radius=8)
        play_lbl = self.font_title.render("▶  JUGAR AHORA", True, (10, 12, 16))
        screen.blit(play_lbl, play_lbl.get_rect(center=self.btn_play_rect.center))

        # Botón FAVORITO
        self.btn_fav_rect = pygame.Rect(self.btn_play_rect.right + 20, footer_y, 220, 48)
        pygame.draw.rect(screen, (24, 30, 45), self.btn_fav_rect, border_radius=8)
        pygame.draw.rect(screen, (255, 215, 0) if is_fav else (80, 95, 120), self.btn_fav_rect, 2, border_radius=8)
        fav_text = "★ QUITAR FAVORITO" if is_fav else "☆ AGREGAR FAVORITO"
        fav_lbl = self.font_bold.render(fav_text, True, (255, 215, 0) if is_fav else (220, 225, 235))
        screen.blit(fav_lbl, fav_lbl.get_rect(center=self.btn_fav_rect.center))

        # Botón VOLVER / CERRAR
        self.btn_close_rect = pygame.Rect(mx + mw - 180, footer_y, 155, 48)
        pygame.draw.rect(screen, (24, 28, 38), self.btn_close_rect, border_radius=8)
        pygame.draw.rect(screen, (100, 110, 125), self.btn_close_rect, 1, border_radius=8)
        close_lbl = self.font_bold.render("✕  VOLVER (ESC)", True, (200, 205, 215))
        screen.blit(close_lbl, close_lbl.get_rect(center=self.btn_close_rect.center))
