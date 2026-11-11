"""test_game_library_scanner.py - Suite Completa de Pruebas Unitarias para GameLibraryScannerService.
Valida arquitectura no invasiva, escaneo asíncrono, metadatos, deduplicación, SQLite y aislamiento con fixtures.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from backend.games.scanner_service import GameLibraryScannerService
from backend.games.rom_metadata import ROMMetadataExtractor
from omnidash_screens import ALL_GAMES


class TestGameLibraryScannerService(unittest.TestCase):
    def setUp(self):
        self.service = GameLibraryScannerService.get_instance()

    def test_01_singleton_instance(self):
        inst1 = GameLibraryScannerService.get_instance()
        inst2 = GameLibraryScannerService.get_instance()
        self.assertIs(inst1, inst2, "GameLibraryScannerService debe ser Singleton.")

    def test_02_catalog_count_and_contract(self):
        games = self.service.get_games()
        # En checkout limpio de CI existen 36 ROMs versionadas + 14 metadatos remotos (>= 50);
        # en entorno local completo con ROMs ignoradas supera los 69 títulos.
        self.assertGreaterEqual(len(games), 50, "El catálogo debe contener al menos 50 juegos.")
        self.assertEqual(len(games), len(ALL_GAMES), "Paridad requerida con ALL_GAMES.")

        required_keys = {"id", "title", "console", "badge", "core", "rom", "cover", "year", "desc", "installed"}
        for g in games:
            missing = required_keys - set(g.keys())
            self.assertEqual(missing, set(), f"Juego {g.get('id')} carece de claves requeridas: {missing}")
            self.assertTrue(g["id"] and isinstance(g["id"], str))
            self.assertTrue(g["title"] and isinstance(g["title"], str))

    def test_03_no_unauthorized_download_urls_and_neutral_catalog(self):
        for g in self.service.get_games():
            self.assertNotIn("download_url", g, f"Juego {g.get('id')} contiene 'download_url' no autorizada.")
            for val in g.values():
                if isinstance(val, str):
                    self.assertNotIn("retrostic", val.lower(), f"Encontrado enlace de terceros: {val}")
            if g.get("on_demand"):
                self.assertNotIn("vault_status", g, "No deben emplearse claims de autorización legal no probados.")
                self.assertEqual(g.get("catalog_type"), "remote_metadata")

    def test_04_header_extractors_integration(self):
        # Verificar que los metadatos de cabecera fueron llamados e integrados
        games = self.service.get_games()
        installed_snes = [g for g in games if g.get("badge") == "SNES" and g.get("installed")]
        self.assertTrue(len(installed_snes) > 0)
        has_internal_title = any(g.get("internal_title") for g in installed_snes)
        self.assertTrue(has_internal_title, "Debe existir al menos un título interno extraído por cabecera.")

        # Limpieza de títulos
        raw = "0168 - Mario Kart DS (U)(SCZ) [!]"
        cleaned = ROMMetadataExtractor.clean_display_title(raw)
        self.assertEqual(cleaned, "Mario Kart DS")
        reg, rev = ROMMetadataExtractor.extract_region_and_revision(raw)
        self.assertEqual(reg, "USA")

    def test_05_dynamic_directory_and_scan_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            snes_dir = tmp_path / "snes"
            snes_dir.mkdir(parents=True)

            # Crear ROM ficticia con cabecera mínima SNES
            mock_rom = snes_dir / "Super Test Adventure (USA).sfc"
            dummy_data = bytearray(0x8000)
            # Título interno en LoROM offset 0x7FC0
            dummy_data[0x7FC0 : 0x7FD5] = b"SUPER TEST ADVENTURE"
            mock_rom.write_bytes(dummy_data)

            # Probar registrar directorio configurable
            added = self.service.add_scan_directory(tmp_path)
            self.assertTrue(added, "add_scan_directory debe aceptar directorio válido.")
            self.assertIn(str(tmp_path.resolve()), self.service.get_scan_directories())

            # Escanear
            scanned = self.service.scan_all()
            found = [g for g in scanned if "super test adventure" in g.get("title", "").lower()]
            self.assertTrue(len(found) >= 1, "El scanner debe detectar la ROM del directorio temporal.")

            # Limpiar directorio configurable
            removed = self.service.remove_scan_directory(tmp_path)
            self.assertTrue(removed)

    def test_06_non_destructive_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            snes_dir = tmp_path / "snes"
            snes_dir.mkdir(parents=True)

            # Mismo juego en dos regiones diferentes (USA y Europe)
            rom_us = snes_dir / "Chrono Game (USA).sfc"
            rom_eu = snes_dir / "Chrono Game (Europe).sfc"
            rom_us.write_bytes(b"\x00" * 1024)
            rom_eu.write_bytes(b"\x00" * 1024)

            self.service.add_scan_directory(tmp_path)
            scanned = self.service.scan_all()

            chrono_games = [g for g in scanned if "chrono game" in g.get("title", "").lower()]
            # No deben ser fusionados destructivamente si tienen diferente región
            self.assertEqual(len(chrono_games), 2, "Variantes regionales deben preservarse.")
            self.service.remove_scan_directory(tmp_path)

    def test_07_cue_bin_missing_file_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cue_file = tmp_path / "Corrupted.cue"
            cue_file.write_text('FILE "MissingTrack01.bin" BINARY\n  TRACK 01 MODE2/2352\n', encoding="utf-8")

            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(cue_file)
            self.assertFalse(ok, "CUE con archivo BIN faltante debe fallar la verificación.")
            self.assertIn("MissingTrack01.bin", msg)

    def test_08_async_scan_worker(self):
        completed_signal = []
        progress_signal = []

        def on_prog(done, total, name):
            progress_signal.append((done, total))

        def on_comp(games):
            completed_signal.append(len(games))

        self.service.scan_async(on_progress=on_prog, on_complete=on_comp)

        # Esperar al hilo en segundo plano con timeout seguro
        t0 = time.time()
        while not completed_signal and time.time() - t0 < 5.0:
            time.sleep(0.05)

        self.assertTrue(len(completed_signal) > 0, "El escaneo asíncrono debe invocar on_complete.")
        self.assertGreaterEqual(completed_signal[0], 50)

    def test_09_sqlite_transactional_sync_and_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test_cci.sqlite3"
            count = self.service.sync_to_sqlite(db_path)
            self.assertGreaterEqual(count, 50)

            # Verificar tabla y contenido en SQLite
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM installed_roms WHERE available = 1")
                avail_count = cur.fetchone()[0]
                self.assertGreaterEqual(avail_count, 30)

                # Simular reconciliación: insertar registro obsoleto
                cur.execute("""
                    INSERT INTO installed_roms (id, title, console, badge, core, on_demand, available)
                    VALUES ('phantom_rom', 'Ghost Game', 'SNES', 'SNES', 'core.dylib', 0, 1)
                """)

            # Sincronizar de nuevo: el registro ausente debe quedar reconciliado a available=0
            self.service.sync_to_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT available FROM installed_roms WHERE id = 'phantom_rom'")
                st = cur.fetchone()[0]
                self.assertEqual(st, 0, "Registro ausente debe reconciliarse con available=0.")

    def test_10_launch_pre_verification_security(self):
        # 1. Juego físico verificado (seleccionado dinámicamente entre ROMs y cores presentes en disco/CI)
        verified_candidates = [
            g for g in self.service.get_games()
            if not g.get("on_demand")
            and g.get("rom")
            and g.get("core")
            and (self.service.root_dir / g["rom"]).exists()
            and (self.service.root_dir / g["core"]).exists()
        ]
        self.assertTrue(len(verified_candidates) > 0, "Debe existir al menos un juego físico con ROM y core en disco.")
        target = verified_candidates[0]
        ok, msg = self.service.verify_game_file(target["id"])
        self.assertTrue(ok, f"{target['title']} debe ser verificado: {msg}")

        # 2. Juego inexistente debe denegar lanzamiento
        ok_missing, _ = self.service.verify_game_file("nonexistent_game_id")
        self.assertFalse(ok_missing, "Un ID inexistente debe denegar ejecución.")

        # 3. Juego remoto sin instalar debe denegar lanzamiento directo
        gow = self.service.get_game_by_id("gow_ps2_1")
        self.assertIsNotNone(gow)
        ok_gow, msg_gow = self.service.verify_game_file("gow_ps2_1")
        self.assertFalse(ok_gow, "Juego On-Demand sin instalar debe denegar ejecución.")


if __name__ == "__main__":
    unittest.main()
