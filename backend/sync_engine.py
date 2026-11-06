"""
backend/sync_engine.py - Motor de simulación autoritativa y sincronización de estado.
Maneja paso de tiempo fijo (60 Hz), buffers de entradas de jugadores y cálculo de snapshots.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from backend.contracts import PlayerInputPacket, WorldSnapshotPacket


@dataclass
class FighterSimState:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    hp: int = 100
    state: str = "idle"
    facing_right: bool = True


class AuthoritativeSyncEngine:
    """Motor de simulación autoritativa en servidor a 60 Hz para Da Vinci Fighters."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.tick: int = 0
        self.p1 = FighterSimState(x=800.0, y=550.0, facing_right=True)
        self.p2 = FighterSimState(x=1300.0, y=550.0, facing_right=False)
        self.timer: float = 99.0
        self.current_round: int = 1
        self.p1_wins: int = 0
        self.p2_wins: int = 0
        self.status: str = "fighting"

        # Colas de entradas por tick
        self._p1_inputs: Dict[int, PlayerInputPacket] = {}
        self._p2_inputs: Dict[int, PlayerInputPacket] = {}

    def push_input(self, packet: PlayerInputPacket) -> None:
        """Encola la entrada recibida para su respectivo jugador."""
        if packet.player_id == 1:
            self._p1_inputs[packet.tick] = packet
        elif packet.player_id == 2:
            self._p2_inputs[packet.tick] = packet

    def step(self, dt: float = 1.0 / 60.0) -> WorldSnapshotPacket:
        """Avanza la simulación un paso determinista de 16.66ms."""
        self.tick += 1
        self.timer = max(0.0, self.timer - dt)

        # Consumir entradas del tick actual (o la más reciente)
        inp1 = self._p1_inputs.pop(self.tick, None)
        inp2 = self._p2_inputs.pop(self.tick, None)

        if inp1:
            if inp1.dpad == "left":
                self.p1.x = max(100.0, self.p1.x - 5.0)
                self.p1.state = "walk"
            elif inp1.dpad == "right":
                self.p1.x = min(2100.0, self.p1.x + 5.0)
                self.p1.state = "walk"
            else:
                self.p1.state = "idle"

            if "punch" in inp1.buttons:
                self.p1.state = "punch"
                # Validación de impacto autoritativa si están a rango
                if abs(self.p1.x - self.p2.x) < 120 and self.p1.facing_right == (self.p1.x < self.p2.x):
                    self.p2.hp = max(0, self.p2.hp - 8)
                    self.p2.state = "hit"

        if inp2:
            if inp2.dpad == "left":
                self.p2.x = max(100.0, self.p2.x - 5.0)
                self.p2.state = "walk"
            elif inp2.dpad == "right":
                self.p2.x = min(2100.0, self.p2.x + 5.0)
                self.p2.state = "walk"
            else:
                self.p2.state = "idle"

            if "punch" in inp2.buttons:
                self.p2.state = "punch"
                if abs(self.p1.x - self.p2.x) < 120 and self.p2.facing_right == (self.p2.x < self.p1.x):
                    self.p1.hp = max(0, self.p1.hp - 8)
                    self.p1.state = "hit"

        # Orientación automática de luchadores
        self.p1.facing_right = self.p1.x <= self.p2.x
        self.p2.facing_right = self.p2.x < self.p1.x

        # Comprobar KO
        if self.p1.hp <= 0 or self.p2.hp <= 0 or self.timer <= 0:
            self.status = "round_ended"

        return self.get_snapshot()

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
