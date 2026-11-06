# C.C.I. SYSTEM — Fase 7: Adaptación Android (APK)

## 1. Resumen Ejecutivo
La **Fase 7** dota a **C.C.I. SYSTEM** de capacidades completas de empaquetado y ejecución en dispositivos móviles **Android**, cumpliendo estrictamente con:
- **No rotura de la consola PC de escritorio**: La adaptación móvil es puramente aditiva y se activa condicionalmente al detectar el entorno Android o forzarse explícitamente vía flag/variable de entorno.
- **Python como lenguaje central**: Se utiliza la toolchain `buildozer` + `python-for-android` (p4a) sobre SDL2 y Pygame-CE.
- **Soporte de los 9 juegos internos**: Los 9 títulos in-process (`davinci`, `metalslug`, `mario`, `zelda`, `pacman`, `space_invaders`, `asteroids`, `tetris`, `doom`) son 100% compatibles sin depender de subprocesos.

---

## 2. Componentes Implementados

### 2.1 Mando Virtual Multitáctil (`mobile/touch_controls.py`)
- Clase: `VirtualTouchGamepad`
- **Mapeo SDL2 nativo**: Captura eventos `FINGERDOWN`, `FINGERMOTION` y `FINGERUP` con coordenadas normalizadas `[0.0, 1.0]`. Fallback para ratón/simulador de escritorio.
- **D-Pad multidireccional**: Zona muerta central (deadzone) y 8 direcciones (arriba, abajo, izquierda, derecha y diagonales).
- **Layouts dinámicos intercambiables**:
  - `arcade`: 6 botones (golpes y patadas para títulos como *Da Vinci Fighters*).
  - `standard`: 4 botones diamantados (A, B, X, Y).
  - `simple`: 2 botones de acción rápida.
- **Auto-ocultación**: Si se conecta un gamepad físico Bluetooth o USB-OTG (`JOYDEVICEADDED`), el overlay táctil se oculta automáticamente para dejar la pantalla despejada. Al desconectarse (`JOYDEVICEREMOVED`), se restaura.
- **Render semitransparente**: Feedback visual luminoso cyan al presionar botones.

### 2.2 Adaptador de Ciclo de Vida Móvil (`mobile/mobile_adapter.py`)
- Clase: `MobileAdapter`
- **Detección de plataforma**: Detecta variables `ANDROID_ARGUMENT`, `ANDROID_ENTRYPOINT` y `sys.platform == 'android'`.
- **Ciclo de vida SDL2**: Manejo de eventos `APP_WILLENTERBACKGROUND` y `APP_DIDENTERFOREGROUND`:
  - Al pasar a segundo plano: silencia/pausa el mezclador de audio (`pygame.mixer.pause()`) y notifica al bucle de juego para congelar estados.
  - Al regresar al primer plano: reanuda el audio (`pygame.mixer.unpause()`).
- **Botón físico Volver (`K_AC_BACK`)**: Intercepta la tecla de retorno de Android para pausar el juego o volver al menú principal en lugar de matar el proceso abruptamente.
- **Safe Area Insets**: Aplica márgenes de seguridad para muescas de cámara (camera notches) y barras de navegación en pantallas ultrapanorámicas (18:9, 20:9).

### 2.3 Especificación de Empaquetado Buildozer (`buildozer.spec`)
- Identificador: `package.name = ccisystem`, `package.domain = org.ccisystem.arcade`
- Título: `C.C.I. SYSTEM`
- Versión: `2.1.0`
- Requisitos: `python3,pygame-ce,pillow,numpy,pymunk`
- Orientación: `sensorLandscape` (forzado apaisado con rotación automática)
- Pantalla completa: `fullscreen = 1`
- Permisos Android:
  - `INTERNET`: Multijugador en tiempo real y llamadas de voz WebRTC.
  - `RECORD_AUDIO`: Chat de voz P2P.
  - `MODIFY_AUDIO_SETTINGS`: Enrutamiento de altavoz/auriculares.
  - `VIBRATE`: Respuesta háptica táctil en pulsaciones.
- Arquitecturas: `arm64-v8a`, `armeabi-v7a`
- API target: Android API 34 (Android 14) con min API 24 (Android 7.0 Nougat).

### 2.4 Script de Validación y Compilación (`mobile/build_apk.py`)
- Valida la integridad del archivo `buildozer.spec`.
- Comprueba presencia de Java JDK, Android SDK, Android NDK y Buildozer.
- Modo pre-flight check `--dry-run` para CI/CD sin necesidad de descargar gigabytes de NDK.
- Soporta `--build debug` y `--build release`.

---

## 3. Pruebas Unitarias y Regresión (`test_phase7_evolution.py`)
- 8 pruebas unitarias específicas de la Fase 7:
  1. `test_virtual_gamepad_init_and_scaling`: Geometría y layout arcade/standard.
  2. `test_virtual_gamepad_dpad_touch`: D-pad y deadzone.
  3. `test_virtual_gamepad_button_touch`: Botones de acción individuales.
  4. `test_virtual_gamepad_multitouch_concurrency`: Multitouch concurrente (2 dedos simultáneos).
  5. `test_virtual_gamepad_hardware_gamepad_toggle`: Conexión/desconexión de gamepad físico.
  6. `test_mobile_adapter_lifecycle`: Pausa y reanudación de ciclo de vida.
  7. `test_mobile_adapter_back_button`: Manejo de botón Atrás de Android.
  8. `test_buildozer_spec_and_preflight`: Validación de `buildozer.spec` y chequeos previos.
- **Resultado acumulado**: 100% aprobadas sin regresiones en fases 1-6.
