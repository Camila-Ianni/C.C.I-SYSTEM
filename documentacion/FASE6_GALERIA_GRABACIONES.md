# C.C.I. SYSTEM — FASE 6: GALERÍA DE GRABACIONES DE GAMEPLAY
**Versión del proyecto:** v2.1.0  
**Fecha de finalización:** 5 de noviembre de 2026  
**Rama activa:** `feature/evolution-phase6`  
**Autora:** Camila Carolina Ianni  

---

## 1. Resumen de Entregables de la Fase 6

La Fase 6 implementa el Módulo C (Galería de Grabaciones de Gameplay) mediante un motor de captura de video asíncrono en segundo plano sobre Worker Thread con OpenCV Headless, generación automática de miniaturas PNG, límites de almacenamiento configurables con purga FIFO, visor/gestor de galería y apertura segura en reproductores del sistema.

| Módulo / Archivo | Responsabilidad Técnica |
|---|---|
| [recorder/video_recorder.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/recorder/video_recorder.py) | Grabador de gameplay desacoplado en segundo plano: encolamiento no bloqueante de frames desde Pygame, codificación MP4 en Worker Thread a 30 FPS (resolución 960×540, ~9.7 MB/min), captura de miniatura PNG y control de cuota FIFO. |
| [recorder/gallery_service.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/recorder/gallery_service.py) | Servicio de gestión de galería: filtrado por juego, cálculo de cuotas de disco, actualización de privacidad (`private`/`shared`), eliminación física de video y miniatura, y apertura con reproductor nativo del SO. |
| [cci_database.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/cci_database.py) | Persistencia y consultas en tabla `gameplay_recordings` (usuario, juego, ruta, duración, bytes, miniatura, privacidad). |
| [backend/server.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/backend/server.py) | Endpoints REST (`/api/v1/recordings/...`) para control de grabación, consulta de cuota, listado de galería, visibilidad y reproducción. |
| [test_phase6_evolution.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase6_evolution.py) | 4 pruebas automatizadas que verifican la creación de MP4 válido, generación de miniatura PNG, persistencia de metadatos, purga FIFO ante exceso de cuota y endpoints REST. |

---

## 2. Rendimiento y No-Penalización de FPS (Sección 7)

1. **Bucle de Juego Protegido a 60 FPS:**
   - La llamada `recorder.capture_surface(surface)` extrae el buffer y lo encola mediante `queue.Queue.put_nowait()`.
   - Si la CPU se satura transitoriamente, el grabador descarta frames de forma controlada sin reducir los FPS de la partida.
2. **Compresión Óptima (960×540 @ 30 FPS):**
   - Consume únicamente **~9.7 MB por minuto** de juego grabado.
   - Genera una miniatura fija de 320×180 píxeles a partir del primer cuadro capturado.
3. **Política de Depuración Automática FIFO (First In, First Out):**
   - Límite de disco por defecto: **2048 MB (2 GB)** configurables en [.env.example](file:///Users/cami/Desktop/C.C.I%20SYSTEM/.env.example).
   - Cuando el disco supera la cuota permitida, el sistema purga automáticamente la grabación más antigua (eliminando el archivo MP4, el thumbnail PNG y la fila en SQLite).
4. **Privacidad de Clips:**
   - Todo clip nuevo se registra como `visibility = 'private'` por defecto.

---

## 3. Endpoints REST Implementados

- `POST /api/v1/recordings/start`: Inicia sesión de grabación (`game_id`, `owner_id`).
- `POST /api/v1/recordings/stop`: Finaliza contenedor MP4 y persiste metadatos.
- `GET /api/v1/recordings/status`: Estado del grabador (tiempo transcurrido, frames escritos).
- `GET /api/v1/recordings/<owner_id>?game_id=...`: Galería de clips con filtros por juego y existencia física.
- `DELETE /api/v1/recordings/<recording_id>`: Eliminación física de video, miniatura y registro.
- `PATCH /api/v1/recordings/<recording_id>/visibility`: Actualización de privacidad (`private` o `shared`).
- `GET /api/v1/recordings/storage/stats`: Estadísticas de almacenamiento (MB usados, porcentaje y restante).
- `POST /api/v1/recordings/<recording_id>/play`: Apertura en reproductor nativo del SO (`open`, `start`, `xdg-open`).

---

## 4. Resultados de Pruebas de Regresión y Nuevas Pruebas

```
Ran 62 tests in 5.968s
OK (100% de éxito en todas las suites acumuladas)
- test_phase1_evolution.py: 9 tests pasados
- test_phase2_evolution.py: 11 tests pasados
- test_phase3_evolution.py: 8 tests pasados
- test_phase4_evolution.py: 8 tests pasados
- test_phase5_evolution.py: 6 tests pasados
- test_phase6_evolution.py: 4 tests pasados
- test_phase2.py: 9 tests pasados
- test_phase3.py: 7 tests pasados
```
- Consola de escritorio [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y catálogo de 19 títulos continúan 100% operativos.
