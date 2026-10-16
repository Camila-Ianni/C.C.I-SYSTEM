# Metal Slug 1: Super Vehicle-001 (Pygame Arcade Replica)

Réplica fiel para PC del clásico arcade **Metal Slug (1996 - SNK)** desarrollado en **Python** utilizando **pygame-ce**, **Pymunk** y arquitectura arcade original a resolución nativa Neo-Geo (320x224 escalado pixel-perfect).

---

## 📋 Requisitos Previos

- **Python 3.10 o superior** (probado y verificado en Python 3.11, 3.12, 3.13 y 3.14).
- **Git** instalado en tu sistema.
- **pip** (administrador de paquetes de Python).

---

## 🚀 Cómo Iniciar el Juego desde la Terminal

Sigue estos sencillos pasos desde tu terminal (macOS, Linux o Windows):

### 1. Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/Metal-Slug.git
cd Metal-Slug
```

---

### 2. Crear y Activar el Entorno Virtual (Recomendado)

#### En macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### En Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### En Windows (Símbolo del sistema / CMD):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

---

### 3. Instalar las Dependencias
Con el entorno virtual activado, instala las librerías necesarias ejecutando:
```bash
pip install -r requirements.txt
```

> **Librerías instaladas:**
> - `pygame-ce` (Motor de gráficos y eventos 2D de alta fidelidad)
> - `pymunk` (Motor de física 2D para proyectiles, gravedad y colisiones)
> - `Pillow` (Procesamiento y carga de spritesheets)
> - `numpy` (Cálculos de transformaciones)

---

### 4. Iniciar el Juego 🎮

Para lanzar el juego:
```bash
python3 main.py
```
*(En Windows puedes usar `python main.py`)*

---

## 🕹️ Controles del Juego

El juego cuenta con soporte para **Teclado** y soporte automático plug-and-play para **Gamepads / Joysticks** (PlayStation 5 DualSense, Xbox, etc.):

| Acción | Teclado (Primario) | Teclado (Alternativo) | Gamepad (PS5 / Xbox) |
| :--- | :--- | :--- | :--- |
| **Moverse / Agacharse / Apuntar** | `W`, `A`, `S`, `D` | Flechas direccionales | D-Pad o Stick analógico |
| **Disparar / Cuchillo (Melee)** | `J` | `Z` / `F` | Cuadrado / Botón X / R1 / R2 |
| **Saltar** | `K` | `X` / `Barra Espaciadora` | Cruz (X) / Botón A / L1 |
| **Granada / Bomba** | `L` | `C` / `E` | Círculo (O) / Triángulo / L2 |
| **Entrar al Tanque (Metal Slug)** | `S` + `K` (Abajo + Salto) | Flecha Abajo + `X` | Abajo + Cruz |
| **Salir del Tanque (Slug Out)** | `S` + `K` (Abajo + Salto) | Flecha Abajo + `X` | Abajo + Cruz |
| **Insertar Ficha (Insert Coin)** | `5` | `5` | Botón Share / Touchpad / Back |
| **Iniciar Juego (Start)** | `Enter` | `1` | Botón Options / Menu / Start |

---

## 🧪 Ejecución de Pruebas (Tests Automatizados)

El proyecto cuenta con una suite completa de pruebas unitarias y de integración end-to-end (202 tests E2E + 4 tests de arquitectura de capas y física):

```bash
# Ejecutar la suite completa de pruebas E2E (en modo headless)
python3 tests/run_all_tests.py

# Ejecutar las pruebas de la arquitectura moderna (Pymunk + FRect + LayeredUpdates)
python3 -m unittest tests/test_modern_architecture.py
```

---

## 🛠️ Tecnologías y Arquitectura

- **Resolución nativa Neo-Geo**: Renderizado a 320x224 reescalado x3 (960x672) con filtrado vecino más cercano (pixel art nítido).
- **`pygame.FRect`**: Posicionamiento con precisión sub-píxel de punto flotante para trayectorias suaves.
- **`pygame.sprite.LayeredUpdates`**: Orden de dibujado por capas arcade (Fondo lejano, Terreno, Elementos interactivos, Jugador, Enemigos, HUD).
- **`Pymunk 7.3+`**: Simulaciones físicas precisas y colisiones sólidas sin riesgo de clip o caída al vacío.
- **Audio y SFX**: Efectos de sonido y voces sintetizadas fieles a la placa Neo-Geo MVS.
