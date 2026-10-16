# Manual de Usuario y Operación Arcade
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform)
**Documento:** Manual del Operador y Guía de Jugabilidad  
**Versión:** 2.0.0  

---

## 1. Guía Rápida de Inicio (Quickstart)

Bienvenido a **C.C.I. SYSTEM**, una consola virtual arcade que reúne 6 títulos clásicos en una única experiencia interactiva. 

### Pasos para jugar de inmediato:
1. Conecta tu mando de consola (PlayStation, Xbox o Switch) a tu computadora por USB o Bluetooth.
2. Inicia la consola desde la terminal con:
   ```bash
   python main.py
   ```
3. Disfruta de la cinemática de arranque, o pulsa **Enter** / **Espacio** / **Botón A** en tu mando para saltar directo al menú.
4. Desplázate por los 6 cartuchos usando el stick analógico o las flechas de dirección. Notarás que el juego enfocado se ilumina a todo color.
5. Pulsa **Enter** o **Botón A** para iniciar el juego.
6. Cuando quieras cambiar de juego, pulsa **ESC** o el botón **Select** para regresar al menú principal.

---

## 2. Mapa de Navegación y Flujo de Pantallas

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      ARRANQUE (BOOT)                        │
 │         Video CCI_INTRO.mp4 a pantalla completa             │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Al finalizar o Skip)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                  CINEMÁTICA DEL AVATAR                      │
 │    Pixel_girl_reading_dialogue_boxes_20261016123851.mp4     │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Al finalizar o Skip)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                   MENÚ ARCADE (games.png)                   │
 │                                                             │
 │   [ (0,0) Da Vinci ]   [ (0,1) Metal Slug ]   [ (0,2) Asteroids ]   │
 │   [ (1,0) Mario    ]   [ (1,1) Pac-Man    ]   [ (1,2) Space Inv ]   │
 └──────────────────────────────┬──────────────────────────────┘
                                │
               [ Seleccionar Cartucho + Confirmar ]
                                │
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     ESTADO DE JUEGO                         │
 │          Ejecución del título a 1280x720 centrado           │
 └──────────────────────────────┬──────────────────────────────┘
                                │
                  [ Presionar ESC / Botón Select ]
                                │
                                ▼
                 (Retorno Limpio al MENÚ ARCADE)
```

---

## 3. Tabla Maestra de Mapeo de Controles

El sistema cuenta con un traductor inteligente (`JoystickManager`) que homologa los botones de mandos comerciales con los eventos de teclado de Pygame:

| Acción en la Consola | Teclado | PlayStation (DualShock / DualSense) | Xbox (One / Series / 360) | Nintendo Switch (Pro Controller) |
| :--- | :--- | :--- | :--- | :--- |
| **Navegar Cuadrícula (Arriba/Abajo/Izq/Der)** | `Flechas` o `W, A, S, D` | `Stick Analógico Izquierdo` o `D-pad` | `Stick Analógico Izquierdo` o `D-pad` | `Palanca Izquierda` o `D-pad` |
| **Confirmar / Jugar / Disparar** | `Enter`, `Espacio` | Botón `Cruz ✕` (Botón 0) | Botón `A` (Botón 0) | Botón `B` (Botón 0) |
| **Acción Secundaria / Granada / Bomba** | `B` | Botón `Círculo ○` (Botón 1) | Botón `B` (Botón 1) | Botón `A` (Botón 1) |
| **Golpe Débil / Ataque Ligero** | `J` | Botón `Cuadrado ◻` (Botón 2) | Botón `X` (Botón 2) | Botón `Y` (Botón 2) |
| **Golpe Fuerte / Ataque Pesado** | `K` | Botón `Triángulo △` (Botón 3) | Botón `Y` (Botón 3) | Botón `X` (Botón 3) |
| **Patada Débil / Salto Secundario** | `U` | Botón `L1` (Botón 4) | Botón `LB` (Botón 4) | Botón `L` (Botón 4) |
| **Patada Fuerte / Turbo / Correr** | `I` | Botón `R1` (Botón 5) | Botón `RB` (Botón 5) | Botón `R` (Botón 5) |
| **Pausar / Iniciar Partida (Start)** | `Enter` | Botón `Options` (Botón 7) | Botón `Menu / Start` (Botón 7) | Botón `+ (Plus)` (Botón 7) |
| **Volver al Menú Principal** | `ESC` | Botón `Share / Create` (Botón 6) | Botón `View / Back` (Botón 6) | Botón `- (Minus)` (Botón 6) |
| **Salir de C.C.I. System** | `ESC` (en el Menú) | Cerrar ventana | Cerrar ventana | Cerrar ventana |

---

## 4. Manual de Juego Cartucho por Cartucho

### 4.1. Da Vinci Fighters (Fila 0, Columna 0)
* **Descripción:** Juego de lucha 2D arcade con física de combate, barras de vida, efectos de impacto y selección de personajes históricos.
* **Mecánica:**
  * Puedes elegir modo `1P vs AI` o `1P vs 2P Local`.
  * Reduce la vida de tu adversario antes de que termine el tiempo para ganar el round.
* **Controles Jugador 1:**
  * `A` / `D`: Caminar hacia adelante y atrás.
  * `W`: Saltar.
  * `S`: Agacharse.
  * `J`: Puño ligero | `K`: Puño fuerte.
  * `U`: Patada ligera | `I`: Patada fuerte.
  * `L`: Bloqueo defensivo.
  * `O`: Ataque especial | `P`: Ataque Ultimate.

---

### 4.2. Metal Slug (Fila 0, Columna 1)
* **Descripción:** Recreación fidedigna de la obra maestra de Neo-Geo (SNK). Shooter de plataformas lateral donde encarnas a los soldados de las Fuerzas Especiales Peregrine Falcons.
* **Mecánica:**
  * Dispara a la infantería enemiga, destruye tanques y helicópteros, libera a los prisioneros de guerra para obtener potenciadores de armamento (Heavy Machine Gun, Shotgun, Rocket Launcher).
* **Controles:**
  * `Flechas` o `Stick Analógico`: Mover y apuntar en 8 direcciones.
  * `Espacio` / `Botón Cruz (PS)` / `Botón A (Xbox)`: Disparo continuo.
  * `W` / `Gatillo`: Salto.
  * `B` / `Botón Círculo (PS)`: Lanzar granadas demoledoras.

---

### 4.3. Asteroids (Fila 0, Columna 2)
* **Descripción:** Tributo al clásico de Atari de 1979 basado en gráficos vectoriales monocromáticos y física de inercia newtoniana.
* **Mecánica:**
  * Pilota una nave en gravedad cero. Al disparar contra los grandes asteroides, estos se fracturarán en piezas medianas y pequeñas que se desplazan a mayor velocidad. Destruye también los platillos voladores enemigos.
* **Controles:**
  * `Flecha Izquierda` / `Flecha Derecha`: Rotar orientación de la nave.
  * `Flecha Arriba`: Encender cohetes de propulsión (Thrust) para ganar inercia.
  * `Espacio`: Disparo de cañón de plasma.
  * `H`: Salto al Hiperespacio (teletransportación instantánea aleatoria en situaciones límite).

---

### 4.4. Super Mario Bros (Fila 1, Columna 0)
* **Descripción:** El legendario plataformas de Nintendo. Controla a Mario a través del Mundo 1-1, sorteando fosos, Goombas y Koopas.
* **Mecánica:**
  * Golpea los bloques `?` para obtener monedas y champiñones mágicos. Salta sobre los enemigos para derrotarlos y alcanza el asta final de la bandera para completar el nivel.
* **Controles:**
  * `Flecha Izquierda` / `Derecha`: Caminar.
  * `A` o `Espacio`: Salto (mantén presionado para mayor elevación).
  * `S` / `Botón X`: Correr a alta velocidad / Lanzar bolas de fuego (si tienes la flor).

---

### 4.5. Pac-Man (Fila 1, Columna 1)
* **Descripción:** El videojuego de laberintos por antonomasia de Namco.
* **Mecánica:**
  * Limpia el laberinto comiendo todos los pequeños pellets mientras evitas ser atrapado por los cuatro fantasmas (Blinky, Pinky, Inky y Clyde). Ingiere un "Power Pellet" (pellet grande) para volver azules a los fantasmas y devóralos para obtener puntaje extra.
* **Controles:**
  * `Flechas Arriba, Abajo, Izquierda, Derecha` o `WASD`: Marcar el siguiente giro en el laberinto.

---

### 4.6. Space Invaders (Fila 1, Columna 2)
* **Descripción:** El icónico shooter de Taito de 1978.
* **Mecánica:**
  * Una formación de naves alienígenas desciende progresivamente hacia la superficie terrestre mientras aumenta su cadencia de disparo y velocidad de marcha. Usa los 4 búnkeres protectores como cobertura antes de que sean perforados por el fuego enemigo.
* **Controles:**
  * `Flechas Izquierda / Derecha`: Desplazar el cañón láser terrestre.
  * `Espacio` / `Botón A`: Disparar pulso láser hacia arriba.
