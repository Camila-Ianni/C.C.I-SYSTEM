# C.C.I. SYSTEM — CCI COMMUNITIES
# RUNBOOKS DE OPERACIÓN, MANTENIMIENTO SQLITE WAL Y RECUPERACIÓN ANTE DESASTRES (SRE)
**Versión:** 1.2 (Fase 0.2 — Estabilización Pre-Merge)  
**Fecha:** 06/11/2026  
**Área:** Infraestructura, Confiabilidad y Operaciones (SRE / DevOps)  
**Motor de Persistencia Activo:** SQLite 3 en modo `WAL` (`/data/cci_communities.sqlite3`)

---

## 1. ÍNDICE DE PROCEDIMIENTOS OPERATIVOS

| ID | Incidente / Escenario | Severidad | RTO | RPO |
|---|---|---|---|---|
| **RB-01** | Caída o Degradación del SFU LiveKit / Señalización | P1 (Crítico) | < 2 min | 0 s |
| **RB-02** | Contención de Locks o Crecimiento de Archivo WAL en SQLite 3 | P2 (Alto) | < 2 min | 0 s |
| **RB-03** | Mantenimiento, VACUUM, Integridad y Online Backup de SQLite 3 | P3 (Medio) | N/A (Online) | < 15 min |
| **RB-04** | Mitigación de Spam o Abuso en Soundboard | P3 (Medio) | Inmediato | 0 s |
| **RB-05** | Plan de Contingencia y Recuperación ante Desastres (DRP) | P1 (Crítico) | < 15 min | < 15 min |

---

## 2. PROCEDIMIENTOS DETALLADOS

### RB-01: Caída o Degradación del SFU LiveKit / Señalización
#### Síntomas
- Clientes reportan error `VOICE_CONNECTION_FAILED` al intentar usar un token emitido por `POST /api/v1/channels/{id}/voice-token`.
- Endpoint `GET /api/v1/communities/health` reporta estado degradado o errores de red.

#### Pasos de Resolución
1. **Comprobar estado del contenedor LiveKit y API:**
   ```bash
   docker ps -a | grep cci_communities
   docker logs --tail 100 cci_communities_livekit
   docker logs --tail 100 cci_communities_api
   ```
2. **Reinicio controlado del servicio SFU:**
   ```bash
   docker restart cci_communities_livekit
   ```
3. **Verificación de puertos STUN/TURN (puerto 3478 UDP/TCP; TURNS 5349 deshabilitado con `no-tls`):**
   ```bash
   nc -zvu 127.0.0.1 3478
   nc -zv 127.0.0.1 3478
   ```
4. **Verificación de métricas y sesiones activas:**
   - Consultar `http://127.0.0.1:5050/api/v1/communities/metrics` y verificar `communities_voice_sessions_active`.

---

### RB-02: Contención de Locks o Crecimiento de Archivo WAL en SQLite 3
#### Síntomas
- Incremento del contador `communities_db_errors_total` en `GET /api/v1/communities/metrics`.
- El archivo `/data/cci_communities.sqlite3-wal` supera los 100 MB sin truncarse automáticamente.

#### Pasos de Resolución
1. **Inspeccionar tamaño del archivo principal y archivos `-wal` / `-shm`:**
   ```bash
   ls -lh /data/cci_communities.sqlite3*
   ```
2. **Ejecutar checkpoint y truncado en caliente del archivo WAL:**
   ```bash
   sqlite3 /data/cci_communities.sqlite3 "PRAGMA busy_timeout=10000; PRAGMA wal_checkpoint(TRUNCATE);"
   ```
3. **Verificar integridad física del archivo SQLite:**
   ```bash
   sqlite3 /data/cci_communities.sqlite3 "PRAGMA integrity_check;"
   ```

---

### RB-03: Mantenimiento, VACUUM, Integridad y Online Backup de SQLite 3
#### Mantenimiento Preventivo Online
- Optimización del planificador de consultas e índices de SQLite sin detener el servicio:
  ```bash
  sqlite3 /data/cci_communities.sqlite3 "PRAGMA optimize; ANALYZE;"
  ```

#### Respaldo Consistente en Caliente (SQLite Online Backup API)
El comando `.backup` de SQLite copia páginas de forma segura en modo `WAL` sin bloquear las lecturas ni detener el contenedor `api`:
```bash
mkdir -p /data/backups
sqlite3 /data/cci_communities.sqlite3 ".backup '/data/backups/cci_communities_$(date +%Y%m%d_%H%M%S).sqlite3'"
```

#### Restauración desde Respaldo Local
```bash
docker stop cci_communities_api
cp /data/backups/cci_communities_target.sqlite3 /data/cci_communities.sqlite3
rm -f /data/cci_communities.sqlite3-wal /data/cci_communities.sqlite3-shm
docker start cci_communities_api
```

---

### RB-04: Mitigación de Spam o Abuso en Soundboard
#### Síntomas
- Usuarios reportan reproducción excesiva de sonidos en salas de voz.
- Respuestas HTTP 429 (`SOUND_COOLDOWN`) frecuentes en `/api/v1/sounds/<id>/play-authorize`.

#### Acciones Operativas
1. **Comprobar límites configurados:**
   - La API expone en `GET /api/v1/communities/system/limits` un cooldown estricto de 5 segundos por sonido y límite de 15.0 segundos por pista MP3.
2. **Revocar permiso o silenciar al infractor:**
   - Denegar el permiso `soundboard.play` en el canal afectado mediante `PUT /api/v1/channels/<id>/overrides`.
   - Aplicar silenciamiento temporal mediante `POST /api/v1/communities/<id>/moderation/mute`.

---

### RB-05: Plan de Contingencia y Recuperación ante Desastres (DRP)
#### Escenario de Pérdida Total del Nodo
1. Aprovisionar nuevo host con Docker y Docker Compose.
2. Clonar el repositorio, configurar `deploy/.env` con secretos reales (`openssl rand -hex 32`) y restaurar el archivo `cci_communities.sqlite3` en el volumen `cci_app_data:/data`.
3. Levantar el stack:
   ```bash
   docker compose -f deploy/docker-compose.communities.yml up -d
   ```
4. Ejecutar verificación de salud en el puerto canónico `5050`:
   ```bash
   curl -s http://127.0.0.1:5050/api/v1/communities/health
   ```
5. Confirmar que la respuesta HTTP sea `200 OK` con `"status": "healthy"` y `"database": "connected"`.
