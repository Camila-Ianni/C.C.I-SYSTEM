"""backend/games/package_validator.py - Validación estricta de identidad, plataforma y asociación única de paquetes.

Implementa los controles P0, P1 y P2 de la Auditoría Técnica de C.C.I. SYSTEM:
- Prohibición total de sustituciones silenciosas entre títulos distintos o plataformas distintas.
- Prohibición de fallbacks genéricos (ej. Crash Bandicoot: Warped) cuando falta el archivo real.
- Verificación de unicidad: ningún archivo ROM o ejecutable puede asociarse a más de un game_id distinto.
- Validación de identidad (nombre normalizado, expected_rom, manifiesto o código de producto) y formato por plataforma.
- Separación explícita de estados:
  * VERIFIED_PLAYABLE: Binario real instalado, identidad verificada, emulador compatible disponible.
  * INSTALLED_CONTAINER: Contenedor local registrado para el game_id exacto.
  * INSTALLED_NEEDS_EMULATOR: Binario instalado, pero falta el emulador externo en el SO actual.
  * DOWNLOADABLE_CLOUD: Ficha remota en la nube pendiente de descarga/instalación.
  * UNSUPPORTED_PLATFORM: Plataforma de nueva generación (PS5 / Switch 2) sin emulador comercial estable.
  * INVALID_ASSOCIATION: Archivo inexistente, formato incompatible, identidad no coincidente o archivo compartido.
"""
from __future__ import annotations

import json
import re
import unicodedata
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


def normalize_identity_token(text: str) -> str:
    t = unicodedata.normalize("NFKD", text or "").encode("ASCII", "ignore").decode("utf-8")
    return re.sub(r"[^a-z0-9]", "", t.lower())


class ROMPackageIdentityValidator:
    """Validador estricto de paquetes de juegos para C.C.I. SYSTEM."""

    CATALOG_BY_ID: dict[str, dict] = {e["id"]: e for e in MODERN_GAMES_CATALOG}

    @classmethod
    def get_source_url(cls, game_id: str) -> str | None:
        return CATALOG_SOURCE_URLS.get(str(game_id or "").strip())

    @classmethod
    def inspect_cci_container(cls, rom_path: Path) -> dict | None:
        """Si el archivo es un contenedor CCI_PKG_V2, extrae y devuelve su manifiesto JSON."""
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
    def verify_package_identity(
        cls,
        game_id: str,
        title: str,
        platform_key: str,
        rom_path: Path,
        allowed_extensions: list[str] | tuple[str, ...] | None = None,
        expected_rom: str | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Verifica que rom_path exista, tenga extensión válida para platform_key y corresponda exactamente al título/game_id."""
        gid = str(game_id or "").strip()
        if not rom_path.exists() or not rom_path.is_file():
            return False, f"Archivo no encontrado en disco: {rom_path}", {"package_kind": "missing"}

        if rom_path.stat().st_size <= 0:
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

        # Prohibir explícitamente que una ROM de otra carpeta de consolación retro (assets_omnidash/playable_roms/)
        # se haga pasar por un título moderno de otra plataforma
        resolved_str = str(rom_path.resolve()).replace("\\", "/")
        if "/assets_omnidash/playable_roms/" in resolved_str:
            return (
                False,
                f"Asociación cruzada bloqueada: '{rom_path.name}' pertenece al repositorio retro auxiliar y no al paquete oficial de '{title}' ({gid}).",
                {"package_kind": "cross_game_substitution"},
            )

        # Verificar si es contenedor CCI_PKG_V2
        manifest = cls.inspect_cci_container(rom_path)
        if manifest is not None:
            m_gid = str(manifest.get("game_id") or "")
            m_plat = str(manifest.get("platform_key") or "")
            if m_gid != gid:
                return (
                    False,
                    f"Contenedor pertenece a otro game_id ('{m_gid}' != '{gid}').",
                    {"package_kind": "mismatched_container", "manifest": manifest},
                )
            if m_plat and platform_key and m_plat != platform_key:
                return (
                    False,
                    f"Plataforma del contenedor ('{m_plat}') no coincide con '{platform_key}'.",
                    {"package_kind": "mismatched_platform", "manifest": manifest},
                )
            return (
                True,
                f"Contenedor local verificado para '{title}' ({gid}).",
                {"package_kind": "cci_container", "manifest": manifest},
            )

        # Si es imagen .cue, comprobar integridad de todas las pistas .bin
        if ext == ".cue":
            cue_ok, cue_msg = ROMMetadataExtractor.verify_cue_bin_integrity(rom_path)
            if not cue_ok:
                return False, f"Error de integridad CUE/BIN: {cue_msg}", {"package_kind": "corrupted_cue"}

        # Verificar coincidencia de identidad (expected_rom o título normalizado)
        if expected_rom and Path(expected_rom).name.lower() == rom_path.name.lower():
            return (
                True,
                f"Paquete binario oficial verificado por nombre esperado ({rom_path.name}).",
                {"package_kind": "native_rom", "matched_by": "expected_rom"},
            )

        clean_title = ROMMetadataExtractor.clean_display_title(title)
        title_norm = normalize_identity_token(clean_title)
        stem_norm = normalize_identity_token(ROMMetadataExtractor.clean_display_title(rom_path.stem))
        raw_stem_norm = normalize_identity_token(rom_path.stem)

        # Palabras significativas del título (>= 3 caracteres)
        title_words = [
            w for w in re.split(r"[^a-z0-9]+", clean_title.lower())
            if len(w) >= 3 and w not in ("the", "and", "for", "edition", "deluxe", "pack", "game")
        ]
        matched_words = [w for w in title_words if w in raw_stem_norm]

        identity_ok = False
        if title_norm and (title_norm in stem_norm or stem_norm in title_norm or title_norm in raw_stem_norm):
            identity_ok = True
        elif title_words and len(matched_words) >= max(1, (len(title_words) + 1) // 2):
            identity_ok = True

        if not identity_ok:
            return (
                False,
                f"El archivo '{rom_path.name}' no coincide con la identidad esperada del título '{title}' ({gid}).",
                {"package_kind": "identity_mismatch"},
            )

        # Verificar que un título con variante específica (ej. XCI vs NSP) no colisione
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

        return (
            True,
            f"Paquete binario nativo verificado para '{title}' ({rom_path.name}).",
            {"package_kind": "native_rom", "matched_by": "title_identity"},
        )

    @classmethod
    def audit_entire_catalog(cls, scanner: Any = None) -> dict[str, Any]:
        """Ejecuta el Plan de Auditoría Automatizada (Sección 9 y 10) sobre las 90 fichas y los juegos instalados."""
        from backend.games.scanner_service import GameLibraryScannerService

        svc = scanner or GameLibraryScannerService.get_instance()
        games = svc.get_games()

        # 1. Detectar posibles IDs duplicados y uso compartido de archivos ROM
        seen_ids: set[str] = set()
        duplicate_ids: list[str] = []
        rom_to_ids: dict[str, list[str]] = {}

        for g in games:
            gid = str(g.get("id") or "")
            if gid in seen_ids:
                duplicate_ids.append(gid)
            seen_ids.add(gid)
            rom_val = g.get("rom")
            if rom_val and not g.get("on_demand"):
                rom_abs = str((svc.root_dir / rom_val).resolve()) if not Path(rom_val).is_absolute() else str(Path(rom_val).resolve())
                rom_to_ids.setdefault(rom_abs, []).append(gid)

        shared_rom_map = {k: v for k, v in rom_to_ids.items() if len(v) > 1}

        entries_report: list[dict[str, Any]] = []
        counts = {
            "VERIFIED_PLAYABLE": 0,
            "INSTALLED_CONTAINER": 0,
            "INSTALLED_NEEDS_EMULATOR": 0,
            "DOWNLOADABLE_CLOUD": 0,
            "UNSUPPORTED_PLATFORM": 0,
            "INVALID_ASSOCIATION": 0,
        }

        for g in games:
            gid = str(g.get("id") or "")
            title = str(g.get("title") or "")
            plat_key = str(g.get("platform_key") or "ps3")
            spec = svc.PLATFORM_SPECS.get(plat_key, {})
            allowed_exts = spec.get("extensions", [])
            core = g.get("core")
            rom_val = g.get("rom")
            on_demand = bool(g.get("on_demand", False))

            # Verificar disponibilidad del emulador requerido
            emu_available = False
            emu_binary = None
            if core:
                if str(core).startswith("external:"):
                    resolved_emu = svc.resolve_external_emulator(str(core))
                    if resolved_emu:
                        emu_available = True
                        emu_binary = resolved_emu[1]
                else:
                    cp = svc.root_dir / str(core)
                    if cp.exists():
                        emu_available = True
                        emu_binary = str(cp)

            if on_demand or not rom_val:
                if plat_key in ("ps5", "switch2") or not core:
                    status = "UNSUPPORTED_PLATFORM"
                    reason = f"Título en catálogo remoto para {g.get('console')}; aún no existe emulador comercial estable."
                else:
                    status = "DOWNLOADABLE_CLOUD"
                    reason = f"Disponible para descarga/instalación en roms/{plat_key}/."
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
                    "identity_valid": True,
                    "emulator_spec": core,
                    "emulator_available": emu_available,
                    "emulator_binary": emu_binary,
                    "unique_association": True,
                    "shared_with": [],
                    "status": status,
                    "reason": reason,
                    "source_url": cls.get_source_url(gid),
                })
                continue

            rom_path = Path(rom_val) if Path(rom_val).is_absolute() else (svc.root_dir / rom_val)
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

            if not id_ok or not unique_assoc:
                status = "INVALID_ASSOCIATION"
                reason = id_msg if not id_ok else f"Archivo compartido indebidamente con: {shared_with}"
            elif id_meta.get("package_kind") == "cci_container":
                status = "INSTALLED_CONTAINER"
                reason = id_msg
            elif not core:
                status = "UNSUPPORTED_PLATFORM"
                reason = f"Paquete presente, pero {g.get('console')} no dispone de emulador comercial estable."
            elif not emu_available:
                status = "INSTALLED_NEEDS_EMULATOR"
                reason = f"Paquete verificado ({rom_path.name}), pero falta instalar el emulador {core} en el sistema."
            else:
                status = "VERIFIED_PLAYABLE"
                reason = f"Paquete nativo ({rom_path.name}) y emulador ({Path(emu_binary).name}) verificados."

            counts[status] += 1
            entries_report.append({
                "game_id": gid,
                "title": title,
                "platform_key": plat_key,
                "console": g.get("console"),
                "badge": g.get("badge"),
                "installed": True,
                "file_path": str(rom_val),
                "file_exists": rom_path.exists(),
                "identity_valid": id_ok,
                "package_kind": id_meta.get("package_kind"),
                "emulator_spec": core,
                "emulator_available": emu_available,
                "emulator_binary": emu_binary,
                "unique_association": unique_assoc,
                "shared_with": shared_with,
                "status": status,
                "reason": reason,
                "source_url": cls.get_source_url(gid),
            })

        return {
            "total_catalog_games": len(games),
            "duplicate_ids": duplicate_ids,
            "shared_roms": shared_rom_map,
            "status_counts": counts,
            "all_associations_valid": (len(duplicate_ids) == 0 and len(shared_rom_map) == 0 and counts["INVALID_ASSOCIATION"] == 0),
            "entries": entries_report,
        }
