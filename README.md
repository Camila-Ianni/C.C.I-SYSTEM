# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![OpenCV](https://img.shields.io/badge/opencv--python-4.8%2B-red)
![Architecture](https://img.shields.io/badge/architecture-State%20Machine-purple)
![Gamepads](https://img.shields.io/badge/gamepad-DualSense%20%7C%20Xbox%20%7C%20Generic-orange)

**C.C.I. SYSTEM** es una plataforma arcade integral desarrollada en **Python** y **Pygame-CE (Community Edition)**. Unifica seis títulos arcade clásicos y de autor bajo un entorno gráfico retrofuturista de ventana única (`1280x720`), orquestado mediante un patrón arquitectónico de **Máquina de Estados Finita (State Machine)** con aislamiento estricto de entornos y namespaces.

---

## 🎮 Videojuegos Integrados (6 Títulos)

La consola incluye un catálogo de 6 juegos organizados en una cuadrícula interactiva con preview dinámica:

| Juego | Género | Motor / Características |
| :--- | :--- | :--- |
| **Da Vinci Fighters** | Lucha 2D Arcade (CPS-1 Style) | Motor propio de combate, soporte 1P vs CPU y 2P Local, selector de personajes, supers, combos y cinemáticas. |
| **Metal Slug: Super Vehicle-001** | Run & Gun | Motor de físicas Pymunk, renderizado multicapa y vehículos operables. |
| **Asteroids** | Arcade Espacial Vectorial | Vector arcade retro clásico con sistema de físicas de inercia y disparos. |
| **Super Mario Bros** | Plataformas 2D | Recreación con motor modular por estados, físicas y niveles clásicos. |
| **Pac-Man** | Laberinto Arcade | IA de fantasmas basada en cuadrícula, pellets y efectos de sonido arcade. |
| **Space Invaders** | Shoot 'em up Fijo | Sistema de oleadas alienígenas, bunkers destructibles y disparos reactivos. |

---

## 🥊 Novedades en Da Vinci Fighters

### 🌟 Nuevos Personajes Jugables
Además del elenco original de profesores de Da Vinci (*Carloni, Cavasso, Romero, Gamaliel*), se incorporan 3 nuevos luchadores con hojas de spritesheets completas, animaciones calibradas, retratos en el Character Select y mecánicas únicas:

1. **Cami (C.C.I. Online)**:
   - *Estilo:* Combate cibernético veloz con ráfagas de ki púrpura.
   - *Ataques Clave:* Cyber Palm, Ki Burst Strike, Low Cyber Kick, Timed Axe Kick.
   - *Super / Combo:* **Purple Multi-Strike** y **Max Ki Overdrive** tras encadenar combos de más de 4 golpes.
2. **Enith (Fuerza Andina)**:
   - *Estilo:* Boxeo andino contundente con invocaciones ancestrales.
   - *Ataques Clave:* Jab de Boxeadora, Directo Andino, Patadas Solares.
   - *Super / Combo:* **Ataque de Cuys** (enjambre) y **Furia Solar Andina** activados tras racha de combos.
3. **Martín (Fisicoquímica Láctea & Prismas)**:
   - *Estilo:* Boxeo y combate a distancia retro con proyectiles lácteos y dispersión cromática.
   - *Ataques Clave:* Puño Retro, Lanzamiento de Sachet, Patada Rompedora.
   - *Super / Combo:* **Lluvia de Leche** y **Prismas Arcoíris** tras encadenar combos superiores a 4 golpes.

### 🎮 Soporte Integral para Joysticks / Gamepads
- **Detección automática y Hot-plugging:** DualSense (PS5), DualShock (PS4), mandos de Xbox Series/One, Switch Pro y mandos genéricos USB (`pygame._sdl2.controller` con fallback a `pygame.joystick`).
- **Navegación completa con Gamepad:**
  - Navegación y confirmación en el Menú Principal de la consola.
  - Selección de luchador en la pantalla de selección de personaje (**Character Select**).
  - Control completo de combate para Player 1 y Player 2.

---

## 🔄 Flujo de la Máquina de Estados

La consola corre en una única ventana de `1280x720` con gestión de audio e intros sincronizadas con OpenCV y reproductores nativos:

```
[BOOT] (CCI_INTRO.mp4)
   │  ↳ Salto con ENTER / ESPACIO / Botón Mando ──┐
   ▼ (Al finalizar)                              │
[INTRO_AVATAR] (Cinemática interactiva con audio) │
   │  ↳ Salto con ENTER / ESPACIO / Botón Mando ──┤
   ▼ (Al finalizar)                              │
   └────────────────────────────────────────────►▼
                                              [MENU] (Rejilla interactiva 2x3 con selector dinámico)
                                                 │
                   ┌──────────────┬──────────────┼──────────────┬──────────────┬──────────────┐
                   ▼              ▼              ▼              ▼              ▼              ▼
                Da Vinci      Metal Slug     Asteroids        Mario         Pac-Man     Space Invaders
                   │              │              │              │              │              │
                   └──────────────┴──────────────┴──────┬───────┴──────────────┴──────────────┘
                                                        │
                                                        ▼ (Escape o fin de partida)
                                                      [MENU]
```

- **Aislamiento de Módulos (Sandbox de ejecución):** Al cargar y salir de cualquier juego, el sistema purga colisiones de módulos cacheados (`sys.modules` como `settings`, `game`, `audio_manager`) y restaura `sys.path` y `cwd` para permitir alternar entre todos los títulos sin reiniciar la aplicación.

---

## ⌨️ Controles

### 🕹️ Controles Generales (Launcher y Menús)
| Acción | Teclado | Mando / Joystick |
| :--- | :--- | :--- |
| **Navegar en Rejilla** | `Flechas` o `W / A / S / D` | `D-Pad` o `Stick Izquierdo` |
| **Seleccionar / Confirmar** | `Enter` o `Espacio` | `Botón A / Cruz / X / Start` |
| **Saltar Cinemáticas** | `Enter` o `Espacio` | `Cualquier Botón Principal` |
| **Volver al Menú Principal** | `Escape` | `Botón Select / Share` |

### 🥊 Controles de Combate (Da Vinci Fighters)
| Movimiento / Acción | Teclado P1 | Joystick (P1 / P2) |
| :--- | :--- | :--- |
| **Moverse / Saltar / Agacharse** | `W / A / S / D` | `D-Pad` o `Stick Izquierdo` |
| **Puño Ligero** | `U` | `Botón X / Cuadrado (West)` |
| **Puño Fuerte** | `I` | `Botón Y / Triángulo (North)` |
| **Patada Ligera** | `J` | `Botón A / Cruz (South)` |
| **Patada Fuerte** | `K` | `Botón B / Círculo (East)` |
| **Bloqueo / Guardia** | `L` o `S` (Agachado) | `L1 / LB` o `Abajo en D-Pad` |
| **Ataque Especial** | `O` (o racha > 4 golpes) | `R1 / RB` |
| **Ataque Ultimate** | `P` (barra de super llena) | `L2 / LT`, `R2 / RT` o ambos gatillos |

---

## 🚀 Instalación y Ejecución

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
```

### 2. Crear y Activar Entorno Virtual
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **Windows:**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```

### 3. Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Importante:** El proyecto utiliza `pygame-ce` (Community Edition). No debe instalarse junto con el paquete `pygame` tradicional.

### 4. Iniciar la Consola
```bash
python main.py
```

---

## 📁 Estructura del Repositorio

```text
C.C.I-SYSTEM/
├── main.py                     # Entry point y bucle principal del sistema
├── states.py                   # Máquina de estados (Boot, IntroAvatar, Menu, Playing)
├── requirements.txt            # Dependencias del proyecto
├── README.md                   # Documentación oficial
├── CCI_INTRO.mp4               # Video de arranque de la consola
├── Pixel_girl_...mp4           # Video cinemático del avatar con audio sincronizado
├── games.png                   # Arte base del selector de juegos (2x3)
├── cards-color.jpeg            # Texturas HD para el efecto hover de selección
├── documentacion/              # Documentación técnica y especificaciones de software
│   ├── 1_RELEVAMIENTO_Y_ALCANCE.md
│   ├── 2_PROPUESTA_DE_VALOR.md
│   ├── 3_SRS_ESPECIFICACION_REQUERIMIENTOS.md
│   ├── 4_CASOS_DE_USO.md
│   ├── 5_MANUAL_DE_INSTALACION.md
│   ├── 6_MANUAL_DE_USUARIO.md
│   ├── 7_DIAGRAMA_DE_GANTT.md
│   └── 8_CODIGO_FUENTE_Y_ARQUITECTURA.md
├── Davinci-Fighter/            # Juego de lucha arcade (Personajes, AI, Spritesheets, InputManager)
├── METAL SLUG/                 # Juego de acción 2D (Físicas Pymunk)
├── Mario/                      # Recreación de Super Mario Bros
├── PacMan/                     # Clásico Pac-Man arcade
├── Space-invaders/             # Space Invaders clásico
└── asteroids/                  # Asteroids retro vectorial
```

---

## 🛠️ Tecnologías y Librerías

- **Python 3.10+** (Probado y compatible con 3.14)
- **Pygame-CE** (Renderizado 2D de alto rendimiento, SDL2 GameController y Mixer)
- **OpenCV (`opencv-python`)** (Decodificación de video y renderizado a buffers)
- **NumPy** (Procesamiento matricial y manipulación de audio)
- **Pymunk** (Simulación física 2D de cuerpos rígidos)

---

## 👩‍💻 Autora

Desarrollado por **Camila Ianni** ([@Camila-Ianni](https://github.com/Camila-Ianni))
