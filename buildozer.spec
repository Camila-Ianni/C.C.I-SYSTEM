[app]

# (str) Title of your application
title = C.C.I. SYSTEM

# (str) Package name
package.name = ccisystem

# (str) Package domain (needed for android/ios packaging)
package.domain = org.ccisystem.arcade

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,jpeg,ttf,otf,wav,ogg,mp3,json,sqlite3,db,md,txt

# (list) List of inclusions using pattern matching
source.include_patterns = assets/*,data/*,backend/*,mobile/*,recorder/*

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_dirs = tests,documentacion,.venv,venv,.git,.github,.gemini,screenshots,temp_test*

# (str) Application versioning (method 1)
version = 2.1.0

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3,pygame-ce,pillow,numpy,pymunk

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = sensorLandscape

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET,RECORD_AUDIO,MODIFY_AUDIO_SETTINGS,VIBRATE

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APP will support.
android.minapi = 24

# (str) Android NDK version to use
# android.ndk = 25b

# (int) Android NDK API to use. This is the minimum API your app will support, it should usually match android.minapi.
android.ndk_api = 24

# (list) The Android architectures to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Presplash background color (for android toolchain)
android.presplash_color = #0A0D14

# (str) Icon of the application
# icon.filename = %(source.dir)s/assets/icon.png

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
