# Manual de Instalación, Configuración y Despliegue
## Proyecto: C.C.I. SYSTEM (Virtual Arcade Console Platform & Retro Emulator)
**Documento:** Manual Técnico de Instalación, Despliegue y Administración de Entorno  
**Versión:** 3.0.0 (Lanzamiento Multiplataforma & Web Cloud)  
**URL Oficial en Producción:** [https://c-c-i-system.onrender.com](https://c-c-i-system.onrender.com)  

---

## 1. Métodos de Instalación y Despliegue

El sistema ofrece tres canales de instalación y uso según el perfil del usuario:

```
                                ┌─────────────────────────────────────────┐
                                │        CANALES DE C.C.I. SYSTEM         │
                                └────────────────────┬────────────────────┘
                                                     │
             ┌───────────────────────────────────────┼───────────────────────────────────────┐
             ▼                                       ▼                                       ▼
  [ MODO USUARIO FINAL ]                  [ MODO DESARROLLADOR ]                  [ MODO SERVIDOR WEB ]
  - Web o GitHub Releases                 - Terminal y Git                        - Flask & Render.com
  - DMG (Mac) / EXE (Win)                 - requirements-dev.txt                  - c-c-i-system.onrender.com
  - 1-clic con asistente                  - python main.py                        - python run_web.py
```

---

## 2. Método 1: Instalación de Usuario Final (Sin Terminal)

Para usuarios finales que desean jugar de inmediato sin configurar entornos de programación:

### 2.1. macOS (`.dmg`)
1. Descarga el paquete oficial desde la web o GitHub Releases:
   * **Enlace Oficial:** `https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_macOS.dmg`
2. Abre la imagen de disco descargada `CCI_System_macOS.dmg`.
3. Haz **Clic derecho** (o `Control + Clic`) en **`C.C.I. SYSTEM`** y selecciona **«Abrir»** (requerido únicamente en el primer inicio por el sistema Gatekeeper de macOS al tratarse de software independiente).
4. El asistente interactivo te preguntará dónde ubicar la consola (por defecto en tu **Escritorio**).
5. Se creará el acceso directo y la consola se iniciará de forma automática con 0 perfiles de fábrica, lista para crear tu jugador.

### 2.2. Windows (`.exe`)
1. Descarga el ejecutable desde la web o GitHub Releases:
   * **Enlace Oficial:** `https://github.com/Camila-Ianni/C.C.I-SYSTEM/releases/download/v1.0.0/CCI_System_Windows_Installer.exe`
2. Haz doble clic en `CCI_System_Windows_Installer.exe`.
3. Sigue el instalador gráfico que extraerá los 19 juegos y generará el acceso directo en tu Escritorio.
4. La consola se abre directamente sin comandos de PowerShell ni CMD.

---

## 3. Método 2: Despliegue de la Web Oficial (Flask Cloud en Render.com)

La landing page oficial opera 100% en Python mediante Flask y se encuentra desplegada en:
**`https://c-c-i-system.onrender.com`**

### 3.1. Arquitectura de Despliegue en la Nube
* **Repositorio de Origen:** `https://github.com/Camila-Ianni/C.C.I-SYSTEM` (rama `main`).
* **CI/CD Automático:** Cada `git push origin main` desencadena una compilación y despliegue continuo en Render.
* **Separación de Cargas:** El repositorio almacena el código fuente, la landing page y las imágenes de `fotos web` (~35 MB), mientras que los instaladores pesados (734 MB DMG y 628 MB EXE) residen en **GitHub Releases** y son redirigidos de forma transparente por [web/app.py](../web/app.py) para descarga a máxima velocidad.

### 3.2. Parámetros de Despliegue en Render
* **Runtime:** Python 3 (3.14.8).
* **Build Command:** `pip install -r requirements.txt` (instala únicamente dependencias web ligeras: Flask, Werkzeug).
* **Start Command:** `python run_web.py`.
* **Variables de Entorno (Opcionales):**
  * `MAC_DOWNLOAD_URL`: URL oficial de descarga del DMG en GitHub Releases.
  * `WIN_DOWNLOAD_URL`: URL oficial de descarga del EXE en GitHub Releases.

---

## 4. Método 3: Instalación Local para Desarrolladores

Para depuración, adición de nuevos juegos o modificaciones de código:

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/Camila-Ianni/C.C.I-SYSTEM.git
cd C.C.I-SYSTEM
```

### Paso 2: Crear y Activar el Entorno Virtual (`.venv`)
```bash
# macOS / Linux:
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Paso 3: Instalar Dependencias de Desarrollo
```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

#### Dependencias en `requirements-dev.txt`:
* `pygame-ce>=2.5.8`: Motor gráfico 2D, bucle a 60 FPS, entrada SDL2 y mezclador de audio.
* `opencv-python>=4.8.0`: Decodificación de video de intro y animaciones.
* `numpy>=1.24.0`: Procesamiento numérico y síntesis sonora.
* `pymunk>=6.5.0`: Motor de físicas de cuerpos rígidos para proyectiles.
* `flask>=3.0.0`: Servidor web para la landing page oficial.

### Paso 4: Comprobación de Diagnóstico
```bash
python -c "
import pygame, cv2, numpy, pymunk, flask
print('--- C.C.I. SYSTEM DIAGNÓSTICO ---')
print('Pygame-CE :', pygame.__version__)
print('OpenCV    :', cv2.__version__)
print('Pymunk    :', pymunk.__version__)
print('Flask     :', flask.__version__)
print('Joysticks :', pygame.joystick.get_count())
print('ESTADO    : TODO CORRECTO')
"
```

### Paso 5: Ejecución
```bash
# Para ejecutar la consola emuladora:
python main.py

# Para ejecutar el servidor web localmente:
python run_web.py
```

---

## 5. Matriz de Resolución de Problemas

### 5.1. Aviso de macOS: «Apple no pudo verificar que C.C.I. SYSTEM no contenga software malicioso»
* **Diagnóstico:** Gatekeeper de macOS coloca el atributo `com.apple.quarantine` a descargas web de aplicaciones no notarizadas.
* **Solución:** Haz **Clic derecho** sobre `C.C.I. SYSTEM.app` -> selecciona **«Abrir»** -> pulsa **«Abrir»** en el cuadro de diálogo. Solo se realiza una única vez; al instalarse en el Escritorio la aplicación limpia sus atributos automáticamente.

### 5.2. En macOS: Mensajes de consola `objc[...] Class SDLApplication is implemented in both...`
* **Diagnóstico:** Duplicación inofensiva de dylibs de SDL2 entre OpenCV y Pygame.
* **Solución:** Ya se encuentra neutralizado en [main.py](../main.py) y [states.py](../states.py) mediante redirección controlada de descriptores de error durante la importación.

### 5.3. El mando USB / Bluetooth no responde
* **Diagnóstico:** El gamepad entró en suspensión por inactividad.
* **Solución:** Presiona el botón central (PlayStation / Guía Xbox). La clase `JoystickManager` detecta la reconexión en caliente y lo reasigna instantáneamente con retroalimentación háptica.
