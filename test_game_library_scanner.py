"""test_game_library_scanner.py - Suite de Pruebas Automatizadas para GameLibraryScannerService.
Verifica escaneo de biblioteca, integridad, deduplicación, metadatos y ausencia de URLs no autorizadas.
100% Python estándar con unittest.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import unittest
from pathlib import Path

from backend.games.scanner_service import GameLibraryScannerService
from backend.games.rom_metadata import ROMMetadataExtractor
from omnidash_screens import ALL_GAMES, load_all_games


class TestGameLibraryScannerService(unittest.TestCase):
    def setUp(self):
        self.service = GameLibraryScannerService.get_instance()

    def test_01_singleton_instance(self):
        inst1 = GameLibraryScannerService.get_instance()
        inst2 = GameLibraryScannerService.get_instance()
        self.assertIs(inst1, inst2, "GameLibraryScannerService debe ser Singleton.")

    def test_02_catalog_count_and_parity(self):
        games = self.service.get_games()
        self.assertGreaterEqual(len(games), 69, "El catálogo debe contener al menos 69 juegos.")
        self.assertEqual(len(games), len(ALL_GAMES), "Paridad 1:1 requerida con ALL_GAMES.")

    def test_03_contract_structure(self):
        required_keys = {"id", "title", "console", "badge", "core", "rom", "cover", "year", "desc", "installed"}
        for g in self.service.get_games():
            missing = required_keys - set(g.keys())
            self.assertEqual(missing, set(), f"Juego {g.get('id')} carece de claves obligatorias: {missing}")
            self.assertTrue(isinstance(g["id"], str) and g["id"], "ID debe ser string no vacío.")
            self.assertTrue(isinstance(g["title"], str) and g["title"], "Title debe ser string no vacío.")

    def test_04_no_unauthorized_download_urls(self):
        for g in self.service.get_games():
            self.assertNotIn("download_url", g, f"Juego {g.get('id')} contiene 'download_url' no autorizada.")
            for val in g.values():
                if isinstance(val, str):
                    self.assertNotIn("retrostic", val.lower(), f"Juego {g.get('id')} tiene URL externa no autorizada: {val}")

    def test_05_installed_games_physical_verification(self):
        # Metal Slug 2 (Arcade MAME)
        ok, msg = self.service.verify_game_file("mame_mslug2")
        self.assertTrue(ok, f"mame_mslug2 debe estar verificado: {msg}")

        # Super Mario World 2 - Yoshi's Island (SNES)
        ok_yoshi, msg_yoshi = self.service.verify_game_file("snes_Super Mario World 2 - Yoshi's Island (U) (V1.1)")
        self.assertTrue(ok_yoshi, f"Yoshi's Island debe estar verificado: {msg_yoshi}")

    def test_06_on_demand_vault_integrity(self):
        gow = self.service.get_game_by_id("gow_ps2_1")
        self.assertIsNotNone(gow, "God of War PS2 debe estar en el catálogo On-Demand.")
        self.assertTrue(gow.get("on_demand"), "Debe tener bandera on_demand=True.")
        self.assertFalse(gow.get("installed"), "Debe tener bandera installed=False.")
        self.assertEqual(gow.get("vault_status"), "authorized", "Debe pertenecer a la bóveda autorizada.")

        # Verificar que verify_game_file rechace ejecución directa si no está instalado
        ok, msg = self.service.verify_game_file("gow_ps2_1")
        self.assertFalse(ok, "Juego On-Demand sin instalar no debe verificar como ejecutable.")
        self.assertIn("On-Demand", msg)

    def test_07_metadata_clean_title(self):
        raw = "0168 - Mario Kart DS (U)(SCZ)"
        cleaned = ROMMetadataExtractor.clean_display_title(raw)
        self.assertEqual(cleaned, "Mario Kart DS")

        raw_snes = "Super Mario World 2 - Yoshi's Island (U) (V1.1) [!]"
        cleaned_snes = ROMMetadataExtractor.clean_display_title(raw_snes)
        self.assertEqual(cleaned_snes, "Super Mario World 2 - Yoshi's Island")

    def test_08_ps1_cue_integrity_validator(self):
        cue_path = Path("roms/ps1/Castlevania - Symphony of the Night (USA).cue")
        if cue_path.exists():
            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(cue_path)
            self.assertTrue(ok, f"Castlevania CUE debe ser íntegro: {msg}")

    def test_09_hot_refresh_stability(self):
        before = len(self.service.get_games())
        refreshed = self.service.refresh()
        self.assertEqual(before, len(refreshed), "Refresh en caliente debe ser estable y consistente.")

    def test_10_sqlite_sync(self):
        count = self.service.sync_to_sqlite()
        self.assertGreaterEqual(count, 69, "Debe sincronizar al menos 69 juegos a SQLite.")


if __name__ == "__main__":
    unittest.main()
