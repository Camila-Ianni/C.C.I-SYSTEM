# Manual de Instalación, Configuración y Despliegue
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform)
**Documento:** Manual Técnico de Instalación y Administración de Entorno  
**Versión:** 2.0.0  

---

## 1. Requisitos de Hardware y Arquitectura Soportada

### 1.1. Arquitecturas y Plataformas Homologadas
* **macOS:** Compatible con macOS Monterey 12.0 o superior en arquitecturas:
  * **Apple Silicon:** M1, M2, M3, M4 (ejecución nativa `arm64`).
  * **Intel Core:** Core i5/i7/i9 (`x86_64`).
* **Linux:** Compatible con distribuciones modernas:
  * Ubuntu 20.04 LTS / 22.04 LTS / 24.04 LTS.
  * Debian 11 / 12, Fedora 38+, Arch Linux.
* **Windows (Experimental):** Windows 10/11 con Python oficial y drivers SDL2 actualizados.

### 1.2. Especificaciones Mínimas y Recomendadas

| Componente | Especificación Mínima | Especificación Recomendada |
| :--- | :--- | :--- |
| **CPU** | Procesador Dual-Core 2.0 GHz | Quad-Core 2.5 GHz o Apple Silicon M-Series |
| **Memoria RAM** | 4 GB | 8 GB o superior |
| **Resolución de Pantalla** | 1280 x 720 píxeles (720p) | 1920 x 1080 píxeles (1080p) con escalado |
| **Tarjeta Gráfica** | Gráficos integrados con soporte OpenGL 2.1 | GPU dedicada o integrada moderna (Metal / Vulkan / Direct3D) |
| **Tarjeta de Sonido** | Estéreo integrada estándar con soporte de 44.1 kHz | Dispositivo de audio compatible con baja latencia |
| **Espacio en Disco** | 500 MB libres | 1 GB libre (para paquetes de audio y logs) |

---

## 2. Árbol de Directorios y Estructura del Software

Para que el sistema funcione correctamente, la jerarquía de carpetas debe mantenerse intacta:

```text
C.C.I SYSTEM/
│
├── main.py                                      # Entry point principal y ciclo de eventos
├── states.py                                    # Gestor de Estados, JoystickManager y Runners
├── requirements.txt                             # Especificación estricta de dependencias
├── README.md                                    # Resumen rápido del proyecto
│
├── CCI_INTRO.mp4                                # Video cinemático de arranque (Boot)
├── Pixel_girl_reading_dialogue_boxes_....mp4     # Video cinemático de avatar (Intro Cami)
│
├── games.png                                    # Arte de fondo base del arcade (1452x1083)
├── cards-bn.jpeg                                # Grilla de tarjetas en blanco y negro (2400x1792)
├── cards-color.jpeg                             # Grilla de tarjetas a color (2400x1792)
│
├── documentacion/                               # Suite documental técnica integral (8 archivos)
│   ├── 1_RELEVAMIENTO_Y_ALCANCE.md
│   ├── 2_PROPUESTA_DE_VALOR.md
│   ├── 3_SRS_ESPECIFICACION_REQUERIMIENTOS.md
│   ├── 4_CASOS_DE_USO.md
│   ├── 5_MANUAL_DE_INSTALACION.md
│   ├── 6_MANUAL_DE_USUARIO.md
│   ├── 7_DIAGRAMA_DE_GANTT.md
│   └── 8_CODIGO_FUENTE_Y_ARQUITECTURA.md
│
├── Davinci-Fighter/                             # Cartucho 1: Juego de Pelea 2D
├── METAL SLUG/                                  # Cartucho 2: Run & Gun Neo-Geo
├── Mario/                                       # Cartucho 3: Super Mario Bros
├── PacMan/                                      # Cartucho 4: Pac-Man Clásico
├── Space-invaders/                              # Cartucho 5: Space Invaders
└── asteroids/                                   # Cartucho 6: Atari Asteroids Vectorial
```

---

## 3. Guía de Instalación Paso a Paso

### Paso 1: Clonar el Repositorio Oficial
Abre una ventana de terminal y descarga el código fuente mediante Git:
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd "C.C.I-SYSTEM"
```

### Paso 2: Crear el Entorno Virtual Aislado (`.venv`)
No instales los paquetes globalmente para evitar conflictos con versiones previas de Pygame o herramientas del sistema operativo.
```bash
# Crear entorno virtual con Python 3
python3 -m venv .venv

# Activar el entorno virtual:
# En macOS / Linux:
source .venv/bin/activate
# En Windows (PowerShell):
# .venv\Scripts\Activate.ps1
```
*(Al activarse con éxito, tu prompt mostrará `(.venv)` al inicio de la línea).*

### Paso 3: Actualizar el Gestor Pip e Instalar Dependencias
Instala las librerías necesarias con las versiones validadas:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Lista de Paquetes en `requirements.txt`:
* `pygame-ce==2.5.8`: Motor de renderizado 2D, interfaz con SDL2, audio estéreo y control de eventos.
* `opencv-python==5.0.0.93`: Decodificador acelerado de video MP4 y lectura de fotogramas en matrices numéricas.
* `numpy==2.5.4`: Estructuras de datos de alto rendimiento requeridas por OpenCV y transformaciones de superficies.
* `pymunk==7.3.1`: Motor de físicas 2D basado en Chipmunk (utilizado en las colisiones de Metal Slug).
* `cffi==2.1.1`: Interfaz de funciones foráneas en C requerida para bindings de bajo nivel.

### Paso 4: Comprobación de Integridad de la Instalación
Ejecuta el siguiente comando para verificar que todas las dependencias y submódulos compilen y carguen correctamente:
```bash
python -c "
import pygame, cv2, numpy, pymunk
print('--- C.C.I. SYSTEM DIAGNÓSTICO ---')
print('Pygame-CE :', pygame.__version__)
print('OpenCV    :', cv2.__version__)
print('Pymunk    :', pymunk.__version__)
print('Joysticks :', pygame.joystick.get_count())
print('ESTADO    : TODO CORRECTO PARA EJECUTAR')
"
```

---

## 4. Despliegue y Ejecución

Para iniciar la consola virtual, ejecuta en tu terminal con el entorno virtual activo:
```bash
python main.py
```

### Opciones de Ejecución Especiales:
* **Ejecución directa en pantalla completa / modo arcade:**
  La ventana está preconfigurada en `1280x720`. Si se desea ejecutar en monitores arcade o televisores de salón, la superficie centra automáticamente el aspecto mediante pillarboxing sin deformar los juegos.

---

## 5. Matriz de Resolución de Problemas y Diagnósticos Técnicos

```
                               ┌───────────────────────────┐
                               │   ÁRBOL DE RESOLUCIÓN     │
                               └─────────────┬─────────────┘
                                             │
             ┌───────────────────────────────┴───────────────────────────────┐
             ▼                                                               ▼
   [ Error al importar ]                                          [ Problemas de Mandos ]
             │                                                               │
   - ¿Activaste .venv?                                            - ¿Mando conectado por USB/BT?
   - source .venv/bin/activate                                    - Presiona botón para despertar
   - pip install -r requirements.txt                              - Hotplugging automático activo
```

### 5.1. Error: `ModuleNotFoundError: No module named 'pygame'`
* **Diagnóstico:** Se está utilizando el intérprete de Python global del sistema en lugar del entorno virtual.
* **Solución:** Ejecuta `source .venv/bin/activate` antes de correr el script.

### 5.2. En macOS: `objc[...] Class SDLApplication is implemented in both...`
* **Diagnóstico:** Conflicto originado cuando `opencv-python` y `pygame-ce` traen librerías SDL2 dinámicas compiladas dentro de sus directorios `.dylibs/`.
* **Solución:** Ya se encuentra implementado en [main.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/main.py) y [states.py](file:///Users/cami/Desktop/C.C.I%20SYSTEM/states.py) un supresor de bajo nivel (`os.dup2` sobre el descriptor `stderr` durante la importación inicial), evitando la emisión de estos mensajes sin perjudicar la ejecución.

### 5.3. El audio no se escucha en el video de inicio
* **Diagnóstico:** En macOS, `afplay` requiere permisos estándar de audio del usuario.
* **Solución:** Verifica que el volumen del sistema esté encendido y que el archivo `CCI_INTRO.mp4` o `Pixel_girl...mp4` no hayan sido renombrados.

### 5.4. El mando no responde en el menú
* **Diagnóstico:** Algunos mandos entran en suspensión tras unos minutos de inactividad.
* **Solución:** Presiona el botón central (PlayStation / Xbox) para reactivar la conexión Bluetooth. Gracias a la clase `JoystickManager`, el sistema detectará el evento `JOYDEVICEADDED` y lo reconfigurará al instante.
