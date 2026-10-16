# Original User Request

## 2026-09-25T14:24:00Z

Recreación arcade idéntica y 100% animada de la secuencia pre-combate de Street Fighter II (Intro Arcade, Opening Cutscene del golpe y paneo, Title Screen home.png, Player Select player select.png, VS Screen con vuelo de avión sobre mapa mundial) para Da Vinci Fighters en Python 3 + Pygame.

Working directory: /Users/cami/Desktop/Final Python

## Requirements

### R1. Secuencia Completa Pre-Combate y Cutscenes Animadas
Implementar la secuencia continua previa al combate basada exactamente en Street Fighters.mov:
1. Intro Arcade & Opening Cutscene Animada: Reproducción fluida a 60 FPS de la escena de apertura (luchadores golpeando en la calle frente al edificio, paneo de cámara hacia el cielo y caída del logotipo).
2. Title Screen Oficial (home.png): Logotipo con brillo animado, música Opening Theme.mp3 y texto parpadeante "PRESS ANY KEY TO START".
3. Player Select Screen (player select.png): Mapa mundial real de player select.png, casillas de retratos animadas para los 5 profesores (Carloni, Cavasso, Romero, Gamaliel, Sellanes), selecciones P1/P2/IA con parpadeo y audio Character Select.mp3.
4. VS Screen & Animación de Vuelo del Avión: Cutscene animada del avión sobrevolando el mapa mundial desde el país de origen de P1 hasta la ubicación del oponente P2 con destellos "VS" y retratos de combate antes de ingresar a la pelea.

### R2. Integración Fiel de Assets y Motor de Animación
Usar assets/backgrounds/player select.png, assets/backgrounds/home.png y la secuencia de frames de assets/Street Fighters.mov para garantizar máxima fidelidad visual arcade a 60 FPS.

## Acceptance Criteria

### Secuencia Pre-Combate Animada
- [ ] La secuencia inicial ejecuta: Intro -> Opening Cutscene animada -> Title Screen (home.png) -> Player Select (player select.png) -> VS Screen con Vuelo de Avión -> Escenario de Combate.
- [ ] La escena de apertura (luchador golpeando y paneo de cámara hacia el título) se reproduce de forma fluida a 60 FPS.
- [ ] La pantalla player select.png utiliza el mapa mundial con recuadros alineados para los 5 profesores y selectores parpadeantes P1/P2.
- [ ] La pantalla VS reproduce la animación del avión volando por el mapa con puntos de ruta hacia el país de destino.
- [ ] Sincronización completa de audio MP3 (Opening Theme.mp3, Character Select.mp3, fight, victory).
