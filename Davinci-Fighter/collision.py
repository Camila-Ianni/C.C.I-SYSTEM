import pygame
from effects import effect_manager
from settings import COLOR_YELLOW, COLOR_RED, COLOR_GREEN

class CollisionManager:
    """
    Gestor de colisiones entre Hitboxes y Hurtboxes con partículas, sacudida de pantalla y SFX.
    """
    @staticmethod
    def check_attack_collision(attacker, defender):
        if not attacker.active_hitbox or attacker.has_hit_target:
            return False

        if defender.state == "ko":
            return False

        if attacker.active_hitbox.colliderect(defender.rect):
            attacker.has_hit_target = True

            # Registrar golpe en el contador de combos del atacante
            if hasattr(attacker, "register_hit"):
                attacker.register_hit()
            else:
                attacker.gain_special_meter(10)

            atk = attacker.current_attack
            damage = atk.damage if atk else 10
            knockback = atk.knockback if atk else 5.0
            stun = atk.stun if atk else 15
            effects = atk.effects if atk else []

            knockback_dir = 1.0 if attacker.facing_right else -1.0

            defender.take_damage(damage, knockback * knockback_dir, stun)

            hit_x = defender.rect.centerx
            hit_y = defender.rect.centery

            # Generar estallido de partículas al golpear
            particle_color = COLOR_RED if damage > 20 else COLOR_YELLOW
            effect_manager.add_particles(hit_x, hit_y, color=particle_color, count=15)

            # Sacudida de pantalla para golpes pesados o ultimates
            if damage >= 18:
                effect_manager.trigger_screen_shake(intensity=8, duration=12)

            effect_manager.add_floating_text(f"-{damage}", hit_x, hit_y - 20, COLOR_RED if damage > 20 else COLOR_YELLOW)

            # Mostrar contador de combo visual
            hits = getattr(attacker, "combo_hits", 0)
            if hits > 1:
                atk_x = attacker.rect.centerx
                atk_y = attacker.rect.top - 20
                if hits > 4 and attacker.char_id in ("cami", "enith", "martin"):
                    effect_manager.add_floating_text(f"COMBO x{hits}! ¡ESPECIAL DESBLOQUEADO!", atk_x, atk_y, (255, 230, 40))
                    effect_manager.trigger_screen_shake(intensity=6, duration=8)
                else:
                    effect_manager.add_floating_text(f"COMBO x{hits}!", atk_x, atk_y, (255, 180, 40))

            for eff in effects:
                effect_manager.add_visual_effect(eff, defender.rect.centerx, defender.rect.centery, attacker.facing_right)

                if eff == "sql_beam":
                    effect_manager.add_floating_text("SELECT * MATCH!", hit_x, hit_y - 35, (40, 180, 255))
                    effect_manager.trigger_screen_shake(intensity=10, duration=15)
                elif eff == "snake":
                    defender.apply_status_effect("vulnerable", duration=120)
                    effect_manager.add_floating_text("VULNERABILITY FOUND!", hit_x, hit_y - 35, COLOR_GREEN)
                elif eff == "meeting":
                    defender.apply_status_effect("rooted", duration=90)
                    effect_manager.add_floating_text("REUNIÓN OBLIGATORIA", hit_x, hit_y - 35, (220, 140, 40))
                elif eff == "exception":
                    defender.apply_status_effect("error", duration=75)
                    effect_manager.add_floating_text("NullPointerException!", hit_x, hit_y - 35, COLOR_RED)
                elif eff == "req_change":
                    defender.apply_status_effect("req_changed", duration=90)
                    effect_manager.add_floating_text("REQUIREMENTS CHANGED!", hit_x, hit_y - 35, (200, 100, 240))
                elif eff in ["purple_flame", "overdrive"]:
                    effect_manager.add_floating_text("AURA VIOLETA!", hit_x, hit_y - 40, (180, 40, 255))
                    effect_manager.trigger_screen_shake(intensity=14, duration=20)
                elif eff == "cuy_swarm":
                    effect_manager.add_floating_text("¡¡ATAQUE DE CUYS!!", hit_x, hit_y - 40, (230, 140, 40))
                    effect_manager.trigger_screen_shake(intensity=12, duration=18)
                elif eff == "solar_flare":
                    effect_manager.add_floating_text("¡FURIA ANDINA SOLAR!", hit_x, hit_y - 45, (255, 180, 20))
                    effect_manager.trigger_screen_shake(intensity=16, duration=24)
                elif eff == "milk_splash":
                    effect_manager.add_floating_text("¡LLUVIA DE LECHE!", hit_x, hit_y - 40, (220, 240, 255))
                    effect_manager.trigger_screen_shake(intensity=12, duration=18)
                elif eff == "rainbow_prism":
                    effect_manager.add_floating_text("¡PRISMAS ARCOÍRIS!", hit_x, hit_y - 45, (255, 80, 220))
                    effect_manager.trigger_screen_shake(intensity=16, duration=24)
                elif eff in ["drop_table", "breach", "network", "oop", "req_final"]:
                    effect_manager.add_floating_text("ULTIMATE IMPACT!", hit_x, hit_y - 45, COLOR_RED)
                    effect_manager.trigger_screen_shake(intensity=16, duration=24)

            return True

        return False
