"""
backend/communities/sound_validator.py
Validador técnico de archivos MP3 para Sound Deck (Soundboard).
Requisitos:
- Formato: MP3 (audio/mpeg con magic bytes ID3 o MPEG sync words).
- Tamaño máximo: 5 MB (5 * 1024 * 1024 bytes).
- Duración máxima: 15.0 segundos.
- Verificación SHA-256 de integridad.
"""

import os
import hashlib
from typing import Tuple, Optional

MAX_SOUND_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SOUND_DURATION_SECONDS = 15.0       # 15 s
MIN_SOUND_SIZE_BYTES = 32               # Mínimo para cabecera básica


class SoundValidationError(Exception):
    def __init__(self, message: str, code: str = "INVALID_AUDIO"):
        super().__init__(message)
        self.message = message
        self.code = code


def validate_mp3_payload(
    file_bytes: bytes,
    declared_duration: Optional[float] = None
) -> Tuple[bool, float, str]:
    """
    Valida tamaño, magic bytes y duración de un archivo MP3.
    Retorna (es_valido, duracion_calculada_o_declarada, sha256_checksum).
    Lanza SoundValidationError si no cumple la especificación.
    """
    if not file_bytes:
        raise SoundValidationError("El archivo está vacío", "EMPTY_FILE")

    size = len(file_bytes)
    if size < MIN_SOUND_SIZE_BYTES:
        raise SoundValidationError(
            f"El archivo es demasiado pequeño ({size} bytes)",
            "FILE_TOO_SMALL"
        )

    if size > MAX_SOUND_SIZE_BYTES:
        raise SoundValidationError(
            f"El archivo excede el tamaño máximo permitido de 5 MB ({size} bytes)",
            "FILE_TOO_LARGE"
        )

    # 1. Verificación de Magic Bytes (ID3 o MPEG Frame Sync)
    is_mp3 = False

    # Check ID3v2 tag
    if file_bytes.startswith(b"ID3"):
        is_mp3 = True
    else:
        # Check MPEG audio frame sync word (0xFF seguido de bits 111 y layer bits 01)
        # Buscar en los primeros 4096 bytes
        limit = min(4096, size - 1)
        for i in range(limit):
            if file_bytes[i] == 0xFF:
                b2 = file_bytes[i + 1]
                # Sync word bits: 111 (0xE0)
                if (b2 & 0xE0) == 0xE0:
                    # Layer bits (bits 1,2 de b2): 01 = Layer III (MP3)
                    layer = (b2 >> 1) & 0x03
                    if layer == 1:
                        is_mp3 = True
                        break

    if not is_mp3:
        raise SoundValidationError(
            "El archivo no es un MP3 válido (magic bytes ausentes o corruptos)",
            "INVALID_FORMAT"
        )

    # 2. Verificación de Duración
    # Si se suministró duración declarada, validar
    duration = declared_duration if declared_duration is not None else 0.0

    # Estimación de respaldo si duration no fue pasada:
    # A un bitrate típico de 128 kbps (16 KB/s), size / 16000
    if duration <= 0.0:
        # Si el archivo tiene un tamaño razonable, estimar conservadoramente
        est_duration = round(size / 16000.0, 2)
        duration = min(est_duration, MAX_SOUND_DURATION_SECONDS)
        # Si sobrepasaría holgadamente 15s aun a 320kbps (40 KB/s -> 600 KB):
        if size > 15 * 40 * 1024:
            # Asumir duración excesiva si excede ~600KB salvo que se declare lo contrario
            if declared_duration is None:
                duration = round(size / 16000.0, 2)

    if duration > MAX_SOUND_DURATION_SECONDS:
        raise SoundValidationError(
            f"La duración ({duration:.1f}s) excede el máximo permitido de 15.0 segundos",
            "DURATION_EXCEEDED"
        )

    # 3. Cálculo de Checksum SHA-256
    checksum = hashlib.sha256(file_bytes).hexdigest()

    return True, duration, checksum


def save_sound_file(storage_dir: str, sound_id: str, file_bytes: bytes) -> str:
    """
    Guarda los bytes del sonido en el directorio de almacenamiento local
    y retorna la clave de almacenamiento relativa.
    """
    os.makedirs(storage_dir, exist_ok=True)
    filename = f"{sound_id}.mp3"
    full_path = os.path.join(storage_dir, filename)
    with open(full_path, "wb") as f:
        f.write(file_bytes)
    return f"sounds/{filename}"
