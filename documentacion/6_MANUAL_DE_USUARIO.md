# Manual de Usuario y Operación Arcade
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform & Retro Emulator)
**Documento:** Manual del Operador, Guía de Jugabilidad y Portal Web  
**Versión:** 3.0.0  
**Sitio Web Oficial:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)  

---

## 1. Guía Rápida de Inicio (Quickstart)

Bienvenido a **C.C.I. SYSTEM**, una consola virtual y emulador multiplataforma que reúne **19 clásicos arcade** en un entorno gráfico Cyberpunk / PS5 con renderizado a 60 FPS, soporte de mando háptico y perfiles de usuario independientes.

### Pasos para jugar de inmediato:
1. **Descarga el instalador de 1-clic:**
   * **macOS:** [Descargar DMG](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg) (Abrir con clic derecho > «Abrir» en primer inicio).
   * **Windows:** [Descargar EXE](https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe).
2. **Conecta tu mando de consola:** Soporta mandos de PS5 (DualSense), PS4 (DualShock 4), Xbox Series/One, Switch Pro y USB Arcade de forma automática (*Plug & Play*).
3. **Primer inicio con 0 perfiles de fábrica:**
   * La consola te recibirá invitándote a crear tu jugador.
   * Escribe tu nombre o alias, elige tu avatar cyberpunk con anillo de neón y confirma con `Enter` o `Botón A`.
4. **Navega por la Biblioteca y Carrusel:**
   * Explora los 19 juegos con las flechas o el stick del mando.
   * Presiona `Enter` o `Botón A` para iniciar el juego enfocado.
   * Presiona `F12` en cualquier momento para capturar la pantalla a 720p sin pérdidas.
5. **Cambiar de juego o volver al Menú:** Pulsa `Escape` o el botón `Select / Share` de tu mando para retornar al hub principal sin fugas de memoria.

---

## 2. Flujo Completo del Sistema y Estados Finitos

```
 ┌─────────────────────────────────────────────────────────────┐
 │                      ARRANQUE (BOOT)                        │
 │         Video CCI_INTRO.mp4 a pantalla completa             │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Al finalizar o Skip con Enter/A)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                  CINEMÁTICA DEL AVATAR                      │
 │       Pixel_girl_reading_dialogue_boxes_....mp4             │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Al finalizar o Skip con Enter/A)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │           PANTALLA DE SELECCIÓN DE USUARIO                  │
 │       Gestión de perfiles independientes y avatares         │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Elegir perfil activo)
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                 MENÚ PRINCIPAL (CARRUSEL 3D)                │
 │       19 títulos arcade, filtros, estadísticas y logros     │
 └──────┬───────────────────────┼───────────────────────┬──────┘
        │                       │                       │
        ▼                       ▼                       ▼
 ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
 │  BIBLIOTECA  │        │ PERFIL & F3  │        │ CONFIG (F8)  │
 │  (19 Juegos) │        │ (Trofeos/Hrs)│        │ (CRT/Haptics)│
 └──────┬───────┘        └──────┬───────┘        └──────┬───────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     ESTADO DE JUEGO                         │
 │     Ejecución segura a 1280x720 centrado con pillarbox      │
 └──────────────────────────────┬──────────────────────────────┘
                                │ (Presionar ESC / Botón Select)
                                ▼
                 (Retorno Limpio al MENÚ ARCADE)
```

---

## 3. Tabla Maestra de Mapeo de Controles

| Acción en la Consola | Teclado | PlayStation (PS4 / PS5) | Xbox (One / Series) | Switch Pro |
| :--- | :--- | :--- | :--- | :--- |
| **Navegar (Menús / Carrusel / Biblioteca)** | `Flechas` o `W, A, S, D` | `D-pad` o `Stick Izquierdo` | `D-pad` o `Stick Izquierdo` | `D-pad` o `Stick Izquierdo` |
| **Confirmar / Jugar / Seleccionar** | `Enter` o `Espacio` | Botón `Cruz ✕` (Botón 0) | Botón `A` (Botón 0) | Botón `B` (Botón 0) |
| **Volver / Salir de Juego** | `Escape` | Botón `Share / Create` (Botón 6) | Botón `View / Back` (Botón 6) | Botón `- (Minus)` |
| **Saltar Cinemáticas de Intro** | `Enter` o `Espacio` | `Cualquier botón frontal` | `Cualquier botón frontal` | `Cualquier botón frontal` |
| **Cambiar Usuario / Switch Perfil** | `F3` (en Perfil o Menú) | `Botón Cambiar Perfil` | `Botón Cambiar Perfil` | `Botón Cambiar Perfil` |
| **Capturador HD Instantáneo** | `F12` | — | — | — |
| **Navegación Rápida Sidebar** | `F4` Juegos · `F5` Inicio · `F6` Perfil · `F7` Logros · `F8` Ajustes | `Sidebar interactiva` | `Sidebar interactiva` | `Sidebar interactiva` |

---

## 4. Catálogo Detallado de los 19 Juegos Integrados

1. **Da Vinci Fighters (Lucha 2D Arcade):** Motor CPS-1 propio, combate 1P vs CPU y 2P Local, supers, combos, cinemáticas y personajes originales (*Cami, Enith, Martín*).
2. **Asteroids (Arcade Espacial Vectorial):** Tributo al clásico de Atari de 1979 con física de inercia newtoniana, disparos de plasma y salto al hiperespacio (`H`).
3. **Super Mario Bros (Plataformas 2D):** Aventura de plataformas modular con físicas precisas de salto, power-ups y niveles emblemáticos.
4. **The Legend of Zelda (Acción / RPG):** Exploración top-down en Hyrule, recolección de armas, magias e inventario dinámico.
5. **Pac-Man (Laberinto Clásico):** IA de fantasmas basada en cuadrícula, consumo de pellets, power pellets y audio retro.
6. **Tetris (Puzzle):** Caída y rotación de tetriminos, despeje de líneas, puntuación progresiva y control de velocidad.
7. **Space Invaders (Shoot 'em up Fijo):** Formación de naves alienígenas descendentes, 4 búnkeres destructibles y ovnis sorpresa.
8. **Metal Slug (Run & Gun):** Recreación fiel de Neo-Geo con físicas Pymunk, armamento pesado y vehículos de combate.
9. **DOOM (FPS 3D):** Motor de renderizado en primera persona por Raycasting, enemigos animados, mapa laberíntico y captura de mouse.
10. **Flappy Bird (Arcade de Habilidad):** Vuelo y esquive de tuberías retro con colisión píxel a píxel.
11. **Dino Run (Endless Runner):** Salto y agachado esquivando cactus y pterodáctilos con aceleración continua.
12. **Ghostbusters (Acción / Aventura):** Scroll lateral con efecto parallax, captura de fantasmas y granadas demoledoras.
13. **Cyberpunk Metroidvania (Plataformas / Aventura):** Ambientación futurista distópica con parkour y combate cuerpo a cuerpo.
14. **Pokémon (RPG por Turnos):** Aventura clásica por Kanto, combates estratégicos por turnos y selección de ataques elementales.
15. **Mega Man (Acción / Plataformas):** Disparos Buster, saltos milimétricos y desafíos de escenario.
16. **Castlevania (Aventura Gótica):** Látigo Vampire Killer, candelabros, subarmas mágicas y enemigos clásicos contra Drácula.
17. **Bubble Bobble (Plataformas Arcade):** Disparo de burbujas, atrapado de monstruos y recolección de frutas.
18. **Plants vs. Zombies (Tower Defense):** Siembra estratégica de plantas, gestión de soles y oleadas de no-muertos.
19. **Donkey Kong (Plataformas Clásico):** Escalada por andamios metálicos esquivando barriles rodantes para rescatar a Pauline.

---

## 5. Portal Web Oficial ([https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com))

El proyecto cuenta con una landing page oficial alojada en la nube construida 100% en Python mediante Flask:
- **Catálogo Interactivo:** Tarjetas con los logos e ilustraciones oficiales de los 19 juegos.
- **Fichas Técnicas Modales:** Cada tarjeta se puede inspeccionar con un clic para conocer año, desarrollador, género y mecánicas.
- **Descargas Oficiales:** Botones de descarga directa que enlazan con los instaladores empaquetados en GitHub Releases para macOS y Windows.
- **Ficha de Autoría:** Sección de perfil dedicada a la autora **Camila Carolina Ianni** (Estudiante de Analista de Sistemas - Escuela Da Vinci).
