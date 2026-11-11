"""test_game_storage_lifecycle.py - Pruebas del ciclo estilo PS5 de almacenamiento, desinstalación y preservación de progreso.

Verifica:
1. Un juego instalado (ej. Minecraft PS3 o Just Dance 2025 Edition tras importar su paquete) registra progreso y partidas guardadas en saves/games/<id>/ + SQLite game_progress.
2. Al desinstalar el juego para liberar espacio en disco, el archivo ROM pesado se elimina de roms/<plat>/ pero:
   - El juego sigue apareciendo en el catálogo (on_demand=True, installed=False).
   - Sus archivos de partida guardada en saves/games/<id>/ y su registro en SQLite (tiempo jugado, porcentaje, slots) quedan 100% intactos.
3. Si el usuario intenta instalar otro juego sin suficiente espacio disponible, el gestor bloquea la instalación e informa cuánto espacio falta; al desinstalar un juego previo, el espacio se libera y permite instalar el nuevo.
4. Al volver a instalar un juego previamente desinstalado, recupera automáticamente todo su progreso y slots guardados.
5. La interfaz Qt (LibraryView, GameDetailsView, StorageManagerDialog) refleja en vivo los estados Instalado / En la nube con Progreso conservado, botones de Instalar/Liberar espacio y métricas reales.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from backend.games.scanner_service import GameLibraryScannerService
from backend.games.storage_manager import GameStorageManager


def _create_isolated_env(tmp_path: Path) -> tuple[GameLibraryScannerService, GameStorageManager]:
    """Crea un entorno aislado con carpeta roms/, saves/games/ y SQLite propio."""
    (tmp_path / "fotos juegos").mkdir(parents=True, exist_ok=True)
    for pk in ("ps5", "ps4", "switch", "ps3", "ps2", "ps1"):
        (tmp_path / "roms" / pk).mkdir(parents=True, exist_ok=True)
    db_path = tmp_path / "cci_console.db"
    scanner = GameLibraryScannerService(root_dir=tmp_path)
    storage = GameStorageManager(root_dir=tmp_path, db_path=db_path)
    return scanner, storage


class TestGameStorageLifecycle(unittest.TestCase):
    def test_uninstall_frees_space_while_preserving_progress_and_catalog_presence(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            scanner, storage = _create_isolated_env(tmp_path)

            # 1. Instalar Just Dance 2025 Edition (Switch) desde un paquete local simulado
            pkg = tmp_path / "downloads" / "Just Dance 2025 Edition.nsp"
            pkg.parent.mkdir(parents=True, exist_ok=True)
            pkg.write_bytes(b"NSP_HEADER_PAYLOAD_" * 2048)

            ok, msg, installed_entry = storage.install_local_package("switch_just_dance_2025_edition", pkg, scanner=scanner)
            self.assertTrue(ok, msg)
            self.assertTrue(installed_entry["installed"])
            self.assertFalse(installed_entry["on_demand"])
            rom_file = tmp_path / installed_entry["rom"]
            self.assertTrue(rom_file.exists())
            expected_bytes = rom_file.stat().st_size

            # 2. Registrar progreso del jugador (2h 15m jugados, 45% completado y 2 slots de guardado reales en disco)
            storage.record_progress(
                game_id="switch_just_dance_2025_edition",
                title="Just Dance 2025 Edition",
                last_played="Hoy",
                play_time_delta_s=8100,
                progress_pct=45,
                slot_name="profile_save_01.sav",
                slot_bytes=b"JD2025_HIGHSCORE_DATA_SLOT_1",
            )
            storage.record_progress(
                game_id="switch_just_dance_2025_edition",
                title="Just Dance 2025 Edition",
                slot_name="unlocks_save_02.sav",
                slot_bytes=b"JD2025_UNLOCKED_SONGS_SLOT_2",
            )

            prog_before = storage.get_progress("switch_just_dance_2025_edition")
            self.assertTrue(prog_before["has_progress"])
            self.assertEqual(prog_before["save_slots"], 2)
            self.assertEqual(prog_before["play_time_seconds"], 8100)
            self.assertEqual(prog_before["progress_pct"], 45)

            # 3. Desinstalar el juego para liberar espacio (como en PS4/PS5)
            ok_un, msg_un, uninstalled_entry = storage.uninstall_game("switch_just_dance_2025_edition", scanner=scanner)
            self.assertTrue(ok_un, msg_un)
            self.assertIn("Conservado intacto", msg_un)
            self.assertFalse(rom_file.exists(), "El binario ROM debe eliminarse del disco al desinstalar")

            # 4. El juego sigue en el catálogo (En la nube) pero conserva todo su progreso y archivos de guardado
            self.assertFalse(uninstalled_entry["installed"])
            self.assertTrue(uninstalled_entry["on_demand"])

            save_dir = storage.game_save_dir("switch_just_dance_2025_edition")
            self.assertEqual((save_dir / "profile_save_01.sav").read_bytes(), b"JD2025_HIGHSCORE_DATA_SLOT_1")
            self.assertEqual((save_dir / "unlocks_save_02.sav").read_bytes(), b"JD2025_UNLOCKED_SONGS_SLOT_2")

            prog_after = storage.get_progress("switch_just_dance_2025_edition")
            self.assertTrue(prog_after["has_progress"])
            self.assertEqual(prog_after["save_slots"], 2)
            self.assertEqual(prog_after["play_time_seconds"], 8100)
            self.assertEqual(prog_after["progress_pct"], 45)
            self.assertEqual(prog_after["last_uninstalled_bytes"], expected_bytes)

    def test_storage_limit_blocks_install_until_space_is_freed_and_reinstall_restores_progress(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            scanner, storage = _create_isolated_env(tmp_path)

            # Instalar Juego A (Minecraft Switch - 50 KB simulados) con progreso guardado
            pkg_mc = tmp_path / "downloads" / "Minecraft_Switch.nsp"
            pkg_mc.parent.mkdir(parents=True, exist_ok=True)
            pkg_mc.write_bytes(b"M" * 50_000)

            ok_a, _, _ = storage.install_local_package("switch_minecraft", pkg_mc, scanner=scanner)
            self.assertTrue(ok_a)
            storage.record_progress(
                game_id="switch_minecraft",
                title="Minecraft",
                play_time_delta_s=3600,
                progress_pct=30,
                slot_name="world_survival.dat",
                slot_bytes=b"MINECRAFT_WORLD_SEED_999",
            )

            # Intentar instalar Juego B (Just Dance 2025 - 80 KB) cuando solo quedan 20 KB libres simulados
            pkg_jd = tmp_path / "downloads" / "Just_Dance_2025.nsp"
            pkg_jd.write_bytes(b"J" * 80_000)

            ok_b_fail, msg_b_fail, _ = storage.install_local_package(
                "switch_just_dance_2025_edition",
                pkg_jd,
                scanner=scanner,
                free_override_bytes=20_000,
            )
            self.assertFalse(ok_b_fail)
            self.assertIn("Espacio insuficiente", msg_b_fail)

            # Desinstalar Juego A (Minecraft Switch) para liberar espacio sin perder el mundo guardado
            ok_un, _, _ = storage.uninstall_game("switch_minecraft", scanner=scanner)
            self.assertTrue(ok_un)

            # Ahora con espacio suficiente (100 KB libres), instalar Juego B funciona
            ok_b_ok, _, entry_b = storage.install_local_package(
                "switch_just_dance_2025_edition",
                pkg_jd,
                scanner=scanner,
                free_override_bytes=100_000,
            )
            self.assertTrue(ok_b_ok)
            self.assertTrue(entry_b["installed"])

            # Más adelante, reinstalar Juego A (Minecraft Switch) restaura su progreso (30%, 1h 0m y world_survival.dat)
            ok_re, msg_re, entry_mc_re = storage.install_local_package(
                "switch_minecraft",
                pkg_mc,
                scanner=scanner,
                free_override_bytes=100_000,
            )
            self.assertTrue(ok_re)
            self.assertIn("Progreso previo detectado y restaurado", msg_re)
            self.assertTrue(entry_mc_re["installed"])
            prog_mc = storage.get_progress("switch_minecraft")
            self.assertEqual(prog_mc["save_slots"], 1)
            self.assertEqual(prog_mc["progress_pct"], 30)
            self.assertEqual(prog_mc["play_time_label"], "1h 0m")

    def test_qt_game_details_and_storage_manager_buttons(self):
        from PySide6.QtWidgets import QApplication
        import omnidash_qt

        app = QApplication.instance() or QApplication([])
        details = omnidash_qt.GameDetailsView()

        # Cargar un juego instalado (Minecraft PS3)
        scanner = GameLibraryScannerService.get_instance()
        mc_ps3 = scanner.get_game_by_id("ps3_minecraft")
        self.assertIsNotNone(mc_ps3)
        self.assertTrue(mc_ps3["installed"])

        details.load_game(mc_ps3)
        self.assertFalse(details.uninstall_btn.isHidden())
        self.assertTrue(details.install_pkg_btn.isHidden())
        self.assertIn("JUGAR", details.play_btn.text())

        # Cargar un juego en la nube (Just Dance 2025 Edition)
        jd_2025 = scanner.get_game_by_id("switch_just_dance_2025_edition")
        self.assertIsNotNone(jd_2025)
        self.assertTrue(jd_2025["on_demand"])

        details.load_game(jd_2025)
        self.assertTrue(details.uninstall_btn.isHidden())
        self.assertFalse(details.install_pkg_btn.isHidden())
        self.assertIn("397.0 MB", details.play_btn.text())

        # Verificar que el diálogo de Gestión de Almacenamiento enumera los juegos instalados
        dlg = omnidash_qt.StorageManagerDialog()
        self.assertIn("Juegos instalados:", dlg.summary_lbl.text())
        dlg.close()
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
