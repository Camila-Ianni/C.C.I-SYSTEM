# C.C.I. SYSTEM — Fase 8: Adaptación iOS (IPA & Xcode Blueprint)

## 1. Resumen Ejecutivo
La **Fase 8** implementa la adaptación para el ecosistema **Apple iOS** (iPhone e iPad) de **C.C.I. SYSTEM**, completando la estrategia multiplataforma móvil sin alterar el funcionamiento en escritorio PC:
- **Áreas Seguras Dinámicas**: Compensación exacta de píxeles para Notch (iPhone X a 14) y Dynamic Island (iPhone 14 Pro a 16), reubicando el overlay de controles táctiles fuera de zonas ciegas.
- **Permisos y Privilegios Apple**: Declaración formal de `NSMicrophoneUsageDescription` para llamadas de voz WebRTC en `ios/Info.plist` y `ios/Entitlements.plist`.
- **Soporte ProMotion y Audio**: Activación de 60/120 FPS (`CADisableMinimumFrameDurationOnPhone`) y modo audio en segundo plano (`UIBackgroundModes = [audio]`).
- **Retroalimentación Háptica**: Emulación e integración de `UIImpactFeedbackGenerator` (`light`, `medium`, `heavy`, `selection`).

---

## 2. Componentes Implementados

### 2.1 Adaptador Específico de iOS (`mobile/ios_adapter.py`)
- Clase: `IOSAdapter`
- **Safe Area Insets**:
  - `notch`: (47px izquierda, 0 arriba, 47px derecha, 21px abajo para barra de inicio).
  - `dynamic_island`: (59px izquierda, 0 arriba, 59px derecha, 21px abajo).
  - `ipad`: (0 izquierda, 24px arriba, 0 derecha, 20px abajo).
  - `classic`: (0, 0, 0, 0).
- **Alineación del Virtual Gamepad**: Los botones de acción y el D-pad son desplazados automáticamente en función de los insets calculados para no quedar cubiertos por los recortes de pantalla.
- **Ciclo de vida iOS**: Captura `APP_WILLENTERBACKGROUND` y `APP_DIDENTERFOREGROUND`, pausando el mixer de audio y congelando el bucle de render.
- **Háptica**: Interfaz `trigger_haptic(style)` preparada para generadores de impacto de iOS.

### 2.2 Manifiesto de Configuración iOS (`ios/Info.plist`)
- Identificador de Bundle: `org.ccisystem.arcade`
- Nombre visible: `C.C.I. SYSTEM`
- Orientaciones permitidas: `UIInterfaceOrientationLandscapeLeft`, `UIInterfaceOrientationLandscapeRight`.
- Pantalla completa obligatoria: `UIRequiresFullScreen = true`.
- Descripción del micrófono:
  > *"C.C.I. SYSTEM requiere acceso al micrófono para llamadas de voz WebRTC y chat durante partidas multijugador."*
- ProMotion Display: `CADisableMinimumFrameDurationOnPhone = true`.

### 2.3 Privilegios de Seguridad (`ios/Entitlements.plist`)
- `com.apple.security.network.client`: Conexión cliente a servidores WebSocket / ICE.
- `com.apple.security.device.audio-input`: Acceso a captura de audio de micrófono.
- `get-task-allow`: Habilitado para compilaciones de depuración y testing.

### 2.4 Validador de Toolchain Apple (`ios/build_ios.py`)
- Valida la sintaxis XML de `Info.plist` y la presencia obligatoria de permisos y orientaciones apaisadas.
- Verifica herramientas de compilación de macOS: `xcode-select`, `xcrun`, `codesign` y generadores `kivy-ios` / `briefcase`.
- Ejecutable mediante `--dry-run`.

---

## 3. Pruebas Unitarias y Regresión (`test_phase8_evolution.py`)
- 7 pruebas unitarias específicas de iOS:
  1. `test_ios_safe_area_presets`: Verificación de insets de notch, isla e iPad.
  2. `test_touch_gamepad_offset_under_safe_area`: Desplazamiento dinámico de botones.
  3. `test_ios_haptic_feedback`: Estilos válidos e inválidos de háptica.
  4. `test_ios_lifecycle_event_handling`: Suspensión y reanudación de la app.
  5. `test_info_plist_validity`: Integridad de `Info.plist` y descripción de micrófono.
  6. `test_entitlements_plist_validity`: Privilegios de red y entrada de audio.
  7. `test_ios_preflight_check`: Chequeo previo de toolchain Apple.
- **Resultado acumulado**: 61/61 tests aprobados sin fallos.
