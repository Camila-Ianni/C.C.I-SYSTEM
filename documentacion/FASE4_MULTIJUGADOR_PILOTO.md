# C.C.I. SYSTEM — FASE 4: MULTIJUGADOR ONLINE PILOTO (DA VINCI FIGHTERS)
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase4`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 4

La Fase 4 implementa el Módulo A (Multijugador Online) con un juego piloto integrado: **Da Vinci Fighters**. Establece la infraestructura de salas públicas y privadas con código de invitación, bucle de simulación autoritativo a 60 Hz en servidor, sincronización ligera por instantáneas, manejo de desconexión temporal y registro de resultados en base de datos.

| Módulo / Archivo | Responsabilidad Técnica |
|---|---|
| [catalog_data.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/catalog_data.py) | Declaración formal de modalidades multijugador (`single`, `local`, `online`). Da Vinci Fighters habilitado para online; los demás preservan modos locales e individuales. |
| [backend/room_manager.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/room_manager.py) | Creación y administración de salas en memoria con código de invitación alfanumérico, roles de anfitrión (iniciar, expulsar, transferir) y ventana de gracia por desconexión (5 segundos). |
| [backend/sync_engine.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/sync_engine.py) | Motor autoritativo a 60 Hz (paso de tiempo fijo de 16.66ms): consumo de entradas por tick, validación de hitboxes, resta de vida autoritativa en servidor, progresión al mejor de 3 rounds (Best of 3) y empate/victoria. |
| [backend/multiplayer_client.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/multiplayer_client.py) | Cliente de red ligero en Python para Pygame: medición de latencia/RTT, predicción local, buffer de interpolación y reconexión suave. |
| [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | Persistencia relacional de partidas en `matches` y búsqueda de salas por `invite_code`. |
| [backend/server.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/server.py) | Endpoints REST (`/api/v1/multiplayer/...`) y eventos en tiempo real (`game:start`, `game:input`, `game:snapshot`, `game:pause`, `game:resume`). |
| [test_phase4_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase4_evolution.py) | 8 pruebas automatizadas de extremo a extremo que validan salas privadas, anfitrión, simulación autoritativa, rounds, desconexión/reconexión y persistencia. |

---

## 2. Arquitectura de Sincronización y Autoridad del Servidor

1. **Simulación a 60 FPS ($dt = 16.66\text{ ms}$):**
   - El cliente envía periódicamente `PlayerInputPacket(tick, seq, dpad, buttons, timestamp_ms)`.
   - El servidor encola los paquetes por tick y avanza la física determinista.
2. **Autoridad de Combate:**
   - El servidor evalúa las posiciones relativas y estados de ataque. Si un golpe conecta, el servidor reduce la vida canónica y difunde el evento de impacto (`hit`).
   - El cliente no tiene autoridad para alterar vidas ni inventar puntajes.
3. **Progresión de Partida:**
   - La partida se define al **mejor de 3 rounds** (`Best of 3`).
   - Al finalizar, el servidor inserta el registro consolidado en la tabla `matches` con `room_id`, `game_id`, duración y metadatos (`winner_slot`, `p1_wins`, `p2_wins`).
4. **Desconexiones y Reconexión:**
   - Ante un corte de socket, la sala pasa a estado `PAUSED` con ventana de gracia de **5 segundos**.
   - Si el jugador reconecta, el servidor le envía un paquete `FullWorldSync` con el estado íntegro del combate y reanuda el juego.
   - Si expira la ventana sin reconexión, el servidor declara victoria por abandono (`Forfeit`) en favor del jugador conectado.

---

## 3. Endpoints REST y Eventos WebSocket Implementados

### Endpoints REST
- `POST /api/v1/multiplayer/rooms/create`: Creación de sala con generación de código de invitación de 6 caracteres.
- `POST /api/v1/multiplayer/rooms/join`: Unión a sala pública o privada (requiere código válido).
- `GET /api/v1/multiplayer/rooms/<room_id>`: Consulta de estado en vivo de la sala y miembros.
- `GET /api/v1/multiplayer/matches/history?game_id=davinci&limit=20`: Historial de partidas registradas.

### Eventos WebSocket (Socket.IO)
- `game:start`: Anfitrión lanza el combate una vez que ambos jugadores están en estado `READY`.
- `game:input`: Transmisión de entradas de mando a 60 Hz.
- `game:snapshot`: Difusión autoritativa a 30 Hz del estado del mundo.
- `game:pause`: Pausa manual o automática por desconexión.
- `game:resume`: Reanudación sincronizada con paquete de recuperación total.

---

## 4. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 52 tests in 3.530s
OK (100% de éxito en todas las suites acumuladas)
- test_phase1_evolution.py: 9 tests pasados
- test_phase2_evolution.py: 11 tests pasados
- test_phase3_evolution.py: 8 tests pasados
- test_phase4_evolution.py: 8 tests pasados
- test_phase2.py: 9 tests pasados
- test_phase3.py: 7 tests pasados
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y catálogo de 19 títulos continúan 100% operativos.
