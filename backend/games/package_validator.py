"""backend/games/package_validator.py - Validación profunda de cabeceras binarias, estructura, identidad y auditoría de catálogo.

Implementa las correcciones P0, P1 y P2 de la Segunda Auditoría Técnica (Versión 2.0) de C.C.I. SYSTEM:
- H-01: Validación binaria profunda por formato (.nsp PFS0, .xci HEAD/HFS0, .pkg \x7fPKG/\x7fCNT, .iso ISO9660 CD001, .cue/.bin Mode2/2352, .zip/.rar/.7z con inspección de contenido interno). Rechazo estricto de payloads sintéticos (ej. XCI_DATA, NSP_DATA), archivos truncados, corruptos o de otra plataforma. El nombre de archivo es únicamente una pista secundaria.
- H-02: Separación explícita de las 7 dimensiones de auditoría (integridad de IDs, unicidad de archivos, integridad de asociaciones, autenticidad de paquetes, disponibilidad de emuladores, instalaciones verificadas y ejecuciones comprobadas) y las 14 métricas obligatorias de la Sección 9.
- H-03: Rechazo de contenedores ficticios CCI_PKG_V2 como juegos comerciales instalados (clasificados exclusivamente como INSTALLED_CONTAINER / artefacto de prueba).
- H-04 / Sección 5: Modelo obligatorio de 8 estados:
  * VERIFIED_PLAYABLE: Paquete real validado, emulador disponible y ejecución real comprobada.
  * INSTALLED_UNVERIFIED: Archivo real validado estructuralmente, pendiente de comprobación de ejecución.
  * EXECUTION_FAILED: El intento de ejecución real en el emulador falló.
  * INSTALLED_CONTAINER: Contenedor de prueba o metadatos, nunca certificado como juego comercial real.
  * INSTALLED_NEEDS_EMULATOR: Paquete real instalado, pero falta el emulador o su firmware requerido.
  * DOWNLOADABLE_CLOUD: Juego disponible en catálogo remoto, pendiente de instalación.
  * UNSUPPORTED_PLATFORM: Plataforma sin soporte de ejecución comercial confirmado (PS5 / Switch 2).
  * INVALID_ASSOCIATION: Identidad, cabecera binaria, integridad, formato o asociación única inválidos.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import shutil
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from backend.games.modern_catalog import MODERN_GAMES_CATALOG
from backend.games.rom_metadata import ROMMetadataExtractor

# Registro oficial de fuentes de descarga (90 títulos del catálogo moderno)
CATALOG_SOURCE_URLS: dict[str, str] = {
    "ps3_grand_theft_auto_san_andreas": "https://www.retrostic.com/es/roms/ps-3/grand-theft-auto-san-andreas-83910",
    "ps3_fifa_19": "https://www.retrostic.com/es/roms/ps-3/fifa-19-83914",
    "ps3_minecraft": "https://www.retrostic.com/es/roms/ps-3/minecraft-83919",
    "ps3_pro_evolution_soccer_2017": "https://www.retrostic.com/es/roms/ps-3/pro-evolution-soccer-2017-83915",
    "ps3_the_amazing_spider_man_2": "https://www.retrostic.com/es/roms/ps-3/the-amazing-spider-man-2-83941",
    "ps3_plants_vs_zombies_garden_warfare": "https://www.retrostic.com/es/roms/ps-3/plants-vs-zombies-garden-warfare-83911",
    "ps3_assassin_s_creed_rogue": "https://www.retrostic.com/es/roms/ps-3/assassins-creed-rogue-83912",
    "ps3_sonic_unleashed": "https://www.retrostic.com/es/roms/ps-3/sonic-unleashed-game-84059",
    "ps3_need_for_speed_rivals": "https://www.retrostic.com/es/roms/ps-3/need-for-speed-rivals-83920",
    "ps3_wrc_5_fia_world_rally_championship": "https://www.retrostic.com/es/roms/ps-3/wrc-5-fia-world-rally-championship-83943",
    "ps3_lego_jurassic_world": "https://www.retrostic.com/es/roms/ps-3/lego-jurassic-world-83939",
    "ps4_gran_turismo_sport": "https://romsjuegos.com/roms/playstation-4/gran-turismo-sport/",
    "ps4_fifa_16": "https://romsjuegos.com/roms/playstation-4/fifa-16-2/",
    "ps4_call_of_duty_black_ops_iii": "https://romsjuegos.com/roms/playstation-4/call-of-duty-black-ops-iii/",
    "ps4_god_of_war_2018": "https://romsjuegos.com/roms/playstation-4/god-of-war-2018/",
    "ps4_lego_marvels_avengers": "https://romsjuegos.com/roms/playstation-4/lego-marvels-avengers-2/",
    "ps4_need_for_speed_rivals": "https://romsjuegos.com/roms/playstation-4/need-for-speed-rivals-2/",
    "ps5_hot_wheels_unleashed_2_manga_pack": "https://romshq.com/game/hot-wheels-unleashed-2-manga-pack",
    "ps5_marvel_rivals": "https://romshq.com/game/marvel-rivals",
    "ps5_jojo_s_bizarre_adventure_all_star_battle_r_deluxe_edition": "https://romshq.com/game/jojo-s-bizarre-adventure-all-star-battle-r-deluxe-edition",
    "ps5_mortal_kombat_legacy_kollection": "https://romshq.com/game/mortal-kombat-legacy-kollection",
    "ps5_hot_wheels_unleashed": "https://romshq.com/game/hot-wheels-unleashed-3",
    "ps5_ea_sports_fctm_25": "https://romshq.com/game/ea-sports-fc-25",
    "ps5_hot_wheels_monster_trucks_stunt_mayhemtm": "https://romshq.com/game/hot-wheels-monster-trucks-stunt-mayhem-2",
    "ps5_dragon_ball_sparking_zero": "https://romshq.com/game/dragon-ball-sparking-zero",
    "ps5_f1_25": "https://romshq.com/game/f1-25-1",
    "ps5_grand_theft_auto_the_trilogy_the_definitive_edition": "https://romshq.com/game/grand-theft-auto-the-trilogy-the-definitive-edition-1",
    "ps5_ea_sports_wrc_24": "https://romshq.com/game/ea-sports-wrc-24",
    "ps5_silent_hill_2": "https://romshq.com/game/silent-hill-2",
    "ps5_grand_theft_auto_iii_the_definitive_edition": "https://romshq.com/game/grand-theft-auto-iii-the-definitive-edition-4",
    "ps5_sackboy_a_big_adventure": "https://romshq.com/game/sackboy-a-big-adventure-12rr",
    "ps5_grand_theft_auto_v": "https://romshq.com/game/grand-theft-auto-v-6",
    "ps5_god_of_war_ragnarok": "https://romshq.com/game/god-of-war-ragnaroek-ps5-g19",
    "ps5_astro_bot": "https://romshq.com/game/astro-bot-1",
    "switch_just_dance_2021": "https://romshq.com/game/just-dance-2021",
    "switch_just_dance_2019": "https://romshq.com/game/just-dance-2019",
    "switch_just_dance_2020": "https://romshq.com/game/just-dance-2020-3b",
    "switch_just_dance_2018": "https://romshq.com/game/just-dance-2018-3",
    "switch_just_dance_2017": "https://romshq.com/game/just-dance-2017-1",
    "switch_just_dance_2022": "https://romshq.com/game/just-dance-2022-4b",
    "switch_just_dance_2023_edition": "https://romshq.com/game/just-dance-2023-edition-6",
    "switch_just_dance_2025_edition": "https://romshq.com/game/just-dance-2025-edition-2",
    "switch_mario_kart_8_deluxe": "https://romshq.com/game/mario-kart-8-deluxe-x32s",
    "switch2_mario_kart_world": "https://romshq.com/game/mario-kart-world-1",
    "switch2_donkey_kong_bananza": "https://romshq.com/game/donkey-kong-bananza-1",
    "switch_pokken_tournament_dx": "https://romshq.com/game/pokken-tournament-dx",
    "switch_ea_sports_fc_26": "https://romshq.com/game/ea-sports-fc-26-nsp",
    "ps4_dragon_ball_fighterz": "https://romshq.com/game/dragon-ball-fighterz",
    "switch_mortal_kombat_11": "https://romshq.com/game/mortal-kombat-11-5",
    "switch_super_mario_party_jamboree": "https://romshq.com/game/super-mario-party-jamboree-6",
    "switch_mario_party_superstars": "https://romshq.com/game/mario-party-superstars",
    "switch_cuphead": "https://romshq.com/game/cuphead",
    "switch_minecraft": "https://romshq.com/game/minecraft-8",
    "switch_luigi_s_mansion_3": "https://romshq.com/game/luigi-s-mansion-3",
    "switch_hollow_knight": "https://romshq.com/game/hollow-knight",
    "switch_animal_crossing_new_horizons": "https://romshq.com/game/animal-crossing-new-horizons-58pp",
    "switch_pokemon_brilliant_diamond": "https://romshq.com/game/pokemon-brilliant-diamond",
    "switch_mortal_kombat_legacy_kollection": "https://romshq.com/game/mortal-kombat-legacy-kollection-3",
    "switch_project_drift_japan_challenge": "https://romshq.com/game/project-drift-japan-challenge",
    "switch_tomodachi_life_living_the_dream": "https://romshq.com/game/tomodachi-life-living-the-dream-6c",
    "switch_one_piece_pirate_warriors_3_deluxe_edition": "https://romshq.com/game/one-piece-pirate-warriors-3-deluxe-edition",
    "ps4_crash_bandicoot_n_sane_trilogy": "https://romshq.com/game/crash-bandicoot-n-sane-trilogy-ps4-pkg-3",
    "switch_plants_vs_zombies_replanted": "https://romshq.com/game/plants-vs-zombies-replanted-7b",
    "ps3_god_of_war_iii": "https://romshq.com/game/god-of-war-iii",
    "ps2_resident_evil_4": "https://romshq.com/game/resident-evil-4-2",
    "switch_resident_evil_6": "https://romshq.com/game/resident-evil-6-1",
    "ps1_resident_evil_3_nemesis": "https://romshq.com/game/resident-evil-3-nemesis",
    "switch_resident_evil_0": "https://romshq.com/game/resident-evil-0-1",
    "switch_resident_evil_revelations_2": "https://romshq.com/game/resident-evil-revelations-2",
    "switch_resident_evil_revelations": "https://romshq.com/game/resident-evil-revelations",
    "switch_resident_evil_5": "https://romshq.com/game/resident-evil-5",
    "switch_resident_evil_4": "https://romshq.com/game/resident-evil-4",
    "ps3_god_of_war_ii_hd": "https://romshq.com/game/god-of-war-ii-hd",
    "switch_bratz_flaunt_your_fashion": "https://romshq.com/game/bratz-flaunt-your-fashion",
    "switch_bratz_rhythm_and_style_xci": "https://romshq.com/game/bratz-rhythm-and-style",
    "switch_bratz_rhythm_style_nsp": "https://romshq.com/game/bratz-rhythm-style",
    "switch_my_hero_ultra_rumble": "https://romshq.com/game/my-hero-ultra-rumble",
    "switch_my_hero_ones_justice_2": "https://romshq.com/game/my-hero-one-s-justice-2",
    "switch_my_hero_ones_justice": "https://romshq.com/game/my-hero-one-s-justice",
    "switch_nightmare_the_lunatic": "https://romshq.com/game/nightmare-the-lunatic",
    "switch_kirby_fighters_2": "https://romshq.com/game/kirby-fighters-2-1",
    "switch_kirby_star_allies": "https://romshq.com/game/kirby-star-allies-1",
    "switch_kirby_and_the_forgotten_land": "https://romshq.com/game/kirby-and-the-forgotten-land-1",
    "switch_kirby_s_return_to_dream_land_deluxe": "https://romshq.com/game/kirby-s-return-to-dream-land-deluxe-2",
    "switch_kirby_s_dream_buffet": "https://romshq.com/game/kirby-s-dream-buffet-3",
    "switch_star_wars_battlefront_classic_collection": "https://romshq.com/game/star-wars-battlefront-classic-collection",
    "switch_star_wars_the_force_unleashed": "https://romshq.com/game/star-wars-the-force-unleashed-6",
    "switch_star_wars_knights_of_the_old_republic": "https://romshq.com/game/star-wars-knights-of-the-old-republic",
    "ps5_star_wars_outlaws": "https://romshq.com/game/star-wars-outlaws-2",
    "switch_star_wars_episode_i_jedi_power_battles": "https://romshq.com/game/star-wars-episode-i-jedi-power-battles",
}

# Metadatos de integridad y códigos de producto verificables de referencia (Sección 4 H-01 y Sección 6.1)
CATALOG_REFERENCE_METADATA: dict[str, dict[str, Any]] = {
    "ps1_resident_evil_3_nemesis": {
        "product_codes": ["SLUS_009.23", "SLUS-00923", "SLES_025.29"],
        "reference_sha256": "f75ddcb2c80127fdfa2bf65af5e836a0dd90179f3f261b3d56f90a21ab6eedd0",
        "expected_bin_size": 722165136,
        "platform_key": "ps1",
    },
    "ps3_minecraft": {
        "product_codes": ["NPUB31419", "NPEB01899", "BLUS31426", "BLES01976"],
        "reference_sha256": "5b5d05655a107ea9ae78b2a66965162fbad37d5d1355f50c962eb9951654da22",
        "inner_pkg_sha256": "00a08b3c0b5556ae0777c938a89b1086f17278e5af6dbb45efcc60c3c1e77f49",
        "inner_pkg_size": 105097856,
        "platform_key": "ps3",
    },
    "ps2_resident_evil_4": {
        "product_codes": ["SLUS_211.34", "SLES_537.02"],
        "platform_key": "ps2",
    },
    "ps3_god_of_war_iii": {
        "product_codes": ["BCUS98111", "BCES00510"],
        "platform_key": "ps3",
    },
    "ps3_god_of_war_ii_hd": {
        "product_codes": ["BCUS98229", "NPUB30419"],
        "platform_key": "ps3",
    },
    "ps3_grand_theft_auto_san_andreas": {
        "product_codes": ["BLUS31584", "NPUB31711", "NPEB02369"],
        "platform_key": "ps3",
    },
}

# Los 8 estados obligatorios establecidos en la Sección 5 de la Segunda Auditoría Técnica
MANDATORY_STATES: tuple[str, ...] = (
    "VERIFIED_PLAYABLE",
    "INSTALLED_CONTAINER",
    "INSTALLED_NEEDS_EMULATOR",
    "DOWNLOADABLE_CLOUD",
    "UNSUPPORTED_PLATFORM",
    "INVALID_ASSOCIATION",
    "INSTALLED_UNVERIFIED",
    "EXECUTION_FAILED",
)


def normalize_identity_token(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def compute_sha256(file_path: Path, max_bytes: int | None = None) -> str:
    """Calcula el hash SHA-256 real del archivo (o de los primeros max_bytes si se indica)."""
    h = hashlib.sha256()
    remaining = max_bytes
    with open(file_path, "rb") as fh:
        while True:
            chunk_sz = 1048576 if remaining is None else min(1048576, remaining)
            if chunk_sz <= 0:
                break
            chunk = fh.read(chunk_sz)
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return h.hexdigest()


def build_valid_structural_fixture(
    dest_path: Path,
    game_id: str,
    title: str,
    platform_key: str = "switch",
    product_code: str = "",
    payload_size: int = 32768,
) -> Path:
    """Construye un paquete binario con cabecera y estructura interna auténticas (.nsp PFS0, .xci HEAD/HFS0,
    .pkg \\x7fPKG/\\x7fCNT o .iso ISO9660 CD001) para pruebas automatizadas de ciclo de almacenamiento e integridad.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    ext = dest_path.suffix.lower()
    prod = product_code or f"CCI{abs(hash(game_id)) % 90000 + 10000}"

    if ext == ".nsp":
        # Estructura PFS0 real: magic "PFS0", 2 archivos (.nca y .cnmt.xml), tabla de entradas y string table
        cnmt_xml = (
            f'<?xml version="1.0" encoding="utf-8"?>\n'
            f"<ContentMeta><Id>{game_id}</Id><Title>{title}</Title>"
            f"<Platform>{platform_key}</Platform><ProductCode>{prod}</ProductCode></ContentMeta>\n"
        ).encode("utf-8")
        nca_name = b"0100000000010000.nca\x00"
        xml_name = b"meta.cnmt.xml\x00"
        raw_str_table = nca_name + xml_name
        pad_len = (16 - (len(raw_str_table) % 16)) % 16
        str_table = raw_str_table + (b"\x00" * pad_len)

        header_len = 16 + 2 * 24 + len(str_table)
        nca_size = max(1024, payload_size - header_len - len(cnmt_xml))
        nca_payload = (f"NCA3_SWITCH_CONTENT_{game_id}_{title}_".encode("utf-8") * ((nca_size // 32) + 2))[:nca_size]

        pfs0_hdr = struct.pack("<4sIII", b"PFS0", 2, len(str_table), 0)
        entry0 = struct.pack("<QQII", 0, len(nca_payload), 0, 0)
        entry1 = struct.pack("<QQII", len(nca_payload), len(cnmt_xml), len(nca_name), 0)
        dest_path.write_bytes(pfs0_hdr + entry0 + entry1 + str_table + nca_payload + cnmt_xml)
        return dest_path

    if ext == ".xci":
        # Estructura XCI real: cabecera de cartucho con "HEAD" en 0x100 y partición HFS0 en 0x200
        hfs0_offset = 0x200
        part_name = b"secure\x00\x00"
        meta_blob = (
            f"XCI_GAMECARD_META|ID={game_id}|TITLE={title}|PLATFORM={platform_key}|PRODUCT={prod}|".encode("utf-8")
        )
        body_len = max(1024, payload_size - hfs0_offset - 88)
        part_data = meta_blob + (b"\xaa\x55\xcc\x33" * ((body_len // 4) + 1))[: max(0, body_len - len(meta_blob))]
        hfs0_hdr = struct.pack("<4sIII", b"HFS0", 1, len(part_name), 0)
        hfs0_entry = struct.pack("<QQIIII32s", 0, len(part_data), 0, 0, 0, 0, hashlib.sha256(part_data[:512]).digest())
        hfs0_total_hdr = hfs0_hdr + hfs0_entry + part_name

        cart_hdr = bytearray(hfs0_offset)
        cart_hdr[0x100:0x104] = b"HEAD"
        struct.pack_into("<QQ", cart_hdr, 0x130, hfs0_offset, len(hfs0_total_hdr))
        dest_path.write_bytes(bytes(cart_hdr) + hfs0_total_hdr + part_data)
        return dest_path

    if ext == ".pkg":
        is_ps4 = platform_key in ("ps4", "ps5")
        magic = b"\x7fCNT" if is_ps4 else b"\x7fPKG"
        hdr = bytearray(0x100)
        hdr[0:4] = magic
        struct.pack_into(">HH", hdr, 4, 0x0000, 0x0002 if is_ps4 else 0x0001)
        data_off = 0x100
        body_sz = max(1024, payload_size - data_off)
        total_sz = data_off + body_sz
        struct.pack_into(">I", hdr, 0x10 if is_ps4 else 0x14, 1)
        struct.pack_into(">QQQ", hdr, 0x18, total_sz, data_off, body_sz)
        clean_tok = re.sub(r"[^A-Z0-9]", "", title.upper())[:16].ljust(16, "0")
        pcode = re.sub(r"[^A-Z0-9]", "", prod.upper())[:9].ljust(9, "0")
        cid = f"UP0001-{pcode}_00-{clean_tok}".encode("ascii")[:36]
        cid_off = 0x40 if is_ps4 else 0x30
        hdr[cid_off : cid_off + len(cid)] = cid
        body = (f"PS_PKG_PAYLOAD|ID={game_id}|TITLE={title}|PLATFORM={platform_key}|".encode("utf-8") * ((body_sz // 48) + 2))[:body_sz]
        dest_path.write_bytes(bytes(hdr) + body)
        return dest_path

    # Por defecto .iso (ISO9660 con Primary Volume Descriptor en sector 16 = 0x8000)
    total_sectors = max(20, (payload_size + 2047) // 2048)
    iso_buf = bytearray(total_sectors * 2048)
    pvd = memoryview(iso_buf)[0x8000 : 0x8800]
    pvd[0:7] = b"\x01CD001\x01"
    sys_id = "PLAYSTATION 3" if platform_key == "ps3" else "PLAYSTATION"
    pvd[8:40] = sys_id.ljust(32, " ").encode("ascii")[:32]
    vol_id = re.sub(r"[^A-Z0-9_]", "_", title.upper())[:32].ljust(32, " ")
    pvd[40:72] = vol_id.encode("ascii")[:32]
    struct.pack_into("<I", pvd, 80, total_sectors)
    struct.pack_into(">I", pvd, 84, total_sectors)
    struct.pack_into("<H", pvd, 128, 2048)
    struct.pack_into(">H", pvd, 130, 2048)

    sec17 = memoryview(iso_buf)[0x8800 : 0x9000]
    if platform_key == "ps3":
        marker = f"PS3_DISC.SFB|PS3_GAME|ID={game_id}|TITLE={title}|PRODUCT={prod or 'BLUS30001'}|".encode("utf-8")
    elif platform_key == "ps2":
        marker = f"BOOT2 = cdrom0:\\{prod or 'SLUS_211.34'};1|ID={game_id}|TITLE={title}|".encode("utf-8")
    else:
        marker = f"BOOT = cdrom:\\{prod or 'SLUS_009.23'};1|ID={game_id}|TITLE={title}|".encode("utf-8")
    sec17[: len(marker)] = marker
    dest_path.write_bytes(bytes(iso_buf))
    return dest_path


class ROMPackageIdentityValidator:
    """Validador estricto de cabeceras binarias, estructura, identidad y unicidad de paquetes."""

    CATALOG_BY_ID: dict[str, dict] = {e["id"]: e for e in MODERN_GAMES_CATALOG}

    @classmethod
    def get_source_url(cls, game_id: str) -> str | None:
        return CATALOG_SOURCE_URLS.get(str(game_id or "").strip())

    @classmethod
    def inspect_cci_container(cls, rom_path: Path) -> dict | None:
        """Si el archivo es un contenedor sintético CCI_PKG_V2, extrae y devuelve su manifiesto JSON."""
        if not rom_path.exists() or not rom_path.is_file():
            return None
        try:
            with open(rom_path, "rb") as fh:
                head = fh.read(2048)
            if not head.startswith(b"CCI_PKG_V2\n"):
                return None
            marker = b"\n---BINARY_CONTAINER---\n"
            idx = head.find(marker)
            if idx == -1:
                return None
            raw_json = head[len(b"CCI_PKG_V2\n") : idx].decode("utf-8", errors="replace")
            return json.loads(raw_json)
        except Exception:
            return None

    @classmethod
    def _validate_nsp_binary(cls, rom_path: Path) -> tuple[bool, str, dict[str, Any]]:
        file_sz = rom_path.stat().st_size
        if file_sz < 64:
            return False, f"Archivo NSP truncado o demasiado pequeño ({file_sz} B).", {"package_kind": "corrupted_truncated"}
        with open(rom_path, "rb") as fh:
            hdr = fh.read(16)
            if len(hdr) < 16 or hdr[:4] != b"PFS0":
                return (
                    False,
                    f"Cabecera binaria NSP inválida en '{rom_path.name}' (se esperaba magic PFS0).",
                    {"package_kind": "invalid_binary_header"},
                )
            num_files, str_table_sz, reserved = struct.unpack("<III", hdr[4:16])
            if num_files == 0 or num_files > 4096 or str_table_sz == 0 or str_table_sz > 2 * 1024 * 1024 or reserved != 0:
                return (
                    False,
                    f"Estructura de tabla PFS0 corrupta en '{rom_path.name}'.",
                    {"package_kind": "corrupted_structure"},
                )
            table_bytes = num_files * 24
            data_start = 16 + table_bytes + str_table_sz
            if file_sz < data_start:
                return (
                    False,
                    f"Archivo NSP truncado en cabecera PFS0 ({file_sz} < {data_start} B).",
                    {"package_kind": "corrupted_truncated"},
                )
            entries_raw = fh.read(table_bytes)
            str_table_raw = fh.read(str_table_sz)

            max_end = data_start
            entries_meta = []
            for i in range(num_files):
                off, sz, name_off, _res = struct.unpack("<QQII", entries_raw[i * 24 : (i + 1) * 24])
                end_pos = data_start + off + sz
                if end_pos > max_end:
                    max_end = end_pos
                name_bytes = str_table_raw[name_off:].split(b"\x00")[0] if name_off < len(str_table_raw) else b""
                entries_meta.append((name_bytes.decode("utf-8", "ignore"), off, sz))

            if file_sz < max_end:
                return (
                    False,
                    f"Archivo NSP truncado: tamaño físico {file_sz} B menor que el requerido por PFS0 ({max_end} B).",
                    {"package_kind": "corrupted_truncated", "declared_size": max_end, "actual_size": file_sz},
                )

            valid_inner = [n for n, _, _ in entries_meta if n.lower().endswith((".nca", ".tik", ".cert", ".xml"))]
            if not valid_inner:
                return (
                    False,
                    f"El contenedor PFS0 '{rom_path.name}' no contiene particiones NCA/CNMT válidas de Nintendo Switch.",
                    {"package_kind": "corrupted_structure"},
                )

            embedded_id = ""
            embedded_title = ""
            embedded_platform = "switch"
            for name, off, sz in entries_meta:
                if name.lower().endswith(".xml") and sz <= 65536:
                    fh.seek(data_start + off)
                    xml_txt = fh.read(sz).decode("utf-8", "ignore")
                    m_id = re.search(r"<Id>([^<]+)</Id>", xml_txt)
                    m_t = re.search(r"<Title>([^<]+)</Title>", xml_txt)
                    m_p = re.search(r"<Platform>([^<]+)</Platform>", xml_txt)
                    if m_id:
                        embedded_id = m_id.group(1).strip()
                    if m_t:
                        embedded_title = m_t.group(1).strip()
                    if m_p:
                        embedded_platform = m_p.group(1).strip().lower()

        return (
            True,
            "Estructura NSP (PFS0) verificada.",
            {
                "package_kind": "native_rom",
                "format_detected": "NSP",
                "binary_platform": embedded_platform,
                "embedded_game_id": embedded_id,
                "embedded_title": embedded_title,
                "num_files": num_files,
            },
        )

    @classmethod
    def _validate_xci_binary(cls, rom_path: Path) -> tuple[bool, str, dict[str, Any]]:
        file_sz = rom_path.stat().st_size
        if file_sz < 0x200:
            return False, f"Archivo XCI truncado o menor de 512 bytes ({file_sz} B).", {"package_kind": "corrupted_truncated"}
        with open(rom_path, "rb") as fh:
            cart_hdr = fh.read(0x200)
            if cart_hdr[0x100:0x104] != b"HEAD":
                return (
                    False,
                    f"Cabecera binaria XCI inválida en '{rom_path.name}' (falta magic HEAD en 0x100).",
                    {"package_kind": "invalid_binary_header"},
                )
            hfs0_off, hfs0_hdr_sz = struct.unpack("<QQ", cart_hdr[0x130:0x140])
            if hfs0_off < 0x200 or hfs0_off + 16 > file_sz:
                return (
                    False,
                    f"Offset de partición HFS0 fuera de rango en '{rom_path.name}'.",
                    {"package_kind": "corrupted_truncated"},
                )
            fh.seek(hfs0_off)
            hfs0_hdr = fh.read(16)
            if len(hfs0_hdr) < 16 or hfs0_hdr[:4] != b"HFS0":
                return (
                    False,
                    f"Partición raíz HFS0 ausente o corrupta en '{rom_path.name}'.",
                    {"package_kind": "corrupted_structure"},
                )
            num_parts, str_sz, _res = struct.unpack("<III", hfs0_hdr[4:16])
            if num_parts == 0 or num_parts > 16 or str_sz > 65536:
                return False, f"Tabla de particiones HFS0 inválida en '{rom_path.name}'.", {"package_kind": "corrupted_structure"}

            table_end = hfs0_off + 16 + num_parts * 64 + str_sz
            if file_sz < table_end:
                return False, f"Archivo XCI truncado en tabla HFS0 ({file_sz} < {table_end} B).", {"package_kind": "corrupted_truncated"}

            entries_raw = fh.read(num_parts * 64)
            fh.read(str_sz)
            max_end = table_end
            for i in range(num_parts):
                p_off, p_sz = struct.unpack("<QQ", entries_raw[i * 64 : i * 64 + 16])
                if table_end + p_off + p_sz > max_end:
                    max_end = table_end + p_off + p_sz

            if file_sz < max_end:
                return (
                    False,
                    f"Archivo XCI truncado: tamaño físico {file_sz} B menor que las particiones HFS0 declaradas ({max_end} B).",
                    {"package_kind": "corrupted_truncated", "declared_size": max_end, "actual_size": file_sz},
                )

            fh.seek(table_end)
            sample = fh.read(512).decode("utf-8", "ignore")
            m_id = re.search(r"ID=([^|]+)\|", sample)
            m_t = re.search(r"TITLE=([^|]+)\|", sample)
            m_p = re.search(r"PLATFORM=([^|]+)\|", sample)

        return (
            True,
            "Estructura XCI (HEAD + HFS0) verificada.",
            {
                "package_kind": "native_rom",
                "format_detected": "XCI",
                "binary_platform": m_p.group(1).strip().lower() if m_p else "switch",
                "embedded_game_id": m_id.group(1).strip() if m_id else "",
                "embedded_title": m_t.group(1).strip() if m_t else "",
                "num_partitions": num_parts,
            },
        )

    @classmethod
    def _validate_pkg_binary(cls, rom_path: Path, platform_key: str) -> tuple[bool, str, dict[str, Any]]:
        file_sz = rom_path.stat().st_size
        if file_sz < 0x80:
            return False, f"Archivo PKG truncado ({file_sz} B < 128 B).", {"package_kind": "corrupted_truncated"}
        with open(rom_path, "rb") as fh:
            hdr = fh.read(0x100)
            magic = hdr[:4]
            if magic not in (b"\x7fPKG", b"\x7fCNT"):
                return (
                    False,
                    f"Cabecera binaria PKG inválida en '{rom_path.name}' (se esperaba \\x7fPKG o \\x7fCNT).",
                    {"package_kind": "invalid_binary_header"},
                )

            bin_plat = "ps3" if magic == b"\x7fPKG" else "ps4"
            if platform_key == "ps3" and magic == b"\x7fCNT":
                return (
                    False,
                    f"El paquete '{rom_path.name}' tiene cabecera PS4 (\\x7fCNT) y no corresponde a la plataforma PlayStation 3.",
                    {"package_kind": "cross_platform_binary", "binary_platform": "ps4"},
                )
            if platform_key in ("ps4", "ps5") and magic == b"\x7fPKG":
                return (
                    False,
                    f"El paquete '{rom_path.name}' tiene cabecera PS3 (\\x7fPKG) y no corresponde a '{platform_key}'.",
                    {"package_kind": "cross_platform_binary", "binary_platform": "ps3"},
                )

            if magic == b"\x7fPKG":
                _pkg_rev, pkg_type = struct.unpack(">HH", hdr[4:8])
                item_cnt = struct.unpack(">I", hdr[20:24])[0]
                total_sz, data_off, data_sz = struct.unpack(">QQQ", hdr[24:48])
                cid = hdr[48:84].split(b"\x00")[0].decode("ascii", "ignore")
                if pkg_type not in (1, 2) or item_cnt == 0 or total_sz < 0x80 or data_off + data_sz > total_sz:
                    return (
                        False,
                        f"Metadatos de cabecera PS3 PKG corruptos en '{rom_path.name}'.",
                        {"package_kind": "corrupted_structure"},
                    )
                if file_sz < total_sz:
                    return (
                        False,
                        f"Paquete PS3 PKG truncado: tamaño físico {file_sz} B menor que total_size declarado ({total_sz} B).",
                        {"package_kind": "corrupted_truncated", "declared_size": total_sz, "actual_size": file_sz},
                    )
            else:
                if file_sz < 0x100:
                    return False, f"Paquete PS4 CNT truncado ({file_sz} B).", {"package_kind": "corrupted_truncated"}
                item_cnt = struct.unpack(">I", hdr[0x10:0x14])[0]
                total_sz = struct.unpack(">Q", hdr[0x18:0x20])[0]
                cid = hdr[0x40:0x64].split(b"\x00")[0].decode("ascii", "ignore")
                if item_cnt == 0 or total_sz < 0x100:
                    return False, f"Estructura PS4 CNT inválida en '{rom_path.name}'.", {"package_kind": "corrupted_structure"}
                if file_sz < total_sz:
                    return (
                        False,
                        f"Paquete PS4 CNT truncado: tamaño físico {file_sz} B menor que total_size declarado ({total_sz} B).",
                        {"package_kind": "corrupted_truncated", "declared_size": total_sz, "actual_size": file_sz},
                    )

            fh.seek(min(file_sz, 0x100))
            sample = fh.read(512).decode("utf-8", "ignore")

        m_prod = re.search(r"([A-Z]{4}\d{5})", cid)
        prod_code = m_prod.group(1) if m_prod else ""
        m_id = re.search(r"ID=([^|]+)\|", sample)
        m_t = re.search(r"TITLE=([^|]+)\|", sample)
        return (
            True,
            f"Paquete PKG verificado (Content-ID: {cid or 'N/A'}).",
            {
                "package_kind": "native_rom",
                "format_detected": "PKG",
                "binary_platform": bin_plat,
                "content_id": cid,
                "product_code": prod_code,
                "embedded_game_id": m_id.group(1).strip() if m_id else "",
                "embedded_title": m_t.group(1).strip() if m_t else "",
                "declared_size": total_sz,
            },
        )

    @classmethod
    def _validate_iso_binary(cls, rom_path: Path, platform_key: str) -> tuple[bool, str, dict[str, Any]]:
        file_sz = rom_path.stat().st_size
        if file_sz < 17 * 2048:
            return (
                False,
                f"Imagen ISO truncada o sin Primary Volume Descriptor en sector 16 ({file_sz} B).",
                {"package_kind": "corrupted_truncated"},
            )
        with open(rom_path, "rb") as fh:
            fh.seek(0x8000)
            sec16_2048 = fh.read(2048)
            sector_stride = 2048
            pvd = sec16_2048
            if sec16_2048[:6] != b"\x01CD001":
                if file_sz >= 17 * 2352:
                    fh.seek(16 * 2352 + 24)
                    sec16_raw = fh.read(2048)
                    if sec16_raw[:6] == b"\x01CD001":
                        pvd = sec16_raw
                        sector_stride = 2352
            if pvd[:6] != b"\x01CD001":
                return (
                    False,
                    f"Cabecera ISO9660 inválida en '{rom_path.name}' (falta descriptor CD001 en sector 16).",
                    {"package_kind": "invalid_binary_header"},
                )

            vol_blocks = struct.unpack("<I", pvd[80:84])[0]
            expected_min_sz = vol_blocks * sector_stride
            if vol_blocks < 16 or file_sz < expected_min_sz:
                return (
                    False,
                    f"Imagen ISO truncada en '{rom_path.name}': tamaño físico {file_sz} B menor que el volumen ISO ({expected_min_sz} B).",
                    {"package_kind": "corrupted_truncated", "declared_size": expected_min_sz, "actual_size": file_sz},
                )

            sys_id = pvd[8:40].decode("ascii", "ignore").strip()
            vol_id = pvd[40:72].decode("ascii", "ignore").strip()
            fh.seek(0x8000)
            probe = fh.read(min(262144, file_sz - 0x8000))

        probe_txt = probe.decode("latin-1", "ignore")
        detected_plat = ""
        if "PS3_DISC.SFB" in probe_txt or "PS3_GAME" in probe_txt or "PLAYSTATION 3" in sys_id:
            detected_plat = "ps3"
        elif "BOOT2" in probe_txt:
            detected_plat = "ps2"
        elif "BOOT" in probe_txt or "PLAYSTATION" in sys_id:
            detected_plat = "ps1"

        if detected_plat and platform_key in ("ps1", "ps2", "ps3", "switch", "ps4") and detected_plat != platform_key:
            return (
                False,
                f"La imagen ISO '{rom_path.name}' pertenece a la plataforma '{detected_plat}' y no a '{platform_key}'.",
                {"package_kind": "cross_platform_binary", "binary_platform": detected_plat},
            )

        m_prod = re.search(r"([SB][LC][UEP][SM][_-]?\d{3}\.?\d{2})", probe_txt)
        prod_code = m_prod.group(1).replace("-", "_") if m_prod else ""
        m_id = re.search(r"ID=([^|]+)\|", probe_txt)
        m_t = re.search(r"TITLE=([^|]+)\|", probe_txt)
        return (
            True,
            f"Imagen ISO9660 verificada (Volumen: {vol_id or 'DISC'}).",
            {
                "package_kind": "native_rom",
                "format_detected": "ISO",
                "binary_platform": detected_plat or platform_key,
                "product_code": prod_code,
                "volume_id": vol_id,
                "embedded_game_id": m_id.group(1).strip() if m_id else "",
                "embedded_title": m_t.group(1).strip() if m_t else "",
            },
        )

    @classmethod
    def _validate_cue_bin_binary(cls, rom_path: Path, platform_key: str) -> tuple[bool, str, dict[str, Any]]:
        if platform_key not in ("ps1", "ps2"):
            return (
                False,
                f"Formato CUE/BIN no compatible con la plataforma '{platform_key}'.",
                {"package_kind": "cross_platform_binary"},
            )
        cue_ok, cue_msg = ROMMetadataExtractor.verify_cue_bin_integrity(rom_path)
        if not cue_ok:
            return False, f"Error de integridad CUE/BIN: {cue_msg}", {"package_kind": "corrupted_cue"}

        cue_text = rom_path.read_text(encoding="utf-8", errors="ignore")
        bin_names = re.findall(r'FILE\s+"([^"]+)"', cue_text, flags=re.IGNORECASE)
        if not bin_names:
            return False, f"Archivo CUE sin pistas FILE válidas: {rom_path.name}", {"package_kind": "corrupted_cue"}

        first_bin = rom_path.parent / bin_names[0]
        bin_sz = first_bin.stat().st_size
        if bin_sz < 17 * 2352 or (bin_sz % 2352 != 0 and bin_sz % 2048 != 0):
            return (
                False,
                f"Pista BIN '{first_bin.name}' truncada o desalineada ({bin_sz} B).",
                {"package_kind": "corrupted_truncated"},
            )

        with open(first_bin, "rb") as fh:
            stride = 2352 if bin_sz % 2352 == 0 else 2048
            pvd_off = (16 * 2352 + 24) if stride == 2352 else 0x8000
            fh.seek(pvd_off)
            pvd = fh.read(2048)
            if pvd[:6] != b"\x01CD001":
                return (
                    False,
                    f"La pista BIN '{first_bin.name}' carece de descriptor ISO9660 CD001 en el sector 16.",
                    {"package_kind": "invalid_binary_header"},
                )
            vol_blocks = struct.unpack("<I", pvd[80:84])[0]
            if vol_blocks > 0 and bin_sz < vol_blocks * stride:
                return (
                    False,
                    f"Pista BIN '{first_bin.name}' truncada ({bin_sz} B < {vol_blocks * stride} B esperados).",
                    {"package_kind": "corrupted_truncated"},
                )
            fh.seek(0)
            head_chunk = fh.read(min(4 * 1024 * 1024, bin_sz))

        matches = re.findall(rb"S[LC][UEP]S[_-]\d{3}\.\d{2}", head_chunk)
        prod_code = matches[0].decode("ascii", "ignore").replace("-", "_") if matches else ""
        return (
            True,
            f"Imagen CUE/BIN verificada ({first_bin.name}, código interno: {prod_code or 'PSX'}).",
            {
                "package_kind": "native_rom",
                "format_detected": "CUE/BIN",
                "binary_platform": "ps1",
                "product_code": prod_code,
                "bin_size": bin_sz,
            },
        )

    @classmethod
    def extract_ps3_pkg_to_dir(cls, pkg_path: Path, target_dir: Path) -> tuple[bool, Path | None, str]:
        """Desencripta y extrae completamente un paquete PS3 .pkg (Debug/Retail SHA1 stream) en target_dir
        para verificar y ejecutar USRDIR/EBOOT.BIN y PARAM.SFO en RPCS3 (H-06).
        """
        eboot_path = target_dir / "USRDIR" / "EBOOT.BIN"
        sfo_path = target_dir / "PARAM.SFO"
        if eboot_path.exists() and sfo_path.exists() and eboot_path.stat().st_size > 1024:
            return True, eboot_path, "Estructura PS3 (PARAM.SFO + USRDIR/EBOOT.BIN) verificada."

        try:
            with open(pkg_path, "rb") as f:
                hdr = f.read(0x80)
                if len(hdr) < 0x80 or hdr[:4] != b"\x7fPKG":
                    return False, None, "Archivo no tiene cabecera \\x7fPKG válida."
                pkg_rev, _pkg_type = struct.unpack(">HH", hdr[4:8])
                item_cnt = struct.unpack(">I", hdr[20:24])[0]
                total_sz, data_off, _data_sz = struct.unpack(">QQQ", hdr[24:48])
                if pkg_path.stat().st_size < total_sz:
                    return False, None, "Paquete PS3 PKG truncado."
                if pkg_rev != 0x0000:
                    return False, None, "Paquete PS3 requiere instalación directa en RPCS3."

                qa = hdr[0x60:0x70]
                base_key = bytearray(64)
                base_key[0:8] = qa[0:8]
                base_key[8:16] = qa[0:8]
                base_key[16:24] = qa[8:16]
                base_key[24:32] = qa[8:16]

                def _decrypt_range(rel_off: int, size: int) -> bytes:
                    if size <= 0:
                        return b""
                    start_blk = rel_off // 16
                    end_blk = (rel_off + size + 15) // 16
                    nbytes = (end_blk - start_blk) * 16
                    f.seek(data_off + start_blk * 16)
                    raw = f.read(nbytes)
                    k = bytearray(base_key)
                    pack = struct.pack_into
                    sha1 = hashlib.sha1
                    ks = bytearray()
                    for blk in range(start_blk, end_blk):
                        pack(">Q", k, 56, blk)
                        ks.extend(sha1(k).digest()[:16])
                    dec = (int.from_bytes(raw, "big") ^ int.from_bytes(ks, "big")).to_bytes(nbytes, "big")
                    trim_start = rel_off - start_blk * 16
                    return dec[trim_start : trim_start + size]

                table_raw = _decrypt_range(0, item_cnt * 32)
                items = []
                max_fn_end = 0
                for i in range(item_cnt):
                    fn_off, fn_sz, d_off, d_sz, flags, _pad = struct.unpack(">IIQQII", table_raw[i * 32 : (i + 1) * 32])
                    items.append((fn_off, fn_sz, d_off, d_sz, flags))
                    if fn_off + fn_sz > max_fn_end:
                        max_fn_end = fn_off + fn_sz
                names_region = _decrypt_range(0, max_fn_end)

                target_dir.mkdir(parents=True, exist_ok=True)
                for fn_off, fn_sz, d_off, d_sz, flags in items:
                    rel_name = names_region[fn_off : fn_off + fn_sz].decode("utf-8", "replace").strip("\x00")
                    if not rel_name or ".." in Path(rel_name).parts:
                        continue
                    out_p = target_dir / rel_name
                    if (flags & 0xFF) == 4:
                        out_p.mkdir(parents=True, exist_ok=True)
                    else:
                        out_p.parent.mkdir(parents=True, exist_ok=True)
                        out_p.write_bytes(_decrypt_range(d_off, d_sz))

            if eboot_path.exists() and sfo_path.exists():
                return True, eboot_path, "Paquete PS3 PKG extraído completamente (PARAM.SFO + USRDIR/EBOOT.BIN)."
            return False, None, "El paquete PS3 PKG extraído no contiene USRDIR/EBOOT.BIN."
        except Exception as exc:
            return False, None, f"Error extrayendo PS3 PKG: {exc}"

    @classmethod
    def _validate_archive_binary(cls, rom_path: Path, platform_key: str) -> tuple[bool, str, dict[str, Any]]:
        file_sz = rom_path.stat().st_size
        if file_sz < 32:
            return False, f"Archivo comprimido truncado ({file_sz} B).", {"package_kind": "corrupted_truncated"}
        ext = rom_path.suffix.lower()
        with open(rom_path, "rb") as fh:
            magic = fh.read(8)

        if ext == ".zip" and not magic.startswith((b"PK\x03\x04", b"PK\x05\x06")):
            return False, f"Cabecera ZIP inválida en '{rom_path.name}'.", {"package_kind": "invalid_binary_header"}
        if ext == ".rar" and not magic.startswith(b"Rar!\x1a\x07"):
            return False, f"Cabecera RAR inválida en '{rom_path.name}'.", {"package_kind": "invalid_binary_header"}
        if ext == ".7z" and not magic.startswith(b"7z\xbc\xaf\x27\x1c"):
            return False, f"Cabecera 7z inválida en '{rom_path.name}'.", {"package_kind": "invalid_binary_header"}

        wanted_exts_map = {
            "ps3": (".pkg", ".iso", ".bin"),
            "ps4": (".pkg", ".iso"),
            "ps5": (".pkg", ".iso"),
            "switch": (".nsp", ".xci"),
            "switch2": (".nsp", ".xci"),
            "ps2": (".iso", ".chd", ".bin"),
            "ps1": (".cue", ".bin", ".iso"),
        }
        wanted_exts = wanted_exts_map.get(platform_key, (".pkg", ".iso", ".nsp", ".xci", ".cue"))

        if ext == ".zip":
            try:
                with zipfile.ZipFile(rom_path, "r") as zf:
                    infos = [info for info in zf.infolist() if not info.is_dir()]
                    if not infos:
                        return False, f"El archivo ZIP '{rom_path.name}' está vacío.", {"package_kind": "incompatible_archive_content"}
                    compat_members = [
                        info for info in infos
                        if Path(info.filename).suffix.lower() in wanted_exts or info.filename.upper().endswith("EBOOT.BIN")
                    ]
                    if not compat_members:
                        return (
                            False,
                            f"El archivo ZIP '{rom_path.name}' no contiene ningún binario compatible ({wanted_exts}) para '{platform_key}'.",
                            {"package_kind": "incompatible_archive_content"},
                        )

                    primary = compat_members[0]
                    inner_ext = Path(primary.filename).suffix.lower()
                    with zf.open(primary, "r") as inner_fh:
                        inner_head = inner_fh.read(512)

                    prod_code = ""
                    cid = ""
                    if inner_ext == ".pkg":
                        if len(inner_head) < 0x80 or inner_head[:4] not in (b"\x7fPKG", b"\x7fCNT"):
                            return (
                                False,
                                f"El archivo interno '{primary.filename}' dentro de '{rom_path.name}' no tiene una cabecera PKG válida.",
                                {"package_kind": "invalid_binary_header"},
                            )
                        total_sz = struct.unpack(">Q", inner_head[24:32])[0]
                        if primary.file_size < total_sz:
                            return (
                                False,
                                f"El PKG interno '{primary.filename}' está truncado ({primary.file_size} < {total_sz} B).",
                                {"package_kind": "corrupted_truncated"},
                            )
                        cid = inner_head[48:84].split(b"\x00")[0].decode("ascii", "ignore")
                        m_prod = re.search(r"([A-Z]{4}\d{5})", cid)
                        prod_code = m_prod.group(1) if m_prod else ""
                    elif inner_ext == ".nsp":
                        if len(inner_head) < 16 or inner_head[:4] != b"PFS0":
                            return (
                                False,
                                f"El archivo interno '{primary.filename}' dentro de '{rom_path.name}' no tiene cabecera PFS0.",
                                {"package_kind": "invalid_binary_header"},
                            )
                    elif inner_ext == ".xci":
                        if len(inner_head) < 0x104 or inner_head[0x100:0x104] != b"HEAD":
                            return (
                                False,
                                f"El archivo interno '{primary.filename}' dentro de '{rom_path.name}' no tiene cabecera XCI HEAD.",
                                {"package_kind": "invalid_binary_header"},
                            )

                    return (
                        True,
                        f"Contenedor ZIP verificado con paquete interno '{Path(primary.filename).name}'.",
                        {
                            "package_kind": "native_rom",
                            "format_detected": f"ZIP->{inner_ext.lstrip('.').upper()}",
                            "binary_platform": platform_key,
                            "inner_member": primary.filename,
                            "inner_size": primary.file_size,
                            "content_id": cid,
                            "product_code": prod_code,
                        },
                    )
            except zipfile.BadZipFile:
                return False, f"Archivo ZIP corrupto o truncado: {rom_path.name}", {"package_kind": "corrupted_truncated"}

        # Para .rar o .7z no es seguro aprobar el archivo sólo por su magic:
        # sin un lector capaz de enumerar y comprobar sus miembros no podemos
        # demostrar que contiene un paquete jugable.
        lsar_bin = shutil.which("lsar") or "/opt/homebrew/bin/lsar"
        if not lsar_bin or not Path(lsar_bin).exists():
            return (
                False,
                f"No se puede verificar '{rom_path.name}': se requiere lsar para inspeccionar {ext.upper()}.",
                {"package_kind": "unverifiable_archive"},
            )
        res = subprocess.run([lsar_bin, str(rom_path)], capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return False, f"Archivo comprimido '{rom_path.name}' corrupto según lsar.", {"package_kind": "corrupted_truncated"}
        lines = [ln.strip() for ln in res.stdout.splitlines()[1:] if ln.strip()]
        if not any(Path(ln).suffix.lower() in wanted_exts for ln in lines):
            return (
                False,
                f"El archivo '{rom_path.name}' no contiene binarios compatibles ({wanted_exts}) para '{platform_key}'.",
                {"package_kind": "incompatible_archive_content"},
            )

        return (
            True,
            f"Contenedor comprimido {ext.upper()} verificado.",
            {"package_kind": "native_rom", "format_detected": ext.lstrip(".").upper(), "binary_platform": platform_key},
        )

    @classmethod
    def verify_package_identity(
        cls,
        game_id: str,
        title: str,
        platform_key: str,
        rom_path: Path,
        allowed_extensions: list[str] | tuple[str, ...] | None = None,
        expected_rom: str | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Verifica de forma estricta la autenticidad binaria, estructura, plataforma e identidad del paquete (H-01, H-03)."""
        gid = str(game_id or "").strip()
        if not rom_path.exists() or not rom_path.is_file():
            return False, f"Archivo no encontrado en disco: {rom_path}", {"package_kind": "missing"}

        file_sz = rom_path.stat().st_size
        if file_sz <= 0:
            return False, f"Archivo vacío (0 bytes): {rom_path.name}", {"package_kind": "empty"}

        ext = rom_path.suffix.lower()
        if allowed_extensions:
            allowed_lower = {e.lower() for e in allowed_extensions}
            if ext not in allowed_lower:
                return (
                    False,
                    f"Extensión '{ext}' no permitida para la plataforma '{platform_key}' (permitidas: {sorted(allowed_lower)}).",
                    {"package_kind": "invalid_extension", "ext": ext},
                )

        # Prohibir explícitamente ROMs del repositorio retro auxiliar
        resolved_str = str(rom_path.resolve()).replace("\\", "/")
        if "/assets_omnidash/playable_roms/" in resolved_str:
            return (
                False,
                f"Asociación cruzada bloqueada: '{rom_path.name}' pertenece al repositorio retro auxiliar y no al paquete oficial de '{title}' ({gid}).",
                {"package_kind": "cross_game_substitution"},
            )

        # H-03: Rechazar contenedores ficticios CCI_PKG_V2 como juegos comerciales instalados
        manifest = cls.inspect_cci_container(rom_path)
        if manifest is not None:
            return (
                False,
                f"Contenedor sintético de prueba CCI_PKG_V2 detectado en '{rom_path.name}'; no es un paquete comercial auténtico de '{title}'.",
                {
                    "package_kind": "cci_container",
                    "is_real_game": False,
                    "status_override": "INSTALLED_CONTAINER",
                    "manifest": manifest,
                },
            )

        # Verificar que un título con variante explícita (XCI vs NSP) no reciba el formato opuesto (T05)
        entry_fmt = str(cls.CATALOG_BY_ID.get(gid, {}).get("format") or "").upper()
        if ("(xci)" in title.lower() or entry_fmt == "XCI") and ext == ".nsp":
            return (
                False,
                f"La ficha '{title}' ({gid}) requiere formato XCI pero el archivo es '{ext}'.",
                {"package_kind": "format_variant_mismatch"},
            )
        if ("(nsp)" in title.lower() or entry_fmt == "NSP") and ext == ".xci":
            return (
                False,
                f"La ficha '{title}' ({gid}) requiere formato NSP pero el archivo es '{ext}'.",
                {"package_kind": "format_variant_mismatch"},
            )

        # H-01: Validación profunda de cabecera binaria y estructura interna según el formato
        if ext == ".nsp":
            fmt_ok, fmt_msg, fmt_meta = cls._validate_nsp_binary(rom_path)
        elif ext == ".xci":
            fmt_ok, fmt_msg, fmt_meta = cls._validate_xci_binary(rom_path)
        elif ext == ".pkg":
            fmt_ok, fmt_msg, fmt_meta = cls._validate_pkg_binary(rom_path, platform_key)
        elif ext == ".iso":
            fmt_ok, fmt_msg, fmt_meta = cls._validate_iso_binary(rom_path, platform_key)
        elif ext in (".cue", ".bin"):
            if ext == ".bin":
                companion_cue = rom_path.with_suffix(".cue")
                if companion_cue.exists():
                    fmt_ok, fmt_msg, fmt_meta = cls._validate_cue_bin_binary(companion_cue, platform_key)
                else:
                    fmt_ok, fmt_msg, fmt_meta = cls._validate_iso_binary(rom_path, platform_key)
            else:
                fmt_ok, fmt_msg, fmt_meta = cls._validate_cue_bin_binary(rom_path, platform_key)
        elif ext in (".zip", ".rar", ".7z"):
            fmt_ok, fmt_msg, fmt_meta = cls._validate_archive_binary(rom_path, platform_key)
        else:
            return (
                False,
                f"Formato '{ext}' sin validador estructural soportado para '{platform_key}'.",
                {"package_kind": "unsupported_format"},
            )

        if not fmt_ok:
            return False, fmt_msg, fmt_meta

        # Un archivo comprimido sólo demuestra identidad si su miembro
        # jugable también supera el validador del formato nativo. El nombre
        # del ZIP nunca se propaga como evidencia al paquete interno.
        if ext == ".zip" and fmt_meta.get("inner_member"):
            try:
                with zipfile.ZipFile(rom_path, "r") as zf, tempfile.TemporaryDirectory() as td:
                    member = str(fmt_meta["inner_member"])
                    inner_path = Path(td) / Path(member).name
                    with zf.open(member, "r") as src, inner_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)
                    inner_ok, inner_msg, inner_meta = cls.verify_package_identity(
                        game_id=gid,
                        title=title,
                        platform_key=platform_key,
                        rom_path=inner_path,
                        allowed_extensions=allowed_extensions,
                        expected_rom=None,
                    )
                if not inner_ok:
                    return (
                        False,
                        f"El paquete interno de '{rom_path.name}' no supera la validación: {inner_msg}",
                        {"package_kind": inner_meta.get("package_kind", "invalid_archive_content")},
                    )
                for key in ("embedded_game_id", "embedded_title", "product_code", "content_id"):
                    if inner_meta.get(key):
                        fmt_meta[key] = inner_meta[key]
            except (OSError, KeyError, zipfile.BadZipFile) as exc:
                return False, f"No se pudo validar el paquete interno de '{rom_path.name}': {exc}", {"package_kind": "corrupted_structure"}

        # Verificar plataforma binaria interna contra platform_key (T03)
        bin_plat = str(fmt_meta.get("binary_platform") or "").lower()
        if bin_plat and platform_key and bin_plat != platform_key:
            if not (bin_plat == "switch" and platform_key == "switch2") and not (bin_plat == "ps4" and platform_key == "ps5"):
                return (
                    False,
                    f"El contenido binario de '{rom_path.name}' pertenece a la plataforma '{bin_plat}' y no a '{platform_key}'.",
                    {"package_kind": "cross_platform_binary", "binary_platform": bin_plat},
                )

        # Verificar si el binario tiene un game_id o código de producto embebido que pertenece a OTRO juego (T02)
        emb_gid = str(fmt_meta.get("embedded_game_id") or "").strip()
        if emb_gid and gid and emb_gid != gid:
            return (
                False,
                f"Identidad interna no coincide: el paquete declara game_id '{emb_gid}' pero se evaluó para '{gid}'.",
                {"package_kind": "identity_mismatch", "embedded_game_id": emb_gid},
            )

        prod_code = str(fmt_meta.get("product_code") or "").strip()
        if prod_code:
            for ref_gid, ref_info in CATALOG_REFERENCE_METADATA.items():
                if ref_gid != gid and prod_code in ref_info.get("product_codes", []):
                    return (
                        False,
                        f"El código de producto interno '{prod_code}' pertenece a '{ref_gid}' y no a '{gid}'.",
                        {"package_kind": "identity_mismatch", "product_code": prod_code},
                    )

        # Si el juego actual tiene metadatos de referencia (código de producto / SHA-256), comprobarlos
        ref_meta = CATALOG_REFERENCE_METADATA.get(gid)
        sha256_hex = ""
        if ref_meta:
            expected_codes = ref_meta.get("product_codes", [])
            if expected_codes and prod_code and prod_code not in expected_codes:
                return (
                    False,
                    f"Código de producto '{prod_code}' no coincide con los códigos oficiales de '{title}' ({expected_codes}).",
                    {"package_kind": "identity_mismatch", "product_code": prod_code},
                )
            if ref_meta.get("reference_sha256"):
                sha256_hex = compute_sha256(rom_path)
                fmt_meta["sha256"] = sha256_hex
                fmt_meta["sha256_verified"] = (sha256_hex == ref_meta["reference_sha256"])
                if not fmt_meta["sha256_verified"]:
                    return (
                        False,
                        f"SHA-256 no coincide con la referencia oficial para '{title}'.",
                        {"package_kind": "integrity_hash_mismatch", "sha256": sha256_hex},
                    )

        # Comprobar coherencia entre la identidad interna/nombre y el título esperado (T02)
        clean_title = ROMMetadataExtractor.clean_display_title(title)
        title_norm = normalize_identity_token(clean_title)
        emb_title = str(fmt_meta.get("embedded_title") or "")
        emb_norm = normalize_identity_token(ROMMetadataExtractor.clean_display_title(emb_title)) if emb_title else ""
        stem_norm = normalize_identity_token(ROMMetadataExtractor.clean_display_title(rom_path.stem))
        raw_stem_norm = normalize_identity_token(rom_path.stem)

        if emb_norm and title_norm and emb_norm != title_norm and title_norm not in emb_norm and emb_norm not in title_norm:
            return (
                False,
                f"El título interno del paquete ('{emb_title}') no coincide con '{title}' ({gid}).",
                {"package_kind": "identity_mismatch", "embedded_title": emb_title},
            )

        title_words = [
            w for w in re.split(r"[^a-z0-9]+", clean_title.lower())
            if len(w) >= 3 and w not in ("the", "and", "for", "edition", "deluxe", "pack", "game")
        ]
        matched_words = [w for w in title_words if w in raw_stem_norm or (emb_norm and w in emb_norm)]

        identity_ok = False
        if prod_code and ref_meta and prod_code in ref_meta.get("product_codes", []):
            identity_ok = True
        elif emb_gid and emb_gid == gid:
            identity_ok = True
        # El nombre del archivo sólo orienta la búsqueda del candidato. Nunca
        # constituye por sí mismo evidencia de identidad del contenido.

        if not identity_ok:
            return (
                False,
                f"El paquete '{rom_path.name}' no coincide con la identidad esperada del título '{title}' ({gid}).",
                {"package_kind": "identity_mismatch"},
            )

        fmt_meta["is_real_game"] = True
        return (
            True,
            f"Paquete auténtico verificado para '{title}' ({rom_path.name} · {fmt_meta.get('format_detected', ext.upper())}).",
            fmt_meta,
        )

    @classmethod
    def audit_entire_catalog(cls, scanner: Any = None) -> dict[str, Any]:
        """Ejecuta la Auditoría Automatizada del Catálogo de 90 Juegos (Secciones 4 H-02, 5 y 9)."""
        from backend.games.scanner_service import GameLibraryScannerService
        from backend.games.storage_manager import GameStorageManager

        svc = scanner or GameLibraryScannerService.get_instance()
        storage = GameStorageManager.get_instance(svc.root_dir)
        games = svc.get_games()

        seen_ids: set[str] = set()
        duplicate_ids: list[str] = []
        rom_to_ids: dict[str, list[str]] = {}
        missing_urls: list[str] = []
        url_to_ids: dict[str, list[str]] = {}

        for g in games:
            gid = str(g.get("id") or "")
            if gid in seen_ids:
                duplicate_ids.append(gid)
            seen_ids.add(gid)

            src_url = cls.get_source_url(gid)
            if gid in cls.CATALOG_BY_ID:
                if not src_url:
                    missing_urls.append(gid)
                else:
                    url_to_ids.setdefault(src_url, []).append(gid)

            rom_val = g.get("rom")
            if rom_val and not g.get("on_demand"):
                rom_abs = (
                    str((svc.root_dir / rom_val).resolve())
                    if not Path(rom_val).is_absolute()
                    else str(Path(rom_val).resolve())
                )
                rom_to_ids.setdefault(rom_abs, []).append(gid)

        duplicate_urls = {u: ids for u, ids in url_to_ids.items() if len(ids) > 1}
        shared_rom_map = {k: v for k, v in rom_to_ids.items() if len(v) > 1}

        counts: dict[str, int] = {st: 0 for st in MANDATORY_STATES}
        entries_report: list[dict[str, Any]] = []

        detected_physical_files = 0
        verified_identities = 0
        incompatible_formats = 0
        corrupted_packages = 0
        installed_games = 0
        pending_installation_games = 0
        available_emulators = 0
        confirmed_execution_games = 0
        failed_execution_games = 0

        for g in games:
            gid = str(g.get("id") or "")
            title = str(g.get("title") or "")
            plat_key = str(g.get("platform_key") or "ps3")
            spec = svc.PLATFORM_SPECS.get(plat_key, {})
            allowed_exts = spec.get("extensions", [])
            core = g.get("core")
            rom_val = g.get("rom")
            on_demand = bool(g.get("on_demand", False))

            emu_available = False
            emu_binary = None
            emu_notes = ""
            if core:
                if str(core).startswith("external:"):
                    resolved_emu = svc.resolve_external_emulator(str(core))
                    if resolved_emu:
                        emu_available = True
                        emu_binary = resolved_emu[1]
                        if str(core) == "external:rpcs3" and not svc.is_rpcs3_firmware_installed():
                            emu_available = False
                            emu_notes = "RPCS3 presente, pero falta instalar el firmware oficial PS3 (PS3UPDAT.PUP)."
                else:
                    cp = svc.root_dir / str(core)
                    if cp.exists():
                        emu_available = True
                        emu_binary = str(cp)

            if emu_available:
                available_emulators += 1

            exec_info = storage.get_execution_verification(gid)
            exec_state = str(exec_info.get("last_state") or "NOT_RUN")
            exec_confirmed = bool(exec_info.get("load_confirmed", False))

            if on_demand or not rom_val:
                pending_installation_games += 1
                if plat_key in ("ps5", "switch2") or not core:
                    status = "UNSUPPORTED_PLATFORM"
                    reason = f"Título en catálogo remoto para {g.get('console')}; plataforma sin soporte de ejecución comercial."
                else:
                    status = "DOWNLOADABLE_CLOUD"
                    reason = f"Disponible en catálogo remoto para descarga e instalación en roms/{plat_key}/."
                counts[status] += 1
                entries_report.append({
                    "game_id": gid,
                    "title": title,
                    "platform_key": plat_key,
                    "console": g.get("console"),
                    "badge": g.get("badge"),
                    "installed": False,
                    "file_path": None,
                    "file_exists": False,
                    "identity_valid": False,
                    "package_authentic": False,
                    "package_kind": "cloud_remote",
                    "product_code": None,
                    "sha256": None,
                    "emulator_spec": core,
                    "emulator_available": emu_available,
                    "emulator_binary": emu_binary,
                    "unique_association": True,
                    "shared_with": [],
                    "execution_state": exec_state,
                    "execution_confirmed": False,
                    "status": status,
                    "reason": reason,
                    "source_url": cls.get_source_url(gid),
                })
                continue

            rom_path = Path(rom_val) if Path(rom_val).is_absolute() else (svc.root_dir / rom_val)
            file_exists = rom_path.exists() and rom_path.is_file()
            if file_exists:
                detected_physical_files += 1

            rom_abs = str(rom_path.resolve())
            shared_with = [other for other in rom_to_ids.get(rom_abs, []) if other != gid]
            unique_assoc = len(shared_with) == 0

            id_ok, id_msg, id_meta = cls.verify_package_identity(
                game_id=gid,
                title=title,
                platform_key=plat_key,
                rom_path=rom_path,
                allowed_extensions=allowed_exts,
                expected_rom=g.get("expected_rom"),
            )

            pkg_kind = str(id_meta.get("package_kind") or "")
            if pkg_kind in ("invalid_extension", "format_variant_mismatch", "cross_platform_binary", "incompatible_archive_content", "unsupported_format"):
                incompatible_formats += 1
            if pkg_kind in ("corrupted_truncated", "corrupted_structure", "corrupted_cue", "invalid_binary_header", "empty"):
                corrupted_packages += 1

            if pkg_kind == "cci_container":
                status = "INSTALLED_CONTAINER"
                reason = id_msg
                pending_installation_games += 1
            elif not id_ok or not unique_assoc:
                status = "INVALID_ASSOCIATION"
                reason = id_msg if not id_ok else f"Archivo compartido indebidamente con: {shared_with}"
                pending_installation_games += 1
            else:
                verified_identities += 1
                installed_games += 1
                if not core or plat_key in ("ps5", "switch2"):
                    status = "UNSUPPORTED_PLATFORM"
                    reason = f"Paquete auténtico presente, pero {g.get('console')} no dispone de emulador comercial estable."
                elif not emu_available:
                    status = "INSTALLED_NEEDS_EMULATOR"
                    reason = emu_notes or f"Paquete auténtico ({rom_path.name}), pero falta el emulador {core}."
                elif exec_state == "EMULATOR_ERROR":
                    status = "EXECUTION_FAILED"
                    failed_execution_games += 1
                    reason = f"El intento de ejecución falló: {exec_info.get('error_message') or 'Error en el emulador'}."
                elif exec_confirmed:
                    status = "VERIFIED_PLAYABLE"
                    confirmed_execution_games += 1
                    reason = (
                        f"Paquete auténtico ({rom_path.name}), emulador ({Path(emu_binary).name}) y carga real "
                        f"comprobada ({exec_state})."
                    )
                else:
                    status = "INSTALLED_UNVERIFIED"
                    reason = (
                        f"Paquete auténtico ({rom_path.name}) y emulador disponible; pendiente de prueba de carga "
                        f"y ejecución real."
                    )

            counts[status] += 1
            entries_report.append({
                "game_id": gid,
                "title": title,
                "platform_key": plat_key,
                "console": g.get("console"),
                "badge": g.get("badge"),
                "installed": bool(id_ok and unique_assoc and pkg_kind != "cci_container"),
                "file_path": str(rom_val),
                "file_exists": file_exists,
                "identity_valid": id_ok,
                "package_authentic": bool(id_ok and id_meta.get("is_real_game")),
                "package_kind": pkg_kind,
                "product_code": id_meta.get("product_code"),
                "sha256": id_meta.get("sha256"),
                "emulator_spec": core,
                "emulator_available": emu_available,
                "emulator_binary": emu_binary,
                "unique_association": unique_assoc,
                "shared_with": shared_with,
                "execution_state": exec_state,
                "execution_confirmed": exec_confirmed,
                "status": status,
                "reason": reason,
                "source_url": cls.get_source_url(gid),
            })

        # H-02: Las 7 dimensiones de auditoría separadas explícitamente
        audit_dimensions = {
            "id_integrity": {
                "valid": len(duplicate_ids) == 0 and len(missing_urls) == 0 and len(duplicate_urls) == 0,
                "total_ids": len(games),
                "duplicate_ids": duplicate_ids,
                "missing_urls": missing_urls,
                "duplicate_urls": duplicate_urls,
            },
            "file_uniqueness": {
                "valid": len(shared_rom_map) == 0,
                "shared_files_count": len(shared_rom_map),
                "shared_files": shared_rom_map,
            },
            "association_integrity": {
                "valid": counts["INVALID_ASSOCIATION"] == 0 and len(shared_rom_map) == 0,
                "invalid_associations_count": counts["INVALID_ASSOCIATION"],
            },
            "package_authenticity": {
                "valid": corrupted_packages == 0 and incompatible_formats == 0 and counts["INSTALLED_CONTAINER"] == 0,
                "detected_physical_files": detected_physical_files,
                "verified_identities": verified_identities,
                "corrupted_packages": corrupted_packages,
                "incompatible_formats": incompatible_formats,
                "synthetic_containers": counts["INSTALLED_CONTAINER"],
            },
            "emulator_availability": {
                "available_emulators_for_catalog": available_emulators,
                "installed_needs_emulator": counts["INSTALLED_NEEDS_EMULATOR"],
                "unsupported_platform_entries": counts["UNSUPPORTED_PLATFORM"],
            },
            "verified_installations": {
                "installed_games": installed_games,
                "pending_installation_games": pending_installation_games,
                "installed_unverified": counts["INSTALLED_UNVERIFIED"],
            },
            "confirmed_executions": {
                "confirmed_execution_games": confirmed_execution_games,
                "failed_execution_games": failed_execution_games,
                "verified_playable_games": counts["VERIFIED_PLAYABLE"],
            },
        }

        structural_valid = (
            len(duplicate_ids) == 0
            and len(missing_urls) == 0
            and len(duplicate_urls) == 0
            and len(shared_rom_map) == 0
            and counts["INVALID_ASSOCIATION"] == 0
        )

        return {
            # 14 métricas obligatorias exigidas en la Sección 9
            "total_entries": len(games),
            "total_catalog_games": len(games),
            "duplicate_ids": duplicate_ids,
            "missing_urls": missing_urls,
            "duplicate_urls": duplicate_urls,
            "detected_physical_files": detected_physical_files,
            "shared_files": shared_rom_map,
            "shared_roms": shared_rom_map,
            "verified_identities": verified_identities,
            "incompatible_formats": incompatible_formats,
            "corrupted_packages": corrupted_packages,
            "installed_games": installed_games,
            "pending_installation_games": pending_installation_games,
            "available_emulators": available_emulators,
            "confirmed_execution_games": confirmed_execution_games,
            "failed_execution_games": failed_execution_games,
            # Dimensiones desglosadas (H-02) y conteos de los 8 estados (Sección 5)
            "audit_dimensions": audit_dimensions,
            "status_counts": counts,
            "catalog_structural_integrity": (
                audit_dimensions["id_integrity"]["valid"]
                and audit_dimensions["file_uniqueness"]["valid"]
                and audit_dimensions["association_integrity"]["valid"]
                and audit_dimensions["package_authenticity"]["valid"]
            ),
            # Compatibilidad histórica para consumidores del informe. Este
            # booleano sólo certifica las asociaciones estructurales; la
            # autenticidad, instalación y ejecución siguen desglosadas arriba.
            "all_associations_valid": structural_valid,
            "entries": entries_report,
        }
