# C.C.I. SYSTEM — CCI COMMUNITIES
# RUNBOOKS DE OPERACIÓN, ESCALABILIDAD Y RECUPERACIÓN ANTE DESASTRES (SRE)
**Versión:** 1.0  
**Fecha:** 06/11/2026  
**Área:** Infraestructura, Confiabilidad y Operaciones (SRE / DevOps)

---

## 1. ÍNDICE DE PROCEDIMIENTOS OPERATIVOS

| ID | Incidente / Escenario | Severidad | RTO | RPO |
|---|---|---|---|---|
| **RB-01** | Caída o Degradación del SFU LiveKit | P1 (Crítico) | < 2 min | 0 s |
| **RB-02** | Saturación / Desconexión de Memoria en Redis | P2 (Alto) | < 3 min | < 5 s |
| **RB-03** | Mantenimiento, VACUUM y Backup de PostgreSQL | P3 (Medio) | N/A (Online) | < 1 hr |
| **RB-04** | Mitigación de Spam o Abuso en Soundboard | P3 (Medio) | Inmediato | 0 s |
| **RB-05** | Plan de Contingencia y Recuperación ante Desastres (DRP) | P1 (Crítico) | < 15 min | < 15 min |

---

## 2. PROCEDIMIENTOS DETALLADOS

### RB-01: Caída o Degradación del SFU LiveKit
#### Síntomas
- Clientes reportan error `VOICE_CONNECTION_FAILED` o desconexión abrupta en canales de audio y transmisiones de pantalla.
- Endpoint `/api/v1/communities/health` reporta estado degradado o timeouts al contactar el SFU.
- Alerta Prometheus: `livekit_active_rooms` cae a 0 o `livekit_packet_loss_ratio > 0.05`.

#### Pasos de Resolución
1. **Comprobar estado del contenedor LiveKit:**
   ```bash
   docker ps -a | grep livekit
   docker logs --tail 100 cci_livekit
   ```
2. **Reinicio controlado del servicio SFU:**
   ```bash
   docker restart cci_livekit
   ```
3. **Verificación de puertos y TURN/STUN:**
   - Validar que CoTURN esté respondiendo en UDP 3478 y 5349:
     ```bash
     nc -zvu 127.0.0.1 3478
     ```
4. **Reconexión de clientes:**
   - Los clientes del frontend de C.C.I. ejecutan un algoritmo de backoff exponencial automático (1s, 2s, 4s, máx 10s).
   - Validar en `/api/v1/communities/metrics` que `communities_voice_joins_total` reanude su incremento regular.

---

### RB-02: Saturación o Desconexión de Redis
#### Síntomas
- Errores de caché, fallas en la emisión de eventos Socket.IO o advertencias de presencia congelada.
- Alerta Prometheus: `redis_memory_used_bytes > 90% maxmemory`.

#### Pasos de Resolución
1. **Inspección de memoria y políticas de desalojo:**
   ```bash
   redis-cli -a $REDIS_PASSWORD INFO memory
   ```
2. **Confirmar directiva `volatile-lru` o `allkeys-lru`:**
   ```bash
   redis-cli -a $REDIS_PASSWORD CONFIG GET maxmemory-policy
   ```
   Si está en `noeviction`, reconfigurar de inmediato:
   ```bash
   redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory-policy allkeys-lru
   ```
3. **Purgado de claves huérfanas de presencia:**
   ```bash
   redis-cli -a $REDIS_PASSWORD EVAL "for _,k in ipairs(redis.call('keys','presence:ephemeral:*')) do redis.call('del',k) end" 0
   ```
4. **Reinicio de la conexión del backend:**
   - El backend reconecta automáticamente con pool de conexiones tolerante a caídas.

---

### RB-03: Mantenimiento, VACUUM y Backup de PostgreSQL
#### Mantenimiento Preventivo Online
- Ejecución semanal programada sin bloqueo de lecturas/escrituras:
  ```bash
  psql -U cci_admin -d cci_communities -c "VACUUM ANALYZE channels, channel_messages, community_members;"
  ```
- Detección de índices inflados:
  ```bash
  psql -U cci_admin -d cci_communities -c "REINDEX TABLE CONCURRENTLY channel_messages;"
  ```

#### Respaldo Lógico Diario (pg_dump)
```bash
pg_dump -U cci_admin -d cci_communities -Fc -Z 6 -f /backups/cci_communities_$(date +%Y%m%d_%H%M%S).dump
```

#### Restauración
```bash
pg_restore -U cci_admin -d cci_communities -c -v /backups/cci_communities_target.dump
```

---

### RB-04: Mitigación de Spam o Abuso en Soundboard
#### Síntomas
- Usuarios quejándose de reproducción excesiva de sonidos o picos de tráfico en canales de voz.
- HTTP 429 (`SOUND_COOLDOWN`) en `/sounds/<id>/play-authorize`.

#### Acciones Operativas
1. **Comprobar límites configurados:**
   - La API expone formalmente en `GET /api/v1/communities/system/limits` un cooldown de 5 segundos por usuario.
2. **Silenciar o mutear permisos de Soundboard a nivel de rol o canal:**
   - Revocar permiso `USE_SOUNDBOARD` (bit 10) en el canal afectado mediante anulación (`overrides`).
   - Muteo temporal del actor ofensivo mediante endpoint de moderación:
     `POST /api/v1/communities/<id>/moderation/mute` con `target_user_id` y `duration_minutes`.

---

### RB-05: Plan de Contingencia y Recuperación ante Desastres (DRP)
#### Escenario de Pérdida Total del Nodo
1. Levantar nuevo nodo base (Ubuntu LTS / macOS Server).
2. Clonar repositorio y levantar stack Docker Compose:
   ```bash
   docker compose -f docker-compose.communities.yml up -d
   ```
3. Restaurar último backup de base de datos desde almacenamiento S3/MinIO.
4. Ejecutar suite de pruebas de salud:
   ```bash
   curl -s http://127.0.0.1:5000/api/v1/communities/health | jq .
   ```
5. Confirmar que `status == "healthy"` y `database == "connected"`.
