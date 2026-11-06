# C.C.I. SYSTEM — FASE 1: PREPARACIÓN DE ARQUITECTURA
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase1`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 1

La Fase 1 establece los cimientos técnicos sin alterar la experiencia de usuario existente ni la consola de PC.

| Componente | Archivo / Recurso | Descripción |
|---|---|---|
| **Copia de seguridad BD** | `.cci-user-data/cci_system.sqlite3.backup_fase1` | Snapshot seguro de 94 KB antes de aplicar migraciones. |
| **Migración relacional v2** | [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | `schema_version` (v2) y 9 tablas nuevas con índices y claves foráneas. |
| **Separación de requisitos** | [requirements.txt](file:///Users/cami/Desktop/C.C.I%20SYSTEM/requirements.txt) | Cliente de escritorio con `opencv-python-headless` (evita conflicto SDL2 en macOS). |
| **Requisitos de servidor** | [requirements-server.txt](file:///Users/cami/Desktop/C.C.I%20SYSTEM/requirements-server.txt) | Dependencias backend: `Flask`, `Flask-SocketIO`, `python-socketio`, `simple-websocket`. |
| **Variables de entorno** | [.env.example](file:///Users/cami/Desktop/C.C.I%20SYSTEM/.env.example) | Puertos, STUN/TURN, rutas de grabaciones y límites de almacenamiento. |
| **Módulos de backend** | [backend/](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/) | Servicios desacoplados: configuración, contratos tipados, salas, motor de simulación y señalización WebRTC. |
| **Suite de pruebas unitarias** | [test_phase1_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase1_evolution.py) | 9 tests unitarios para verificar migraciones, salas, simulación autoritativa y señalización. |

---

## 2. Detalle de la Migración Relacional (Esquema v2)

Se incorporaron 9 entidades sin eliminar ni sobrescribir las tablas de cuentas, perfiles, catálogo ni puntajes:

```sql
1. friendships (requester_id, addressee_id, status, created_at, updated_at)
2. groups (id, name, owner_id, avatar, visibility, created_at)
3. group_members (id, group_id, user_id, role, status, joined_at)
4. messages (id, group_id, sender_id, body, created_at, edited_at, deleted_at)
5. call_sessions (id, group_id, started_by, status, started_at, ended_at)
6. game_rooms (id, game_id, host_id, visibility, status, invite_code, created_at)
7. game_room_members (id, room_id, user_id, player_slot, ready_state, connection_state, joined_at)
8. matches (id, room_id, game_id, started_at, ended_at, result_metadata)
9. gameplay_recordings (id, owner_id, game_id, local_path, duration_seconds, size_bytes, visibility, thumbnail_path, created_at)
```

### Plan de Rollback (Reversibilidad)
En caso de requerir volver al estado inicial:
```bash
cp .cci-user-data/cci_system.sqlite3.backup_fase1 .cci-user-data/cci_system.sqlite3
```

---

## 3. Contratos de Eventos y Señalización ([backend/contracts.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/contracts.py))

- **Salas:** `room:create`, `room:join`, `room:leave`, `room:ready`, `room:state`, `room:error`.
- **Multijugador:** `game:input` (60 Hz), `game:snapshot` (30 Hz), `game:pause`, `game:resume`, `game:round_end`.
- **Chat:** `chat:send`, `chat:message`, `chat:history`.
- **Voz WebRTC:** `webrtc:offer`, `webrtc:answer`, `webrtc:ice_candidate`.

---

## 4. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 25 tests in 0.921s
OK (100% éxito en test_phase1_evolution.py, test_phase2.py y test_phase3.py)
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y lanzador [emulator.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/emulator.py) intactos y funcionales.
