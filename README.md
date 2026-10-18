# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![OpenCV](https://img.shields.io/badge/opencv--python-4.8%2B-red)
![Architecture](https://img.shields.io/badge/architecture-State%20Machine-purple)
![Gamepads](https://img.shields.io/badge/gamepad-DualSense%20%7C%20Xbox%20%7C%20Generic-orange)

**C.C.I. SYSTEM** es una plataforma arcade integral desarrollada en **Python** y **Pygame-CE (Community Edition)**. Unifica catorce títulos arcade clásicos y de autor bajo un entorno gráfico retrofuturista de ventana única (`1280x720`), orquestado mediante un patrón arquitectónico de **Máquina de Estados Finita (State Machine)** con aislamiento estricto de entornos y namespaces.

---

## 🎮 Videojuegos Integrados (14 Títulos)

La consola incluye un catálogo de 14 juegos organizados en un menú con **carrusel vertical cilíndrico** de estética Sci-Fi, efectos de perspectiva y animación fluida:

| Juego | Género | Motor / Características |
| :--- | :--- | :--- |
| **Da Vinci Fighters** | Lucha 2D Arcade (CPS-1 Style) | Motor propio de combate, soporte 1P vs CPU y 2P Local, selector de personajes, supers, combos y cinemáticas. |
| **Metal Slug: Super Vehicle-001** | Run & Gun | Motor de físicas Pymunk, renderizado multicapa y vehículos operables. |
| **Asteroids** | Arcade Espacial Vectorial | Vector arcade retro clásico con sistema de físicas de inercia y disparos. |
| **Super Mario Bros** | Plataformas 2D | Recreación con motor modular por estados, físicas y niveles clásicos. Corrección en transición de daño para evitar desapariciones de sprite. |
| **Pac-Man** | Laberinto Arcade | IA de fantasmas basada en cuadrícula, pellets y efectos de sonido arcade. |
| **Space Invaders** | Shoot 'em up Fijo | Sistema de oleadas alienígenas, bunkers destructibles y disparos reactivos. |
| **Tetris** | Puzzle Clásico | Caída libre de tetriminos, rotación, cálculo de puntuación y eliminación de líneas con aceleración progresiva. |
| **The Legend of Zelda** | Action RPG 2D | Exploración en Hyrule con vista top-down, sistema de armas, magias, enemigos y audio interactivo. |
| **DOOM** | First Person Shooter (FPS 3D) | Motor 3D por Raycasting, armas, enemigos animados, mapa laberíntico y captura de ratón. |
| **Minecraft** | Sandbox 3D | Construcción de bloques en primera persona con Ursina (requiere `pip install ursina`); corre en su propia ventana. |
| **Flappy Bird** | Arcade | Vuela entre tuberías; corre en su propio proceso. |
| **Dino** | Endless Runner | Corre, salta y agáchate para esquivar cactus y pterodáctilos. |
| **GhostBusters** | Plataformas de acción | Plataformas con scroll y parallax, fantasmas y granadas. |
| **Cyberpunk Metroidvania** | Plataformas de acción | Metroidvania distópico con niveles Tiled (`Cyberpunk-Metroidvania/Platformer 01-04-2022`). |

---

## 🎡 Nuevo Menú de Selección Estilo Carrusel Sci-Fi

El menú principal de la consola ha sido rediseñado con un estilo arcade avanzado:
- **Fondo Futurista (`select_game.jpeg`):** Pantalla de control con estética cyber-arcade.
- **Rueda Cilíndrica (Carrusel Vertical):** Rueda de tarjetas a la derecha con curvatura, escala dinámica, profundidad e interpolación suave (*lerp*).
- **Marco de Selección:** Recuadro blanco brillante y flechas indicadoras (`< >`) sobre el título seleccionado.
- **Cuadro de Diálogo Dinámico:** Caja inferior con retrato del avatar y descripción interactiva de cada título.

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
  - Navegación y confirmación en el Menú Principal y Carrusel.
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
                                              [MENU] (Carrusel interactivo 3D con 14 títulos)
                                                 │
          ┌──────────────┬──────────────┬────────┼──────────────┬──────────────┬──────────────┐
          ▼              ▼              ▼        ▼              ▼              ▼              ▼
       Da Vinci      Metal Slug     Asteroids  Mario         Pac-Man     Space Invaders   Tetris / Zelda / DOOM
          │              │              │        │              │              │              │
          └──────────────┴──────────────┴────────┴──────┬───────┴──────────────┴──────────────┘
                                                        │
                                                        ▼ (Escape o fin de partida)
                                                      [MENU]
```

- **Aislamiento de Módulos (Sandbox de ejecución):** Al cargar y salir de cualquier juego, el sistema purga colisiones de módulos cacheados (`sys.modules` como `settings`, `game`, `audio_manager`) y restaura `sys.path` y `cwd` para permitir alternar entre los 9 títulos sin reiniciar la aplicación ni degradar el rendimiento.

---

## ⌨️ Controles

### 🕹️ Controles Generales (Launcher y Menús)
| Acción | Teclado | Mando / Joystick |
| :--- | :--- | :--- |
| **Navegar en Carrusel** | `W / S` o `Flechas Arriba / Abajo` | `D-Pad` o `Stick Izquierdo` |
| **Seleccionar / Jugar** | `Enter` o `Espacio` | `Botón A / Cruz / X / Start` |
| **Saltar Cinemáticas** | `Enter` o `Espacio` | `Cualquier Botón Principal` |
| **Volver al Menú Principal** | `Escape` | `Botón Select / Share` |

### 🥊 Controles de Combate (Da Vinci Fighters)
| Movimiento / Acción | Teclado P1 | Joystick (P1 / P2) |
| :--- | :--- | :--- |
| **Moverse / Desplazamiento** | `A / D` | `Left Joystick` (o D-Pad) |
| **Saltar** | `W` | `Botón ✕ (Cruz / A)` |
| **Agacharse** | `S` | `Left Joystick Abajo` (o D-Pad Abajo) |
| **Guardia Alta / Bloqueo** | `L` | `Botón ◻ (Cuadrado / X)` |
| **Patadas** | `U` / `O` | `Botón ◯ (Círculo / B)` |
| **Ataque Especial** | `I` | `Botón △ (Triángulo / Y)` |
| **Ataque Ultimate** | `P` (barra de super llena) | `L2 / LT` o `R2 / RT` |

> ⏱️ **Recarga de Ataque Especial:** Al usar el ataque especial con `I` (o `△`), la barra se vacía por completo y entra en recarga durante **10 segundos**, mostrando el tiempo restante en pantalla hasta volver a estar lista.

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

### Interfaz interactiva C.C.I.

El launcher usa las pantallas de `pantallas/finales_entrega/` como base visual y las convierte en vistas interactivas de Pygame. **Inicio** usa `pantallas/Menú futurista C.C.I System.png` con el carrusel lateral vertical interactivo; **Juegos** abre la biblioteca con filtros, búsqueda, favoritos y fichas de juego. Perfil, logros y configuración comparten una barra lateral consistente. Los banners conservan su proporción para evitar deformaciones. Los datos locales se guardan en `.cci-user-data/system.json` (se crea al utilizar la consola y no se versiona).

**Controles de la consola:** flechas o WASD para navegar; en Logros, `↑/↓` seleccionan y `←/→` cambian el filtro por juego; `Q/E` cambia el filtro en Juegos; `Enter` abre/juega; `F` marca favorito; `F3` busca; `F2` edita el nombre del perfil y `Esc` vuelve (o sale desde Inicio). `F4` abre Juegos; `F5` Inicio; `F6` Perfil; `F7` Logros y `F8` Configuración. En mandos estándar, `B` vuelve a Inicio y `X/Y/Guide` abren Perfil/Logros/Configuración. También se puede navegar con mouse y con los mandos compatibles con Pygame.

Los nueve juegos ya integrados por `PlayingState` se ejecutan en la ventana de la consola. Dino, Flappy Bird y GhostBusters se inician como procesos Pygame independientes, usando sus carpetas existentes. Un título sin ejecutable o dependencias disponibles se muestra como no disponible en lugar de simular un lanzamiento.

---

## 📁 Estructura del Repositorio

```text
C.C.I-SYSTEM/
├── main.py                     # Entry point y bucle principal del sistema
├── states.py                   # Máquina de estados (Boot, IntroAvatar, Menu con carrusel, Playing)
├── requirements.txt            # Dependencias del proyecto
├── README.md                   # Documentación oficial
├── CCI_INTRO.mp4               # Video de arranque de la consola
├── Pixel_girl_...mp4           # Video cinemático del avatar con audio sincronizado
├── select_game.jpeg            # Fondo base de alta definición del menú arcade
├── assets_cards/               # Tarjetas y texturas transparentes de los 14 juegos (nuevas generadas con tools/build_new_cards.py)
├── Davinci-Fighter/            # Juego de lucha arcade (Personajes, AI, Spritesheets, InputManager)
├── METAL SLUG/                 # Juego de acción 2D (Físicas Pymunk)
├── Mario/                      # Recreación de Super Mario Bros
├── PacMan/                     # Clásico Pac-Man arcade
├── Space-invaders/             # Space Invaders clásico
├── asteroids/                  # Asteroids retro vectorial
├── tetris/                     # Tetris clásico interactivo
├── Zelda/                      # The Legend of Zelda (Action RPG)
├── DOOM/                       # DOOM 3D Raycasting Engine
├── Minecraft/ Flappy-Bird/ Dino/ GhostBusters/ Cyberpunk-Metroidvania/   # Juegos lanzados como procesos externos
└── tools/                      # Utilidades (recorte de tarjetas del carrusel)
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
