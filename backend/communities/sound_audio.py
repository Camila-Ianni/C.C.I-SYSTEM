"""
backend/communities/sound_audio.py - Decodificación y síntesis PCM 48kHz para Soundboard RTC.

Convierte archivos de audio reales (MP3/WAV) y presets integrados a PCM 16-bit mono a 48 kHz
para mezclarlos directamente dentro del track saliente WebRTC en DesktopVoiceEngine.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import wave
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    import numpy as np


def _require_numpy():
    import numpy as np

    return np

SOUNDBOARD_PRESETS: List[Dict[str, Any]] = [
    {
        "id": "preset_gg",
        "title": "GG",
        "icon": "🟢",
        "description": "Acorde retro C-E-G",
        "duration_seconds": 0.42,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
    {
        "id": "preset_airhorn",
        "title": "AIRHORN",
        "icon": "📢",
        "description": "Bocina MLG armónica",
        "duration_seconds": 0.45,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
    {
        "id": "preset_ko",
        "title": "K.O.",
        "icon": "💥",
        "description": "Impacto descendente",
        "duration_seconds": 0.50,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
    {
        "id": "preset_victory",
        "title": "VICTORY",
        "icon": "🏆",
        "description": "Fanfarria estelar",
        "duration_seconds": 0.52,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
    {
        "id": "preset_levelup",
        "title": "LEVEL UP",
        "icon": "⚡",
        "description": "Arpegio subida de nivel",
        "duration_seconds": 0.42,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
    {
        "id": "preset_buzzer",
        "title": "BUZZER",
        "icon": "🛑",
        "description": "Alerta doble tono",
        "duration_seconds": 0.36,
        "volume_scale": 0.75,
        "cooldown_seconds": 3,
        "is_preset": True,
    },
]

_PRESET_PATTERNS: Dict[str, List[tuple[List[float], float]]] = {
    "preset_gg": [([523.25], 0.09), ([659.25], 0.09), ([783.99, 1046.50], 0.24)],
    "preset_airhorn": [([587.33, 880.0], 0.07), ([587.33, 880.0], 0.07), ([587.33, 880.0], 0.07), ([880.0, 1174.66], 0.24)],
    "preset_ko": [([440.0], 0.09), ([329.63], 0.09), ([220.0], 0.11), ([110.0, 165.0], 0.21)],
    "preset_victory": [([440.0], 0.09), ([554.37], 0.09), ([659.25], 0.09), ([880.0, 1108.73], 0.25)],
    "preset_levelup": [([329.63], 0.08), ([392.0], 0.08), ([523.25], 0.08), ([659.25], 0.18)],
    "preset_buzzer": [([160.0, 215.0], 0.15), ([130.0, 185.0], 0.21)],
}


def get_soundboard_preset(preset_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Resuelve un preset integrado por id o título normalizado."""
    raw = str(preset_id_or_name or "").strip().lower()
    if not raw:
        return None
    norm = raw.replace(" ", "").replace(".", "")
    for item in SOUNDBOARD_PRESETS:
        iid = str(item["id"]).lower()
        ititle = str(item["title"]).lower().replace(" ", "").replace(".", "")
        if raw == iid or norm == ititle or raw == f"snd_{ititle}":
            return dict(item)
    return None


def synthesize_preset_pcm(
    preset_id_or_name: str,
    volume_scale: float = 0.75,
    sample_rate: int = 48000,
) -> "np.ndarray":
    """Sintetiza un efecto de soundboard en PCM int16 mono a sample_rate Hz."""
    np = _require_numpy()
    preset = get_soundboard_preset(preset_id_or_name)
    key = str(preset["id"]) if preset else "preset_airhorn"
    pattern = _PRESET_PATTERNS.get(key, _PRESET_PATTERNS["preset_airhorn"])
    vol = max(0.0, min(2.0, float(volume_scale)))

    segments: List["np.ndarray"] = []
    sr = max(8000, int(sample_rate))
    for freqs, dur_s in pattern:
        n = max(1, int(round(sr * float(dur_s))))
        t = np.arange(n, dtype=np.float64) / float(sr)
        wave_acc = np.zeros(n, dtype=np.float64)
        for idx, freq in enumerate(freqs):
            weight = 1.0 if idx == 0 else 0.45
            wave_acc += weight * np.sin(2.0 * np.pi * float(freq) * t)
        peak = max(1.0, float(np.max(np.abs(wave_acc))))
        wave_acc /= peak
        # Envolvente suave de ataque y caída para evitar clics
        fade_len = min(n // 4, max(1, int(sr * 0.008)))
        env = np.linspace(1.0, 0.55, n, dtype=np.float64)
        env[:fade_len] *= np.linspace(0.0, 1.0, fade_len, dtype=np.float64)
        env[-fade_len:] *= np.linspace(1.0, 0.0, fade_len, dtype=np.float64)
        seg = np.clip(wave_acc * env * 12000.0 * vol, -32768.0, 32767.0).astype(np.int16)
        segments.append(seg)

    return np.concatenate(segments) if segments else np.zeros(0, dtype=np.int16)


def resample_pcm_mono(
    pcm: "np.ndarray",
    src_rate: int,
    dst_rate: int = 48000,
) -> "np.ndarray":
    """Normaliza cualquier arreglo PCM a mono int16 remuestreado a dst_rate."""
    np = _require_numpy()
    arr = np.asarray(pcm)
    if arr.size == 0:
        return np.zeros(0, dtype=np.int16)
    if arr.ndim > 1:
        # Promedio de canales manteniendo escala int16
        mono = np.mean(arr.astype(np.float64), axis=1)
    else:
        mono = arr.astype(np.float64)

    if int(src_rate) > 0 and int(src_rate) != int(dst_rate) and mono.size > 1:
        new_len = max(1, int(round(mono.size * (float(dst_rate) / float(src_rate)))))
        x_old = np.linspace(0.0, 1.0, mono.size, endpoint=False)
        x_new = np.linspace(0.0, 1.0, new_len, endpoint=False)
        mono = np.interp(x_new, x_old, mono)

    return np.clip(mono, -32768.0, 32767.0).astype(np.int16)


def _decode_wav_bytes(wav_bytes: bytes, target_sample_rate: int) -> "np.ndarray":
    np = _require_numpy()
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        nch = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        src_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if sampwidth != 2:
        raise ValueError(f"Ancho de muestra WAV no soportado: {sampwidth * 8} bits")
    arr = np.frombuffer(raw, dtype=np.int16)
    if nch > 1:
        arr = arr.reshape(-1, nch)
    return resample_pcm_mono(arr, src_rate=src_rate, dst_rate=target_sample_rate)


def _decode_via_afconvert(audio_bytes: bytes, target_sample_rate: int) -> Optional["np.ndarray"]:
    afconv = shutil.which("afconvert")
    if not afconv:
        return None
    with tempfile.TemporaryDirectory(prefix="cci_sb_dec_") as td:
        in_path = os.path.join(td, "input.mp3")
        out_path = os.path.join(td, "output.wav")
        with open(in_path, "wb") as f:
            f.write(audio_bytes)
        proc = subprocess.run(
            [
                afconv,
                "-f",
                "WAVE",
                "-d",
                f"LEI16@{int(target_sample_rate)}",
                "-c",
                "1",
                in_path,
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        if proc.returncode != 0 or not os.path.isfile(out_path):
            return None
        with open(out_path, "rb") as wf:
            return _decode_wav_bytes(wf.read(), target_sample_rate=target_sample_rate)


def _decode_via_pygame_mixer(audio_bytes: bytes, target_sample_rate: int) -> Optional["np.ndarray"]:
    prev_driver = os.environ.get("SDL_AUDIODRIVER")
    initialized_here = False
    try:
        if "SDL_AUDIODRIVER" not in os.environ:
            os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame

        init_info = pygame.mixer.get_init()
        if init_info is None:
            pygame.mixer.init(frequency=int(target_sample_rate), size=-16, channels=1, buffer=1024)
            initialized_here = True
            src_rate = int(target_sample_rate)
        else:
            src_rate = int(init_info[0])

        snd = pygame.mixer.Sound(file=io.BytesIO(audio_bytes))
        arr = pygame.sndarray.array(snd)
        return resample_pcm_mono(arr, src_rate=src_rate, dst_rate=target_sample_rate)
    except Exception:
        return None
    finally:
        if initialized_here:
            try:
                import pygame

                pygame.mixer.quit()
            except Exception:
                pass
        if prev_driver is None and "SDL_AUDIODRIVER" in os.environ and initialized_here:
            os.environ.pop("SDL_AUDIODRIVER", None)


def decode_audio_bytes_to_pcm(
    audio_bytes: bytes,
    volume_scale: float = 1.0,
    target_sample_rate: int = 48000,
) -> "np.ndarray":
    """Decodifica audio MP3 o WAV en PCM int16 mono listo para LiveKit RTC."""
    np = _require_numpy()
    if not audio_bytes:
        raise ValueError("El payload de audio está vacío")

    pcm: Optional["np.ndarray"] = None
    if len(audio_bytes) >= 12 and audio_bytes[:4] == b"RIFF" and audio_bytes[8:12] == b"WAVE":
        pcm = _decode_wav_bytes(audio_bytes, target_sample_rate=target_sample_rate)
    else:
        pcm = _decode_via_afconvert(audio_bytes, target_sample_rate=target_sample_rate)
        if pcm is None or pcm.size == 0:
            pcm = _decode_via_pygame_mixer(audio_bytes, target_sample_rate=target_sample_rate)

    if pcm is None or pcm.size == 0:
        raise ValueError("No se pudo decodificar el archivo de audio a PCM 48kHz")

    vol = max(0.0, min(2.0, float(volume_scale)))
    if abs(vol - 1.0) > 1e-4:
        scaled = np.clip(pcm.astype(np.float64) * vol, -32768.0, 32767.0).astype(np.int16)
        return scaled
    return pcm.astype(np.int16, copy=False)
