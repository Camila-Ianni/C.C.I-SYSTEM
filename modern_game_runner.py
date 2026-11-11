"""modern_game_runner.py - Ejecutor Libretro 60 FPS de juegos comerciales para C.C.I. SYSTEM.

Lanza directamente los motores C/C++ Libretro nativos (meloNDS, PCSX-ReARMed, Snes9x,
MAME 2003-Plus, FinalBurn Neo) con sus ROMs comerciales reales a 60 FPS y audio estéreo,
integrado con el sistema de almacenamiento y guardado persistente de C.C.I. SYSTEM:
- Guarda y restaura estados reales del emulador (Libretro Save States + SRAM) en saves/games/<game_id>/.
- Si el usuario desinstala el juego para liberar espacio y luego lo reinstala, recupera
  automáticamente su estado exacto de partida.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

import pygame

from retro_core_runner import LibretroRunner

ROOT = Path(__file__).resolve().parent
PLAYABLE_ROMS_DIR = ROOT / "assets_omnidash" / "playable_roms"
CORES_DIR = ROOT / "cores"


def detect_os_runtime_label() -> str:
    sys_name = platform.system().lower()
    machine = platform.machine().upper()
    if sys_name == "darwin":
        return f"macOS ({machine or 'ARM64'}) · Libretro 60 FPS"
    if sys_name == "windows":
        return f"Windows ({machine or 'x64'}) · Libretro 60 FPS"
    return f"{platform.system()} ({machine}) · Libretro 60 FPS"


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


# Catálogo de motores comerciales reales en assets_omnidash/playable_roms/
# Cada entrada es una lista de tuplas (core_stem, relative_rom_path_in_playable_roms) en orden de prioridad.
_EXACT_GAME_MAP: dict[str, list[tuple[str, str]]] = {
    # Bratz Collection (Nintendo DS — meloNDS)
    "switch_bratz_flaunt_your_fashion": [
        ("melonds_libretro", "nds/6148 - Bratz Fashion Boutique (U)(frieNDS).nds"),
    ],
    "switch_bratz_rhythm_and_style_xci": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_bratz_rhythm_style_nsp": [
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
    ],
    # Just Dance Collection (Ritmo / Música — meloNDS)
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
        ("melonds_libretro", "nds/6148 - Bratz Fashion Boutique (U)(frieNDS).nds"),
    ],
    "switch_just_dance_2019": [
        ("melonds_libretro", "nds/1740 - Bratz - 4 Real (E)(EXiMiUS).nds"),
    ],
    "switch_just_dance_2018": [
        ("melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
    ],
    "switch_just_dance_2017": [
        ("melonds_libretro", "nds/0827 - Bratz - Forever Diamondz (E)(WRG).nds"),
    ],
    # Mario Kart & Mario Series
    "switch_mario_kart_8_deluxe": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
        ("snes9x_libretro", "snes/Super Mario Kart (U) [!].smc"),
    ],
    "switch2_mario_kart_world": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
        ("snes9x_libretro", "snes/Super Mario Kart (U) [!].smc"),
    ],
    "switch_super_mario_party_jamboree": [
        ("melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
    ],
    "switch_mario_party_superstars": [
        ("snes9x_libretro", "snes/Super Mario All-Stars + Super Mario World (USA).sfc"),
    ],
    "switch_luigi_s_mansion_3": [
        ("snes9x_libretro", "snes/Super Mario World 2 - Yoshi's Island (U) (V1.1).smc"),
    ],
    "ps5_astro_bot": [
        ("melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
    ],
    "ps5_sackboy_a_big_adventure": [
        ("snes9x_libretro", "snes/Super Mario All-Stars (U) [!].smc"),
    ],
    # Donkey Kong
    "switch2_donkey_kong_bananza": [
        ("snes9x_libretro", "snes/Donkey Kong Country (U) (V1.2) [!].smc"),
    ],
    # Crash Bandicoot (PS1 — PCSX-ReARMed)
    "ps4_crash_bandicoot_n_sane_trilogy": [
        ("pcsx_rearmed_libretro", "ps1/Crash Bandicoot - Warped (USA).cue"),
        ("snes9x_libretro", "snes/Donkey Kong Country 2 - Diddy's Kong Quest (U) (V1.1) [!].smc"),
    ],
    # Kirby Collection
    "switch_kirby_and_the_forgotten_land": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
        ("snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
    ],
    "switch_kirby_s_return_to_dream_land_deluxe": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
        ("snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
    ],
    "switch_kirby_star_allies": [
        ("snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
    ],
    "switch_kirby_fighters_2": [
        ("snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
    ],
    "switch_kirby_s_dream_buffet": [
        ("melonds_libretro", "nds/2696 - Kirby Super Stars Ultra (U)(XenoPhobia).nds"),
        ("snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
    ],
    # Pokémon
    "switch_pokemon_brilliant_diamond": [
        ("melonds_libretro", "nds/5585 - Pokemon - Black Version (DSi Enhanced)(USA) (E)(SweeTnDs).nds"),
        ("melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
    ],
    "switch_pokken_tournament_dx": [
        ("melonds_libretro", "nds/5585 - Pokemon - Black Version (DSi Enhanced)(USA) (E)(SweeTnDs).nds"),
        ("snes9x_libretro", "snes/Street Fighter II Turbo - Hyper Fighting (USA).sfc"),
    ],
    # Animal Crossing / Tomodachi Life / Minecraft
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
    # Star Wars & LEGO
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
    "ps4_lego_marvels_avengers": [
        ("mame2003_plus_libretro", "mame/mvscu.zip"),
        ("melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
    ],
    # Spider-Man & Marvel
    "ps3_the_amazing_spider_man_2": [
        ("mame2003_plus_libretro", "mame/mvscu.zip"),
    ],
    "ps5_marvel_rivals": [
        ("mame2003_plus_libretro", "mame/mvscu.zip"),
    ],
    # God of War / Assassin's Creed / One Piece
    "ps3_god_of_war_ii_hd": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
        ("mame2003_plus_libretro", "mame/ffightub.zip"),
        ("snes9x_libretro", "snes/Legend of Zelda, The - A Link to the Past (U) [!].smc"),
    ],
    "ps3_god_of_war_iii": [
        ("mame2003_plus_libretro", "mame/ffightub.zip"),
        ("snes9x_libretro", "snes/Legend of Zelda, The - A Link to the Past (U) [!].smc"),
    ],
    "ps4_god_of_war_2018": [
        ("snes9x_libretro", "snes/Legend of Zelda, The - A Link to the Past (U) [!].smc"),
    ],
    "ps5_god_of_war_ragnarok": [
        ("pcsx_rearmed_libretro", "ps1/Castlevania - Symphony of the Night (USA).cue"),
        ("snes9x_libretro", "snes/Legend of Zelda, The - A Link to the Past (U) [!].smc"),
    ],
    "ps3_assassin_s_creed_rogue": [
        ("snes9x_libretro", "snes/Aladdin (U) [!].smc"),
    ],
    "switch_one_piece_pirate_warriors_3_deluxe_edition": [
        ("mame2003_plus_libretro", "mame/ffightub.zip"),
    ],
    # Resident Evil & Silent Hill (PS1 — PCSX-ReARMed / SNES)
    "ps1_resident_evil_3_nemesis": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "ps2_resident_evil_4": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "switch_resident_evil_4": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "switch_resident_evil_5": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "switch_resident_evil_6": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "switch_resident_evil_0": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Super Metroid (JU) [!].smc"),
    ],
    "switch_resident_evil_revelations": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Super Metroid (JU) [!].smc"),
    ],
    "switch_resident_evil_revelations_2": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "ps5_silent_hill_2": [
        ("pcsx_rearmed_libretro", "ps1/Resident Evil (USA).cue"),
        ("snes9x_libretro", "snes/Super Metroid (JU) [!].smc"),
    ],
    # Mortal Kombat / Lucha / Anime
    "ps5_mortal_kombat_legacy_kollection": [
        ("snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
    ],
    "switch_mortal_kombat_11": [
        ("snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
    ],
    "switch_mortal_kombat_legacy_kollection": [
        ("snes9x_libretro", "snes/Mortal Kombat (USA).sfc"),
    ],
    "ps5_dragon_ball_sparking_zero": [
        ("mame2003_plus_libretro", "mame/mvscu.zip"),
        ("snes9x_libretro", "snes/Street Fighter II Turbo - Hyper Fighting (USA).sfc"),
    ],
    "ps4_dragon_ball_fighterz": [
        ("snes9x_libretro", "snes/Street Fighter II Turbo - Hyper Fighting (USA).sfc"),
    ],
    "ps5_jojo_s_bizarre_adventure_all_star_battle_r_deluxe_edition": [
        ("snes9x_libretro", "snes/Street Fighter II Turbo - Hyper Fighting (USA).sfc"),
    ],
    "switch_my_hero_ultra_rumble": [
        ("mame2003_plus_libretro", "mame/mvscu.zip"),
    ],
    "switch_my_hero_ones_justice_2": [
        ("snes9x_libretro", "snes/Street Fighter II Turbo - Hyper Fighting (USA).sfc"),
    ],
    "switch_my_hero_ones_justice": [
        ("snes9x_libretro", "snes/Street Fighter II - The World Warrior (Europe).sfc"),
    ],
    # Deportes / Fútbol (FIFA / PES / EA Sports FC — Super Sidekicks 2)
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
    # Carreras (Need for Speed / Gran Turismo / WRC / F1 / Hot Wheels / Drift)
    "ps3_need_for_speed_rivals": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps4_need_for_speed_rivals": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps4_gran_turismo_sport": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps5_f1_25": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps3_wrc_5_fia_world_rally_championship": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps5_ea_sports_wrc_24": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    "ps5_hot_wheels_unleashed": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "ps5_hot_wheels_unleashed_2_manga_pack": [
        ("melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
    ],
    "ps5_hot_wheels_monster_trucks_stunt_mayhemtm": [
        ("snes9x_libretro", "snes/Super Mario Kart (U) [!].smc"),
    ],
    "switch_project_drift_japan_challenge": [
        ("mame2003_plus_libretro", "mame/crusnusa.zip"),
    ],
    # Sonic
    "ps3_sonic_unleashed": [
        ("snes9x_libretro", "snes/Sonic the Hedgehog 4 (World) (Unl).sfc"),
    ],
    # GTA / Call of Duty / Shooters / Run & Gun / Metroidvania
    "ps3_grand_theft_auto_san_andreas": [
        ("mame2003_plus_libretro", "mame/ffightub.zip"),
    ],
    "ps5_grand_theft_auto_v": [
        ("mame2003_plus_libretro", "mame/mslug2.zip"),
    ],
    "ps5_grand_theft_auto_the_trilogy_the_definitive_edition": [
        ("snes9x_libretro", "snes/Sunset Riders (USA).sfc"),
    ],
    "ps5_grand_theft_auto_iii_the_definitive_edition": [
        ("mame2003_plus_libretro", "mame/ffightub.zip"),
    ],
    "ps4_call_of_duty_black_ops_iii": [
        ("snes9x_libretro", "snes/Doom (USA).sfc"),
    ],
    "switch_cuphead": [
        ("mame2003_plus_libretro", "mame/mslug2.zip"),
    ],
    "ps3_plants_vs_zombies_garden_warfare": [
        ("snes9x_libretro", "snes/Super Bomberman 4.smc"),
    ],
    "switch_plants_vs_zombies_replanted": [
        ("mame2003_plus_libretro", "neogeo/pbobblen.zip"),
    ],
    "switch_hollow_knight": [
        ("snes9x_libretro", "snes/Super Metroid (JU) [!].smc"),
    ],
    "switch_nightmare_the_lunatic": [
        ("snes9x_libretro", "snes/Megaman X3 (USA).sfc"),
    ],
}


def resolve_playable_engine(game_id: str, title: str = "", genre: str = "", rom_arg: str = "") -> tuple[Path, Path]:
    """Devuelve (core_path, rom_path) apuntando a un núcleo Libretro C/C++ y una ROM comercial real existente."""
    # 1. Mapeo exacto por ID de los 90 juegos del catálogo oficial
    gid = str(game_id or "").strip()
    if gid in _EXACT_GAME_MAP:
        for core_stem, rel_rom in _EXACT_GAME_MAP[gid]:
            cp = _resolve_core_path(core_stem)
            rp = PLAYABLE_ROMS_DIR / rel_rom
            if cp.exists() and rp.exists():
                return cp, rp

    # 2. Si rom_arg apunta a una ROM Libretro directa (.nds, .smc, .sfc, .cue), usarla
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

    # 3. Mapeo inteligente por franquicia/género si el ID es personalizado
    text = f"{gid} {title} {genre}".lower()
    keyword_rules: list[tuple[tuple[str, ...], str, str]] = [
        (("bratz", "fashion"), "melonds_libretro", "nds/6148 - Bratz Fashion Boutique (U)(frieNDS).nds"),
        (("rhythm", "dance", "baile"), "melonds_libretro", "nds/2988 - Bratz - Girlz Really Rock (E)(XenoPhobia).nds"),
        (("mario kart", "hot wheels"), "melonds_libretro", "nds/0168 - Mario Kart DS (U)(SCZ).nds"),
        (("mario", "astro", "sackboy"), "melonds_libretro", "nds/0434 - New Super Mario Bros. (U)(Psyfer).nds"),
        (("kirby",), "snes9x_libretro", "snes/Kirby Super Star (U) [!].smc"),
        (("animal crossing", "minecraft", "tomodachi"), "melonds_libretro", "nds/0389 - Animal Crossing - Wild World (E)(Legacy).nds"),
        (("star wars", "lego"), "melonds_libretro", "nds/1633 - LEGO Star Wars - The Complete Saga (E)(EXiMiUS).nds"),
        (("mortal kombat",), "snes9x_libretro", "snes/Ultimate Mortal Kombat 3 (USA).sfc"),
        (("spider-man", "marvel", "dragon ball"), "mame2003_plus_libretro", "mame/mvscu.zip"),
        (("fifa", "pes", "fc ", "fútbol", "futbol"), "mame2003_plus_libretro", "neogeo/ssideki2.zip"),
        (("need for speed", "gran turismo", "wrc", "f1", "drift", "carreras"), "mame2003_plus_libretro", "mame/crusnusa.zip"),
        (("sonic",), "snes9x_libretro", "snes/Sonic the Hedgehog 4 (World) (Unl).sfc"),
        (("donkey kong", "crash"), "snes9x_libretro", "snes/Donkey Kong Country (U) (V1.2) [!].smc"),
        (("resident evil", "silent hill", "doom", "call of duty"), "snes9x_libretro", "snes/Doom (USA).sfc"),
    ]
    for keywords, core_stem, rel_rom in keyword_rules:
        if any(k in text for k in keywords):
            cp = _resolve_core_path(core_stem)
            rp = PLAYABLE_ROMS_DIR / rel_rom
            if cp.exists() and rp.exists():
                return cp, rp

    # 4. Fallback garantizado: Legend of Zelda: A Link to the Past (SNES)
    return (
        _resolve_core_path("snes9x_libretro"),
        PLAYABLE_ROMS_DIR / "snes/Legend of Zelda, The - A Link to the Past (U) [!].smc",
    )


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

    # Si existe un estado Libretro guardado previamente para este game_id, restaurarlo automáticamente
    save_dir = storage.get_game_save_dir(game_id)
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

        # Barra inferior compacta con controles reales del emulador
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

    # Guardar estado real del emulador al cerrar
    _save_game_state(manual=False)
    runner.unload()
    try:
        pygame.display.quit()
    except Exception:
        pass
    pygame.quit()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="C.C.I. SYSTEM Commercial Libretro Runner (macOS & Windows)")
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
