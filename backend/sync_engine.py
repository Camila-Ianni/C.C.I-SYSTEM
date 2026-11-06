"""
backend/sync_engine.py - Motor de simulación autoritativa y sincronización de estado.
Maneja paso de tiempo fijo (60 Hz), buffers de entradas de jugadores y cálculo de snapshots.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pygame
from backend.contracts import PlayerInputPacket, WorldSnapshotPacket


@dataclass
class FighterSimState:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    hp: int = 100
    state: str = "idle"  # idle, walk, punch_light, punch_heavy, kick_light, kick_heavy, hit, block, ko
    facing_right: bool = True
    stun_frames: int = 0
    attack_frame: int = 0
    active_attack: Optional[str] = None
    is_blocking: bool = False

    @property
    def hurtbox(self) -> pygame.Rect:
        """Caja de daño real del luchador (80x180 px centrada en el eje vertical)."""
        return pygame.Rect(int(self.x - 40), int(self.y - 180), 80, 180)

    def get_hitbox(self) -> Optional[pygame.Rect]:
        """Caja de golpe activa según el ataque y la orientación del luchador."""
        if not self.active_attack:
            return None

        # Especificaciones reales extraídas de Davinci-Fighter/attack.py
        hitbox_data = {
            "punch_light": (80, 50, 1, 14, 10),     # (w, h, startup, active, damage)
            "punch_heavy": (90, 55, 3, 16, 20),
            "kick_light": (80, 50, 1, 14, 12),
            "kick_heavy": (95, 55, 3, 20, 24),
        }

        data = hitbox_data.get(self.active_attack)
        if not data:
            return None

        w, h, startup, active_time, _ = data
        # Solo activa durante el intervalo [startup, startup + active_time]
        if not (startup <= self.attack_frame <= startup + active_time):
            return None

        offset_x = 45
        offset_y = 100
        x = (self.x + offset_x) if self.facing_right else (self.x - offset_x - w)
        y = self.y - offset_y
        return pygame.Rect(int(x), int(y), w, h)


class AuthoritativeSyncEngine:
    """
    Motor de simulación autoritativa a 60 Hz para Da Vinci Fighters.
    Integra reglas reales de colisión (Hitbox vs Hurtbox), daño, stun y cadencia fija independiente.
    """

    STAGE_MIN_X = 150.0
    STAGE_MAX_X = 2050.0
    STAGE_FLOOR_Y = 550.0
    WALK_SPEED = 6.0

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.tick: int = 0
        self.p1 = FighterSimState(x=800.0, y=self.STAGE_FLOOR_Y, facing_right=True)
        self.p2 = FighterSimState(x=1300.0, y=self.STAGE_FLOOR_Y, facing_right=False)
        self.timer: float = 99.0
        self.current_round: int = 1
        self.p1_wins: int = 0
        self.p2_wins: int = 0
        self.status: str = "fighting"

        # Colas de entradas por tick con búfer anti-jitter
        self._p1_inputs: Dict[int, PlayerInputPacket] = {}
        self._p2_inputs: Dict[int, PlayerInputPacket] = {}
        self._last_p1_input: Optional[PlayerInputPacket] = None
        self._last_p2_input: Optional[PlayerInputPacket] = None

    def push_input(self, packet: PlayerInputPacket) -> None:
        """Encola la entrada recibida para su respectivo jugador."""
        if packet.player_id == 1:
            self._p1_inputs[packet.tick] = packet
        elif packet.player_id == 2:
            self._p2_inputs[packet.tick] = packet

    def step(self, dt: float = 1.0 / 60.0) -> WorldSnapshotPacket:
        """
        Avanza la simulación un paso determinista de 16.66ms (60 Hz).
        Ejecuta físicas, hitboxes, hurtboxes, bloqueos y chequeos de impacto reales.
        """
        self.tick += 1
        self.timer = max(0.0, self.timer - dt)

        # Consumir entradas del tick actual (con fallback anti-pérdida de paquetes al último dpad)
        inp1 = self._p1_inputs.pop(self.tick, None)
        if inp1:
            self._last_p1_input = PlayerInputPacket(
                room_id=inp1.room_id,
                player_id=inp1.player_id,
                tick=self.tick,
                seq=inp1.seq,
                dpad=inp1.dpad,
                buttons=[],  # Botones son disparadores; no repetir en fallback
            )
        else:
            inp1 = self._last_p1_input

        inp2 = self._p2_inputs.pop(self.tick, None)
        if inp2:
            self._last_p2_input = PlayerInputPacket(
                room_id=inp2.room_id,
                player_id=inp2.player_id,
                tick=self.tick,
                seq=inp2.seq,
                dpad=inp2.dpad,
                buttons=[],  # Botones son disparadores; no repetir en fallback
            )
        else:
            inp2 = self._last_p2_input

        # 1. Actualizar Luchador 1
        self._update_fighter(self.p1, inp1, self.p2)

        # 2. Actualizar Luchador 2
        self._update_fighter(self.p2, inp2, self.p1)

        # 3. Orientación automática hacia el oponente
        if self.p1.state != "hit" and self.p1.active_attack is None:
            self.p1.facing_right = self.p1.x <= self.p2.x
        if self.p2.state != "hit" and self.p2.active_attack is None:
            self.p2.facing_right = self.p2.x < self.p1.x

        # 4. Chequeo de colisiones autoritativo (Hitbox vs Hurtbox)
        self._check_hitbox_collision(attacker=self.p1, defender=self.p2)
        self._check_hitbox_collision(attacker=self.p2, defender=self.p1)

        # 5. Comprobar condiciones de KO o finalización de round
        if self.p1.hp <= 0 or self.p2.hp <= 0 or self.timer <= 0:
            if self.status != "match_over":
                self.status = "round_ended"
                if self.p1.hp > self.p2.hp:
                    self.p1_wins += 1
                elif self.p2.hp > self.p1.hp:
                    self.p2_wins += 1

                if self.p1_wins >= 2 or self.p2_wins >= 2:
                    self.status = "match_over"

        return self.get_snapshot()

    def _update_fighter(self, fighter: FighterSimState, inp: Optional[PlayerInputPacket], opponent: FighterSimState) -> None:
        """Actualiza estados, transiciones y físicas de un luchador en base a entradas y stun."""
        # Si está aturdido (hit stun / block stun), no puede moverse ni atacar
        if fighter.stun_frames > 0:
            fighter.stun_frames -= 1
            if not fighter.is_blocking:
                fighter.state = "hit"
            else:
                fighter.state = "block"
            return

        # Si está ejecutando un ataque, avanzar animación y frames activos
        if fighter.active_attack:
            fighter.attack_frame += 1
            # Duración total del ataque: 28 frames
            if fighter.attack_frame > 28:
                fighter.active_attack = None
                fighter.attack_frame = 0
                fighter.state = "idle"
            return

        if not inp:
            fighter.state = "idle"
            fighter.is_blocking = False
            return

        # Movimiento horizontal con límites del escenario
        if inp.dpad == "left":
            fighter.x = max(self.STAGE_MIN_X, fighter.x - self.WALK_SPEED)
            fighter.is_blocking = fighter.facing_right  # Caminar hacia atrás = guardia
            fighter.state = "block" if fighter.is_blocking else "walk"
        elif inp.dpad == "right":
            fighter.x = min(self.STAGE_MAX_X, fighter.x + self.WALK_SPEED)
            fighter.is_blocking = not fighter.facing_right
            fighter.state = "block" if fighter.is_blocking else "walk"
        else:
            fighter.state = "idle"
            fighter.is_blocking = False

        # Iniciar ataques según botones recibidos
        btns = inp.buttons or []
        attack_type = None
        if "punch_heavy" in btns:
            attack_type = "punch_heavy"
        elif "punch_light" in btns or "punch" in btns:
            attack_type = "punch_light"
        elif "kick_heavy" in btns:
            attack_type = "kick_heavy"
        elif "kick_light" in btns or "kick" in btns:
            attack_type = "kick_light"

        if attack_type:
            fighter.active_attack = attack_type
            fighter.attack_frame = 1
            fighter.state = attack_type
            fighter.is_blocking = False

    def _check_hitbox_collision(self, attacker: FighterSimState, defender: FighterSimState) -> None:
        """Verifica si la hitbox del atacante intersecta la hurtbox del defensor."""
        hitbox = attacker.get_hitbox()
        if not hitbox:
            return

        if hitbox.colliderect(defender.hurtbox):
            # Obtener daño base
            damage_map = {
                "punch_light": 10,
                "punch_heavy": 20,
                "kick_light": 12,
                "kick_heavy": 24,
            }
            base_damage = damage_map.get(attacker.active_attack, 10)

            # Reducción por bloqueo / guardia
            if defender.is_blocking:
                final_damage = max(1, base_damage // 5)
                defender.stun_frames = 6
                defender.state = "block"
            else:
                final_damage = base_damage
                defender.stun_frames = 15
                defender.state = "hit"

            defender.hp = max(0, defender.hp - final_damage)

            # Empuje (knockback)
            push_dir = 1.0 if attacker.facing_right else -1.0
            defender.x = max(self.STAGE_MIN_X, min(self.STAGE_MAX_X, defender.x + push_dir * 18.0))

            # Desactivar ataque para evitar daño múltiple por frame
            attacker.attack_frame = 30
            attacker.active_attack = None

    def start_next_round(self) -> None:
        """Reinicia el estado para el siguiente round manteniendo el puntaje global."""
        if self.status == "match_over":
            return
        self.current_round += 1
        self.p1.x = 800.0
        self.p1.y = 550.0
        self.p1.hp = 100
        self.p1.state = "idle"
        self.p1.facing_right = True

        self.p2.x = 1300.0
        self.p2.y = 550.0
        self.p2.hp = 100
        self.p2.state = "idle"
        self.p2.facing_right = False

        self.timer = 99.0
        self.status = "fighting"

    def handle_forfeit(self, quitter_slot: int) -> WorldSnapshotPacket:
        """Declara victoria por abandono para el rival."""
        if quitter_slot == 1:
            self.p2_wins = 2
            self.p1.hp = 0
        else:
            self.p1_wins = 2
            self.p2.hp = 0
        self.status = "match_over"
        return self.get_snapshot()

    def get_winner_slot(self) -> Optional[int]:
        if self.status == "match_over":
            if self.p1_wins > self.p2_wins:
                return 1
            elif self.p2_wins > self.p1_wins:
                return 2
        return None

    def get_full_world_sync(self) -> Dict[str, Any]:
        """Empaqueta el estado íntegro para recuperación de desconexión."""
        snap = self.get_snapshot()
        data = snap.to_dict()
        data["full_recovery"] = True
        return data

    def get_snapshot(self) -> WorldSnapshotPacket:
        return WorldSnapshotPacket(
            room_id=self.room_id,
            tick=self.tick,
            p1_state={
                "x": self.p1.x,
                "y": self.p1.y,
                "hp": self.p1.hp,
                "state": self.p1.state,
                "facing_right": self.p1.facing_right,
            },
            p2_state={
                "x": self.p2.x,
                "y": self.p2.y,
                "hp": self.p2.hp,
                "state": self.p2.state,
                "facing_right": self.p2.facing_right,
            },
            timer=round(self.timer, 1),
            current_round=self.current_round,
            p1_wins=self.p1_wins,
            p2_wins=self.p2_wins,
            status=self.status,
        )
