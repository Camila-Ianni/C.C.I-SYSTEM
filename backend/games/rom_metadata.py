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
        # Remover tags entre corchetes como [!], [SLES-02529], [b1]
        name = re.sub(r"\s*\[[^\]]*\]", "", name)
        # Remover tags entre paréntesis como (USA), (Europe), (U), (J), (V1.1)
        name = re.sub(r"\s*\([^)]*\)", "", name)
        # Remover prefijos numéricos de lanzamientos NDS/GBA como "0168 - Mario Kart DS"
        if " - " in name:
            parts = name.split(" - ", 1)
            if parts[0].strip().isdigit():
                name = parts[1].strip()
        return name.strip()

    @staticmethod
    def extract_region_and_revision(stem: str) -> tuple[str, str]:
        """Extrae región y revisión a partir de los tags estándar del nombre de archivo."""
        region = "Unknown"
        revision = "1.0"

        # Detección de Región
        reg_map = {
            "USA": "USA", "US": "USA", "U": "USA",
            "Europe": "Europe", "EUR": "Europe", "E": "Europe",
            "Japan": "Japan", "JPN": "Japan", "J": "Japan",
            "World": "World", "W": "World",
        }
        for match in re.findall(r"\(([^)]+)\)", stem):
            tokens = [t.strip() for t in match.replace("/", ",").split(",")]
            for tok in tokens:
                if tok in reg_map:
                    region = reg_map[tok]
                    break
            if region != "Unknown":
                break

        # Detección de Revisión / Versión
        rev_match = re.search(r"\(V?(\d+\.\d+)\)", stem, re.IGNORECASE)
        if rev_match:
            revision = rev_match.group(1)
        elif "Rev " in stem:
            rm = re.search(r"Rev\s*(\w+)", stem, re.IGNORECASE)
            if rm:
                revision = rm.group(1)

        return region, revision

    @staticmethod
    def compute_file_fingerprint(path: Path) -> str:
        """Calcula un fingerprint rápido basado en tamaño, mtime y CRC32 del primer bloque."""
        try:
            st = path.stat()
            size = st.st_size
            mtime = int(st.st_mtime)
            with open(path, "rb") as fp:
                head = fp.read(8192)
            crc = zlib.crc32(head) & 0xFFFFFFFF
            return f"{size}_{mtime}_{crc:08x}"
        except Exception:
            return ""

    @staticmethod
    def extract_snes_header(path: Path) -> dict:
        """Lee el título interno de la cabecera SNES (LoROM en 0x7FC0 o HiROM en 0xFFC0)."""
        res = {"internal_title": "", "rom_type": "SNES", "source": "none"}
        try:
            with open(path, "rb") as fp:
                data = fp.read(0x10000)
            offset = 512 if len(data) % 1024 == 512 else 0

            # LoROM (offset 0x7FC0) y HiROM (offset 0xFFC0)
            lo_title = data[offset + 0x7FC0 : offset + 0x7FD5].decode("latin-1", errors="ignore").strip()
            hi_title = data[offset + 0xFFC0 : offset + 0xFFD5].decode("latin-1", errors="ignore").strip()

            def is_readable(s: str) -> bool:
                cleaned = "".join(c for c in s if c.isalnum() or c in " -_")
                return len(cleaned) >= 4 and not all(c == s[0] for c in s)

            if is_readable(lo_title):
                res["internal_title"] = lo_title.replace("\x00", "").strip()
                res["source"] = "header_lorom"
            elif is_readable(hi_title):
                res["internal_title"] = hi_title.replace("\x00", "").strip()
                res["source"] = "header_hirom"
        except Exception:
            pass
        return res

    @staticmethod
    def extract_n64_header(path: Path) -> dict:
        """Lee el título interno de la cabecera de Nintendo 64 (offset 0x20 a 0x34)."""
        res = {"internal_title": "", "rom_type": "N64", "source": "none"}
        try:
            with open(path, "rb") as fp:
                fp.seek(0x20)
                raw = fp.read(20)
            title = raw.decode("latin-1", errors="ignore").replace("\x00", "").strip()
            if len(title) >= 3 and any(c.isalnum() for c in title):
                res["internal_title"] = title
                res["source"] = "header_n64"
        except Exception:
            pass
        return res

    @staticmethod
    def extract_nds_header(path: Path) -> dict:
        """Lee el título y GameCode interno de Nintendo DS (offset 0x00 a 0x10)."""
        res = {"internal_title": "", "game_code": "", "rom_type": "NDS", "source": "none"}
        try:
            with open(path, "rb") as fp:
                head = fp.read(16)
            title = head[:12].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            code = head[12:16].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            if len(title) >= 3 and any(c.isalnum() for c in title):
                res["internal_title"] = title
                res["game_code"] = code
                res["source"] = "header_nds"
        except Exception:
            pass
        return res

    @staticmethod
    def extract_gba_header(path: Path) -> dict:
        """Lee el título y GameCode interno de Game Boy Advance (offset 0xA0 a 0xAC)."""
        res = {"internal_title": "", "game_code": "", "rom_type": "GBA", "source": "none"}
        try:
            with open(path, "rb") as fp:
                fp.seek(0xA0)
                head = fp.read(16)
            title = head[:12].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            code = head[12:16].decode("latin-1", errors="ignore").replace("\x00", "").strip()
            if len(title) >= 3 and any(c.isalnum() for c in title):
                res["internal_title"] = title
                res["game_code"] = code
                res["source"] = "header_gba"
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
                    m = re.search(r'FILE\s+"([^"]+)"', line)
                    if m:
                        referenced_bins.append(m.group(1))
                    else:
                        parts = line.split()
                        if len(parts) >= 2:
                            referenced_bins.append(parts[1])

            if not referenced_bins:
                return False, "El archivo .cue no declara ningún archivo binario (FILE)."

            missing = []
            for bin_name in referenced_bins:
                target = cue_path.parent / bin_name
                if not target.exists():
                    missing.append(bin_name)

            if missing:
                return False, f"Faltan archivos binarios referenciados: {', '.join(missing)}"
            return True, f"Integridad CUE/BIN verificada exitosamente ({len(referenced_bins)} pistas)"
        except Exception as err:
            return False, f"Error leyendo CUE: {err}"
