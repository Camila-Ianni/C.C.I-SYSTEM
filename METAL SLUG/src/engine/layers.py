"""
Layered Rendering System using pygame.sprite.LayeredUpdates.
Provides explicit Z-ordering and depth management for Metal Slug entities.
"""
import pygame

class RenderLayer:
    """Standard Z-order layer constants."""
    BACKGROUND = 0      # Parallax sky, sea, and distant terrain
    SCENERY = 10        # Stage background tile/strip (Mission1 background)
    PROPS = 20          # Destructible crates, barrels, stilt huts, rocks, pigs
    PICKUPS = 25        # Weapon boxes, ammo, food, prisoner rewards
    POWS = 28           # Prisoners of War
    ENEMIES = 30        # Rebel infantry, shield soldiers, flying tara
    VEHICLES = 35       # SV-001 Metal Slug Tank, Di-Cokka, R-Shobu
    BOSS = 38           # Stage Boss (Tetsuyuki)
    PLAYER = 40         # Marco / Tarma player character
    PROJECTILES = 50    # Bullets, cannon shells, rockets, enemy fire
    PARTICLES = 60      # Explosion smoke, fire, bullet sparks, blood
    FOREGROUND = 70     # Structural arches, bridge beams, foreground foliage
    HUD = 80            # Scores, life counters, weapon ammo, timer
    OVERLAY = 90        # Mission Complete banners, blackout transitions


class LayeredRenderer(pygame.sprite.LayeredUpdates):
    """
    Extends pygame.sprite.LayeredUpdates to provide camera-aware layered drawing
    and seamless integration with existing entity render loops.
    """
    def __init__(self, *sprites, **kwargs):
        super().__init__(*sprites, **kwargs)
        self._default_layer = RenderLayer.ENTITIES if hasattr(RenderLayer, 'ENTITIES') else RenderLayer.PROPS

    def add_entity(self, entity, layer=RenderLayer.PLAYER):
        """Adds any sprite or entity with an explicit RenderLayer priority."""
        if isinstance(entity, pygame.sprite.Sprite):
            self.add(entity, layer=layer)
        else:
            # Wrap non-sprite entity into a proxy sprite if needed
            self.add(EntityProxySprite(entity, layer), layer=layer)

    def draw_with_camera(self, surface, camera):
        """Draws all layered sprites honoring their Z-index with camera translation."""
        for sprite in self.sprites():
            if hasattr(sprite, 'draw'):
                sprite.draw(surface, camera)
            elif hasattr(sprite, 'image') and hasattr(sprite, 'rect'):
                sx, sy = camera.apply(sprite.rect.x, sprite.rect.y)
                surface.blit(sprite.image, (sx, sy))


class EntityProxySprite(pygame.sprite.Sprite):
    """Proxy sprite wrapper allowing arbitrary game entities to participate in LayeredUpdates."""
    def __init__(self, entity, layer):
        super().__init__()
        self.entity = entity
        self._layer = layer

    @property
    def rect(self):
        return getattr(self.entity, 'rect', getattr(getattr(self.entity, 'physics', None), 'hurtbox', pygame.Rect(0, 0, 0, 0)))

    @property
    def image(self):
        return getattr(self.entity, 'image', None)

    def draw(self, surface, camera):
        if hasattr(self.entity, 'draw'):
            self.entity.draw(surface, camera)
