import pygame

class Attack:
    """
    Representa las propiedades de un ataque genérico (data-driven).
    Permite configurar daño, tiempos de startup/active/recovery, hitbox y knockback.
    """
    def __init__(
        self,
        name,
        damage=10,
        knockback=6.0,
        hitbox_offset=(60, 20),
        hitbox_size=(50, 40),
        startup=5,
        active_time=10,
        recovery=10,
        stun=15,
        effects=None
    ):
        self.name = name
        self.damage = damage
        self.knockback = knockback
        self.hitbox_offset = hitbox_offset    # (offset_x, offset_y) relativo al atacante
        self.hitbox_size = hitbox_size        # (width, height)
        self.startup = startup                # Frames antes de activar la hitbox
        self.active_time = active_time        # Duración de la hitbox activa
        self.recovery = recovery              # Frames de recuperación tras el golpe
        self.stun = stun                      # Duración de stun al oponente
        self.effects = effects or []

    @property
    def total_duration(self):
        """Retorna la duración total del ataque en frames."""
        return self.startup + self.active_time + self.recovery

    def get_hitbox_rect(self, attacker_rect, facing_right):
        """
        Calcula el pygame.Rect de la Hitbox en pantalla según la posición y orientación del atacante.
        """
        off_x, off_y = self.hitbox_offset
        w, h = self.hitbox_size

        if facing_right:
            x = attacker_rect.x + off_x
        else:
            x = attacker_rect.right - off_x - w

        y = attacker_rect.y + off_y
        return pygame.Rect(x, y, w, h)


# Ataques básicos predeterminados
DEFAULT_ATTACKS = {
    "punch_light": Attack("punch_light", damage=8, knockback=4.0, hitbox_offset=(50, 20), hitbox_size=(45, 30), startup=3, active_time=8, recovery=6, stun=10),
    "punch_heavy": Attack("punch_heavy", damage=18, knockback=8.0, hitbox_offset=(55, 15), hitbox_size=(55, 35), startup=7, active_time=12, recovery=12, stun=20),
    "kick_light": Attack("kick_light", damage=10, knockback=5.0, hitbox_offset=(50, 60), hitbox_size=(50, 35), startup=4, active_time=9, recovery=8, stun=12),
    "kick_heavy": Attack("kick_heavy", damage=22, knockback=10.0, hitbox_offset=(60, 50), hitbox_size=(60, 40), startup=9, active_time=14, recovery=15, stun=25),
}
