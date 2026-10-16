import os
import random
import pygame
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_BG, COLOR_GROUND, COLOR_GROUND_LINE

class AssetManager:
    """
    Gestor centralizado de assets.
    Carga imágenes, fondos y sonidos con fallback procedural si el archivo no existe.
    """
    def __init__(self):
        self.images = {}
        self.fonts = {}

    def get_image(self, path, width=None, height=None):
        """Carga una imagen desde disco o retorna un placeholder si no existe."""
        key = (path, width, height)
        if key in self.images:
            return self.images[key]

        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                if width and height:
                    img = pygame.transform.scale(img, (width, height))
                self.images[key] = img
                return img
            except Exception as e:
                print(f"[AssetManager] Advertencia: No se pudo cargar '{path}': {e}")

        # Fallback: Superficie placeholder
        w = width if width else 100
        h = height if height else 100
        placeholder = pygame.Surface((w, h), pygame.SRCALPHA)
        placeholder.fill((100, 100, 120, 180))
        pygame.draw.rect(placeholder, (220, 220, 240), (0, 0, w, h), 2)
        self.images[key] = placeholder
        return placeholder

    def get_stage_background(self):
        """Carga un fondo de escenario real desde assets/backgrounds/ o genera fallback procedural."""
        bg_dir = os.path.join("assets", "backgrounds")

        if os.path.exists(bg_dir):
            bg_files = [f for f in os.listdir(bg_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if bg_files:
                selected_bg = os.path.join(bg_dir, random.choice(bg_files))
                return self.get_image(selected_bg, SCREEN_WIDTH, SCREEN_HEIGHT)

        # Escenario procedural fallback
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.fill(COLOR_BG)

        for y in range(0, 500):
            r = max(0, min(255, 30 + int(y * 0.05)))
            g = max(0, min(255, 30 + int(y * 0.08)))
            b = max(0, min(255, 60 + int(y * 0.1)))
            pygame.draw.line(surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        pygame.draw.rect(surface, (40, 45, 65), (100, 320, 180, 180))
        pygame.draw.rect(surface, (35, 40, 55), (350, 280, 220, 220))
        pygame.draw.rect(surface, (45, 50, 70), (700, 300, 160, 200))
        pygame.draw.rect(surface, (38, 42, 60), (950, 340, 200, 160))

        pygame.draw.rect(surface, COLOR_GROUND, (0, 500, SCREEN_WIDTH, SCREEN_HEIGHT - 500))
        pygame.draw.line(surface, COLOR_GROUND_LINE, (0, 500), (SCREEN_WIDTH, 500), 4)

        return surface

# Instancia global del gestor de assets
asset_manager = AssetManager()
