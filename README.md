# 🎮 C.C.I. SYSTEM — OmniDash Virtual Console (Dark Glass / Frutiger Aero)

[![GitHub Repo](https://img.shields.io/badge/GitHub-Camila--Ianni%2FC.C.I--SYSTEM-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Camila-Ianni/C.C.I-SYSTEM)
[![Web Oficial](https://img.shields.io/badge/Web%20Oficial-c--c--i--system.onrender.com-00f0ff?style=for-the-badge&logo=render&logoColor=white)](https://c-c-i-system.onrender.com)

![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue)
![PySide6](https://img.shields.io/badge/UI%20Engine-PySide6%20(Qt6%20Dark%20Glass)-00d2ff)
![Libretro](https://img.shields.io/badge/Runner-Libretro%20Native%20Cores-10b981)
![Architecture](https://img.shields.io/badge/Motor-Lector%20Local%20(Sin%20URLs%20Externas)-orange)
![Database](https://img.shields.io/badge/database-SQLite%203%20(WAL%20Mode)-6366f1)
![Voice Chat](https://img.shields.io/badge/voice-LiveKit%20SFU%20%2B%20CoTURN%20UDP-cyan)
![Docker](https://img.shields.io/badge/deploy-Docker%20Compose%20(4%20services)-2496ED)

**C.C.I. SYSTEM (v2.1.0)** es una consola virtual de escritorio lista para jugar (**Plug & Play**) desarrollada en **Python + PySide6 (Qt 6)** bajo la estética **OmniDash Dark Glass / Frutiger Aero**. Al abrir la consola, el usuario accede directamente a su biblioteca completa con carátulas oficiales, fichas cinematográficas y lanzamiento inmediato a **60 FPS** vía **núcleos Libretro (`retro_core_runner.py`)**, junto con un ecosistema social integrado en tiempo real (**CCI Communities**, voz UDP/LiveKit, chat y streaming local).

🌐 **Sitio Web Oficial:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)

---

## ✨ Estética OmniDash: Dark Glass & Frutiger Aero

La interfaz principal dejó atrás el menú retro anterior basado en minigames propios en Pygame para evolucionar hacia una experiencia de consola moderna inspirada en **PlayStation 5 y Xbox Dashboard** (`omnidash_qt.py`):

- **Cristal Líquido y Desenfoque Óptico (`AcrylicGlassCard`):** Tarjetas y paneles con muestreo en tiempo real del fondo desenfocado (`GLOBAL_BLURRED_BG`), película oscura translúcida, reflejo especular superior Liquid Glass, bisel luminoso superior blanco/plata y sombras suaves de profundidad.
- **Liquid Glass Dock Superior (`OmniDashNavBar`):** Navegación flotante superior con marca `C.C.I. SYSTEM` / cápsula de perfil del jugador, pestañas activas con brillo cian (**Inicio**, **Biblioteca**, **Comunidades**, **Amigos**, **Ajustes**), indicadores de estado y reloj del sistema.
- **Renderizado HiDPI / Retina Nativo:** Escalado nítido de carátulas, fondos dinámicos y tipografía adaptativa para resoluciones desde `1280×720` hasta pantallas Retina/4K (`1672×941`+).

---

## 🖥️ Pantallas y Funcionalidades Principales

### 1. 🏠 Inicio (`HomeView`)
- Saludo personalizado al usuario y barra lateral de acento cian.
- **4 Tarjetas Principales de Cristal Acrílico** con iluminación de enfoque diferenciada: **Mis juegos y apps**, **Amigos**, **GAME PASS** y **Logros**.
- **Carrusel de Actividad Reciente:** Acceso directo de un clic a los últimos títulos jugados con navegación por teclado, paginación y control rápido.
- **Panel Inferior:** Accesos a **Novedades en C.C.I.**, **Eventos y torneos** y **Transmisiones en vivo**.

### 2. 📚 Biblioteca (`LibraryView`)
- **Sidebar de Cristal Esmerilado:** Botón de regreso rápido, medidor visual de almacenamiento (`Storage`), buscador instantáneo en tiempo real y filtros por consola/plataforma:
  - **Todas** · **Super Nintendo** · **Arcade MAME** · **Nintendo 64** · **PlayStation 1** · **Nintendo DS** · **Neo-Geo** · **Game Boy Advance** · **Nintendo Wii**
- **Catálogo Visual Dual:** Alternancia entre vista en cuadrícula de carátulas oficiales (`fotos juegos/`) y vista en lista, con indicador de favoritos y estado local o metadato pendiente (*En la nube / No instalado*).

### 3. 🎯 Ficha del Videojuego (`GameDetailsView` / `GameDetailsGlassShell`)
- **Contenedor Esmerilado Semi-Opaco:** Panel redondeado de cristal oscuro consistente con Biblioteca, enmarcado sobre el wallpaper activo.
- **Hero Panorámico (`30% / 52% / 18%`):**
  - Izquierda: botón `Volver`, título con tipografía adaptativa para nombres largos, subtítulo (`Plataforma · Desarrolladora · Año`), botón principal **JUGAR** en cian y **FAVORITO**.
  - Centro: ilustración panorámica integrada con desvanecimiento lateral hacia el panel de texto.
  - Derecha: carátula vertical (`BoxArtCoverLabel`) con bordes redondeados y contorno acentuado.
- **Columna Izquierda (`Información`):** Sinopsis del título y metadatos estructurados (`Género`, `Plataforma`, `Desarrollador`, `Lanzamiento`, `Jugadores`).
- **Columna Derecha (`Tu actividad` + `Capturas del juego`):**
  - 4 tarjetas de cristal (`Última vez jugado`, `Tiempo jugado`, `Partidas guardadas`, `Progreso`) con **iconografía SVG lineal cian**.
  - Galería interactiva `16:9` de capturas de gameplay con visor modal ampliado al hacer clic.
- **Acordeón Plegable (`Información técnica`):** Mantiene la ficha limpia y oculta por defecto los datos avanzados (núcleo Libretro asignado, ruta local de ROM, región/revisión y resultado de verificación física).

### 4. 🌐 Comunidades & Amigos (`CommunitiesView` + `backend/communities/`)
- Ecosistema social integrado directamente dentro de la interfaz Dark Glass de OmniDash (`OmniDashMainWindow` + `groups_ui.py` / `backend/communities/`):
  - **Hub de Comunidades y Explorador:** Pestañas de comunidades unidas, descubrimiento y solicitudes.
  - **Canales de Texto y Voz:** Chat en tiempo real con Socket.IO, cursor pagination, reacciones, **@menciones**, adjuntos de capturas y Sound Deck MP3 validado por inspección binaria.
  - **Transmisiones y Voz:** Reproductor **PiP / modo Teatro**, tarjetas de estado de transmisión en vivo, motor de voz UDP/RTP (`48 kHz`), plano de control **LiveKit JWT + CoTURN HMAC-SHA1** y moderación jerárquica **RBAC Fail-Closed** con bitácora de auditoría en SQLite WAL.

### 5. ⚙️ Ajustes (`SettingsView`)
- Personalización en vivo del **Wallpaper del Sistema** con miniaturas previsualizables y selector de imágenes locales personalizadas (`QFileDialog`), recalculando instantáneamente el mapa de desenfoque óptico (`update_global_blurred_wallpaper`) en todas las vistas.

---

## ⚖️ Arquitectura Técnica y Marco Legal ("Lector Local de Archivos Sin URLs")

El motor de catalogación y ejecución separa claramente la experiencia inmediata de consola de la arquitectura técnica del software:

1. **Experiencia Directa de Consola (Entrar y Jugar):**
   - El sistema detecta y organiza automáticamente el almacenamiento local integrado (`roms/` + `cores/`) al iniciar, mostrando en **Inicio** y **Biblioteca** los títulos listos para ejecutar a un clic con sus carátulas oficiales, metadatos, capturas y soporte de mandos sin configuración técnica previa.
2. **Arquitectura de Lector/Intérprete Local (Análogo a un reproductor multimedia):**
   - A nivel de diseño, el software actúa como un **lector e intérprete local de archivos de respaldo y núcleos Libretro** alojados en disco: **no incorpora URLs de descarga externas, enlaces a sitios de terceros ni scrapers remotos de ROMs** (`REMOTE_CATALOG_METADATA` en `backend/games/scanner_service.py` contiene únicamente metadatos descriptivos neutros y cero enlaces externos).
3. **Inspección de Cabeceras y Verificación Física (`GameLibraryScannerService` & `ROMMetadataExtractor`):**
   - [`GameLibraryScannerService`](backend/games/scanner_service.py) indexa el directorio local `roms/` (`snes`, `mame`, `n64`, `ps1`, `nds`, `gba`, `neogeo`, `wii`), sincroniza el catálogo en SQLite (`cci_system.sqlite3`) y valida cabeceras internas junto con la integridad de imágenes de disco (`.cue`/`.bin`) mediante [`ROMMetadataExtractor`](backend/games/rom_metadata.py).
   - Antes de iniciar una partida, `verify_game_file()` confirma la presencia local del archivo y su núcleo Libretro correspondiente; las fichas de catálogo marcadas como `on_demand` / `remote_metadata` permanecen como fichas informativas neutras sin descarga automática externa.
4. **Ejecución Nativa vía Libretro (`retro_core_runner.py`):**
   - [`LibretroRunner`](retro_core_runner.py) carga dinámicamente mediante `ctypes` los núcleos compatibles en `cores/` (como `snes9x`, `mame2003_plus`, `mupen64plus_next`, `pcsx_rearmed`, `melonds`, `vba_next`, `fbneo`, `dolphin`), renderizando vídeo (`XRGB8888`, `RGB565`, `0RGB1555`) y audio estéreo PCM a `60 FPS` con soporte de mandos hápticos (`cci_rumble.py`).

---

## 💻 Puesta en Marcha

### 1. Instalar Git LFS y obtener la Consola
Los juegos y núcleos grandes se distribuyen mediante [Git LFS](https://git-lfs.com/). Instalá Git LFS y activalo antes de clonar; después ejecutá `git lfs pull` para descargar los archivos completos:
```bash
git lfs install
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
git lfs pull
```
La opción **Download ZIP** de GitHub contiene referencias LFS, no las ROMs completas; usá el clon con Git LFS para tener la biblioteca lista para jugar.

### 2. Crear Entorno Virtual e Instalar Dependencias
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt PySide6
```

### 3. Iniciar la Consola o Servicios
```bash
# Interfaz principal OmniDash Dark Glass (PySide6) — consola lista para jugar
python run_omnidash.py
# (equivalente: python run_omnidash_qt.py)

# Servidor Backend Comunidades / API REST + Socket.IO (puerto 5050)
python -m backend.server

# Plataforma web / landing page
python run_web.py
```

> *(Opcional)* Si querés sumar copias adicionales propias en disco, podés colocarlas en `roms/<plataforma>/` y el escáner en caliente las indexa automáticamente en Biblioteca.

---

## 🐳 Despliegue de Comunidades con Docker Compose (`deploy/`)

El directorio `deploy/` contiene la topología de 4 contenedores (`api`, `livekit`, `coturn`, `caddy`) con base de datos SQLite en modo WAL, TLS/WSS y relay TURN:

```bash
cp deploy/.env.communities.example deploy/.env.communities
docker compose -f deploy/docker-compose.communities.yml --env-file deploy/.env.communities up -d --build
```

---

## ✅ Pruebas y Verificación

El proyecto incluye suites modulares en `unittest` y un auditor central (`run_all_evaluations.py` con 23 suites registradas en `CORE_EVOLUTION_SUITES`):

```bash
# Verificación de escaneo local, metadatos ROM e integridad pre-lanzamiento
python test_game_library_scanner.py

# Verificación de la UI de Comunidades y máquina de estados
python test_communities_ui.py

# Ejecución integral de auditoría y generación de evaluations_report.json
python run_all_evaluations.py
```

---

## 📁 Estructura del Repositorio

```text
C.C.I-SYSTEM/
├── run_omnidash.py                    # Lanzador principal de OmniDash (PySide6 Dark Glass)
├── run_omnidash_qt.py                 # Entry point directo de Qt6 OmniDash
├── omnidash_qt.py                     # Interfaz completa: NavBar, Home, Library, GameDetails, Communities, Settings
├── omnidash_engine.py / omnidash_screens.py  # Motores auxiliares y pantallas complementarias
├── retro_core_runner.py               # Ejecutor modular Libretro por FFI/ctypes (vídeo/audio/input a 60 FPS)
├── backend/
│   ├── server.py                      # Servidor Flask + Flask-SocketIO (puerto 5050)
│   ├── games/
│   │   ├── scanner_service.py         # Lector físico de carpeta roms/, caché SQLite y verify_game_file()
│   │   └── rom_metadata.py            # Limpieza No-Intro/Redump, detección de región e integridad .cue/.bin
│   └── communities/                   # Subsistema CCI Communities (SQLite WAL, RBAC, LiveKit, voz y streaming)
├── assets_omnidash/                   # Iconografía Dark Glass, banners panorámicos y capturas
├── fotos juegos/                      # Carátulas locales indexadas para Biblioteca e Inicio
├── roms/ & cores/                     # Directorios locales para copias del usuario y cores Libretro
├── deploy/                            # Stack Docker Compose (api, livekit, coturn, caddy)
├── mobile/ & ios/                     # Adaptaciones táctiles móviles y cliente RTP
├── recorder/                          # Grabador asíncrono de gameplay MP4
├── web/                               # Sitio web Flask y API pública
├── run_all_evaluations.py             # Runner auditor de las suites de prueba
├── test_game_library_scanner.py       # Tests del lector físico de ROMs y catálogo
└── test_communities_ui.py             # Tests de interfaz y navegación de Comunidades
```

---

## 👩‍💻 Autora & Dirección de Proyecto

Desarrollado y diseñado por **Camila Carolina Ianni**  
*Analista de Sistemas — Escuela Da Vinci (2026)*

- 🐙 **GitHub:** [@Camila-Ianni](https://github.com/Camila-Ianni) · [C.C.I-SYSTEM](https://github.com/Camila-Ianni/C.C.I-SYSTEM)
- 🌐 **Web Oficial:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)
