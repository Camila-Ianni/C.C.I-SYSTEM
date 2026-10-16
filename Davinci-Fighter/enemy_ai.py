import random
import pygame

class EnemyAI:
    """
    Inteligencia Artificial para el modo Player vs AI.
    Toma decisiones por distancia, salud, estado del jugador y aleatoriedad controlada.
    """
    def __init__(self, fighter, target_player):
        self.fighter = fighter
        self.target = target_player
        self.decision_timer = 0
        self.decision_cooldown = 15      # Toma una decisión cada ~15 frames
        self.reaction_delay = 0

    def update(self):
        """Calcula la distancia al jugador y ejecuta la acción elegida."""
        if self.fighter.state in ["hurt", "ko"]:
            return

        self.decision_timer += 1
        dist = abs(self.fighter.rect.centerx - self.target.rect.centerx)

        # Reacción ante ataques del jugador en rango cercano (Defensa)
        if self.target.current_attack and dist < 150:
            if random.random() < 0.65:    # 65% de probabilidad de bloquear ataques entrantes
                self.fighter.set_block(True)
                return
        else:
            self.fighter.set_block(False)

        # Toma de decisiones periódica
        if self.decision_timer >= self.decision_cooldown:
            self.decision_timer = 0

            # Si tiene Ultimate lista, alta probabilidad de activarla si está cerca
            if self.fighter.special_meter >= self.fighter.max_special_meter and dist < 140:
                if random.random() < 0.7:
                    self.fighter.execute_attack("ultimate")
                    return

            # Distancia Lejana: Acercarse al jugador
            if dist > 200:
                if self.fighter.rect.centerx < self.target.rect.centerx:
                    self.fighter.move_right()
                else:
                    self.fighter.move_left()

            # Distancia Media: Acercarse o iniciar salto
            elif dist > 110:
                rand_val = random.random()
                if rand_val < 0.6:
                    if self.fighter.rect.centerx < self.target.rect.centerx:
                        self.fighter.move_right()
                    else:
                        self.fighter.move_left()
                elif rand_val < 0.8:
                    self.fighter.execute_attack("special")
                else:
                    self.fighter.jump()

            # Distancia Cercana: Atacar, agacharse o retroceder
            else:
                self.fighter.stop_horizontal()
                atk_choice = random.choice(["punch_light", "punch_heavy", "kick_light", "kick_heavy", "special"])

                if random.random() < 0.8:
                    self.fighter.execute_attack(atk_choice)
                else:
                    if random.random() < 0.5:
                        self.fighter.set_crouch(True)
                    else:
                        # Retroceder brevemente
                        if self.fighter.rect.centerx < self.target.rect.centerx:
                            self.fighter.move_left()
                        else:
                            self.fighter.move_right()
