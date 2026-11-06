# C.C.I. SYSTEM — CCI COMMUNITIES
# FASE 7: ESCALABILIDAD, MÉTRICAS PROMETHEUS, PRUEBAS DE CARGA Y RUNBOOKS
**Versión:** 1.0  
**Fecha:** 06/11/2026  
**Módulo:** Observabilidad, Capacidad, Telemetría y Fiabilidad Operativa

---

## 1. OBJETIVOS DE LA FASE 7

La Fase 7 consolida la operabilidad y confiabilidad en producción de **CCI Communities** dentro del ecosistema de **C.C.I. SYSTEM**, garantizando:

1. **Límites de Capacidad y Cuotas Operativas:** Definición explícita de límites arquitectónicos consultables mediante `GET /api/v1/communities/system/limits`.
2. **Observabilidad y Telemetría Estándar:** Exportador de métricas compatible con el formato de texto Prometheus (RFC 0001) y JSON en `GET /api/v1/communities/metrics`.
3. **Endpoint de Salud (Health Checks):** Verificación viva de dependencias en `GET /api/v1/communities/health`.
4. **Harness de Pruebas de Carga Multihilo:** Módulo `backend/communities/load_testing.py` con `LoadTestBenchmark` para benchmarking concurrente (RPS, latencias p50, p95, p99 y tasa de error).
5. **Runbooks de Operación SRE:** Procedimientos de contingencia documentados en `RUNBOOKS.md`.

---

## 2. LÍMITES OPERATIVOS FORMALES (SISTEMA)

| Parámetro | Límite por Defecto | Justificación Técnica |
|---|---|---|
| Miembros por comunidad | 500 miembros | Rendimiento de consultas de presencia y asignación de roles |
| Canales por comunidad | 100 canales | Navegabilidad óptima en cliente desktop (1280x720) |
| Roles por comunidad | 50 roles | Matriz de cálculo de permisos O(1) con máscaras de bits |
| Streams simultáneos por canal | 1 stream | Prevención de saturación de SFU y bitrate del cliente |
| Participantes en canal de voz | 100 participantes | Límite por sala LiveKit SFU en despliegue estándar |
| Longitud máxima de mensaje | 2000 caracteres | Consistente con especificación técnica de chat |
| Tamaño máximo archivo sonido | 5 MB (5,242,880 B) | Buffer de audio en cliente local |
| Duración máxima clip de sonido | 15.0 segundos | Eficiencia de almacenamiento y prevención de saturación |
| Cooldown de soundboard | 5 segundos | Anti-spam fail-closed por usuario |
| Sonidos personales por usuario | 50 sonidos | Cuota de almacenamiento por cuenta |
| FPS máx. de transmisión | 60 FPS | Experiencia gaming fluida en juegos C.C.I. |
| Resolución máx. transmisión | 4K (2160p) | Adaptable según perfil de hardware |

---

## 3. FORMATO DE MÉTRICAS PROMETHEUS (RFC 0001)

El endpoint `GET /api/v1/communities/metrics` genera salida en formato Prometheus:

```text
# HELP communities_uptime_seconds Tiempo activo del servicio en segundos
# TYPE communities_uptime_seconds gauge
communities_uptime_seconds 1245.50
# HELP communities_created_total Contador acumulado de eventos
# TYPE communities_created_total counter
communities_created_total 12
# HELP communities_messages_total Contador acumulado de eventos
# TYPE communities_messages_total counter
communities_messages_total 354
# HELP communities_voice_joins_total Contador acumulado de eventos
# TYPE communities_voice_joins_total counter
communities_voice_joins_total 48
# HELP communities_streams_started_total Contador acumulado de eventos
# TYPE communities_streams_started_total counter
communities_streams_started_total 7
# HELP communities_soundboard_plays_total Contador acumulado de eventos
# TYPE communities_soundboard_plays_total counter
communities_soundboard_plays_total 89
# HELP communities_moderation_actions_total Contador acumulado de eventos
# TYPE communities_moderation_actions_total counter
communities_moderation_actions_total 5
# HELP communities_api_requests_total Contador acumulado de eventos
# TYPE communities_api_requests_total counter
communities_api_requests_total 1560
# HELP communities_api_latency_seconds Latencia promedio de peticiones REST
# TYPE communities_api_latency_seconds gauge
communities_api_latency_seconds 0.00342
```

Si la petición contiene el header `Accept: application/json`, el endpoint retorna la estructura JSON con contadores y métricas agregadas.

---

## 4. HARNESS DE PRUEBAS DE CARGA (`LoadTestBenchmark`)

La clase [`LoadTestBenchmark`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/communities/load_testing.py) implementa:
- Ejecución paralela controlada mediante `ThreadPoolExecutor`.
- Cálculo de percentiles estadísticos reales (`p50`, `p95`, `p99`).
- Throughput en peticiones por segundo (RPS) y tasa de éxito porcentual.
- Ejecución segura sin bloqueo de base de datos SQLite en pruebas locales.

---

## 5. RUNBOOKS VINCULADOS

Consulte [`documentacion/communities/RUNBOOKS.md`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/documentacion/communities/RUNBOOKS.md) para los procedimientos operativos estándar ante incidentes de infraestructura.
