# C.C.I. SYSTEM — FASE 3: CHAT EN TIEMPO REAL Y MODERACIÓN
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase3`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 3

La Fase 3 implementa el sistema de chat grupal persistente en tiempo real (Módulo B.2) sobre WebSockets y persistencia relacional en SQLite, incorporando controles anti-spam, límites de tamaño, historial paginado y moderación.

| Módulo / Archivo | Responsabilidad Técnica |
|---|---|
| [backend/chat_service.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/chat_service.py) | Servicio de mensajería con protección anti-spam por ventana deslizante (sliding window), validación de longitud (1 a 500 caracteres), control de silenciados (muted/banned), borrado lógico y reportes. |
| [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | Persistencia de mensajes en tabla `messages` e indexación de reportes en `message_reports`. |
| [backend/server.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/server.py) | Endpoints REST (`/api/v1/chat/...`) y eventos WebSocket bidireccionales (`chat:join`, `chat:leave`, `chat:send`, `chat:typing`, `chat:message`). |
| [test_phase3_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase3_evolution.py) | 8 pruebas automatizadas que verifican anti-spam, longitud, no-miembros, silenciados, borrado lógico por permisos y reportes de moderación. |

---

## 2. Controles de Seguridad, Privacidad y Moderación

1. **Protección Anti-Spam (Rate-Limiting):**
   - Máximo **5 mensajes en una ventana deslizante de 3 segundos** por usuario.
   - Mensajes adicionales en ráfaga son rechazados de inmediato con error informativo `"Estás enviando mensajes demasiado rápido"`.
2. **Restricción de Tamaño y Contenido:**
   - Longitud mínima: 1 carácter (mensajes de solo espacios en blanco son rechazados).
   - Longitud máxima: **500 caracteres** por mensaje.
3. **Control de Membresía y Silenciamiento:**
   - Solo miembros activos del grupo pueden emitir mensajes.
   - Usuarios marcados como `muted` o `banned` en `group_members` son bloqueados a nivel de servidor.
4. **Borrado Lógico (Soft-Delete):**
   - El mensaje se marca con `deleted_at = timestamp` en lugar de eliminarse físicamente, preservando la consistencia referencial y auditoría.
   - **Autorización:** Solo el autor original del mensaje, o un usuario con rol `owner` o `admin` del grupo pueden ejecutar el borrado.
5. **Reportes de Contenido:**
   - Cualquier participante puede registrar un reporte con motivo estructurado en `message_reports` para revisión de moderación.

---

## 3. Endpoints REST y Eventos WebSocket Implementados

### Endpoints REST
- `POST /api/v1/chat/send`: Envío de mensaje con validación de rate limit y membresía.
- `GET /api/v1/chat/<group_id>/history?limit=30&before=<timestamp>`: Historial paginado cronológico (excluyendo borrados).
- `DELETE /api/v1/chat/message/<message_id>`: Borrado lógico con validación de rol.
- `POST /api/v1/chat/message/<message_id>/report`: Reporte de abuso o contenido inapropiado.

### Eventos WebSocket (Socket.IO)
- `chat:join`: Suscripción del socket a la sala del grupo.
- `chat:leave`: Desuscripción de la sala del grupo.
- `chat:send`: Emisión de mensaje validado por `ChatService`.
- `chat:message`: Difusión en tiempo real a todos los miembros de la sala.
- `chat:typing`: Notificación de escritura a los demás participantes.

---

## 4. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 44 tests in 2.751s
OK (100% de éxito en todas las suites acumuladas)
- test_phase1_evolution.py: 9 tests pasados
- test_phase2_evolution.py: 11 tests pasados
- test_phase3_evolution.py: 8 tests pasados
- test_phase2.py: 9 tests pasados
- test_phase3.py: 7 tests pasados
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y catálogo de 19 títulos continúan 100% operativos.
