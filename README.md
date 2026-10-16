# 🕹️ C.C.I. SYSTEM - Virtual Arcade Console

![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Pygame-CE](https://img.shields.io/badge/pygame--ce-2.5%2B-brightgreen)
![OpenCV](https://img.shields.io/badge/opencv--python-4.8%2B-red)
![Architecture](https://img.shields.io/badge/architecture-State%20Machine-purple)

**C.C.I. System** es una consola virtual arcade interactiva desarrollada en **Python** y **Pygame-CE (Community Edition)**. Unifica dos títulos de combate y acción bajo una misma ventana gráfica y gestor de ciclo de vida mediante un patrón arquitectónico de **Máquina de Estados (State Machine)**.

---

## 🎮 Videojuegos Integrados

1. **Da Vinci Fighters**
   - Homenaje técnico arcade a los juegos de lucha estilo Capcom CPS-1 / *Street Fighter II*.
   - Modos 1P vs CPU y 2P Local, selector de personajes, cinemáticas y escenarios temáticos.
2. **Metal Slug: Super Vehicle-001**
   - Réplica fiel del clásico de acción arcade de SNK (Neo-Geo).
   - Motor de físicas Pymunk, renderizado por capas, armas arcade y vehículos operables (*Metal Slug*).

---

## 🔄 Flujo de la Máquina de Estados

La consola inicializa una única ventana (`1280x720`) y ejecuta el siguiente pipeline de transiciones:

```
[BOOT] (CCI_INTRO.mp4)
   │  ↳ Salto con ENTER / ESPACIO ──────────┐
   ▼ (Al finalizar)                         │
[INTRO_AVATAR] (intro_cami.mp4)             │
   │  ↳ Salto con ENTER / ESPACIO ──────────┤
   ▼ (Al finalizar)                         │
   └───────────────────────────────────────►▼
                                         [MENU] (Arcade UI interactiva)
                                            │
                       ┌────────────────────┴────────────────────┐
                       ▼                                         ▼
           [PLAYING: Da Vinci Fighters]               [PLAYING: Metal Slug]
                       │                                         │
                       └─────────► Retorno con ESC / Salida ─────┘
                                            │
                                            ▼
                                          [MENU]
```

- **BOOT**: Reproducción fluida y sincronizada de `CCI_INTRO.mp4` a través de OpenCV (`cv2`).
- **INTRO_AVATAR**: Reproducción de la cinemática `intro_cami.mp4`.
- **MENU**: Selector de cartuchos con diseño arcade cyberpunk retro, levitación y resplandor de avatar, rejilla dinámica y efectos de audio.
- **PLAYING**: Ejecución del juego seleccionado compartiendo el mismo contexto gráfico (`screen`), aislando `sys.path` y `cwd` para evitar colisiones entre assets, y retornando de forma segura al menú principal.

> 💡 **Salto de Videos (Skip):** En cualquier momento durante los estados `BOOT` o `INTRO_AVATAR`, puedes presionar `ENTER` o `ESPACIO` para saltar directamente al `MENU`.

---

## 🚀 Requisitos e Instalación

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
```

### 2. Crear y Activar el Entorno Virtual (`venv`)

- **En macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

- **En Windows:**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```

### 3. Instalar Dependencias
Instala los paquetes necesarios definidos en `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Nota:** La librería principal de gráficos es `pygame-ce` (Community Edition). No debe coexistir con `pygame` tradicional en el mismo entorno.

---

## 🕹️ Ejecución

Con el entorno virtual activado, ejecuta el archivo principal:
```bash
python main.py
```

---

## ⌨️ Controles Globales

| Acción | Teclas |
| :--- | :--- |
| **Navegar en Menú** | `Flechas Arriba / Abajo` o `W / S` |
| **Seleccionar / Iniciar Juego** | `Enter` o `Espacio` |
| **Saltar Cinemáticas de Intro** | `Enter` o `Espacio` |
| **Salir al Menú / Cerrar Consola** | `Escape` |

---

## 📁 Estructura del Proyecto

```text
C.C.I-SYSTEM/
├── main.py                     # Punto de entrada principal y bucle del sistema
├── states.py                   # Máquina de Estados (Boot, IntroAvatar, Menu, Playing)
├── requirements.txt            # Dependencias del proyecto
├── .gitignore                  # Exclusión de binarios y cachés
├── README.md                   # Documentación oficial
├── CCI_INTRO.mp4               # Video de arranque de la consola
├── intro_cami.mp4              # Video cinemático del avatar
├── cami_player.png             # Sprite/Avatar para la interfaz gráfica
├── Davinci-Fighter/            # Paquete del juego 1 (Lucha arcade CPS-1)
└── METAL SLUG/                 # Paquete del juego 2 (Run & Gun Neo-Geo)
```

---

## 🛠️ Tecnologías Utilizadas

- **Python 3.10+**
- **Pygame-CE** (Renderizado 2D, gestión de eventos y audio mixer)
- **OpenCV (`cv2`)** (Decodificación de video MP4 y sincronización de FPS)
- **NumPy** (Síntesis y procesamiento de señales sonoras)
- **Pymunk** (Motor físico 2D para simulación arcade)

---

## 👩‍💻 Autora

Desarrollado por **Camila Ianni** ([@Camila-Ianni](https://github.com/Camila-Ianni))
