# Relevamiento Detallado y Alcance Integral del Sistema
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform)
**Código de Proyecto:** CCI-SYS-2026  
**Área:** Arquitectura de Software y Desarrollo de Videojuegos  
**Versión:** 2.0.0 (Edición 6 Cartuchos)  

---

## 1. Contexto y Justificación del Proyecto

### 1.1. Antecedentes
En el ámbito del desarrollo de videojuegos independientes y proyectos académicos con Python, la librería `pygame` (y su iteración moderna optimizada `pygame-ce`) es uno de los frameworks más utilizados para construir títulos en 2D. Sin embargo, los proyectos suelen desarrollarse como islas aisladas: cada programador o equipo define su propia estructura de archivos, resolución nativa arbitraria, gestión de teclado hardcodeada y ciclos de inicialización cerrados mediante llamadas directas a `pygame.init()`, `pygame.display.set_mode()` y `sys.exit()`.

Al intentar exhibir múltiples creaciones en una muestra académica, feria de ciencias o entorno arcade físico (bartop o cabinete arcade), surge un conjunto crítico de problemas técnicos:
1. **Disrupción en la experiencia de usuario:** Salir de un juego cerraba la aplicación por completo, requiriendo abrir una terminal de comandos para ejecutar otro archivo `.py`.
2. **Conflicto de resoluciones:** Títulos arcade retro como *Metal Slug* operan internamente en resolución Neo-Geo (320x224), *Super Mario* en 800x600, *Space Invaders* en 600x600 y *Da Vinci Fighters* en 1280x720. Al ejecutarlos juntos, la ventana de Pygame se deformaba o generaba saltos abruptos de tamaño en el monitor.
3. **Incompatibilidad de periféricos:** La mayoría de los juegos solo implementaban escucha de eventos de teclado mediante `pygame.key.get_pressed()`, dejando inutilizables los gamepads USB o Bluetooth (PlayStation DualSense, Xbox Controller, Switch Pro).
4. **Fugas de recursos y bloqueos de audio:** El subsistema `pygame.mixer` quedaba retenido o desalineado al cambiar de juego, causando colisiones de hilos de sonido o silencios irreversibles.

### 1.2. Justificación Técnica
**C.C.I. SYSTEM** se diseña como una **Consola Virtual de Videojuegos** que actúa como una capa de abstracción de sistema operativo (middleware/frontend). Implementa una arquitectura desacoplada basada en una **Máquina de Estados Finita (Finite State Machine - FSM)**, garantizando que un único ejecutable raíz (`main.py`) administre el ciclo de vida completo de la ventana, la gestión de memoria, la sincronización de audio y la compatibilidad de controladores, ofreciendo un menú de alta definición de 6 cartuchos sin costuras ni fisuras.

---

## 2. Objetivos del Proyecto

### 2.1. Objetivo General
Desarrollar, estructurar y documentar exhaustivamente una plataforma de software en Python utilizando `pygame-ce` que unifique seis (6) videojuegos independientes bajo una única ventana persistente de 1280x720 píxeles, incorporando cinemáticas de arranque con audio nativo, navegación arcade retro mediante un menú con efecto hover dinámico (blanco y negro a color) y soporte universal plug-and-play para mandos de consola.

### 2.2. Objetivos Específicos
1. **Arquitectura de Software Limpia y Desacoplada:**
   * Diseñar una máquina de estados estricta (`StateMachine`) que gestione transiciones seguras entre `BOOT`, `INTRO_AVATAR`, `MENU` y `PLAYING`.
   * Proveer una clase abstracta `BaseState` que estandarice los métodos de ciclo de vida: `enter()`, `exit()`, `handle_events()`, `update()` y `draw()`.
2. **Orquestación y Renderizado de Cinemáticas con Audio:**
   * Implementar un reproductor de video de alto rendimiento con OpenCV (`cv2`) sincronizado frame a frame contra el reloj de hardware para evitar desfases temporales o reproducción acelerada.
   * Superar la limitación de OpenCV (carencia nativa de audio) integrando un gestor complementario (`VideoAudioPlayer`) que reproduzca la pista sonora sin latencia en macOS (`afplay`) y sistemas Linux/Windows (`pygame.mixer`).
   * Proporcionar un mecanismo de interrupción inmediata (*skip*) en cualquier instante mediante teclado o mando.
3. **Interfaz de Menú con Efecto Hover Cromático Puro:**
   * Renderizar el fondo temático `games.png` (1452x1083) centrado y escalado de forma proporcional (aspect-fit) a 1280x720, evitando deformaciones trapezoidales o estiramientos de imagen.
   * Diseñar una cuadrícula simétrica de 2 filas y 3 columnas para los 6 cartuchos.
   * Implementar un algoritmo de superposición que muestre todas las tarjetas inactivas en escala de grises (`cards-bn.jpeg`) y sustituya en caliente por la tarjeta a todo color (`cards-color.jpeg`) con recorte de fondo transparente mediante máscaras alfa sobre la opción que posea el foco.
4. **Capa Universal de Mandos (`JoystickManager`):**
   * Detectar periféricos en caliente (*hotplugging*) mediante eventos `JOYDEVICEADDED` y `JOYDEVICEREMOVED`.
   * Implementar un mecanismo de interceptación transparente sobre `pygame.event.get()` y `pygame.key.get_pressed()`, inyectando eventos sintetizados de teclado a partir de la palanca analógica, cruceta D-pad y botones frontales.
5. **Aislamiento y Ejecución Modular de los 6 Títulos:**
   * Proteger el contexto de cada juego manipulando dinámicamente el directorio de trabajo (`os.chdir`) y el árbol de módulos (`sys.path`).
   * Interceptar las llamadas a `pygame.display.set_mode()` dentro de los submódulos para forzar la reutilización de la superficie `screen` única.
   * Resolver el tearing y parpadeo de pantalla en *Metal Slug* mediante la interceptación de su pipeline de dibujado, reemplazando su escala rígida de 960x672 por un escalado directo a 1280x720 con un único `pygame.display.flip()`.
   * Capturar de manera transversal la señal de retorno (`ESC` o botón `Select/Share`) para detener música/sonidos residuales y restablecer el menú principal sin reinicios.

---

## 3. Relevamiento de la Situación Actual de los Juegos Integrados

A continuación se detalla la auditoría técnica realizada sobre los 6 juegos independientes previo a su integración:

| Juego | Directorio Fuente | Resolución Original | Sistema de Entrada Original | Dependencias Específicas | Particularidad Técnica Resuelta |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Da Vinci Fighters** | `Davinci-Fighter/` | 1280x720 (4:3 pillarbox a 960x720) | Teclado (`pygame.key.get_pressed()`) | `pygame-ce` | Máquina interna de combate con cortes de intro, selección de personajes y bucle de pelea. |
| **Metal Slug** | `METAL SLUG/` | 320x224 (Neo-Geo virtual) escalado a 960x672 | Gestor de mando propio y teclado | `pymunk`, `pygame-ce` | Realizaba dos `pygame.display.flip()` por fotograma causando tearing severo. `SoundManager` singleton requería reinicio de rutas relativas. |
| **Super Mario Bros** | `Mario/` | 800x600 | Teclado estructurado en `tools.keybinding` | `pygame-ce` | Utiliza un gestor de estados propio (`Control`). Se interceptó el bucle para permitir salida limpia al menú. |
| **Pac-Man** | `PacMan/` | 448x496 escalado | Eventos directos `KEYDOWN` | `pygame-ce` | Lógica de laberinto e IA de fantasmas. Requería captura de dirección y reinicio de audio de inicio. |
| **Space Invaders** | `Space-invaders/` | 600x600 | Teclado `pygame.key.get_pressed()` + Temporizador USEREVENT | `pygame-ce` | Requiere temporizadores de disparo alienígena periódicos que debían ser gestionados en el bucle principal. |
| **Asteroids** | `asteroids/` | 800x600 | Teclado vectorial (`processKeys` y eventos `KEYDOWN`) | `pygame-ce` | Renderizado de polígonos vectoriales puros y cálculo de inercia espacial. Se adaptó la superficie de renderizado a la ventana HD. |

---

## 4. Alcance del Sistema (Project Scope)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ALCANCE DEL SISTEMA                             │
├──────────────────────────────────────┬──────────────────────────────────────┤
│           DENTRO DEL ALCANCE         │          FUERA DEL ALCANCE           │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ ✔ Ventana única persistente 1280x720 │ ✖ Modo multijugador online en red    │
│ ✔ Máquina de estados FSM extensible  │ ✖ Guardado de partidas en la nube    │
│ ✔ Videos MP4 con audio y skip        │ ✖ Soporte para juegos en 3D (OpenGL) │
│ ✔ Menú con Hover B&N a color puro    │ ✖ Compilación nativa móvil (Android) │
│ ✔ Soporte universal de mandos USB/BT │ ✖ Descarga de ROMs vía internet      │
│ ✔ Integración de los 6 juegos Python │ ✖ Modificación del código interno    │
│ ✔ Retorno seguro al menú con ESC     │   de las mecánicas de los juegos     │
│ ✔ Supresión de avisos SDL en macOS   │ ✖ Microtransacciones o monetización  │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

### 4.1. Módulos y Entregables dentro del Alcance
1. **Módulo Orquestador (`main.py`):** Inicialización de subsistemas Pygame, ciclo principal a 60 FPS fijos, manejo de eventos globales y orquestación de la ventana.
2. **Módulo de Estados (`states.py`):**
   * `StateMachine`: Registro, transición, actualización y dibujado del estado activo.
   * `VideoAudioPlayer`: Reproducción y sincronización sonora por proceso auxiliar.
   * `BootState`: Video cinemático de booteo `CCI_INTRO.mp4`.
   * `IntroAvatarState`: Video narrativo `Pixel_girl_reading_dialogue_boxes_20261016123851.mp4`.
   * `MenuState`: Menú de 6 cartuchos con fondo `games.png`, tarjetas en blanco y negro `cards-bn.jpeg`, tarjetas a color `cards-color.jpeg` y retroalimentación sonora.
   * `PlayingState`: Sub-ejecutores específicos para Da Vinci Fighters, Metal Slug, Mario, Pac-Man, Space Invaders y Asteroids.
   * `JoystickManager`: Controlador singleton de mandos con traducción de eventos analógicos/digitales y hotplugging.
3. **Módulo de Periféricos:** Soporte plug-and-play para PlayStation 4/5, Xbox 360/One/Series, Switch Pro y arcade sticks genéricos.
4. **Cuerpo Documental Técnico Completo:** Siete manuales y especificaciones técnicas para usuarios, instaladores y evaluadores académicos.

### 4.2. Supuestos y Dependencias
* El sistema host dispone de controladores gráficos con soporte para aceleración de video SDL2.
* Python versión 3.10 o superior se encuentra instalado.
* Los archivos multimedia (`CCI_INTRO.mp4`, `Pixel_girl...mp4`, `games.png`, `cards-bn.jpeg`, `cards-color.jpeg`) deben residir en la raíz del proyecto.
