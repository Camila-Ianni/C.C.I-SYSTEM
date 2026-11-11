"""test_game_library_scanner.py - Suite Completa de Pruebas Unitarias para GameLibraryScannerService (Catálogo Moderno).
Valida arquitectura no invasiva, escaneo asíncrono, metadatos, deduplicación, SQLite y aislamiento con fixtures.
Autora: Camila Carolina Ianni
"""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from backend.games.rom_metadata import ROMMetadataExtractor
from backend.games.scanner_service import GameLibraryScannerService
from omnidash_screens import ALL_GAMES


class TestGameLibraryScannerService(unittest.TestCase):
    def setUp(self):
        self.service = GameLibraryScannerService.get_instance()
        self.service.refresh()

    def test_01_singleton_instance(self):
        inst1 = GameLibraryScannerService.get_instance()
        inst2 = GameLibraryScannerService.get_instance()
        self.assertIs(inst1, inst2, "GameLibraryScannerService debe ser Singleton.")

    def test_02_catalog_count_and_contract(self):
        games = self.service.get_games()
        self.assertGreaterEqual(len(games), 90, "El catálogo moderno debe contener los 90 títulos curados.")
        self.assertEqual(len(games), len(ALL_GAMES), "Paridad requerida con ALL_GAMES.")

        badges = {g.get("badge") for g in games}
        for req_badge in ("PS5", "PS4", "PS3", "SWITCH"):
            self.assertIn(req_badge, badges, f"Debe existir clasificación honesta para {req_badge}.")

        required_keys = {"id", "title", "console", "badge", "core", "rom", "cover", "year", "desc", "installed"}
        for g in games:
            missing = required_keys - set(g.keys())
            self.assertEqual(missing, set(), f"Juego {g.get('id')} carece de claves requeridas: {missing}")
            self.assertTrue(g["id"] and isinstance(g["id"], str))
            self.assertTrue(g["title"] and isinstance(g["title"], str))
            if g.get("cover"):
                cov_p = self.service.root_dir / g["cover"]
                self.assertTrue(cov_p.exists(), f"Falta carátula local para {g['id']}: {cov_p}")

    def test_03_no_unauthorized_download_urls_and_neutral_catalog(self):
        for g in self.service.get_games():
            self.assertNotIn("download_url", g, f"Juego {g.get('id')} contiene 'download_url' no autorizada.")
            for val in g.values():
                if isinstance(val, str):
                    self.assertNotIn("retrostic", val.lower(), f"Encontrado enlace de terceros: {val}")
            if g.get("on_demand"):
                self.assertNotIn("vault_status", g, "No deben emplearse claims de autorización legal no probados.")
                self.assertEqual(g.get("catalog_type"), "remote_metadata")

    def test_04_header_and_metadata_extractors(self):
        # Limpieza de títulos y extracción de región
        raw = "0168 - Mario Kart DS (U)(SCZ) [!]"
        self.assertEqual(ROMMetadataExtractor.clean_display_title(raw), "Mario Kart DS")
        reg, _rev = ROMMetadataExtractor.extract_region_and_revision(raw)
        self.assertEqual(reg, "USA")

        # Extractor binario sobre ROM sintética aislada
        with tempfile.TemporaryDirectory() as tmp_dir:
            mock_sfc = Path(tmp_dir) / "ModernHeaderTest.sfc"
            buf = bytearray(0x8000)
            buf[0x7FC0 : 0x7FD5] = b"MODERN TEST TITLE    "
            mock_sfc.write_bytes(buf)
            meta = ROMMetadataExtractor.extract_snes_header(mock_sfc)
            self.assertEqual(meta.get("internal_title"), "MODERN TEST TITLE")

    def test_05_dynamic_directory_and_scan_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            ps3_dir = tmp_path / "ps3"
            ps3_dir.mkdir(parents=True)

            mock_rom = ps3_dir / "Modern Custom Adventure (USA).iso"
            mock_rom.write_bytes(b"PS3ISO" + b"\x00" * 1024)

            added = self.service.add_scan_directory(tmp_path)
            self.assertTrue(added, "add_scan_directory debe aceptar directorio válido.")
            self.assertIn(str(tmp_path.resolve()), self.service.get_scan_directories())

            scanned = self.service.scan_all()
            found = [g for g in scanned if "modern custom adventure" in g.get("title", "").lower()]
            self.assertTrue(len(found) >= 1, "El scanner debe detectar la ROM del directorio temporal.")

            self.assertTrue(self.service.remove_scan_directory(tmp_path))
            self.service.refresh()

    def test_06_multi_region_variants_preserved(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            switch_dir = tmp_path / "switch"
            switch_dir.mkdir(parents=True)

            (switch_dir / "Chrono Modern (USA).nsp").write_bytes(b"\x00" * 1024)
            (switch_dir / "Chrono Modern (Europe).nsp").write_bytes(b"\x00" * 1024)

            self.service.add_scan_directory(tmp_path)
            scanned = self.service.scan_all()

            chrono_games = [g for g in scanned if "chrono modern" in g.get("title", "").lower()]
            self.assertEqual(len(chrono_games), 2, "Variantes regionales deben preservarse sin colisión.")
            self.service.remove_scan_directory(tmp_path)
            self.service.refresh()

    def test_07_cue_bin_missing_file_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            cue_file = Path(tmp_dir) / "Corrupted.cue"
            cue_file.write_text('FILE "MissingTrack01.bin" BINARY\n  TRACK 01 MODE2/2352\n', encoding="utf-8")

            ok, msg = ROMMetadataExtractor.verify_cue_bin_integrity(cue_file)
            self.assertFalse(ok, "CUE con archivo BIN faltante debe fallar la verificación.")
            self.assertIn("MissingTrack01.bin", msg)

    def test_08_async_scan_worker(self):
        completed_signal = []
        progress_signal = []

        self.service.scan_async(
            on_progress=lambda done, total, _n: progress_signal.append((done, total)),
            on_complete=lambda games: completed_signal.append(len(games)),
        )

        t0 = time.time()
        while not completed_signal and time.time() - t0 < 5.0:
            time.sleep(0.05)

        self.assertTrue(len(completed_signal) > 0, "El escaneo asíncrono debe invocar on_complete.")
        self.assertGreaterEqual(completed_signal[0], 90)

    def test_09_sqlite_transactional_sync_and_reconciliation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "test_cci.sqlite3"
            count = self.service.sync_to_sqlite(db_path)
            self.assertGreaterEqual(count, 90)

            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM installed_roms")
                total_rows = cur.fetchone()[0]
                self.assertGreaterEqual(total_rows, 90)

                cur.execute("SELECT COUNT(*) FROM installed_roms WHERE on_demand = 1")
                cloud_count = cur.fetchone()[0]
                self.assertGreaterEqual(cloud_count, 80)

                cur.execute("""
                    INSERT INTO installed_roms (id, title, console, badge, core, on_demand, available)
                    VALUES ('phantom_rom', 'Ghost Game', 'PlayStation 5', 'PS5', '', 0, 1)
                """)

            self.service.sync_to_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT available FROM installed_roms WHERE id = 'phantom_rom'")
                st = cur.fetchone()[0]
                self.assertEqual(st, 0, "Registro ausente debe reconciliarse con available=0.")

    def test_10_launch_pre_verification_security(self):
        # 1. Juego local PS3 descargado (Minecraft PlayStation 3 Edition.zip) detectado físicamente
        mc_ps3 = self.service.get_game_by_id("ps3_minecraft")
        self.assertIsNotNone(mc_ps3)
        if not mc_ps3.get("on_demand"):
            self.assertTrue((self.service.root_dir / mc_ps3["rom"]).exists())

        # 2. Fixture física con core Libretro real presente en disco debe verificar OK
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            ps1_dir = tmp_path / "ps1"
            ps1_dir.mkdir(parents=True)
            test_iso = ps1_dir / "Modern PS1 Test.iso"
            test_iso.write_bytes(b"ISO" + b"\x00" * 512)

            self.service.add_scan_directory(tmp_path)
            self.service.scan_all()
            target = next(
                (g for g in self.service.get_games() if "modern ps1 test" in g.get("title", "").lower()),
                None,
            )
            self.assertIsNotNone(target)
            ok, msg = self.service.verify_game_file(target["id"])
            if (self.service.root_dir / "cores" / "pcsx_rearmed_libretro.dylib").exists():
                self.assertTrue(ok, f"PS1 con core real debe verificar OK: {msg}")
            self.service.remove_scan_directory(tmp_path)
            self.service.refresh()

        # 3. Juego inexistente debe denegar lanzamiento
        ok_missing, _ = self.service.verify_game_file("nonexistent_game_id")
        self.assertFalse(ok_missing, "Un ID inexistente debe denegar ejecución.")

        # 4. Título PS5 pesado en la nube (>4 GB) debe reportar On-Demand sin ejecución falsa
        ragnarok = self.service.get_game_by_id("ps5_god_of_war_ragnarok")
        self.assertIsNotNone(ragnarok)
        self.assertTrue(ragnarok.get("on_demand"))
        ok_ps5, msg_ps5 = self.service.verify_game_file("ps5_god_of_war_ragnarok")
        self.assertFalse(ok_ps5, "Juego On-Demand en la nube debe denegar ejecución directa.")
        self.assertIn("PS5", msg_ps5)


if __name__ == "__main__":
    unittest.main()
