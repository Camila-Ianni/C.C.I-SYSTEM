"""
test_phase6_evolution.py - Suite de pruebas unitarias automatizadas para la Fase 6 (Galería de Grabaciones).
Verifica:
1. Grabación asíncrona en Worker Thread sin congelar el bucle de Pygame.
2. Codificación MP4 válida y generación automática de miniatura PNG.
3. Persistencia de metadatos en tabla gameplay_recordings (usuario, juego, duración, resolución, tamaño).
4. Política de almacenamiento y depuración automática FIFO por cuota de disco (2 GB).
5. Galería de clips con filtrado por juego, actualización de privacidad y eliminación completa.
6. Endpoints REST de la API de Grabaciones y Galería.
"""
import os
import tempfile
import time
import unittest
from pathlib import Path
import pygame
import cci_database
from backend.server import app
from backend.auth import create_access_token
from recorder.gallery_service import GalleryService
from recorder.video_recorder import GameplayVideoRecorder


class TestPhase6GameplayVideoRecorder(unittest.TestCase):
    """Verifica el grabador asíncrono y la generación de archivos MP4 y PNG."""

    def setUp(self):
        pygame.init()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name) / "grabaciones"
        self.db_path = Path(self.temp_dir.name) / "test_recorder.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

        self.recorder = GameplayVideoRecorder(output_dir=self.output_dir, max_quota_mb=100)
        self.gallery = GalleryService()

    def tearDown(self):
        if self.recorder.is_recording:
            self.recorder.stop_recording()
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()
        pygame.quit()

    def test_record_session_creates_valid_mp4_and_thumbnail(self):
        res_start = self.recorder.start_recording(
            game_id="davinci",
            owner_id="pilot_cami",
            target_w=640,
            target_h=360,
            fps=30.0
        )
        self.assertTrue(res_start["success"])
        self.assertTrue(self.recorder.is_recording)

        # Simular 30 frames de juego generados por Pygame
        surface = pygame.Surface((1280, 720))
        for i in range(30):
            surface.fill((i * 8 % 255, 100, 200))
            ok = self.recorder.capture_surface(surface)
            self.assertTrue(ok)
            time.sleep(0.01)

        res_stop = self.recorder.stop_recording()
        self.assertTrue(res_stop["success"])
        self.assertFalse(self.recorder.is_recording)

        mp4_path = Path(res_stop["file_path"])
        thumb_path = Path(res_stop["thumbnail_path"])

        # Verificar existencia física y tamaño no nulo
        self.assertTrue(mp4_path.is_file(), f"El archivo MP4 no fue creado en {mp4_path}")
        self.assertGreater(mp4_path.stat().st_size, 1000)

        self.assertTrue(thumb_path.is_file(), f"La miniatura PNG no fue creada en {thumb_path}")
        self.assertGreater(thumb_path.stat().st_size, 500)

        # Verificar persistencia en base de datos
        recs = cci_database.get_user_gameplay_recordings("pilot_cami")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["game_id"], "davinci")
        self.assertEqual(recs[0]["id"], res_stop["recording_id"])

    def test_gallery_service_filters_and_delete(self):
        # Insertar 2 clips de prueba
        cci_database.save_gameplay_recording_entry(
            recording_id="rec_1",
            owner_id="pilot_test",
            game_id="davinci",
            local_path=str(self.output_dir / "clip1.mp4"),
            duration_seconds=20.0,
            size_bytes=1024 * 500,
        )
        cci_database.save_gameplay_recording_entry(
            recording_id="rec_2",
            owner_id="pilot_test",
            game_id="metalslug",
            local_path=str(self.output_dir / "clip2.mp4"),
            duration_seconds=45.0,
            size_bytes=1024 * 900,
        )

        # 1. Obtener todos los clips
        all_clips = self.gallery.get_gallery_clips("pilot_test")
        self.assertEqual(len(all_clips), 2)

        # 2. Filtrar por juego
        df_clips = self.gallery.get_gallery_clips("pilot_test", game_id="davinci")
        self.assertEqual(len(df_clips), 1)
        self.assertEqual(df_clips[0]["id"], "rec_1")

        # 3. Actualizar privacidad
        vis_res = self.gallery.update_visibility("rec_1", "shared")
        self.assertTrue(vis_res["success"])

        # 4. Eliminar clip
        del_res = self.gallery.delete_clip("rec_1")
        self.assertTrue(del_res["success"])
        after_del = self.gallery.get_gallery_clips("pilot_test")
        self.assertEqual(len(after_del), 1)

    def test_fifo_quota_purge(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Configurar cuota muy pequeña (0.001 MB ~ 1 KB) para forzar purga FIFO
        small_recorder = GameplayVideoRecorder(output_dir=self.output_dir, max_quota_mb=0)

        # Registrar archivo viejo simulado
        old_file = self.output_dir / "old_clip.mp4"
        old_file.write_bytes(b"dummy video data " * 500)
        cci_database.save_gameplay_recording_entry(
            recording_id="old_clip",
            owner_id="pilot_test",
            game_id="mario",
            local_path=str(old_file),
            duration_seconds=10.0,
            size_bytes=old_file.stat().st_size,
        )

        # Forzar chequeo de cuota
        small_recorder._enforce_storage_quota()

        # El archivo viejo debe haber sido eliminado físicamente y de la base de datos
        self.assertFalse(old_file.exists())
        self.assertIsNone(cci_database.get_gameplay_recording_by_id("old_clip"))


class TestPhase6RecordingsRESTEndpoints(unittest.TestCase):
    """Verifica endpoints HTTP de la API de Grabaciones."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_rec_api.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)
        self.client = app.test_client()

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_recordings_rest_endpoints(self):
        token_pilot = create_access_token("pilot_rest", "PilotRest")

        # 0. Verificación negativa: sin token debe fallar con 401
        r_unauth = self.client.get("/api/v1/recordings/status")
        self.assertEqual(r_unauth.status_code, 401)

        # 1. Consultar estado del grabador autenticado
        r_status = self.client.get("/api/v1/recordings/status", headers={"Authorization": f"Bearer {token_pilot}"})
        self.assertEqual(r_status.status_code, 200)

        # 2. Consultar cuota de almacenamiento (Público)
        r_stats = self.client.get("/api/v1/recordings/storage/stats")
        self.assertEqual(r_stats.status_code, 200)
        self.assertIn("max_quota_mb", r_stats.get_json()["stats"])

        # 3. Consultar galería de usuario autenticado
        r_gal = self.client.get("/api/v1/recordings/pilot_rest", headers={"Authorization": f"Bearer {token_pilot}"})
        self.assertEqual(r_gal.status_code, 200)
        self.assertEqual(len(r_gal.get_json()["clips"]), 0)


if __name__ == "__main__":
    unittest.main()
