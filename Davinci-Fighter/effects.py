import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_WHITE, COLOR_YELLOW, COLOR_RED, COLOR_GREEN

class Particle:
    """Partícula visual dinámica (chispas, polvo, humo)."""
    def __init__(self, x, y, vx, vy, color, size=4, lifetime=20):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.size = max(1, self.size - 0.1)
        self.lifetime -= 1

    def draw(self, screen, camera_x=0):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            r, g, b = self.color[:3]
            pygame.draw.circle(surf, (r, g, b, alpha), (int(self.size), int(self.size)), int(self.size))
            screen_x = self.x - camera_x
            screen.blit(surf, (int(screen_x - self.size), int(self.y - self.size)))


class FloatingText:
    """Texto flotante temporal para daño o nombres de habilidades."""
    def __init__(self, text, x, y, color=COLOR_YELLOW, lifetime=45, velocity_y=-1.5):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.velocity_y = velocity_y

    def update(self):
        self.y += self.velocity_y
        self.lifetime -= 1

    def draw(self, screen, font, camera_x=0):
        if self.lifetime > 0:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            txt_surf = font.render(self.text, True, self.color)

            temp_surf = pygame.Surface(txt_surf.get_size(), pygame.SRCALPHA)
            temp_surf.blit(txt_surf, (0, 0))
            temp_surf.set_alpha(alpha)

            screen_x = self.x - camera_x
            screen.blit(temp_surf, (int(screen_x - txt_surf.get_width() // 2), int(self.y)))


class VisualEffect:
    """Efecto visual en pantalla (rayos, explosiones, cuadros de código)."""
    def __init__(self, effect_type, x, y, facing_right=True, duration=30):
        self.effect_type = effect_type
        self.x = x
        self.y = y
        self.facing_right = facing_right
        self.duration = duration
        self.max_duration = duration

    def update(self):
        self.duration -= 1

    def draw(self, screen, camera_x=0):
        if self.duration <= 0:
            return

        progress = 1.0 - (self.duration / self.max_duration)
        screen_x = self.x - camera_x

        if self.effect_type == "sql_beam":
            w = int(220 * progress) + 60
            h = 45
            rect_x = screen_x if self.facing_right else screen_x - w
            pygame.draw.rect(screen, (40, 180, 255, 180), (rect_x, self.y, w, h))
            pygame.draw.rect(screen, COLOR_WHITE, (rect_x, self.y, w, h), 2)

        elif self.effect_type == "snake":
            for i in range(6):
                offset = (i * 25 * (1 if self.facing_right else -1))
                pygame.draw.circle(screen, (50, 220, 80), (int(screen_x + offset), int(self.y + (i % 2) * 12)), 14)

        elif self.effect_type == "meeting":
            rect = pygame.Rect(screen_x - 70, self.y - 45, 140, 90)
            pygame.draw.rect(screen, (220, 140, 40), rect)
            pygame.draw.rect(screen, COLOR_WHITE, rect, 3)

        elif self.effect_type == "exception":
            font = pygame.font.Font(None, 30)
            txt = font.render("NullPointerException!", True, COLOR_RED)
            screen.blit(txt, (screen_x - txt.get_width() // 2, self.y - 30))

        elif self.effect_type == "req_change":
            font = pygame.font.Font(None, 28)
            txt = font.render("REQUIREMENTS CHANGED!", True, (200, 100, 240))
            screen.blit(txt, (screen_x - txt.get_width() // 2, self.y - 40))


class EffectManager:
    """
    Gestor global de partículas, textos flotantes, efectos visuales y Screen Shake.
    """
    def __init__(self):
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)
        self.particles = []
        self.floating_texts = []
        self.visual_effects = []
        self.shake_intensity = 0
        self.shake_timer = 0

    def add_particles(self, x, y, color=COLOR_YELLOW, count=12):
        for _ in range(count):
            vx = random.uniform(-6, 6)
            vy = random.uniform(-6, 2)
            size = random.uniform(3, 7)
            lifetime = random.randint(15, 30)
            self.particles.append(Particle(x, y, vx, vy, color, size, lifetime))

    def trigger_screen_shake(self, intensity=8, duration=15):
        self.shake_intensity = intensity
        self.shake_timer = duration

    def get_shake_offset(self):
        if self.shake_timer > 0:
            dx = random.randint(-self.shake_intensity, self.shake_intensity)
            dy = random.randint(-self.shake_intensity, self.shake_intensity)
            return dx, dy
        return 0, 0

    def add_floating_text(self, text, x, y, color=COLOR_YELLOW):
        self.floating_texts.append(FloatingText(text, x, y, color))

    def add_visual_effect(self, effect_type, x, y, facing_right=True):
        self.visual_effects.append(VisualEffect(effect_type, x, y, facing_right))

    def update(self):
        if self.shake_timer > 0:
            self.shake_timer -= 1
            if self.shake_timer <= 0:
                self.shake_intensity = 0

        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.lifetime > 0]

        for ft in self.floating_texts:
            ft.update()
        self.floating_texts = [ft for ft in self.floating_texts if ft.lifetime > 0]

        for ve in self.visual_effects:
            ve.update()
        self.visual_effects = [ve for ve in self.visual_effects if ve.duration > 0]

    def draw(self, screen, camera_x=0):
        for p in self.particles:
            p.draw(screen, camera_x)

        for ve in self.visual_effects:
            ve.draw(screen, camera_x)

        for ft in self.floating_texts:
            ft.draw(screen, self.font, camera_x)

# Instancia global del gestor de efectos
effect_manager = EffectManager()
