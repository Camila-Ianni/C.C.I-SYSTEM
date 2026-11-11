"""test_catalog_integrity_audit.py - Pruebas Automáticas de los Criterios de Aceptación de la Auditoría Técnica (Sección 10).

Verifica:
1. Ningún game_id puede resolver a una ROM de otro título (_EXACT_GAME_MAP, _PLAYSTATION_3D_ISO_MAP y _NATIVE_MACOS_APP_MAP vacíos).
2. Si el juego no está instalado, el sistema informa que no está instalado y NO inicia otro juego (sin fallback a Crash Bandicoot).
3. Si la plataforma o el emulador no son compatibles, el lanzamiento se bloquea con un mensaje claro.
4. Cada juego instalado tiene una asociación única y trazable entre ficha, paquete y emulador.
5. Las pruebas automáticas detectan IDs duplicados, archivos compartidos incorrectamente, variantes XCI/NSP cruzadas y fallbacks inseguros.
6. Las pruebas de ejecución controlada se registran por separado de las validaciones estáticas.
7. Los datos de progreso (progress_pct) no se incrementan artificialmente a partir del tiempo transcurrido sin evidencia real del juego.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import modern_game_runner
from backend.games.modern_catalog import MODERN_GAMES_CATALOG
from backend.games.package_validator import CATALOG_SOURCE_URLS, ROMPackageIdentityValidator
from backend.games.scanner_service import GameLibraryScannerService
from backend.games.storage_manager import GameStorageManager


def _create_isolated_env(tmp_path: Path) -> tuple[GameLibraryScannerService, GameStorageManager]:
    (tmp_path / "fotos juegos").mkdir(parents=True, exist_ok=True)
    for pk in ("ps5", "ps4", "switch", "switch2", "ps3", "ps2", "ps1"):
        (tmp_path / "roms" / pk).mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "cci_audit.db"
    scanner = GameLibraryScannerService(root_dir=tmp_path)
    storage = GameStorageManager(root_dir=tmp_path, db_path=db_path)
    return scanner, storage


class TestCatalogIntegrityAudit(unittest.TestCase):
    def test_01_no_silent_substitutions_or_fallback_maps(self):
        """P0: _EXACT_GAME_MAP, _PLAYSTATION_3D_ISO_MAP y _NATIVE_MACOS_APP_MAP deben estar vacíos."""
        self.assertEqual(modern_game_runner._EXACT_GAME_MAP, {})
        self.assertEqual(modern_game_runner._PLAYSTATION_3D_ISO_MAP, {})
        self.assertEqual(modern_game_runner._NATIVE_MACOS_APP_MAP, {})
        self.assertEqual(len(MODERN_GAMES_CATALOG), 90)
        self.assertEqual(len(CATALOG_SOURCE_URLS), 90)

    def test_02_uninstalled_game_blocks_launch_without_fallback_to_crash_bandicoot(self):
        """P0: Si un juego no está instalado (ej. Bratz: Rhythm and Style XCI), devuelve error controlado y jamás abre otro juego."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            scanner, _ = _create_isolated_env(tmp_path)
            GameLibraryScannerService._instance = scanner
            try:
                engine, rom, msg = modern_game_runner.resolve_playable_engine(
                    game_id="switch_bratz_rhythm_and_style_xci",
                    title="Bratz: Rhythm and Style (XCI)",
                    root_dir=tmp_path,
                )
                self.assertIsNone(engine)
                self.assertIsNone(rom)
                self.assertIn("Juego no instalado", msg)

                rc = modern_game_runner.run_modern_game(
                    game_id="switch_bratz_rhythm_and_style_xci",
                    title="Bratz: Rhythm and Style (XCI)",
                    console_name="Nintendo Switch",
                    badge="SWITCH",
                    genre="Moda / Ritmo",
                    cover_rel="",
                    rom_path="",
                    max_frames=5,
                    root_dir=tmp_path,
                )
                self.assertEqual(rc, 2, "Debe retornar código de bloqueo controlado (2) sin ejecutar ningún otro juego.")
            finally:
                GameLibraryScannerService._instance = None

    def test_03_cross_game_substitution_and_format_variant_mismatch_rejected(self):
        """P1: Intentar asociar una ROM de DS o un archivo de otro título / formato XCI vs NSP es rechazado."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            # 1. Intentar pasar una ROM de otro juego ("Mario Kart DS.xci") para Bratz: Rhythm and Style (XCI)
            wrong_file = tmp_path / "Mario Kart DS.xci"
            wrong_file.write_bytes(b"XCI_DATA" * 1024)
            ok_wrong, msg_wrong, meta_wrong = ROMPackageIdentityValidator.verify_package_identity(
                game_id="switch_bratz_rhythm_and_style_xci",
                title="Bratz: Rhythm and Style (XCI)",
                platform_key="switch",
                rom_path=wrong_file,
                allowed_extensions=[".nsp", ".xci", ".rar", ".zip"],
            )
            self.assertFalse(ok_wrong)
            self.assertEqual(meta_wrong["package_kind"], "identity_mismatch")
            self.assertIn("no coincide con la identidad", msg_wrong)

            # 2. Intentar pasar un archivo .nsp para la edición (XCI) de Bratz: Rhythm and Style
            wrong_fmt = tmp_path / "Bratz Rhythm and Style.nsp"
            wrong_fmt.write_bytes(b"NSP_DATA" * 1024)
            ok_fmt, msg_fmt, meta_fmt = ROMPackageIdentityValidator.verify_package_identity(
                game_id="switch_bratz_rhythm_and_style_xci",
                title="Bratz: Rhythm and Style (XCI)",
                platform_key="switch",
                rom_path=wrong_fmt,
                allowed_extensions=[".nsp", ".xci", ".rar", ".zip"],
            )
            self.assertFalse(ok_fmt)
            self.assertEqual(meta_fmt["package_kind"], "format_variant_mismatch")
            self.assertIn("XCI", msg_fmt)

            # 3. Archivo .xci con identidad exacta sí es aceptado para la edición XCI
            valid_xci = tmp_path / "Bratz Rhythm and Style.xci"
            valid_xci.write_bytes(b"XCI_DATA" * 1024)
            ok_valid, _, meta_valid = ROMPackageIdentityValidator.verify_package_identity(
                game_id="switch_bratz_rhythm_and_style_xci",
                title="Bratz: Rhythm and Style (XCI)",
                platform_key="switch",
                rom_path=valid_xci,
                allowed_extensions=[".nsp", ".xci", ".rar", ".zip"],
            )
            self.assertTrue(ok_valid)
            self.assertEqual(meta_valid["package_kind"], "native_rom")

    def test_04_unsupported_platform_and_missing_emulator_blocked_explicitly(self):
        """P1: Títulos de plataformas sin emulador (PS5 / Switch 2) o sin shadPS4 bloquean el lanzamiento con motivo claro."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            scanner, _ = _create_isolated_env(tmp_path)
            # Colocar paquete PS5 con nombre válido
            ps5_pkg = tmp_path / "roms" / "ps5" / "God of War Ragnarok.pkg"
            ps5_pkg.write_bytes(b"PS5_PKG_BINARY_" * 2048)
            scanner.refresh()

            GameLibraryScannerService._instance = scanner
            try:
                engine, rom, msg = modern_game_runner.resolve_playable_engine(
                    game_id="ps5_god_of_war_ragnarok",
                    title="God of War Ragnarök",
                    root_dir=tmp_path,
                )
                self.assertIsNone(engine)
                self.assertIsNone(rom)
                self.assertIn("no dispone de emulador comercial estable", msg)
            finally:
                GameLibraryScannerService._instance = None

    def test_05_telemetry_does_not_fabricate_progress_pct_from_elapsed_time(self):
        """P2: Registrar tiempo de sesión sin porcentaje explícito jamás incrementa progress_pct artificialmente."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _, storage = _create_isolated_env(tmp_path)

            storage.record_progress(
                game_id="ps1_resident_evil_3_nemesis",
                title="Resident Evil 3: Nemesis",
                last_played="Hoy",
                play_time_delta_s=1800,
                progress_pct=None,
            )
            prog = storage.get_progress("ps1_resident_evil_3_nemesis")
            self.assertEqual(prog["play_time_seconds"], 1800)
            self.assertEqual(prog["progress_pct"], 0, "El progreso no debe inventarse a partir del tiempo de sesión.")

    def test_06_full_catalog_static_audit_and_controlled_execution(self):
        """Sección 9 y 10: Auditoría completa de los 90 títulos del catálogo + prueba controlada de ejecución real."""
        GameLibraryScannerService._instance = None
        scanner = GameLibraryScannerService.get_instance()
        scanner.refresh()

        report = ROMPackageIdentityValidator.audit_entire_catalog(scanner=scanner)
        self.assertEqual(report["total_catalog_games"], 90)
        self.assertEqual(report["duplicate_ids"], [])
        self.assertEqual(report["shared_roms"], {})
        self.assertTrue(report["all_associations_valid"], f"Asociaciones inválidas detectadas: {report['status_counts']}")

        # Ejecución controlada separada de la validación estática para Resident Evil 3: Nemesis (PS1) instalado en roms/ps1/
        re3 = scanner.get_game_by_id("ps1_resident_evil_3_nemesis")
        self.assertIsNotNone(re3)
        if re3 and re3.get("installed") and not re3.get("on_demand"):
            rc = modern_game_runner.run_modern_game(
                game_id="ps1_resident_evil_3_nemesis",
                title=re3["title"],
                console_name=re3["console"],
                badge=re3["badge"],
                genre=re3.get("genre", ""),
                cover_rel=re3.get("cover", ""),
                rom_path=re3["rom"],
                max_frames=10,
            )
            self.assertEqual(rc, 0, "Resident Evil 3: Nemesis (PS1) real debe iniciar y cerrar con código 0.")


if __name__ == "__main__":
    unittest.main()
