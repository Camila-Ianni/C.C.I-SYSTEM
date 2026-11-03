# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console & Retro Emulator

[![Web Oficial](https://img.shields.io/badge/Web%20Oficial-c--c--i--system.onrender.com-00f0ff?style=for-the-badge&logo=render&logoColor=white)](https://c-c-i-system.onrender.com)
[![macOS Release](https://img.shields.io/badge/Descargar-macOS%20(.dmg)-white?style=for-the-badge&logo=apple&logoColor=black)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg)
[![Windows Release](https://img.shields.io/badge/Descargar-Windows%20(.exe)-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe)

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![Flask](https://img.shields.io/badge/flask-3.1%2B-lightgrey)
![Architecture](https://img.shields.io/badge/architecture-State%20Machine-purple)
![Gamepads](https://img.shields.io/badge/gamepad-DualSense%20%7C%20Xbox%20%7C%20Generic-orange)
![Haptics](https://img.shields.io/badge/haptics-Rumble%20Feedback-success)
![Multi-User](https://img.shields.io/badge/multi--user-0%20Factory%20Profiles-cyan)

**C.C.I. SYSTEM** es una plataforma arcade integral y emulador multiplataforma desarrollado **100% en Python** con **Pygame-CE (Community Edition)** y orquestación web nativa en **Flask**. Unifica **19 clásicos arcade** bajo un entorno retrofuturista Cyberpunk / PS5 de ventana única (`1280x720`), máquina de estados determinista (`State Machine`), háptica universal plug & play, capturador HD y sistema multiusuario con gestión de estadísticas independientes.

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
| 1 | **Da Vinci Fighters** | C.C.I. System | 2026 | Acción / Lucha | Motor CPS-1 propio, combate 1P vs CPU y 2P Local, supers y cinemáticas. |
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

## 👤 Sistema Multiusuario Limpio (0 Perfiles de Fábrica)

- **Distribución Limpia:** El instalador parte con **0 perfiles precreados** para que cada usuario cree su cuenta personalizada desde el primer boot.
- **Datos Segregados:** Archivos JSON independientes (`.cci-user-data/users/{usuario}.json`) para horas de juego, récords, favoritos y trofeos.
- **Selector de Avatares:** 8 personajes ciberpunk con anillo luminoso de neón.
- **Cambio Rápido:** Alterna de usuario en cualquier momento desde el menú con `F3`.

---

## 📳 Sistema Háptico & Mandos Plug & Play (`cci_rumble.py`)

- Soporte nativo para mandos **Sony DualSense (PS5), DualShock 4, Xbox Series/One, Switch Pro y USB arcade**.
- **Retroalimentación por eventos:** Vibración adaptativa en golpes (`hit_rumble`), daño sostenido (`damage_rumble`), explosiones (`explosion_rumble`) y navegación sutil (`light_rumble`).
- **Captura HD Instantánea:** Presionando `F12` guarda un screenshot 720p sin pérdidas en la carpeta `capturas/` con notificación toast.

---

## 💻 Ejecución para Desarrolladores

Si prefieres ejecutar o modificar el código fuente localmente:

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
```

### 2. Configurar Entorno Virtual
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 4. Lanzar la Consola Emulada o el Servidor Web
```bash
# Iniciar la consola virtual retro
python main.py

# Iniciar la landing page web oficial
python run_web.py
```

---

## 📁 Estructura del Repositorio

```text
C.C.I-SYSTEM/
├── main.py                     # Entry point de la consola virtual en Pygame-CE
├── emulator.py                 # Launcher y verificador integral multiplataforma
├── run_web.py                  # Servidor de producción Flask de la landing page
├── catalog_data.py             # Metadatos del catálogo oficial de 19 juegos (100% Python)
├── build_distribution.py       # Generador de instaladores nativos (.dmg y .exe)
├── states.py                   # Máquina de estados finita (Boot, Intro, Menu, Playing)
├── user_select_state.py        # Selector interactivo de jugadores y creación de perfiles
├── cci_console.py              # Hub: Biblioteca, Perfil, Logros y Configuración
├── cci_rumble.py               # Motor de vibración háptica universal para joysticks
├── screenshot_manager.py       # Módulo capturador de pantalla F12
├── api/
│   └── index.py                # Entrypoint serverless WSGI
├── web/
│   ├── app.py                  # Aplicación web Flask oficial
│   └── landing_page.py         # Generador de landing page interactiva Cyberpunk
├── fotos web/                  # Logos e ilustraciones oficiales de los 19 juegos para la web
├── assets_cards/               # Tarjetas y carátulas nativas para la consola
├── pantallas/                  # Fondos y paneles de interfaz
├── documentacion/              # Especificación técnica, SRS IEEE 830 y manuales
├── requirements.txt            # Dependencias ligeras para hosting cloud (Flask)
└── requirements-dev.txt        # Dependencias completas para el emulador (Pygame-CE, OpenCV, Pymunk)
```

---

## 👩‍💻 Autora & Dirección de Proyecto

Desarrollado y diseñado por **Camila Carolina Ianni**  
*Estudiante de Analista de Sistemas — Escuela Da Vinci (2026)*  
GitHub: [@Camila-Ianni](https://github.com/Camila-Ianni)  
Web del Proyecto: [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)
