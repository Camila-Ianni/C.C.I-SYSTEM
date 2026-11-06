# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console & Retro Emulator (v2.1.0)

[![GitHub Repo](https://img.shields.io/badge/GitHub-Camila--Ianni%2FC.C.I--SYSTEM-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Camila-Ianni/C.C.I-SYSTEM)
[![Web Oficial](https://img.shields.io/badge/Web%20Oficial-c--c--i--system.onrender.com-00f0ff?style=for-the-badge&logo=render&logoColor=white)](https://c-c-i-system.onrender.com)
[![macOS Release](https://img.shields.io/badge/Descargar-macOS%20(.dmg)-white?style=for-the-badge&logo=apple&logoColor=black)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg)
[![Windows Release](https://img.shields.io/badge/Descargar-Windows%20(.exe)-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe)
[![Android Support](https://img.shields.io/badge/Android-APK%20(Buildozer)-brightgreen?style=for-the-badge&logo=android&logoColor=white)](#-soporte-móvil-android--ios)
[![iOS Support](https://img.shields.io/badge/iOS-IPA%20(Xcode%20Blueprint)-lightgrey?style=for-the-badge&logo=apple&logoColor=black)](#-soporte-móvil-android--ios)

![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![Tests](https://img.shields.io/badge/tests-22%20suites%20%2F%20192%20passed%20(0%20skips)-success)
![Database](https://img.shields.io/badge/database-SQLite%203%20(WAL%20Mode)-orange)
![Multiplayer](https://img.shields.io/badge/multiplayer-60%20Hz%20Authoritative-purple)
![Voice Chat](https://img.shields.io/badge/voice-LiveKit%20SFU%20%2B%20CoTURN%20UDP-cyan)
![Recorder](https://img.shields.io/badge/recorder-MP4%20Async%20Worker-red)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose%20(4%20services)-2496ED)

**C.C.I. SYSTEM** es una plataforma arcade integral y emulador multiplataforma desarrollado **100% en Python** con **Pygame-CE (Community Edition)** y orquestación web/tiempo real en **Flask + Flask-SocketIO** (`puerto 5050`). Unifica **19 clásicos arcade** bajo un entorno retrofuturista Cyberpunk / PS5 de ventana única (`1280x720`, 60 FPS), módulo nativo de **Comunidades (`CCI Communities`: grupos pixel-art, canales de texto/voz, chat en tiempo real con clipping independiente, Sound Deck MP3 con inspección binaria MPEG Layer III, plano de control de voz LiveKit SFU + CoTURN UDP relay, streaming local y moderación jerárquica RBAC fail-closed)**, multijugador online autoritativo a 60 Hz, grabador de gameplay en segundo plano, persistencia relacional en **SQLite 3 (modo WAL)** y adaptación móvil táctil para Android e iOS.

🌐 **Sitio Web Oficial en Producción:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)

---

## 📦 Descargas Oficiales (Instaladores de 1-Clic)

Para jugar de inmediato sin necesidad de abrir la terminal ni instalar Python manualmente:

| Plataforma | Formato | Instalación | Enlace Directo |
| :--- | :--- | :--- | :--- |
| **macOS** | `.dmg` (Apple Disk Image) | Abre el archivo `.dmg`, ejecuta `C.C.I. SYSTEM.app` y sigue el asistente interactivo (Escritorio por defecto). | [📥 Descargar para Mac (734 MB)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg) |
| **Windows** | `.exe` (Instalador GUI) | Haz doble clic en el ejecutable `.exe` y sigue el instalador gráfico interactivo. | [📥 Descargar para Windows (628 MB)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe) |

> ⚠️ **Nota para macOS (Primer Inicio):** Al ser un emulador open-source independiente, la primera vez haz **Clic derecho (o Control + Clic)** sobre `C.C.I. SYSTEM` y selecciona **«Abrir»** (o autorízalo en *Ajustes del Sistema > Privacidad y Seguridad > «Abrir igualmente»*). ¡Solo se realiza una única vez!

---

## 🎮 Catálogo Oficial Integrado (19 Títulos)

La consola incluye 19 videojuegos accesibles desde la Biblioteca, el Carrusel 3D y la Landing Page oficial:

| # | Juego | Desarrollador | Año | Género | Características |
| :-: | :--- | :--- | :-: | :--- | :--- |
| 1 | **Da Vinci Fighters** | C.C.I. System | 2026 | Acción / Lucha | Motor CPS-1 propio, combate 1P vs CPU, 2P Local y Online 60 Hz, supers y cinemáticas. |
| 2 | **Asteroids** | Atari | 1979 | Arcade / Shooter | Físicas vectoriales, inercia, disparos reactivos y puntuación. |
| 3 | **Super Mario Bros** | Nintendo | 1985 | Plataformas | Motor modular por estados, físicas precisas y niveles clásicos. |
| 4 | **The Legend of Zelda** | Nintendo | 1986 | Acción / RPG | Exploración top-down en Hyrule, armas, magias e inventario. |
| 5 | **Pac-Man** | Namco | 1980 | Arcade / Laberinto | IA de fantasmas basada en cuadrícula, pellets y audio original. |
| 6 | **Tetris** | C.C.I. System | 2026 | Puzzle | Caída de tetriminos, rotación, líneas y aceleración progresiva. |
| 7 | **Space Invaders** | Taito | 1978 | Shooter / Arcade | Oleadas alienígenas descendentes, bunkers destructibles y ovnis. |
| 8 | **Metal Slug** | SNK | 1996 | Acción / Shooter | Run & Gun clásico, física de proyectiles y vehículos de combate. |
| 9 | **DOOM** | id Software | 1993 | Shooter / FPS | Motor 3D por Raycasting, enemigos animados y captura de mouse. |
| 10 | **Flappy Bird** | C.C.I. System | 2026 | Arcade | Vuelo y esquive de tuberías con detección de colisiones al píxel. |
| 11 | **Dino Run** | C.C.I. System | 2026 | Arcade / Runner | Salto y agachado esquivando cactus y pterodáctilos. |
| 12 | **Ghostbusters** | C.C.I. System | 2026 | Acción / Aventura | Scroll lateral con parallax, captura de espectros y armamento. |
| 13 | **Cyberpunk Metroidvania** | C.C.I. System | 2026 | Acción / Plataformas | Ambientación distópica, exploración vertical y parkour. |
| 14 | **Pokémon** | Game Freak | 1996 | RPG / Aventura | Aventura clásica por Kanto, combate por turnos y selección de ataques. |
| 15 | **Mega Man** | Capcom | 1987 | Acción / Plataformas | Disparos buster, saltos milimétricos y jefes de nivel. |
| 16 | **Castlevania** | Konami | 1986 | Acción / Plataformas | Látigo Vampire Killer, velas, subarmas y ambientación gótica. |
| 17 | **Bubble Bobble** | Taito | 1986 | Arcade / Plataformas | Disparo de burbujas, atrapado de enemigos y frutas bonus. |
| 18 | **Plants vs. Zombies** | PopCap | 2009 | Estrategia / Defense | Siembra estratégica de plantas, recolección de soles y hordas zombi. |
| 19 | **Donkey Kong** | Nintendo | 1981 | Arcade / Plataformas | Escalada por andamios metálicos esquivando barriles rodantes. |

---

## 🌐 Subsistema CCI Communities & Grupos (`groups_ui.py` + `backend/communities/`)

El módulo nativo **CCI Communities** integra un ecosistema social completo dentro de la ventana Pygame-CE (`1280x720`) y del servidor en tiempo real:

- **Hub de Grupos Pixel-Art (`GroupsScreen`):**
  - Pestañas dedicadas para **MIS GRUPOS**, **CHATS PRIVADOS** y **SOLICITUDES**, buscador instantáneo, creación de grupos (`+ CREAR GRUPO`) y unión por código de invitación (`UNIRSE CON CÓDIGO`).
  - Tarjetas interactivas con insignia de rol (`ADMIN`, `MOD`, `MIEMBRO`), contador de integrantes en línea y acceso directo a la comunidad.
- **Vista de Comunidad (`CommunityViewScreen`):**
  - **Árbol de Canales:** Categorías colapsables de **INFORMACIÓN** (`# bienvenida`, `# reglas`, `# anuncios`), **CANALES DE TEXTO** (`# general`, `# clips`, `# memes`) y **SALAS DE VOZ** (`🔊 Sala General`, `🔊 Squad 1`) con avatares y estados de micrófono en vivo.
  - **Chat en Tiempo Real con Scroll Independiente:** Renderizado con recorte (`surface.set_clip`), paginación por cursor compuesto (`created_at, id`), reacciones rápidas, adjuntos y barra de entrada dedicada.
  - **Panel Derecho de Miembros & Sound Deck MP3:** Lista de miembros agrupados por estado (`CONECTADOS` / `DESCONECTADOS`), botonera de efectos de sonido MP3 (**Sound Deck**) con validación binaria de cabeceras ID3v2 / tramas MPEG Layer III reales (`sound_validator.py`) y controles de voz (`Silenciar`, `Ensordecer`, `Compartir pantalla`, `Colgar`).
- **Seguridad y Moderación Jerárquica (RBAC Fail-Closed):**
  - Permisos bitmask granulares (`VIEW_CHANNEL`, `SEND_MESSAGES`, `CONNECT_VOICE`, `SPEAK_VOICE`, `STREAM_VIDEO`, `USE_SOUND_DECK`, `KICK_MEMBERS`, `BAN_MEMBERS`, `MANAGE_CHANNELS`, `MANAGE_ROLES`, `ADMINISTRATOR`) con precedencia explícita de `deny_bits` sobre `allow_bits`.
  - Jerarquía estricta (`owner > admin > mod > member`) y bitácora inmutable de auditoría (`moderation_audit_log`).
- **Plano de Control de Voz, Streaming y Relay TURN:**
  - Emisión de tokens **LiveKit JWT (`HS256`, `TTL <= 300s`)** vinculados criptográficamente a `user_id`, `community_id`, `channel_id` y `session_id`, más credenciales **TURN REST HMAC-SHA1** efímeras (`coturn`) para atravesar NATs simétricos.
  - Adaptador de captura y previsualización de transmisión local (`stream_adapter.py`) a 720p/30fps.

---

## 🚀 Evolución Multiplataforma: Multijugador 60 Hz, Voz, Grabación y Móvil

- **⚔️ Multijugador Autoritativo a 60 Hz (`backend/davinci_bridge.py` + `net_Rollback`):**
  - Sincronización determinista de combate para **Da Vinci Fighters** sobre WebSockets (`Flask-SocketIO`), predicción en cliente y reconciliación de estado en servidor con latencia compensada.
- **🎙️ Chat de Voz P2P & Salas (`mobile/voice_client.py`):**
  - Transporte de audio de baja latencia por paquetes UDP RTP y señalización integrada con el backend unificado.
- **🎥 Grabador Asíncrono de Gameplay (`recorder/`):**
  - Captura de partidas en segundo plano mediante worker multiproceso sin bloquear el bucle de 60 FPS de Pygame-CE, exportando video MP4 listo para compartir en canales de `# clips`.
- **📱 Soporte Móvil: Android & iOS (`mobile/` + `ios/`):**
  - Controles táctiles superpuestos (cruceta virtual y botones arcade adaptativos), empaquetado Android APK mediante `buildozer.spec` y blueprint nativo de Xcode para iOS (`ios/`).

---

## 👤 Sistema Multiusuario Limpio & Mandos Hápticos (`cci_rumble.py`)

- **Distribución Limpia (0 Perfiles de Fábrica):** Cada instalación inicia limpia para que cada jugador cree su perfil personalizado (`.cci-user-data/users/{usuario}.json`) con selector de 8 avatares ciberpunk y cambio rápido con `F3`.
- **Vibración Háptica Plug & Play:** Soporte nativo para **Sony DualSense (PS5), DualShock 4, Xbox Series/One, Switch Pro y USB arcade** (`hit_rumble`, `damage_rumble`, `explosion_rumble`, `light_rumble`).
- **Captura HD Instantánea (`F12`):** Guarda screenshots 720p sin pérdidas en `capturas/`.

---

## 💻 Ejecución para Desarrolladores

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
```

### 2. Configurar Entorno Virtual e Instalar Dependencias
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 3. Lanzar la Consola Emulada o el Servidor Unificado
```bash
# Iniciar la consola virtual retro (1280x720 @ 60 FPS)
python main.py

# Iniciar el servidor unificado (API REST + Socket.IO + Communities en puerto 5050)
python -m backend.server

# Iniciar la landing page web oficial
python run_web.py
```

---

## 🐳 Despliegue con Docker Compose (`deploy/`)

El directorio `deploy/` incluye la topología reproducible de **4 contenedores** (`api`, `livekit`, `coturn`, `caddy`) con persistencia en volúmenes Docker y proxy inverso TLS/WSS:

```bash
# 1. Crear archivo de variables de entorno a partir de la plantilla
cp deploy/.env.communities.example deploy/.env.communities
# (Edita deploy/.env.communities con secretos criptográficos de >= 32 caracteres)

# 2. Levantar el stack completo de producción/staging
docker compose -f deploy/docker-compose.communities.yml --env-file deploy/.env.communities up -d --build
```

- **Persistencia garantizada:** Base de datos SQLite WAL y adjuntos MP3 en el volumen nombrado `cci_app_data` (`/data/communities.db` y `/data/uploads`).
- **TLS / WSS y Relay TURN:** `Caddy` gestiona HTTPS/WSS (`tls internal` en entorno local/CI o ACME Let's Encrypt en dominio público) y `coturn` provee relay UDP/TCP autenticado por HMAC-SHA1.

---

## ✅ Suite de Certificación Automatizada (22 Suites / 192 Pruebas)

El proyecto cuenta con un runner unificado (`run_all_evaluations.py`) que ejecuta las **22 suites de pruebas (192 casos de prueba, 0 fallos, 0 errores y 0 pruebas omitidas)**, incluyendo pruebas E2E en vivo con Docker Compose (`Caddy TLS X.509 + WebSocket 101 + Persistencia de Volúmenes + Relay Bidireccional UDP TURN`):

```bash
python run_all_evaluations.py
```

El reporte auditable se genera automáticamente en `evaluations_report.json` e incluye el hash SHA-256 del árbol de código certificado (`git_code_tree_sha256`).

---

## 📁 Estructura del Repositorio

```text
C.C.I-SYSTEM/
├── main.py                              # Entry point de la consola virtual en Pygame-CE (60 FPS)
├── groups_ui.py                         # Hub de Grupos y Vista de Comunidad pixel-art (Pygame-CE)
├── sidebar_ui.py                        # Barra lateral global (Inicio, Juegos, Grupos, Perfil...)
├── run_all_evaluations.py               # Runner de certificación (22 suites / 192 tests passing, 0 skips)
├── evaluations_report.json              # Reporte auditable de certificación y trazabilidad SHA
├── backend/
│   ├── server.py                        # Servidor unificado Flask + Flask-SocketIO (puerto 5050)
│   ├── davinci_bridge.py                # Motor autoritativo 60 Hz para Da Vinci Fighters Online
│   └── communities/                     # Subsistema CCI Communities (SQLite WAL, RBAC, LiveKit, MP3, Stream)
├── deploy/                              # Docker Compose (api, livekit, coturn, caddy) y configs de red
├── mobile/                              # Adaptación táctil móvil y cliente de voz UDP RTP
├── ios/                                 # Blueprint de empaquetado nativo para iOS (Xcode)
├── recorder/                            # Grabador asíncrono de gameplay a MP4 en segundo plano
├── catalog_data.py                      # Metadatos del catálogo oficial de 19 juegos (100% Python)
├── cci_database.py                      # Capa de persistencia SQLite relacional (WAL mode, foreign keys)
├── cci_sync.py                          # Cliente de sincronización en segundo plano (Daemon Thread)
├── cci_updater.py                       # Módulo de auto-actualización y gestión de versiones SemVer
├── version.json                         # Manifiesto canónico de versión y metadata oficial (v2.1.0)
├── build_distribution.py                # Generador de instaladores nativos (.dmg y .exe)
├── installer.py                         # Asistente gráfico de instalación interactiva 1-clic
├── states.py                            # Máquina de estados finita (Boot, Intro, Menu, Playing)
├── user_select_state.py                 # Selector interactivo de jugadores y creación de perfiles
├── cci_console.py                       # Hub: Biblioteca, Perfil, Logros y Configuración
├── cci_rumble.py                        # Motor de vibración háptica universal para joysticks
├── screenshot_manager.py                # Módulo capturador de pantalla F12
├── web/
│   ├── app.py                           # Aplicación web Flask oficial y API REST v1
│   └── landing_page.py                  # Landing page interactiva, Salón de la Fama y Video en vivo
├── documentacion/                       # Especificación técnica, arquitectura, SRS y certificación
├── test_communities_merge_audit.py      # Suite de auditoría pre-merge y E2E Docker/TLS/WSS/TURN
├── requirements.txt                     # Dependencias para servidor cloud y API
└── requirements-dev.txt                 # Dependencias completas (Pygame-CE, Socket.IO, PyJWT, OpenCV)
```

---

## 👩‍💻 Autora & Dirección de Proyecto

Desarrollado y diseñado por **Camila Carolina Ianni**  
*Estudiante de la carrera de Analista de Sistemas — Escuela Da Vinci (2026)*  

* 🐙 **GitHub:** [@Camila-Ianni](https://github.com/Camila-Ianni) · [Repositorio C.C.I-SYSTEM](https://github.com/Camila-Ianni/C.C.I-SYSTEM)
* 🚀 **Plataforma Web en Producción:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)
