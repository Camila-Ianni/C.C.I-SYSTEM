# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![OpenCV](https://img.shields.io/badge/opencv--python-4.8%2B-red)
![Architecture](https://img.shields.io/badge/architecture-State%20Machine-purple)
![Gamepads](https://img.shields.io/badge/gamepad-DualSense%20%7C%20Xbox%20%7C%20Generic-orange)
![Haptics](https://img.shields.io/badge/haptics-Rumble%20Feedback-success)
![Multi-User](https://img.shields.io/badge/multi--user-Isolated%20Profiles-cyan)

**C.C.I. SYSTEM** es una plataforma arcade integral desarrollada en **Python** y **Pygame-CE (Community Edition)**. Unifica 26 títulos arcade clásicos e independientes bajo un entorno gráfico retrofuturista de ventana única (`1280x720`), orquestado mediante un patrón de **Máquina de Estados Finita (State Machine)** con aislamiento estricto de namespaces, háptica universal y perfiles multiusuario independientes.

---

## 🎮 Videojuegos Integrados (26 Títulos)

La consola cuenta con un catálogo de **26 juegos** accesibles desde la Biblioteca y el Carrusel 3D del Menú Principal:

| # | Juego | Género | Motor / Características |
| :-: | :--- | :--- | :--- |
| 1 | **Da Vinci Fighters** | Lucha 2D Arcade | Motor CPS-1 propio, combate 1P vs CPU y 2P Local, supers, combos, cinemáticas y personajes originales (*Cami, Enith, Martín*). |
| 2 | **Metal Slug: Super Vehicle-001** | Run & Gun | Motor de físicas Pymunk, renderizado multicapa y vehículos operables. |
| 3 | **Asteroids** | Arcade Espacial Vectorial | Clásico vectorial con inercia, disparos reactivos y puntuación. |
| 4 | **Super Mario Bros** | Plataformas 2D | Motor modular por estados, físicas y niveles clásicos. |
| 5 | **The Legend of Zelda** | Action RPG 2D | Exploración top-down en Hyrule, sistema de armas, magias e inventario. |
| 6 | **Pac-Man** | Laberinto Arcade | IA de fantasmas basada en cuadrícula, pellets y audio original. |
| 7 | **Tetris** | Puzzle Clásico | Caída de tetriminos, rotación, cálculo de puntuación y aceleración progresiva. |
| 8 | **Space Invaders** | Shoot 'em up Fijo | Oleadas alienígenas descendentes, bunkers destructibles y ovnis. |
| 9 | **DOOM** | First Person Shooter (FPS) | Motor 3D por Raycasting, enemigos animados, mapa laberíntico y captura de ratón. |
| 10 | **Minecraft** | Sandbox 3D | Construcción de bloques en primera persona con Ursina. |
| 11 | **Flappy Bird** | Arcade | Vuelo y esquive de tuberías retro. |
| 12 | **Dino Run** | Endless Runner | Salto y agachado esquivando cactus y pterodáctilos. |
| 13 | **GhostBusters** | Plataformas / Acción | Scroll con parallax, captura de fantasmas y granadas. |
| 14 | **Cyberpunk Metroidvania** | Plataformas / Metroidvania | Ambientación distópica con niveles y físicas de plataformas. |
| 15 | **Pokémon** | RPG por Turnos | Combate por turnos retro, selección de movimientos y animaciones. |
| 16 | **Street Fighter II** | Lucha 2D | Combates clásicos uno contra uno con ataques especiales. |
| 17 | **Sonic the Hedgehog** | Plataformas de Velocidad | Físicas de loopings, recolección de anillos y velocidad vertiginosa. |
| 18 | **Bomberman** | Acción / Laberinto | Colocación táctica de bombas, power-ups y destrucción de bloques. |
| 19 | **Frogger** | Arcade Clásico | Cruce de autopistas y ríos con temporizador y vidas. |
| 20 | **Mega Man** | Acción / Plataformas | Disparos buster, saltos calibrados y enemigos de escenario. |
| 21 | **Mortal Kombat (MK-Ultra)** | Lucha Arcade | Golpes contundentes, guardias y combate cuerpo a cuerpo. |
| 22 | **Castlevania** | Acción / Aventura Gótica | Látigo Vampire Killer, velas, subarmas y enemigos clásicos. |
| 23 | **Bubble Bobble** | Plataformas Arcade | Disparo de burbujas, captura de monstruos y frutas. |
| 24 | **Plants vs. Zombies** | Tower Defense | Siembra estratégica de plantas, soles y oleadas de zombis. |
| 25 | **Donkey Kong** | Plataformas Arcade | Subida por andamios metálicos esquivando barriles rodantes. |
| 26 | **Q\*bert** | Arcade Isométrico | Pirámide isométrica de cubos con cambio de color y evasión de enemigos. |

---

## 👤 Sistema Multiusuario Independiente

C.C.I. SYSTEM implementa perfiles de usuario completamente aislados (`.cci-user-data/users/{usuario}.json`):
- **Datos Segregados:** Cada jugador mantiene sus propios avances, estadísticas por juego, horas jugadas, nivel de experiencia, partidas recientes, favoritos y logros sin mezclarse con otros usuarios.
- **Perfil Base Migrado:** Los progresos anteriores se conservan en la cuenta principal `CAMI` (más de 36 horas de juego y 33 logros base).
- **Creación Dinámica de Perfiles:** Interfaz gráfica para dar de alta nuevos jugadores con nombre personalizado y elección de avatar.
- **Borrado Seguro:** Opción de eliminar perfiles con confirmación modal (protegiendo el último perfil activo).
- **Cambio Rápido de Cuenta:** Posibilidad de alternar de usuario en cualquier momento desde la pantalla de selección o mediante el botón `CAMBIAR USUARIO` (`F3`) en la sección de Perfil.

---

## 🎴 Pantalla de Selección de Usuario (`USER_SELECT`)

Situada estratégicamente tras las cinemáticas de inicio del sistema:
- **Arte Cyberpunk HD:** Integración visual con `Bienvenida al sistema C.C.I.png`.
- **Avatares Circulares Neón:** 8 retratos circulares transparentes extraídos de `Selector de personajes ciberpunk en blanco-Photoroom.png`.
- **Correspondencia 1:1:** Cada avatar circular se corresponde exactamente con el avatar cuadrado correspondiente en la vista de Perfil de la consola.
- **Tarjetas Interactivas:** Cada tarjeta muestra nombre, avatar con anillo luminoso animado, nivel de jugador, logros obtenidos y tiempo total jugado.
- **Tarjeta `+ NUEVO PERFIL`:** Despliega un modal flotante con caja de texto y selector de los 8 personajes para añadir un nuevo jugador al instante.

---

## 📳 Sistema Háptico / Vibración Universal (`cci_rumble.py`)

Integración nativa de vibración táctil para mandos compatibles con SDL2 / Pygame-CE (DualSense PS5, DualShock 4, Xbox One/Series, Switch Pro y USB genéricos):
- **`hit_rumble()`**: Vibración contundente ante impactos o golpes recibidos por el jugador.
- **`damage_rumble()`**: Vibración moderada ante daño continuo o pérdida de salud.
- **`explosion_rumble()`**: Vibración de máxima potencia en explosiones, KO o muerte.
- **`light_rumble()`**: Vibración sutil en navegación de menús, saltos o impactos menores.
- **Control Global:** Activación y desactivación inmediata desde el menú de Configuración (`vibration: on/off`).

---

## 🔄 Arquitectura y Flujo de Estados

El ciclo de vida de la aplicación se ejecuta en una única ventana de `1280x720` sin parpadeos ni fugas de memoria:

```
[BOOT] (Video de arranque CCI_INTRO.mp4)
   │  ↳ Salto con ENTER / ESPACIO / Botón Mando ──┐
   ▼ (Al finalizar)                              │
[INTRO_AVATAR] (Cinemática interactiva con audio) │
   │  ↳ Salto con ENTER / ESPACIO / Botón Mando ──┤
   ▼ (Al finalizar)                              │
[USER_SELECT] (Selector y creador de perfiles)◄──┘
   │  ↳ Seleccionar usuario / Crear nuevo
   ▼
[MENU] (Carrusel 3D interactivo con los 26 juegos)
   ├──► [LIBRARY]      (Biblioteca completa, filtros, búsqueda y fichas)
   ├──► [PROFILE]      (Nivel, horas, sesiones recientes y cambio de avatar)
   ├──► [ACHIEVEMENTS] (Sistema de logros y trofeos por juego)
   ├──► [SETTINGS]     (Ajustes de video, CRT, volumen y vibración háptica)
   └──► [PLAYING]      (Sandbox de ejecución segura del juego seleccionado)
           │
           ▼ (Escape o fin de partida)
        [MENU]
```

- **Sandbox de Ejecución (`PlayingState`):** Al lanzar y cerrar un juego, el sistema limpia `sys.modules`, restablece descriptores de audio, restaura `sys.path` y `cwd`, garantizando un retorno seguro a la consola.

---

## ⌨️ Controles Generales

### 🖥️ Launcher y Pantallas del Sistema
| Acción | Teclado | Mando / Joystick |
| :--- | :--- | :--- |
| **Navegar (Menús / Carrusel / Avatares)** | `W / A / S / D` o `Flechas` | `D-Pad` o `Stick Izquierdo` |
| **Confirmar / Jugar / Seleccionar** | `Enter` o `Espacio` | `Botón A / Cruz / X` |
| **Volver / Cancelar** | `Escape` | `Botón B / Círculo` |
| **Saltar Cinemáticas** | `Enter` o `Espacio` | `Cualquier botón principal` |
| **Cambiar Usuario** | `F3` (en Perfil o Menú) | `Botón Cambiar Usuario` |
| **Editar Nombre de Perfil** | `F2` (en Perfil) | `Icono de edición` |
| **Eliminar Perfil (Multiusuario)** | `Supr` / `Delete` | `Botón Y / Triángulo` |
| **Atajos directos de pantalla** | `F4` Juegos · `F5` Inicio · `F6` Perfil · `F7` Logros · `F8` Configuración | `Sidebar interactiva` |

### 🥊 Da Vinci Fighters
| Acción | Teclado P1 | Joystick (P1 / P2) |
| :--- | :--- | :--- |
| **Desplazamiento** | `A / D` | `Stick Izquierdo` / `D-Pad` |
| **Saltar** | `W` | `Botón ✕ (Cruz / A)` |
| **Agacharse** | `S` | `Stick Izquierdo Abajo` |
| **Bloqueo / Guardia** | `L` | `Botón ◻ (Cuadrado / X)` |
| **Patadas** | `U` / `O` | `Botón ◯ (Círculo / B)` |
| **Ataque Especial** | `I` | `Botón △ (Triángulo / Y)` |
| **Super / Ultimate** | `P` (con barra llena) | `L2 / LT` o `R2 / RT` |

---

## 🚀 Instalación y Ejecución

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
pip install -r requirements.txt
```

> **Nota:** Se utiliza `pygame-ce` (Community Edition). No debe coexistir con `pygame` estándar.

### 4. Iniciar la Consola
```bash
python main.py
```

---

## 📁 Estructura Principal del Proyecto

```text
C.C.I-SYSTEM/
├── main.py                     # Entry point y orquestación de la consola virtual
├── states.py                   # Máquina de estados base (Boot, Intro, Menu, Playing)
├── user_select_state.py        # Pantalla interactiva de bienvenida y selección de usuario
├── cci_users.py                # Gestor de almacenamiento multiusuario independiente
├── cci_console.py              # Estados de consola: Library, Profile, Achievements, Settings
├── cci_rumble.py               # Motor universal de vibración y retroalimentación háptica
├── sidebar_ui.py               # Barra lateral de navegación futurista compartida
├── requirements.txt            # Dependencias del proyecto (pygame-ce, opencv, pymunk, etc.)
├── README.md                   # Documentación técnica oficial
├── assets_cards/               # Banners y tarjetas transparentes de los 26 juegos
├── pantallas/                  # Assets gráficos originales de las interfaces
├── .cci-user-data/             # Directorio local de perfiles y ajustes (no versionado)
│   └── users/                  # Archivos JSON independientes por usuario
└── [Carpetas de Juegos]/       # Módulos de los 26 videojuegos arcade integrados
```

---

## 🛠️ Tecnologías Empleadas

- **Python 3.10+** (Optimizado para Python 3.14)
- **Pygame-CE** (Renderizado 2D, SDL2 Gamepad, Haptics y Mixer)
- **OpenCV (`opencv-python`)** (Decodificación de video BGR $\rightarrow$ RGB de alta precisión)
- **NumPy** (Procesamiento de buffers gráficos y síntesis de audio)
- **Pymunk** (Físicas 2D de cuerpos rígidos)

---

## 👩‍💻 Autora

Desarrollado por **Camila Ianni** ([@Camila-Ianni](https://github.com/Camila-Ianni))
