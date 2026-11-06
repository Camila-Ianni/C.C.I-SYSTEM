# C.C.I. SYSTEM — CCI COMMUNITIES
## Fase 3: Salas de Voz, Tokens Autoritativos y LiveKit SFU

**Fecha:** 2026-11-06  
**Subsistema:** CCI Communities  
**Estado:** IMPLEMENTACIÓN Y CERTIFICACIÓN APROBADA (Fase 3)  
**Rama:** `feature/communities-phase0-design`  

---

## 1. Alcance y Delimitación Técnica (Fase 3 / Estabilización Fase 0.2)

- **En Alcance (Implementado y Verificado en Runtime Python)**:
  - Emisión y verificación autoritativa de tokens JWT HS256 para LiveKit (`TTL <= 300s`, `240s` por defecto) restringidos por sala (`comm_{comm_id}_chan_{chan_id}`) y permisos (`voice.connect`, `voice.speak`).
  - Ciclo de vida de sesiones de voz en SQLite 3 (`WAL`), control de cupo (`max_participants`), moderación jerárquica (`mute`/`disconnect`), señalización Socket.IO en tiempo real y reconexión sin duplicar sesiones.
  - Enlace local con drivers de hardware (`mobile/audio_drivers.py`) y transporte P2P local UDP RTP (`RFC 3550`) en `mobile/voice_client.py`.
- **Formalmente Fuera del Alcance de esta Fase**:
  - Transporte multimedia WebRTC continuo a través de un servidor `livekit-server` SFU externo y relay TURN/NAT entre redes WAN remotas independientes.

### Funcionalidades Implementadas:
1. **Emisión Segura de Tokens LiveKit JWT (RFC 7519)**:
   - Módulo [`backend/communities/livekit_token.py`](../../backend/communities/livekit_token.py): Generación de tokens JWT firmados con HMAC-SHA256 utilizando `LIVEKIT_API_KEY` y `LIVEKIT_API_SECRET` almacenados exclusivamente en el servidor.
   - Concesiones granulares (`video.roomJoin=True`, `video.canPublish=True/False`, `video.canSubscribe=True`, `video.canPublishData=True`).
   - Expiración temporal corta (`240s` por defecto, máximo estricto `300s`) y alcance mínimo restringido a la sala `comm_{comm_id}_chan_{chan_id}`.
2. **Control de Acceso y Límites de Capacidad**:
   - Validación estricta del permiso `voice.connect` (fail-closed, 403 Forbidden para canales privados o miembros sin acceso).
   - Comprobación autoritativa del cupo de sala (`max_participants`): rechazo con 422 Unprocessable Entity cuando la sala alcanza su capacidad máxima.
   - Concesión de micrófono condicionada por el permiso `voice.speak`: si está denegado, el token se emite con `canPublish=False` (modo solo escucha).
3. **Ciclo de Vida de Sesiones de Voz**:
   - Tabla `voice_sessions` en [`backend/communities/repository.py`](../../backend/communities/repository.py) con registro de participantes, ID de sesión y timestamps `joined_at`/`left_at`.
   - Consulta de participantes conectados mediante `GET /api/v1/channels/{id}/voice-participants`.
   - Desconexión formal y liberación de slots vía `POST /api/v1/channels/{id}/voice-leave`.
4. **Señalización en Tiempo Real Socket.IO**:
   - `community:voice:join` / `voice.participant_joined`: Sincronización inmediata de participantes en la interfaz.
   - `community:voice:mute` / `voice.mute_state_changed`: Difusión de estado de micrófono (silenciado / activo).
   - `community:voice:speakers` / `voice.active_speakers`: Indicador de voz activa (VAD) y nivel de audio.
   - `community:voice:leave` / `voice.participant_left`: Actualización inmediata al salir de la sala.
5. **Moderación de Voz Jerárquica**:
   - Endpoint `POST /api/v1/channels/{id}/voice-moderate` (`action="mute"` o `action="disconnect"`).
   - Exige permisos `voice.mute_members` o `voice.move_members`.
   - Protección absoluta del propietario y respeto a la jerarquía de roles (un moderador no puede moderar a un rango superior o igual).
6. **Hardware de Audio Físico y Reconexión Transparente**:
   - Enlace directo con [`mobile/audio_drivers.py`](../../mobile/audio_drivers.py) ([`AudioDeviceManager`](../../mobile/audio_drivers.py#L214)): enumeración de dispositivos de captura y reproducción, silenciador de hardware y reproducción en DAC mediante `pygame.mixer.Sound`.
   - Reconexión sin duplicación de sesiones (evita participantes fantasma en caso de reingreso rápido).

---

## 2. Cobertura de Pruebas de Fase 3 ([`test_communities_phase3.py`](../../test_communities_phase3.py))

| # | Prueba Automatizada | Requisito Validado | Resultado |
| :--- | :--- | :--- | :--- |
| **01** | `test_01_voice_token_generation_and_jwt_claims` | Emisión autoritativa de LiveKit JWT, validación de firma y concesiones de sala | **PASS** |
| **02** | `test_02_voice_token_rejects_unauthorized_user` | Rechazo con 403 Forbidden en canales privados para usuarios sin acceso | **PASS** |
| **03** | `test_03_voice_token_enforces_participant_limit` | Control de cupo máximo de participantes (`max_participants` -> 422) | **PASS** |
| **04** | `test_04_voice_speak_permission_controls_can_publish` | Concesión `canPublish=False` cuando `voice.speak` está denegado | **PASS** |
| **05** | `test_05_voice_session_lifecycle_and_participants_listing` | Ciclo de vida de sesión de voz, listado de participantes y salida limpia | **PASS** |
| **06** | `test_06_realtime_voice_participant_events_socketio` | Eventos Socket.IO en vivo: unión, muteo y salida de participantes | **PASS** |
| **07** | `test_07_voice_moderation_mute_and_disconnect` | Moderación de sala (silenciar y desconectar) con respeto jerárquico | **PASS** |
| **08** | `test_08_active_speakers_realtime_indicator` | Difusión de participantes hablando (VAD) y nivel de audio | **PASS** |
| **09** | `test_09_platform_audio_driver_and_device_enumeration` | Compatibilidad con hardware físico, selección de micrófono/salida y DAC | **PASS** |
| **10** | `test_10_reconnection_and_session_recovery` | Reconexión transparente sin duplicar registros de sesión activa | **PASS** |

---

## 3. Métricas del Runner Unificado ([`evaluations_report.json`](../../evaluations_report.json))

- **Suites Ejecutadas:** 16 de 16
- **Total de Pruebas:** 135
- **Aprobadas:** 135 (100%)
- **Fallidas:** 0
- **Errores:** 0
- **Tiempo de Ejecución:** 18.43 segundos
- **Regresiones en Consola PC:** 0 (1280x720, 60 FPS, 19 títulos verificados)
