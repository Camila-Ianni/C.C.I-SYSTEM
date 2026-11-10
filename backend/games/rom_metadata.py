"""backend/games/rom_metadata.py - Extractor de metadatos internos e integridad de ROMs.
Permite identificar títulos genuinos desde cabeceras internas y verificar la integridad de los archivos.
100% Python estándar sin dependencias externas.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import re
import zlib
from pathlib import Path


class ROMMetadataExtractor:
    """Extractor seguro y no destructivo de metadatos de cabeceras de videojuegos retro."""

    @staticmethod
    def clean_display_title(stem: str) -> str:
        """Limpia tags No-Intro/GoodNES/Redump comunes de los nombres de archivo."""
        name = stem
        # Remover tags entre paréntesis como (USA), (Europe), (U), (J), (V1.1)
        name = re.sub(r"\s*\([^)]*\)", "", name)
        # Remover tags entre corchetes como [!], [SLES-02529], [b1]
        name = re.sub(r"\s*\[[^\]]*\]", "", name)
        # Remover prefijos numéricos de lanzamientos NDS/GBA como "0168 - Mario Kart DS"
        if " - " in name:
            parts = name.split(" - ", 1)
            if parts[0].strip().isdigit():
                name = parts[1].strip()
        return name.strip()

    @staticmethod
    def compute_file_fingerprint(path: Path) -> str:
        """Calcula un fingerprint rápido basado en tamaño, mtime y CRC32 del primer bloque."""
        try:
            st = path.stat()
            size = st.st_size
            mtime = int(st.st_mtime)
            # Leer primeros 8KB para CRC rápido
            with open(path, "rb") as fp:
                head = fp.read(8192)
            crc = zlib.crc32(head) & 0xFFFFFFFF
            return f"{size}_{mtime}_{crc:08x}"
        except Exception:
            return ""

    @staticmethod
    def extract_snes_header(path: Path) -> dict:
        """Lee el título interno de la cabecera SNES (LoROM en 0x7FC0 o HiROM en 0xFFC0)."""
        res = {"internal_title": "", "country": "", "rom_type": "SNES"}
        try:
            with open(path, "rb") as fp:
                data = fp.read(0x10000)
            offset = 512 if len(data) % 1024 == 512 else 0
            # Probar LoROM
            lo_title = data[offset + 0x7FC0 : offset + 0x7FD5].decode("latin-1", errors="ignore").strip()
            # Probar HiROM
            hi_title = data[offset + 0xFFC0 : offset + 0xFFD5].decode("latin-1", errors="ignore").strip()

            def is_readable(s: str) -> bool:
                return bool(s and sum(1 for c in s if c.isalnum() or c in " -_") >= 3)

            if is_readable(lo_title):
                res["internal_title"] = lo_title
            elif is_readable(hi_title):
                res["internal_title"] = hi_title
        except Exception:
            pass
        return res

    @staticmethod
    def extract_n64_header(path: Path) -> dict:
        """Lee el título interno de la cabecera de Nintendo 64 (offset 0x20 a 0x34)."""
        res = {"internal_title": "", "rom_type": "N64"}
        try:
            with open(path, "rb") as fp:
                fp.seek(0x20)
                raw = fp.read(20)
            title = raw.decode("latin-1", errors="ignore").strip()
            # Limpiar caracteres nulos
            title = title.replace("\x00", "").strip()
            if title:
                res["internal_title"] = title
        except Exception:
            pass
        return res

    @staticmethod
    def extract_nds_header(path: Path) -> dict:
        """Lee el título y GameCode interno de Nintendo DS (offset 0x00 a 0x10)."""
        res = {"internal_title": "", "game_code": "", "rom_type": "NDS"}
        try:
            with open(path, "rb") as fp:
                head = fp.read(16)
            title = head[:12].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            code = head[12:16].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            res["internal_title"] = title
            res["game_code"] = code
        except Exception:
            pass
        return res

    @staticmethod
    def extract_gba_header(path: Path) -> dict:
        """Lee el título y GameCode interno de Game Boy Advance (offset 0xA0 a 0xAC)."""
        res = {"internal_title": "", "game_code": "", "rom_type": "GBA"}
        try:
            with open(path, "rb") as fp:
                fp.seek(0xA0)
                head = fp.read(16)
            title = head[:12].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            code = head[12:16].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            res["internal_title"] = title
            res["game_code"] = code
        except Exception:
            pass
        return res

    @staticmethod
    def verify_cue_bin_integrity(cue_path: Path) -> tuple[bool, str]:
        """Verifica que un archivo .cue de PlayStation 1 apunte a archivos .bin existentes en disco."""
        if not cue_path.exists():
            return False, f"Archivo .cue no encontrado: {cue_path.name}"
        try:
            lines = cue_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            referenced_bins = []
            for line in lines:
                line = line.strip()
                if line.startswith("FILE"):
                    # Extraer el nombre de archivo entre comillas
                    m = re.search(r'FILE\s+"([^"]+)"', line)
                    if m:
                        referenced_bins.append(m.group(1))
            if not referenced_bins:
                # Si no tiene comillas, buscar tokens
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[0] == "FILE":
                        referenced_bins.append(parts[1])

            missing = []
            for bin_name in referenced_bins:
                target = cue_path.parent / bin_name
                if not target.exists():
                    missing.append(bin_name)

            if missing:
                return False, f"Faltan archivos binarios: {', '.join(missing)}"
            return True, "Integridad CUE/BIN verificada exitosamente"
        except Exception as err:
            return False, f"Error leyendo CUE: {err}"
