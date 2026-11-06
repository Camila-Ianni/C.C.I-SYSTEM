# C.C.I. SYSTEM — FASE 5: LLAMADAS DE VOZ GRUPALES WEBRTC
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase5`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 5

La Fase 5 implementa el sistema de llamadas de voz grupales de baja latencia (Módulo B.3) mediante señalización en Python sobre WebSockets, transporte de audio P2P WebRTC Mesh, configuración de servidores STUN/TURN, control de silenciamiento y políticas estrictas de privacidad.

| Módulo / Archivo | Responsabilidad Técnica |
|---|---|
| [backend/voice_service.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/voice_service.py) | Gestión en memoria de sesiones de llamada, participantes, control de micrófono (`muted`), autodetección de llamadas activas por grupo y finalización automática. |
| [backend/webrtc_signaling.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/webrtc_signaling.py) | Enrutador de ofertas y respuestas SDP y candidatos ICE sobre la conexión WebSocket de Socket.IO. |
| [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | Persistencia de sesiones en `call_sessions` (`status='active'`, `status='ended'`, `started_at`, `ended_at`). |
| [backend/server.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/server.py) | Endpoints REST (`/api/v1/voice/...`) y eventos WebSocket (`call:start`, `call:join`, `call:leave`, `call:mute`, `webrtc:offer`, `webrtc:answer`, `webrtc:ice_candidate`). |
| [test_phase5_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase5_evolution.py) | 6 pruebas automatizadas que verifican el ciclo de vida de llamada, privacidad (no-grabación), silenciamiento, enrutamiento WebRTC y configuración ICE. |

---

## 2. Privacidad y Reglas de la Especificación (Sección 6.3)

1. **Garantía de No Grabación por Defecto:**
   - La propiedad `recording_enabled = False` se fuerza por defecto.
   - Cumple estrictamente con la regla de consentimientos: el audio P2P es efímero y nunca se almacena en el servidor ni en SQLite.
2. **Topología de Audio P2P Mesh:**
   - Los participantes del grupo intercambian audio de baja latencia con el códec Opus directamente entre sus dispositivos.
   - El backend de Python solo gestiona la señalización y estado de membresía.
3. **Servidores STUN y TURN:**
   - **STUN:** Provee resolución de IP pública para NAT abiertos (`stun:stun.l.google.com:19302`).
   - **TURN:** Provee retransmisión sobre TLS/TCP o UDP en redes celulares con NAT Simétrico o CGNAT, distribuido vía `/api/v1/voice/ice-servers`.

---

## 3. Prueba de Concepto Técnica Multiplataforma (PoC)

| Plataforma | Capa de Señalización (Python) | Capa de Audio / Medios | Requisitos Nativos / Permisos |
|---|---|---|---|
| **Web / PWA** | WebSocket Socket.IO | WebRTC nativo del navegador (`RTCPeerConnection` + `getUserMedia`) | Prompt de permisos en navegador. |
| **Android (APK)** | WebSocket Socket.IO en Python | WebRTC nativo Android SDK / WebView bridge | `android.permission.RECORD_AUDIO` en `AndroidManifest.xml`. |
| **iOS (IPA)** | WebSocket Socket.IO en Python | WebRTC nativo iOS SDK / Safari bridge | `NSMicrophoneUsageDescription` en `Info.plist`. |
| **PC Escritorio** | WebSocket Socket.IO en Python | PyAudio / SoundCard / `aiortc` puente de audio | Selección de dispositivo de captura local. |

---

## 4. Endpoints REST y Eventos WebSocket Implementados

### Endpoints REST
- `POST /api/v1/voice/calls/start`: Inicia llamada grupal.
- `POST /api/v1/voice/calls/<session_id>/join`: Unión de participante a la llamada activa.
- `POST /api/v1/voice/calls/<session_id>/leave`: Salida de participante.
- `POST /api/v1/voice/calls/<session_id>/mute`: Conmutación de silencio del micrófono.
- `POST /api/v1/voice/calls/<session_id>/end`: Finalización manual de la sesión.
- `GET /api/v1/voice/calls/active/<group_id>`: Consulta de llamada activa en el grupo.
- `GET /api/v1/voice/ice-servers`: Configuración de servidores STUN y credenciales TURN.

### Eventos WebSocket (Socket.IO)
- `call:incoming`: Notificación a los miembros del grupo al iniciarse una llamada.
- `call:joined`: Alerta de nuevo participante para iniciar el intercambio SDP.
- `call:mute_changed`: Sincronización del icono de micrófono en tiempo real.
- `webrtc:offer`, `webrtc:answer`, `webrtc:ice_candidate`: Túnel de señalización.

---

## 5. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 58 tests in 4.142s
OK (100% de éxito en todas las suites acumuladas)
- test_phase1_evolution.py: 9 tests pasados
- test_phase2_evolution.py: 11 tests pasados
- test_phase3_evolution.py: 8 tests pasados
- test_phase4_evolution.py: 8 tests pasados
- test_phase5_evolution.py: 6 tests pasados
- test_phase2.py: 9 tests pasados
- test_phase3.py: 7 tests pasados
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y catálogo de 19 títulos continúan 100% operativos.
