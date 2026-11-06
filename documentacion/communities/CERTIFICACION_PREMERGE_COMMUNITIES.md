# C.C.I. SYSTEM — CERTIFICACIÓN TÉCNICA PRE-MERGE: SUBSISTEMA COMMUNITIES & EVOLUCIÓN v2.1.0

**Fecha:** 2026-11-06  
**Rama Auditada:** `feature/communities-phase0-design`  
**Rama Destino (Merge Target):** `main`  
**Estado de Auditoría (Revisión v6):** APROBADO PARA MERGE — Proyecto Docker Aislado (`cci_e2e_test_<rand>`) con Protección Verificada de Volúmenes Preexistentes + Runner Estricto Cero-Skips + TLS CA/Hostname Verificado + Relay TURN Bidireccional + CI Python 3.14 Autónomo  
**Suites Automatizadas:** 22 de 22 suites ejecutadas (`192 / 192` pruebas aprobadas, `0` fallidas, `0` errores, `0` omitidas / `total_skipped: 0`)

---

## 1. Confirmación Formal del Alcance del Merge (Cierre P0 / P2)

Se confirma explícitamente que la rama `feature/communities-phase0-design` consolida una **entrega unificada de lanzamiento (Release v2.1.0 + Communities)** sobre `main`. Los commits acumulados desde `main` corresponden intencionalmente a dos bloques funcionales integrados y verificados conjuntamente:

1. **Bloque 1 — Evolución Multiplataforma C.C.I. SYSTEM (Fases 0 a 10)**:
   - Backend base en Flask + Flask-SocketIO (`backend/`), autenticación JWT HMAC-SHA256, salas multijugador autoritativas a 60 Hz (`backend/davinci_bridge.py`), llamadas P2P locales sobre sockets UDP RTP RFC 3550 (`mobile/voice_client.py`), grabador asíncrono MP4 (`recorder/`), adaptadores móviles Android/iOS (`mobile/`, `ios/`) y suites `test_phase1_evolution.py` a `test_phase10_media_and_physics.py`.
2. **Bloque 2 — Subsistema CCI Communities y Pantallas Pixel-Art Nativas (Fases 0 a 7 + Estabilización Pre-Merge)**:
   - Persistencia relacional en SQLite 3 modo `WAL` (`backend/communities/repository.py`, [`schema_sqlite.sql`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/documentacion/communities/schema_sqlite.sql)), matriz jerárquica de permisos fail-closed, chat en tiempo real e historial paginado, plano de control de salas de voz con emisión de tokens LiveKit JWT (`TTL <= 300s`), botonera Sound Deck con decodificador real de tramas MPEG Layer III (`sound_validator.py`), adaptador local de streaming (`stream_adapter.py`), moderación jerárquica y auditoría, métricas `process_local`, pantallas nativas Pygame (`groups_ui.py`, `sidebar_ui.py`), manifiestos de despliegue (`deploy/`) y suites `test_communities_phase1.py` a `test_communities_merge_audit.py`.

---

## 2. Cierre de Hallazgos de la Revisión v5 (P0, P1, P2)

### 2.1 [P0] Runner Estricto (`run_all_evaluations.py`) con Conteo Explícito de `skipped` y Prohibición de Omisiones
- **Hallazgo v5**: `run_all_evaluations.py` calculaba `passed = tests_run - failures - errors` sin restar `skipped`, y `test_11` podía invocar `self.skipTest(...)` si Docker no estaba presente.
- **Solución Aplicada**:
  1. [`run_all_evaluations.py`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/run_all_evaluations.py) utiliza ahora una subclase estructurada `StructuredTestResult(unittest.TextTestResult)` que intercepta `addSuccess`, `addFailure`, `addError` y `addSkip` de cada método individual, calculando `passed = tests_run - failures - errors - skipped`.
  2. Si `total_skipped > 0`, el runner marca la suite como `[FAIL]` y termina con código de salida `1`.
  3. En [`test_communities_merge_audit.py`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_communities_merge_audit.py) (`test_10` y `test_11`) se eliminó todo uso de `skipTest`: la presencia de Docker CLI y del daemon activo se valida con `self.assertIsNotNone(shutil.which("docker"))` y `self.assertEqual(info_proc.returncode, 0)`.
  4. [`evaluations_report.json`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/evaluations_report.json) conserva `total_skipped: 0`, `skipped: 0` por suite, el hash `output_sha256` de la salida de cada suite y el arreglo `test_cases` con el `id`, `status` (`PASS`) y `elapsed_ms` de las 192 pruebas ejecutadas.

### 2.2 [P1] Validación Estricta de Cadena de Certificados TLS (`CERT_REQUIRED`) y Hostname (`check_hostname = True`)
- **Hallazgo v5**: `test_11` utilizaba `check_hostname = False` y `verify_mode = ssl.CERT_NONE`.
- **Solución Aplicada**:
  1. En [`test_11_live_docker_caddy_tls_wss_101_volume_restart_and_coturn_allocate`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_communities_merge_audit.py#L768-L826), se extrae la CA raíz generada por la PKI interna de Caddy (`/data/caddy/pki/authorities/local/root.crt`) directamente desde el contenedor `cci_communities_caddy`.
  2. Se construye un contexto estricto `verified_ctx = ssl.create_default_context(cadata=root_ca_pem)` con `verify_mode = ssl.CERT_REQUIRED` y `check_hostname = True`.
  3. Se verifica que cada conexión HTTPS y WSS hacia `server_hostname="api.ccisystem.org"` entregue un certificado X.509 validado (`tls_s.getpeercert()`) con Subject Alternative Name `('DNS', 'api.ccisystem.org')`.
  4. Se ejecutan dos **pruebas negativas obligatorias**:
     - Conectar sin la CA raíz confiable arroja `ssl.SSLCertVerificationError`.
     - Conectar hacia un hostname no coincidente (`untrusted.invalid.example`) es rechazado con `ssl.SSLError`.
  5. **Delimitación explícita de alcance TLS**: Esta prueba certifica la cadena X.509 y validación de hostname contra la CA local de Caddy (`tls internal`) en entorno Docker de integración; la emisión de certificados públicos ACME/Let's Encrypt corresponde al despliegue en staging/producción con DNS público.

### 2.3 [P1] Prueba de Relay de Medios TURN Bidireccional entre Dos Peers (`Allocate` + `CreatePermission` + `ChannelBind` + Transferencia UDP)
- **Hallazgo v5**: `test_11` comprobaba STUN Binding y TURN Allocate, pero no realizaba transferencia real de datos entre dos peers a través del puerto relay asignado.
- **Solución Aplicada**:
  1. En [`test_11`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_communities_merge_audit.py#L905-L985) se abren dos sockets UDP independientes (`peer_a` y `peer_b`).
  2. `peer_b` descubre su dirección reflexiva mediante `STUN Binding (0x0001 -> 0x0101)`.
  3. `peer_a` negocia `TURN Allocate (0x0003 -> 0x0113 Challenge -> 0x0103 Allocate Success)` con credenciales efímeras HMAC-SHA1 (`use-auth-secret`), obteniendo un puerto relay en el rango configurado `49152-49172/UDP`.
  4. `peer_a` autoriza a `peer_b` mediante `TURN CreatePermission (0x0008 -> 0x0108)`.
  5. **Transferencia de medios Peer B -> CoTURN Relay (`relay_port`) -> Peer A**: `peer_b` envía `b"CCI-TURN-RELAY-MEDIA-B2A"` al puerto relay de CoTURN y `peer_a` recibe un `STUN Data Indication (0x0017)` con atributo `DATA (0x0013)` idéntico al payload enviado y `XOR-PEER-ADDRESS (0x0012)` de `peer_b`.
  6. **Transferencia de medios Peer A -> CoTURN (`ChannelBind 0x4000`) -> Peer B**: `peer_a` vincula el canal `0x4000` (`ChannelBind 0x0009 -> 0x0109`) y transmite una trama `ChannelData` (`0x4000`) con `b"CCI-TURN-RELAY-MEDIA-A2B-CHANNEL-0x4000"`, verificando que `peer_b` recibe los bytes íntegros desde el puerto `relay_port` de CoTURN.
  7. **Delimitación explícita de alcance TURN**: Queda demostrado el relay bidireccional real de paquetes UDP entre dos clientes a través de `cci_communities_coturn` (`3478/UDP` y `49152-49172/UDP`). Las pruebas de travesía NAT desde una red WAN externa y `TURNS 5349/TLS` quedan documentadas como alcance de staging externo.

### 2.4 [P1] Alineación de Runtimes (`Python 3.14`) y Workflow CI GitHub Actions
- **Hallazgo v5**: El workflow CI declaraba Python 3.12 mientras el contenedor (`python:3.14-slim`) y el entorno local ejecutaban Python 3.14.
- **Solución Aplicada**:
  1. Se alineó [`.github/workflows/ci-communities-audit.yml`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/.github/workflows/ci-communities-audit.yml) a `python-version: "3.14"`, coincidiendo exactamente con `python:3.14-slim` en [`deploy/Dockerfile.api`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/deploy/Dockerfile.api) y con el intérprete local `Python 3.14.5`.
  2. Además, `test_11` verifica en tiempo de ejecución `docker exec cci_communities_api python --version` (`Python 3.14.x`) dentro del contenedor Linux activo.
  3. El workflow incluye un paso de compuerta explícito (`Verify Zero Skips and Mandatory Docker E2E Execution in Report`) que falla si `total_skipped != 0` o si `test_11` no registra `"status": "PASS"`, y publica `evaluations_report.json` como artifact vinculado al SHA (`evaluations-report-${{ github.sha }}`).

### 2.5 [P1/P2 Revisión v6] Aislamiento de Proyecto Docker (`COMPOSE_PROJECT_NAME` Único), Parametrización de Contenedores y Protección de Volúmenes Persistentes
- **Hallazgo v5/v6**: `test_11` ejecutaba `docker compose down -v --remove-orphans` sobre el proyecto por defecto y con nombres de contenedores fijos (`cci_communities_*`), lo que implicaba riesgo de detener contenedores o borrar volúmenes persistentes (`deploy_cci_app_data`) de una instalación previa.
- **Solución Aplicada**:
  1. En [`deploy/docker-compose.communities.yml`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/deploy/docker-compose.communities.yml) se parametrizaron los nombres de contenedores con `${CCI_CONTAINER_PREFIX:-cci_communities}_api`, `_livekit`, `_coturn` y `_caddy`, así como los puertos publicados (`API_HOST_PORT`, `CADDY_HTTP_PORT`, `CADDY_HTTPS_PORT`, `LIVEKIT_HTTP_PORT`, `LIVEKIT_RTC_TCP_PORT`, `TURN_PORT`).
  2. En [`test_11`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_communities_merge_audit.py#L719-L760), cada corrida genera un proyecto aislado único `test_project = f"cci_e2e_test_{secrets.token_hex(4)}"`, pasa `-p {test_project}` y `CCI_CONTAINER_PREFIX={test_project}`, y utiliza puertos de test aislados (`18080`, `18443`, `17880`, `17881`, `15050`).
  3. **Verificación explícita de no eliminación de volúmenes preexistentes**: Antes de iniciar el stack de test, `test_11` garantiza la existencia de los volúmenes preexistentes `deploy_cci_app_data` y `cci_preexisting_prod_guard_vol`; antes del teardown comprueba `self.assertIn("_test_", test_project)` y `self.assertTrue(test_project.startswith("cci_e2e_test_"))`, ejecuta `down -v` **únicamente** sobre `-p {test_project}`, y verifica con `docker volume inspect` que `deploy_cci_app_data` y `cci_preexisting_prod_guard_vol` permanecen intactos tras el teardown.
  4. **Autonomía en CI (`ubuntu-latest`) y Trazabilidad SHA**: Se dotó a [`test_phase2.py`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase2.py) y [`test_phase3.py`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/test_phase3.py) de arranque automático de `web/app.py` en `setUpClass` cuando el puerto `5050` no está activo en runners limpios de GitHub Actions, y se añadió `git_code_tree_sha256` en [`run_all_evaluations.py`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/run_all_evaluations.py) junto con la verificación `report["git_commit_sha"] == os.environ["GITHUB_SHA"]` en [`.github/workflows/ci-communities-audit.yml`](file:///Users/cami/Desktop/C.C.I%20SYSTEM/.github/workflows/ci-communities-audit.yml).

---

## 3. Checklist Final de Aprobación Pre-Merge (Revisión v5)

- [x] **[P0] Runner `run_all_evaluations.py` contabiliza `skipped` por separado y falla si `total_skipped > 0`**.
- [x] **[P0] `test_11` es obligatorio (sin `skipTest`) y aparece con `"status": "PASS"` en `evaluations_report.json`**.
- [x] **[P1] TLS validado con CA raíz de Caddy (`verify_mode=ssl.CERT_REQUIRED`, `check_hostname=True`, SAN `api.ccisystem.org`) y pruebas negativas de rechazo**.
- [x] **[P1] Relay de medios TURN bidireccional verificado entre `Peer A` y `Peer B` (`Allocate` + `CreatePermission` + `Data Indication 0x0017` + `ChannelBind 0x4000` + `ChannelData`)**.
- [x] **[P1] Runtimes alineados en Python 3.14 entre `.github/workflows/ci-communities-audit.yml`, `deploy/Dockerfile.api` y reporte de certificación**.
- [x] **[P2] Recreación forzada de contenedores y volúmenes (`--build --force-recreate` + teardown `down -v`) con secretos efímeros `secrets.token_hex(32)` por ejecución**.
