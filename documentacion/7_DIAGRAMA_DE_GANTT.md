# Cronograma de Proyecto, Gestión y Diagrama de Gantt
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform)
**Documento:** Gestión de Tiempos, Tareas y Planificación  
**Versión:** 2.0.0  

---

## 1. Metodología de Gestión del Proyecto

El desarrollo de **C.C.I. SYSTEM** se ejecutó bajo una adaptación del marco de trabajo ágil **Scrum**, articulado en **Sprints semanales** enfocados en la entrega continua de valor y la mitigación temprana de riesgos técnicos (como problemas de dependencias nativas SDL2 en macOS, gestión de buffers de sonido en procesos paralelos y compatibilidad de mandos).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CICLO DE DESARROLLO DEL PROYECTO                      │
├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│     SPRINT 1      │     SPRINT 2      │     SPRINT 3      │    SPRINT 4     │
│   (Arquitectura)  │  (DaVinci/MSlug)  │   (6 Cartuchos)   │(Joysticks/Docs) │
├───────────────────┼───────────────────┼───────────────────┼─────────────────┤
│ • FSM Core        │ • Encapsulado DF  │ • 4 Nuevos Juegos │ • Hotplug Joy   │
│ • Window HD 720p  │ • Pipeline MSlug  │ • Grid 2x3 Menú   │ • Intercept Key │
│ • Video + afplay  │ • Fix Tearing     │ • Hover B&N/Color │ • Intro Cami HD │
│ • Skip en Videos  │ • Singleton Sound │ • Cleanup Frames  │ • Suite Docs    │
└───────────────────┴───────────────────┴───────────────────┴─────────────────┘
```

---

## 2. Diagrama de Gantt Integral (Mermaid)

El siguiente diagrama cronológico ilustra el desglose de tareas, precedencias y tiempos de ejecución del proyecto:

```mermaid
gantt
    title Plan de Desarrollo Integral - C.C.I. SYSTEM
    dateFormat  YYYY-MM-DD
    axisFormat  %d/%m

    section Fase 1: Arquitectura Base & FSM
    Levantamiento de Requisitos y FSM       :done, a1, 2026-10-01, 2026-10-03
    Diseño de Window Manager 1280x720       :done, a2, 2026-10-03, 2026-10-05
    Integración OpenCV cv2 para Videos      :done, a3, 2026-10-05, 2026-10-06
    Desarrollo de VideoAudioPlayer (afplay) :done, a4, 2026-10-06, 2026-10-07
    Lógica de Interrupción Skip (Enter/Spc) :done, a5, 2026-10-07, 2026-10-08

    section Fase 2: Integración Da Vinci & Metal Slug
    Encapsulamiento de Da Vinci Fighters    :done, b1, 2026-10-08, 2026-10-10
    Adaptación de Metal Slug (Neo-Geo 320x224):done, b2, 2026-10-10, 2026-10-11
    Corrección de Tearing y Single Flip     :done, b3, 2026-10-11, 2026-10-12
    Reinicio de Rutas Singleton SoundManager:done, b4, 2026-10-12, 2026-10-13

    section Fase 3: Expansión a 6 Juegos & Menú Visual
    Integración de Super Mario Bros         :done, c1, 2026-10-13, 2026-10-14
    Integración de Pac-Man                  :done, c2, 2026-10-14, 2026-10-14
    Integración de Space Invaders           :done, c3, 2026-10-14, 2026-10-15
    Integración de Asteroids Vectorial      :done, c4, 2026-10-15, 2026-10-15
    Diseño de Rejilla 2x3 con games.png     :done, c5, 2026-10-15, 2026-10-15
    Desarrollo de Hover B&N a Color         :done, c6, 2026-10-15, 2026-10-16
    Eliminación de Contorno Celeste Residual:done, c7, 2026-10-16, 2026-10-16
    Nueva Intro Cinemática Pixel Girl       :done, c8, 2026-10-16, 2026-10-16

    section Fase 4: Mandos Universales & Documentación
    Implementación de JoystickManager       :done, d1, 2026-10-16, 2026-10-16
    Soporte de Hotplugging y Mapeo Universal:done, d2, 2026-10-16, 2026-10-16
    Redacción Técnica SRS IEEE 830          :done, d3, 2026-10-16, 2026-10-16
    Redacción de Manuales de Usuario/Instal.:done, d4, 2026-10-16, 2026-10-16
    Modelado UML y Arquitectura de Código   :done, d5, 2026-10-16, 2026-10-16
```

---

## 3. Matriz de Tareas, Responsables y Criterios de Aceptación (WBS)

| Código | Tarea / Entregable | Duración | Dependencia Previa | Criterio de Aceptación y Validación |
| :--- | :--- | :--- | :--- | :--- |
| **WBS 1.1** | Inicializador de Estados `states.py` | 2 días | N/A | Transición limpia entre clases derivadas de `BaseState`. |
| **WBS 1.2** | Renderizador OpenCV con Audio | 3 días | WBS 1.1 | `CCI_INTRO.mp4` se reproduce a 30 FPS sin lag de audio. |
| **WBS 2.1** | Adaptación Gráfica de Metal Slug | 2 días | WBS 1.2 | Neo-Geo se escala a 1280x720 sin estirar proporciones. |
| **WBS 2.2** | Eliminación de Tearing en Metal Slug | 1 día | WBS 2.1 | Se elimina la llamada duplicada a `display.flip()`. |
| **WBS 3.1** | Inclusión de Mario, Pacman, Space, Asteroids | 2 días | WBS 2.2 | Los 4 juegos arrancan en la misma ventana con audio. |
| **WBS 3.2** | Menú Arcade Rejilla 2x3 con Hover | 1 día | WBS 3.1 | Cartucho inactivo en B&N y cartucho enfocado a color. |
| **WBS 3.3** | Integración Video Cinemático Pixel Girl | 0.5 días | WBS 3.2 | Nuevo video con sonido reemplaza la intro previa. |
| **WBS 4.1** | Módulo `JoystickManager` | 1 día | WBS 3.3 | Mandos PS5/Xbox/Switch operan en los 6 juegos. |
| **WBS 4.2** | Suite Documental Completa (8 Documentos) | 1 día | WBS 4.1 | Documentación técnica exhaustiva lista para entrega. |

---

## 4. Gestión de Riesgos y Mitigaciones Implementadas

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MATRIZ DE RIESGOS                                │
├───────────────────────────────────┬──────────────┬──────────────────────────┤
│             RIESGO                │   IMPACTO    │   MITIGACIÓN APLICADA    │
├───────────────────────────────────┼──────────────┼──────────────────────────┤
│ 1. Colisión de librerías dylib    │ Crítico      │ Supresión a nivel de     │
│    SDL2 en macOS.                 │ (Cuelgues)   │ descriptor os.dup2 en    │
│                                   │              │ el arranque temprano.    │
├───────────────────────────────────┼──────────────┼──────────────────────────┤
│ 2. Tearing en Metal Slug por      │ Alto         │ Interceptación de        │
│    doble renderizado de pantalla. │ (Flickering) │ ms_instance.draw para un │
│                                   │              │ único flip por frame.    │
├───────────────────────────────────┼──────────────┼──────────────────────────┤
│ 3. Juegos diseñados sólo para     │ Alto         │ Inyección de eventos y   │
│    teclado ignoran los gamepads.  │ (Injugable)  │ ScancodeWrapper sobre    │
│                                   │              │ pygame.key.get_pressed.  │
├───────────────────────────────────┼──────────────┼──────────────────────────┤
│ 4. Desalineación de audio al      │ Medio        │ Limpieza de canales con  │
│    salir de un juego con ESC.     │ (Ruido/Bug)  │ pygame.mixer.stop() en   │
│                                   │              │ el bloque finally.       │
└───────────────────────────────────┴──────────────┴──────────────────────────┘
```
