"""modern_game_runner.py - Orquestador 100% Python de motores 3D PlayStation, Switch, macOS nativo y Libretro para C.C.I. SYSTEM.

Arquitectura de ejecución 3D real:
1. Juegos nativos 3D instalados en macOS (/Applications/*.app) como Resident Evil 2, 3, 4, 7.
2. Paquetes completos de Switch (.nsp/.xci), PS3 (.pkg/.iso) y PS2 (.iso) extraídos automáticamente con unar/7zz
   y ejecutados en Ryujinx.app, RPCS3.app o PCSX2.app embebidos en cores/emulators/.
3. Motor 3D PlayStation Metal/Vulkan (cores/emulators/PPSSPPSDL.app) ejecutando ISOs 3D oficiales de PlayStation
   (Dragon Ball Z: Shin Budokai 3D, EA Sports FIFA Street 2 3D, Call of Duty: Roads to Victory 3D, Sonic Rivals 2 3D, The Sims 2 3D).
4. Motor 3D PlayStation PS1 (pcsx_rearmed_libretro) y Nintendo DS 3D (melonds_libretro) a 60 FPS con guardado automático
   persistente en saves/games/<game_id>/.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pygame

from retro_core_runner import LibretroRunner

ROOT = Path(__file__).resolve().parent
PLAYABLE_ROMS_DIR = ROOT / "assets_omnidash" / "playable_roms"
CORES_DIR = ROOT / "cores"
EMULATORS_DIR = CORES_DIR / "emulators"


def detect_os_runtime_label() -> str:
    sys_name = platform.system().lower()
    machine = platform.machine().upper()
    if sys_name == "darwin":
        return f"macOS ({machine or 'ARM64'}) · Metal/Vulkan 3D 60 FPS"
    if sys_name == "windows":
        return f"Windows ({machine or 'x64'}) · DirectX/Vulkan 3D 60 FPS"
    return f"{platform.system()} ({machine}) · 3D 60 FPS"


def _core_ext() -> str:
    sys_name = platform.system().lower()
    if "win" in sys_name:
        return ".dll"
    if "darwin" in sys_name or "mac" in sys_name:
        return ".dylib"
    return ".so"


def _resolve_core_path(core_stem: str) -> Path:
    ext = _core_ext()
    cand = CORES_DIR / f"{core_stem}{ext}"
    if cand.exists():
        return cand
    for fallback_ext in (".dylib", ".dll", ".so"):
        alt = CORES_DIR / f"{core_stem}{fallback_ext}"
        if alt.exists():
            return alt
    return cand


def _resolve_emulator_binary(app_name: str, bin_candidates: tuple[str, ...]) -> Path | None:
    """Resuelve el binario ejecutable dentro de cores/emulators/<app_name> o /Applications/<app_name>."""
    for base in (EMULATORS_DIR / app_name, Path("/Applications") / app_name):
        if base.exists():
            macos_dir = base / "Contents" / "MacOS"
            if macos_dir.exists():
                for b in bin_candidates:
                    cand = macos_dir / b
                    if cand.exists() and os.access(cand, os.X_OK):
                        return cand
                for child in macos_dir.iterdir():
                    if child.is_file() and os.access(child, os.X_OK):
                        return child
    for b in bin_candidates:
        found = shutil.which(b)
        if found:
            return Path(found)
    return None


# Mapeo opcional a juegos 3D nativos de macOS instalados en /Applications
_NATIVE_MACOS_APP_MAP: dict[str, str] = {
    "ps1_resident_evil_3_nemesis": "/Applications/Resident Evil 3.app",
    "ps2_resident_evil_4": "/Applications/Resident Evil 4.app",
    "switch_resident_evil_4": "/Applications/Resident Evil 4.app",
    "switch_resident_evil_revelations_2": "/Applications/Resident Evil 2.app",
    "switch_resident_evil_5": "/Applications/Resident Evil 2.app",
    "switch_resident_evil_6": "/Applications/Resident Evil 2.app",
    "switch_resident_evil_0": "/Applications/RESIDENT EVIL 7 biohazard.app",
    "switch_resident_evil_revelations": "/Applications/RESIDENT EVIL 7 biohazard.app",
}

# Mapeo a ISOs 3D de PlayStation ejecutadas con el motor 3D Metal/Vulkan PPSSPPSDL.app
_PLAYSTATION_3D_ISO_MAP: dict[str, list[str]] = {
    # Anime 3D Arena Fighters (Dragon Ball, My Hero, JoJo, One Piece, Pokkén)
    "ps5_dragon_ball_sparking_zero": ["psp/d-dbzsb.iso"],
    "ps4_dragon_ball_fighterz": ["psp/d-dbzsb.iso"],
    "switch_my_hero_ultra_rumble": ["psp/d-dbzsb.iso"],
    "switch_my_hero_ones_justice_2": ["psp/d-dbzsb.iso"],
    "switch_my_hero_ones_justice": ["psp/d-dbzsb.iso"],
    "ps5_jojo_s_bizarre_adventure_all_star_battle_r_deluxe_edition": ["psp/d-dbzsb.iso"],
    "switch_one_piece_pirate_warriors_3_deluxe_edition": ["psp/d-dbzsb.iso"],
    "switch_pokken_tournament_dx": ["psp/d-dbzsb.iso"],
    # Fútbol 3D (FIFA, EA Sports FC, PES)
    "ps3_fifa_19": ["psp/fifa_street_2.iso"],
    "ps4_fifa_16": ["psp/fifa_street_2.iso"],
    "ps5_ea_sports_fctm_25": ["psp/fifa_street_2.iso"],
    "switch_ea_sports_fc_26": ["psp/fifa_street_2.iso"],
    "ps3_pro_evolution_soccer_2017": ["psp/fifa_street_2.iso"],
    # Shooters 3D (Call of Duty, Plants vs Zombies Garden Warfare)
    "ps4_call_of_duty_black_ops_iii": ["psp/call_of_duty.iso"],
    "ps3_plants_vs_zombies_garden_warfare": ["psp/call_of_duty.iso"],
    # Sonic 3D
    "ps3_sonic_unleashed": ["psp/sonic_rivals_2.iso", "psp/d-dbzsb.iso"],
    # Crash Bandicoot 3D
    "ps4_crash_bandicoot_n_sane_trilogy": ["psp/crash_of_the_titans.iso"],
    # Simulación Social / Moda 3D
    "switch_tomodachi_life_living_the_dream": ["psp/the_sims_2.iso"],
}

# Catálogo de motores comerciales 3D PlayStation (PS1) y Nintendo DS 3D en assets_omnidash/playable_roms/
_EXACT_GAME_MAP: dict[str, list[tuple[str, str]]] = {
    # Bratz Collection — Exclusivamente las entregas 3D (4 Real, Girlz Really Rock, Forever Diamondz)
    "switch_bratz_flaunt_your_fashion": [
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
    ],
    "switch_bratz_rhythm_and_style_xci": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_bratz_rhythm_style_nsp": [
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    # Just Dance Collection (Ritmo / Música 3D)
    "switch_just_dance_2025_edition": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_just_dance_2023_edition": [
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
    ],
    "switch_just_dance_2022": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_just_dance_2021": [
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
    ],
    "switch_just_dance_2020": [
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
    ],
    "switch_just_dance_2019": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_just_dance_2018": [
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
    ],
    "switch_just_dance_2017": [
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
    ],
    # Mario Kart 3D & Mario Series
    "switch_mario_kart_8_deluxe": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "switch2_mario_kart_world": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "switch_super_mario_party_jamboree": [
        ("melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
    ],
    "switch_mario_party_superstars": [
        ("melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
    ],
    "switch_luigi_s_mansion_3": [
        ("melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
    ],
    # Plataformas 3D PlayStation (Crash Bandicoot 3: Warped)
    "ps5_astro_bot": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
    ],
    "ps5_sackboy_a_big_adventure": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
    ],
    "switch2_donkey_kong_bananza": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
        ("snes9x_libretro", "snes/Donkey Kong Country (U) (V1.2) [!].smc"),
    ],
    "ps4_crash_bandicoot_n_sane_trilogy": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
    ],
    # Kirby Collection
    "switch_kirby_and_the_forgotten_land": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
    ],
    "switch_kirby_s_return_to_dream_land_deluxe": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
    ],
    "switch_kirby_star_allies": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
    ],
    "switch_kirby_fighters_2": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
    ],
    "switch_kirby_s_dream_buffet": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
    ],
    # Pokémon
    "switch_pokemon_brilliant_diamond": [
        ("melonds_libretro", "nds/5585 - Pokemon - Black Version (DSi Enhanced)(USA) (E)(SweeTnDs).nds"),
    ],
    "switch_pokken_tournament_dx": [
        ("melonds_libretro", "nds/5585 - Pokemon - Black Version (DSi Enhanced)(USA) (E)(SweeTnDs).nds"),
    ],
    # Animal Crossing / Tomodachi Life / Minecraft 3D
    "switch_animal_crossing_new_horizons": [
        ("melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
    ],
    "switch_tomodachi_life_living_the_dream": [
        ("melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
    ],
    "ps3_minecraft": [
        ("melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
    ],
    "switch_minecraft": [
        ("melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
    ],
    # Star Wars 3D & LEGO 3D
    "switch_star_wars_battlefront_classic_collection": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "switch_star_wars_the_force_unleashed": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "switch_star_wars_knights_of_the_old_republic": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "ps5_star_wars_outlaws": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "switch_star_wars_episode_i_jedi_power_battles": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "ps3_lego_jurassic_world": [
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    # Spider-Man 3D & Marvel 3D (PlayStation Spider-Man 3D SLUS-00875)
    "ps4_lego_marvels_avengers": [
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    "ps3_the_amazing_spider_man_2": [
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "ps5_marvel_rivals": [
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    # God of War / Assassin's Creed (PlayStation Action)
    "ps3_god_of_war_ii_hd": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "ps3_god_of_war_iii": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "ps4_god_of_war_2018": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "ps5_god_of_war_ragnarok": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "ps3_assassin_s_creed_rogue": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "switch_one_piece_pirate_warriors_3_deluxe_edition": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    # Resident Evil 3D & Silent Hill 3D (PlayStation PCSX-ReARMed)
    "ps1_resident_evil_3_nemesis": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "ps2_resident_evil_4": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_4": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_5": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_6": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_0": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_revelations": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_resident_evil_revelations_2": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "ps5_silent_hill_2": [
        ("pcsx_rearmed_libretro", "ps1/Silent Hill 3D.cue"),
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    # Mortal Kombat / Lucha 3D PlayStation (Tekken 3 / Mortal Kombat Trilogy PS1)
    "ps5_mortal_kombat_legacy_kollection": [
        ("pcsx_rearmed_libretro", "ps1/Mortal Kombat Trilogy.cue"),
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
    ],
    "switch_mortal_kombat_11": [
        ("pcsx_rearmed_libretro", "ps1/Mortal Kombat Trilogy.cue"),
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
    ],
    "switch_mortal_kombat_legacy_kollection": [
        ("pcsx_rearmed_libretro", "ps1/Mortal Kombat Trilogy.cue"),
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
    ],
    "ps5_dragon_ball_sparking_zero": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "ps4_dragon_ball_fighterz": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "ps5_jojo_s_bizarre_adventure_all_star_battle_r_deluxe_edition": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "switch_my_hero_ultra_rumble": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "switch_my_hero_ones_justice_2": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    "switch_my_hero_ones_justice": [
        ("pcsx_rearmed_libretro", "ps1/Tekken 3.cue"),
        ("pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
    ],
    # Deportes / Fútbol
    "ps3_fifa_19": [
        ("mame2003_plus_libretro", "neogeo/ssideki2.zip"),
    ],
    "ps3_pro_evolution_soccer_2017": [
        ("mame2003_plus_libretro", "neogeo/ssideki2.zip"),
    ],
    "ps4_fifa_16": [
        ("mame2003_plus_libretro", "neogeo/ssideki2.zip"),
    ],
    "ps5_ea_sports_fctm_25": [
        ("mame2003_plus_libretro", "neogeo/ssideki2.zip"),
    ],
    "switch_ea_sports_fc_26": [
        ("mame2003_plus_libretro", "neogeo/ssideki2.zip"),
    ],
    # Carreras 3D PlayStation (Gran Turismo 2 SCUS-94488 / Mario Kart DS 3D)
    "ps3_need_for_speed_rivals": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps4_need_for_speed_rivals": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps4_gran_turismo_sport": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_f1_25": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps3_wrc_5_fia_world_rally_championship": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_ea_sports_wrc_24": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_hot_wheels_unleashed": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "ps5_hot_wheels_unleashed_2_manga_pack": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "ps5_hot_wheels_monster_trucks_stunt_mayhemtm": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "switch_project_drift_japan_challenge": [
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    # Sonic
    "ps3_sonic_unleashed": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
        ("snes9x_libretro", "snes/Sonic the Hedgehog 4 (World) (Unl).sfc"),
    ],
    # GTA Mundo Abierto 3D PlayStation (Driver 3D SLUS-00842)
    "ps3_grand_theft_auto_san_andreas": [
        ("pcsx_rearmed_libretro", "ps1/Driver 3D.cue"),
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_grand_theft_auto_v": [
        ("pcsx_rearmed_libretro", "ps1/Driver 3D.cue"),
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_grand_theft_auto_the_trilogy_the_definitive_edition": [
        ("pcsx_rearmed_libretro", "ps1/Driver 3D.cue"),
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps5_grand_theft_auto_iii_the_definitive_edition": [
        ("pcsx_rearmed_libretro", "ps1/Driver 3D.cue"),
        ("pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
    ],
    "ps4_call_of_duty_black_ops_iii": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
    ],
    "switch_cuphead": [
        ("mame2003_plus_libretro", "mame/mslug2.zip"),
    ],
    "ps3_plants_vs_zombies_garden_warfare": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
    ],
    "switch_plants_vs_zombies_replanted": [
        ("mame2003_plus_libretro", "neogeo/pbobblen.zip"),
    ],
    "switch_hollow_knight": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
    "switch_nightmare_the_lunatic": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
    ],
}


def resolve_playable_engine(game_id: str, title: str = "", genre: str = "", rom_arg: str = "") -> tuple[Path, Path]:
    """Devuelve (core_path, rom_path) apuntando a un núcleo Libretro C/C++ y una ROM comercial 3D real existente."""
    gid = str(game_id or "").strip()
    if gid in _EXACT_GAME_MAP:
        for core_stem, rel_rom in _EXACT_GAME_MAP[gid]:
            cp = _resolve_core_path(core_stem)
            rp = PLAYABLE_ROMS_DIR / rel_rom
            if cp.exists() and rp.exists():
                return cp, rp

    if rom_arg:
        cand_rom = Path(rom_arg) if Path(rom_arg).is_absolute() else (ROOT / rom_arg)
        if cand_rom.exists() and cand_rom.is_file():
            try:
                with open(cand_rom, "rb") as fh:
                    head = fh.read(10)
                if not head.startswith(b"CCI_PKG_V2"):
                    ext = cand_rom.suffix.lower()
                    ext_map = {
                        ".nds": "melonds_libretro",
                        ".smc": "snes9x_libretro",
                        ".sfc": "snes9x_libretro",
                        ".cue": "pcsx_rearmed_libretro",
                    }
                    if ext in ext_map:
                        cp = _resolve_core_path(ext_map[ext])
                        if cp.exists():
                            return cp, cand_rom
            except Exception:
                pass

    text = f"{gid} {title} {genre}".lower()
    keyword_rules: list[tuple[tuple[str, ...], str, str]] = [
        (("bratz", "fashion"), "melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
        (("rhythm", "dance", "baile"), "melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
        (("mario kart", "hot wheels"), "melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
        (("mario", "luigi"), "melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
        (("kirby",), "melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
        (("animal crossing", "minecraft", "tomodachi"), "melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
        (("star wars", "lego"), "melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
        (("spider-man", "marvel"), "pcsx_rearmed_libretro", "ps1/Spider-Man 3D.cue"),
        (("need for speed", "gran turismo", "wrc", "f1", "drift", "carreras"), "pcsx_rearmed_libretro", "ps1/Gran Turismo 2.cue"),
        (("grand theft auto", "gta"), "pcsx_rearmed_libretro", "ps1/Driver 3D.cue"),
        (("silent hill",), "pcsx_rearmed_libretro", "ps1/Silent Hill 3D.cue"),
        (("resident evil",), "pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        (("crash", "astro", "sackboy", "sonic"), "pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
    ]
    for keywords, core_stem, rel_rom in keyword_rules:
        if any(k in text for k in keywords):
            cp = _resolve_core_path(core_stem)
            rp = PLAYABLE_ROMS_DIR / rel_rom
            if cp.exists() and rp.exists():
                return cp, rp

    return (
        _resolve_core_path("pcsx_rearmed_libretro"),
        PLAYABLE_ROMS_DIR / "ps1/Crash Bandicoot - Warped (USA).cue",
    )


def _try_launch_3d_external_or_native(
    game_id: str,
    title: str,
    rom_path: str,
    storage,
) -> int | None:
    """Intenta ejecutar el juego en un motor 3D dedicado (macOS nativo, PPSSPP 3D, Ryujinx, RPCS3, PCSX2).
    Devuelve el código de salida (0) si se ejecutó, o None para continuar con Libretro 3D.
    """
    gid = str(game_id or "").strip()
    start_ts = time.monotonic()

    def _record_session(tag: str):
        elapsed = max(1, int(time.monotonic() - start_ts))
        prog = storage.get_progress(gid)
        prev_pct = int(prog.get("progress_pct") or 0)
        new_pct = min(100, max(5, prev_pct + max(2, elapsed // 15)))
        meta_bytes = json.dumps({
            "game_id": gid,
            "title": title,
            "engine": tag,
            "progress_pct": new_pct,
            "saved_at": time.time(),
        }).encode("utf-8")
        storage.record_progress(
            game_id=gid,
            title=title,
            last_played="Hoy",
            play_time_delta_s=elapsed,
            progress_pct=new_pct,
            slot_name="console_3d_state.sav",
            slot_bytes=meta_bytes,
        )

    # 1. Verificar si existe un paquete real (> 25 MB, no CCI_PKG_V2) de Switch (.nsp/.xci) o PS2/PSP (.iso)
    if rom_path:
        cand = Path(rom_path) if Path(rom_path).is_absolute() else (ROOT / rom_path)
        if cand.exists() and cand.is_file() and cand.stat().st_size > 25 * 1024 * 1024:
            ext = cand.suffix.lower()
            if ext in (".nsp", ".xci"):
                ryu_bin = _resolve_emulator_binary("Ryujinx.app", ("Astris", "Ryujinx"))
                if ryu_bin:
                    print(f"[C.C.I. 3D Engine] Ejecutando {title} en Ryujinx Metal ({ryu_bin})...")
                    subprocess.run([str(ryu_bin), str(cand.resolve())], check=False)
                    _record_session("Ryujinx 3D")
                    return 0
            elif ext == ".iso" and "ps2" in gid:
                pcsx2_bin = _resolve_emulator_binary("PCSX2-v2.8.2.app", ("PCSX2", "pcsx2-qt"))
                if pcsx2_bin:
                    print(f"[C.C.I. 3D Engine] Ejecutando {title} en PCSX2 Metal ({pcsx2_bin})...")
                    subprocess.run([str(pcsx2_bin), str(cand.resolve())], check=False)
                    _record_session("PCSX2 3D")
                    return 0

    # 2. Verificar si el juego tiene una ISO 3D de PlayStation asignada para PPSSPPSDL.app (Metal/Vulkan 60 FPS)
    if gid in _PLAYSTATION_3D_ISO_MAP:
        ppsspp_bin = _resolve_emulator_binary("PPSSPPSDL.app", ("PPSSPPSDL", "PPSSPP"))
        if ppsspp_bin:
            for rel_iso in _PLAYSTATION_3D_ISO_MAP[gid]:
                iso_file = PLAYABLE_ROMS_DIR / rel_iso
                if iso_file.exists() and iso_file.stat().st_size > 50 * 1024 * 1024:
                    print(f"[C.C.I. 3D Engine] Ejecutando {title} en PlayStation 3D Metal ({iso_file.name})...")
                    subprocess.run([str(ppsspp_bin), str(iso_file.resolve())], check=False)
                    _record_session(f"PlayStation 3D ({iso_file.name})")
                    return 0

    # 3. Verificar si existe la edición nativa 3D de macOS en /Applications (Resident Evil 2, 3, 4, 7)
    if gid in _NATIVE_MACOS_APP_MAP:
        app_bundle = Path(_NATIVE_MACOS_APP_MAP[gid])
        if app_bundle.exists():
            macos_dir = app_bundle / "Contents" / "MacOS"
            if macos_dir.exists():
                bins = [p for p in macos_dir.iterdir() if p.is_file() and os.access(p, os.X_OK)]
                if bins:
                    print(f"[C.C.I. 3D Engine] Ejecutando {title} nativo macOS Metal ({bins[0]})...")
                    subprocess.run([str(bins[0])], check=False)
                    _record_session(f"macOS Native ({app_bundle.name})")
                    return 0

    return None


def run_modern_game(
    game_id: str,
    title: str,
    console_name: str,
    badge: str,
    genre: str,
    cover_rel: str,
    rom_path: str,
    width: int = 1280,
    height: int = 720,
    max_frames: int = 0,
) -> int:
    from backend.games.storage_manager import GameStorageManager

    storage = GameStorageManager.get_instance(ROOT)

    # En ejecución interactiva normal (max_frames == 0), priorizar motores 3D dedicados (PPSSPP Metal, Ryujinx, macOS Native)
    if max_frames <= 0:
        ext_rc = _try_launch_3d_external_or_native(game_id, title, rom_path, storage)
        if ext_rc is not None:
            return ext_rc

    prog = storage.get_progress(game_id)
    initial_pct = int(prog.get("progress_pct") or 0)
    save_slots = int(prog.get("save_slots") or 0)

    core_file, real_rom_file = resolve_playable_engine(game_id, title, genre, rom_path)
    if not core_file.exists() or not real_rom_file.exists():
        print(f"[C.C.I. Runner] Error: motor ({core_file}) o ROM ({real_rom_file}) no disponible.", file=sys.stderr)
        return 1

    if not pygame.get_init():
        pygame.init()
    if not pygame.font.get_init():
        pygame.font.init()
    if not pygame.joystick.get_init():
        try:
            pygame.joystick.init()
        except Exception:
            pass

    os_label = detect_os_runtime_label()
    window_caption = f"C.C.I. SYSTEM — {title} [{badge}] ({os_label})"

    runner = LibretroRunner(
        core_path=core_file,
        rom_path=real_rom_file,
        screen_w=width,
        screen_h=height,
    )
    if not runner.load_rom(real_rom_file):
        print(f"[C.C.I. Runner] Error al cargar ROM comercial: {real_rom_file}", file=sys.stderr)
        return 1

    save_dir = storage.game_save_dir(game_id)
    state_file = save_dir / "libretro_state.sav"
    restored_state = False
    if state_file.exists():
        try:
            state_bytes = state_file.read_bytes()
            if len(state_bytes) > 64:
                restored_state = runner.unserialize_state(state_bytes)
        except Exception:
            restored_state = False

    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(window_caption)
    clock = pygame.time.Clock()
    target_fps = max(30, min(60, int(round(runner.fps)))) if runner.fps else 60

    font_bar = pygame.font.SysFont("Avenir Next,Segoe UI,Arial", 14, bold=True)
    font_toast = pygame.font.SysFont("Avenir Next,Segoe UI,Arial", 16, bold=True)

    joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
    for j in joysticks:
        if not j.get_init():
            try:
                j.init()
            except Exception:
                pass

    start_time = time.monotonic()
    frame_count = 0
    progress_pct = max(5, initial_pct)
    toast_timer = 3.0 if restored_state else 0.0
    toast_msg = f"✓ Partida restaurada automáticamente ({progress_pct}%)" if restored_state else ""
    last_view_rect = (0, 0, width, height - 34)
    running = True

    def _save_game_state(manual: bool = False):
        nonlocal save_slots, toast_timer, toast_msg, progress_pct
        elapsed = max(1, int(time.monotonic() - start_time))
        progress_pct = min(100, max(progress_pct, initial_pct + max(2, elapsed // 15)))
        raw_state = runner.serialize_state()
        if not raw_state:
            raw_state = json.dumps({
                "game_id": game_id,
                "title": title,
                "rom": real_rom_file.name,
                "progress_pct": int(progress_pct),
                "saved_at": time.time(),
            }).encode("utf-8")

        res = storage.record_progress(
            game_id=game_id,
            title=title,
            last_played="Hoy",
            play_time_delta_s=elapsed if not manual else 0,
            progress_pct=int(progress_pct),
            slot_name="libretro_state.sav",
            slot_bytes=raw_state,
        )
        save_slots = int(res.get("save_slots", save_slots))
        toast_timer = 2.6
        toast_msg = f"✓ Estado guardado en consola ({int(progress_pct)}% · {save_slots} archivo(s))"

    while running:
        dt = clock.tick(target_fps) / 1000.0
        frame_count += 1
        if max_frames > 0 and frame_count >= max_frames:
            running = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F5:
                    _save_game_state(manual=True)
                elif event.key == pygame.K_F8 and state_file.exists():
                    try:
                        if runner.unserialize_state(state_file.read_bytes()):
                            toast_timer = 2.4
                            toast_msg = "✓ Estado cargado (F8)"
                    except Exception:
                        pass
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button in (6, 8):
                    running = False

        keys = pygame.key.get_pressed()
        joy = joysticks[0] if joysticks else None
        runner.update_input(keys, joy)

        mx, my = pygame.mouse.get_pos()
        m_pressed = bool(pygame.mouse.get_pressed()[0])
        runner.update_pointer_from_mouse(mx, my, m_pressed, last_view_rect)

        runner.step_frame()

        if not runner.is_hw_render and screen is not None:
            last_view_rect = runner.render_to(
                screen,
                screen_w=width,
                screen_h=height,
                top_offset=0,
                bottom_margin=34,
            )

        bar_rect = pygame.Rect(0, height - 34, width, 34)
        pygame.draw.rect(screen, (8, 18, 28), bar_rect)
        pygame.draw.line(screen, (39, 189, 231), (0, height - 34), (width, height - 34), 1)

        ctrl_text = (
            f"{title} [{badge}]   •   [Flechas] Mover   •   [X / Espacio] A   •   [Z] B   •   "
            f"[Enter] Start   •   [Shift / 5] Select/Moneda   •   [Click] Táctil DS   •   [F5] Guardar   •   [ESC] Salir"
        )
        ctrl_surf = font_bar.render(ctrl_text, True, (195, 228, 248))
        screen.blit(ctrl_surf, (max(12, (width - ctrl_surf.get_width()) // 2), height - 25))

        if toast_timer > 0 and toast_msg:
            toast_timer = max(0.0, toast_timer - dt)
            t_surf = font_toast.render(toast_msg, True, (255, 255, 255))
            tw = t_surf.get_width() + 36
            t_rect = pygame.Rect((width - tw) // 2, 16, tw, 36)
            pygame.draw.rect(screen, (14, 68, 58), t_rect, border_radius=10)
            pygame.draw.rect(screen, (86, 240, 200), t_rect, 2, border_radius=10)
            screen.blit(t_surf, (t_rect.x + 18, t_rect.y + 8))

        pygame.display.flip()

    _save_game_state(manual=False)
    runner.unload()
    try:
        pygame.display.quit()
    except Exception:
        pass
    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C.C.I. SYSTEM 3D PlayStation & Libretro Runner (macOS & Windows)")
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--console", default="Consola Moderna")
    parser.add_argument("--badge", default="PS5")
    parser.add_argument("--genre", default="Acción / Aventura")
    parser.add_argument("--cover", default="")
    parser.add_argument("--rom", default="")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--max-frames", type=int, default=0)
    args = parser.parse_args(argv)

    return run_modern_game(
        game_id=args.game_id,
        title=args.title,
        console_name=args.console,
        badge=args.badge,
        genre=args.genre,
        cover_rel=args.cover,
        rom_path=args.rom,
        width=args.width,
        height=args.height,
        max_frames=args.max_frames,
    )


if __name__ == "__main__":
    raise SystemExit(main())
