# Especificación de Requerimientos de Software (SRS)
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform)
**Código de Documento:** SRS-CCI-001  
**Estándar:** IEEE 830-1998 (Recommended Practice for Software Requirements Specifications)  
**Versión:** 2.0.0  

---

## 1. Introducción

### 1.1. Propósito
El propósito de este documento es definir con precisión y formalidad los requisitos funcionales, no funcionales, interfaces de usuario, restricciones de diseño y requerimientos de arquitectura para el software **C.C.I. SYSTEM**, una consola virtual de videojuegos desarrollada sobre Python (`pygame-ce`) y OpenCV. 

### 1.2. Alcance del Producto
El sistema software consiste en una plataforma frontend y motor de orquestación de videojuegos de escritorio. Gestiona el ciclo completo de inicialización de subsistemas de hardware (audio, video, mandos), cinemáticas multimedia, menú de selección de cartuchos y la ejecución aislada de seis títulos de diversa naturaleza gráfica (pixel art, arcade vectorial y Neo-Geo).

### 1.3. Definiciones y Acrónimos
* **FSM (Finite State Machine):** Modelo computacional compuesto por un conjunto finito de estados y transiciones bien delimitadas.
* **Pygame-CE (Community Edition):** Bifurcación activamente mantenida de la biblioteca multimedia Pygame.
* **OpenCV (`cv2`):** Biblioteca de visión artificial utilizada para decodificación de video en formato MP4.
* **Subsurface:** Superficie gráfica derivada que referencia directamente los píxeles de una región específica de una superficie mayor de Pygame.
* **Hotplugging:** Capacidad de un sistema informático para reconocer la conexión o desconexión de periféricos en caliente sin reiniciar.
* **Deadzone:** Zona neutra del stick analógico de un mando donde pequeños movimientos accidentales son ignorados para evitar desplazamientos fantasma.

---

## 2. Descripción General del Sistema

### 2.1. Perspectiva del Producto
C.C.I. SYSTEM opera como una aplicación independiente de escritorio sobre el sistema operativo host (macOS / Linux / Windows). Interactúa directamente con la capa de abstracción de hardware que provee la librería SDL2 subyacente a Pygame-CE.

```
┌────────────────────────────────────────────────────────┐
│                   CAPA DE APLICACIÓN                   │
│        Da Vinci | Metal Slug | Mario | Pac-Man ...     │
├────────────────────────────────────────────────────────┤
│           CAPA DE ORQUESTACIÓN C.C.I. SYSTEM           │
│    StateMachine | VideoState | MenuState | JoyManager  │
├────────────────────────────────────────────────────────┤
│                  CAPA DE FRAMEWORK                     │
│         Pygame-CE (SDL2)   |   OpenCV (cv2)            │
├────────────────────────────────────────────────────────┤
│             HARDWARE / SISTEMA OPERATIVO               │
│      Monitor HD | Tarjeta de Sonido | Mandos USB/BT    │
└────────────────────────────────────────────────────────┘
```

### 2.2. Modos de Operación y Estados del Sistema
El sistema se rige estrictamente por cuatro estados secuenciales y cíclicos:
1. **`BOOT`:** Carga y reproducción sincronizada del video de inicio `CCI_INTRO.mp4`.
2. **`INTRO_AVATAR`:** Reproducción del video cinemático narrativo `Pixel_girl_reading_dialogue_boxes_20261016123851.mp4` con audio.
3. **`MENU`:** Despliegue interactivo de la rejilla arcade de 6 cartuchos con efecto hover cromático y retroalimentación auditiva.
4. **`PLAYING`:** Contención, lanzamiento y ejecución del cartucho seleccionado dentro de la ventana de 1280x720 píxeles.

---

## 3. Requerimientos Específicos

### 3.1. Requerimientos Funcionales (RF)

#### Módulo 1: Inicialización y Orquestación Global
* **RF-01 [Inicialización Única]:** El sistema debe arrancar todos los subsistemas requeridos (`display`, `font`, `mixer`, `joystick`) de manera centralizada en la función `main()` del archivo `main.py`.
* **RF-02 [Gestión de Ventana Persistente]:** La ventana gráfica debe inicializarse exactamente una vez con dimensiones de **1280x720 píxeles**. Queda terminantemente prohibido que los submódulos de juego destruyan la ventana, invoquen `pygame.quit()` prematuramente o creen ventanas secundarias.
* **RF-03 [Mantenimiento de FPS y Delta Time]:** El bucle principal debe estar regulado a un reloj maestro de **60 cuadros por segundo (FPS)** fijos, calculando el diferencial de tiempo (`dt`) en segundos para suministrarlo a los estados.

#### Módulo 2: Reproducción de Videos Cinemáticos
* **RF-04 [Decodificación y Sincronización de Video]:** La clase base `VideoState` debe decodificar cada fotograma MP4 mediante `cv2.VideoCapture` y convertir la matriz de color BGR a RGB, empaquetándola en una superficie Pygame mediante `pygame.image.frombuffer()`.
* **RF-05 [Prevención de Reproducción Acelerada]:** El lector de video debe calcular el tiempo transcurrido contra el reloj de alta resolución (`time.perf_counter()`) y sincronizar el índice de fotograma objetivo (`target_frame = int(elapsed * fps)`), evitando que el video se reproduzca a velocidad desmedida.
* **RF-06 [Reproducción de Audio Paralelo]:** El módulo `VideoAudioPlayer` debe lanzar la pista sonora del video en un subproceso desacoplado utilizando el binario nativo del sistema operativo (`afplay` en macOS) o el canal de música de Pygame, garantizando sincronía audiovisual.
* **RF-07 [Interrupción Inmediata (Skip)]:** Al presionar `Enter`, `Espacio` o el botón de acción principal de un gamepad durante el estado `BOOT` o `INTRO_AVATAR`, el sistema debe detener la pista de audio de inmediato, liberar el archivo con `cap.release()` y transicionar de forma instantánea al estado `MENU`.

#### Módulo 3: Menú de Selección Arcade (Grid 2x3)
* **RF-08 [Renderizado Proporcional del Fondo]:** El menú debe cargar el recurso `games.png` (resolución nativa 1452x1083) y aplicarle un escalado suave (*smoothscale*) a una altura de 720 píxeles y un ancho aproximado de 965 píxeles, posicionándolo horizontalmente en `x ≈ 157 px` con pillarboxing centrado sin distorsión visual.
* **RF-09 [Distribución de Cartuchos]:** La cuadrícula de 6 cartuchos debe respetar exactamente las siguientes coordenadas en la pantalla escalada:
  * **Fila 0:**
    * *(0,0) Da Vinci Fighters:* Rectángulo `(x=410, y=174, w=219, h=162)`.
    * *(0,1) Metal Slug:* Rectángulo `(x=649, y=174, w=216, h=162)`.
    * *(0,2) Asteroids:* Rectángulo `(x=879, y=174, w=213, h=162)`.
  * **Fila 1:**
    * *(1,0) Super Mario Bros:* Rectángulo `(x=410, y=352, w=219, h=168)`.
    * *(1,1) Pac-Man:* Rectángulo `(x=649, y=352, w=216, h=168)`.
    * *(1,2) Space Invaders:* Rectángulo `(x=879, y=352, w=213, h=168)`.
* **RF-10 [Efecto Hover B&N a Color Puro]:**
  * Todas las tarjetas que **no** tengan el foco deben mostrar su representación en blanco y negro recortada de `cards-bn.jpeg`.
  * La tarjeta que **posea el foco** debe mostrar su versión a todo color recortada de `cards-color.jpeg`.
  * Los bordes y esquinas de las tarjetas deben ser limpiados mediante máscaras alfa para evitar artefactos o bordes blancos sobre el gabinete arcade.
  * No deben dibujarse cajas celestes o halos externos invasivos sobre la tarjeta.
* **RF-11 [Retroalimentación Auditiva]:** Al cambiar de posición en la cuadrícula, el sistema debe sintetizar un tono sonoro ligero de 500-600 Hz a través del buffer del mixer. Al pulsar Enter/Confirmar, debe emitir un tono de selección a 900 Hz.

#### Módulo 4: Capa Universal de Mandos (`JoystickManager`)
* **RF-12 [Soporte Universal de Gamepads]:** El sistema debe dar soporte sin configuración previa a mandos de PlayStation (DualShock 4, DualSense PS5), Xbox (360, One, Series X/S), Nintendo Switch (Pro Controller) y sticks arcade USB estándar.
* **RF-13 [Detección en Caliente (Hotplugging)]:** Los mandos conectados con la aplicación ya en ejecución deben ser reconocidos e inicializados de inmediato al recibir el evento `JOYDEVICEADDED`.
* **RF-14 [Traducción Transparente de Eventos]:**
  * Las palancas analógicas que superen la zona muerta de 0.35 deben sintetizar eventos virtuales `KEYDOWN`/`KEYUP` de `K_LEFT`, `K_RIGHT`, `K_UP`, `K_DOWN` y `WASD`.
  * El D-pad / Cruceta debe mapearse a las cuatro direcciones cardinales.
  * El botón principal (Cruz / A) debe mapearse a `K_SPACE` y `K_RETURN`.
  * El botón secundario (Círculo / B) debe mapearse a `K_b`.
  * El botón de ataque frontal (Cuadrado / X) debe mapearse a `K_j`.
  * El botón de golpe alto (Triángulo / Y) debe mapearse a `K_k`.
  * El botón Select / Share / Back debe mapearse a `K_ESCAPE`.
* **RF-15 [Mantenimiento de Polling]:** El interceptor de `pygame.key.get_pressed()` debe devolver `1` en las teclas correspondientes si el botón o stick del mando está presionado, garantizando compatibilidad con juegos que no leen la cola de eventos.

#### Módulo 5: Ejecución Aislada de los 6 Juegos
* **RF-16 [Aislamiento de CWD y SysPath]:** Cada sub-ejecutor de juego debe cambiar el directorio de trabajo actual con `os.chdir()` a la carpeta del juego y anteponer dicha carpeta en `sys.path[0]` para garantizar la resolución correcta de sus assets.
* **RF-17 [Corrección de Tearing en Metal Slug]:** El módulo de Metal Slug debe anular el método interno `ms_instance.draw()` para que no invoque `pygame.display.flip()` dos veces ni escale rígidamente a 960x672. En su lugar, debe escalar directamente el buffer virtual Neo-Geo (320x224) a la resolución completa de 1280x720 centrada con un solo flip por frame.
* **RF-18 [Reinicio del Singleton SoundManager]:** Al lanzar Metal Slug, el singleton `SoundManager._instance` debe purgarse (`None`) para que vuelva a instanciarse apuntando a los directorios de audio correctos.
* **RF-19 [Retorno Seguro al Menú]:** Al presionar `ESC` o botón `Select/Share` en cualquier juego, el bucle del juego debe terminar, silenciar de inmediato `pygame.mixer`, restaurar el directorio de trabajo original y devolver el control al estado `MENU` sin reiniciar el proceso.

---

### 3.2. Requerimientos No Funcionales (RNF)

| Código | Categoría | Requerimiento Técnico | Medición / Criterio de Aceptación |
| :--- | :--- | :--- | :--- |
| **RNF-01** | Rendimiento | Tasa de Refresco Estable | Mantener **60 FPS sostenidos** con una fluctuación máxima de ±2 FPS en hardware estándar. |
| **RNF-02** | Rendimiento | Latencia de Entrada | El tiempo transcurrido entre la pulsación de un botón en el gamepad y su procesamiento gráfico no debe exceder los **16 ms** (1 frame). |
| **RNF-03** | Estabilidad | Gestión de Memoria | La memoria RAM utilizada por el proceso no debe crecer en más de **50 MB** tras alternar 20 veces entre juegos diferentes (sin fugas acumulativas). |
| **RNF-04** | Portabilidad | Compatibilidad de SO | Operatividad garantizada en **macOS (Intel y Apple Silicon M1-M4)** y distribuciones **Linux** x86_64 con Python 3.10 a 3.14. |
| **RNF-05** | Usabilidad | Simplicidad de Operación | El sistema debe ser completamente operable sin ratón ni comandos de texto tras su arranque. |
| **RNF-06** | Mantenibilidad | Silenciado de Avisos en Terminal | El arranque no debe emitir warnings de bibliotecas dylib Objective-C duplicadas en macOS. |
