"""
recorder/gallery_service.py - Servicio de gestión de la Galería de Grabaciones de Gameplay.
Permite listar clips con miniaturas, filtrar por juego/fecha, eliminar, actualizar visibilidad
y exportar/reproducir con el reproductor nativo del sistema operativo.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import cci_database
from backend.config import config


class GalleryService:
    """Servicio de administración de clips de gameplay y galería multimedia."""

    _instance: Optional[GalleryService] = None

    @classmethod
    def get_instance(cls) -> GalleryService:
        if cls._instance is None:
            cls._instance = GalleryService()
        return cls._instance

    def get_gallery_clips(self, owner_id: str, game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene las grabaciones registradas filtrando opcionalmente por juego."""
        recordings = cci_database.get_user_gameplay_recordings(owner_id)
        if game_id:
            recordings = [r for r in recordings if r.get("game_id") == game_id]

        for r in recordings:
            r["size_mb"] = round(r.get("size_bytes", 0) / (1024 * 1024), 2)
            # Verificar existencia física
            r["file_exists"] = bool(r.get("local_path") and os.path.exists(r["local_path"]))

        return recordings

    def delete_clip(self, recording_id: str) -> Dict[str, Any]:
        """Elimina el archivo de video, su miniatura y su registro en base de datos."""
        rec = cci_database.get_gameplay_recording_by_id(recording_id)
        if not rec:
            return {"success": False, "error": "Grabación no encontrada."}

        # Borrar archivo MP4
        if rec.get("local_path") and os.path.exists(rec["local_path"]):
            try:
                os.remove(rec["local_path"])
            except Exception as exc:
                print(f"[GalleryService] Error borrando archivo de video: {exc}")

        # Borrar miniatura PNG
        if rec.get("thumbnail_path") and os.path.exists(rec["thumbnail_path"]):
            try:
                os.remove(rec["thumbnail_path"])
            except Exception:
                pass

        ok = cci_database.delete_gameplay_recording_entry(recording_id)
        return {"success": ok, "message": "Grabación eliminada del disco y la galería."}

    def update_visibility(self, recording_id: str, visibility: str) -> Dict[str, Any]:
        """Actualiza la privacidad del clip ('private', 'shared')."""
        if visibility not in ("private", "shared"):
            return {"success": False, "error": "Visibilidad inválida (debe ser private o shared)."}

        ok = cci_database.update_gameplay_recording_visibility_entry(recording_id, visibility)
        return {"success": ok, "message": f"Visibilidad actualizada a {visibility}."}

    def get_storage_stats(self) -> Dict[str, Any]:
        """Calcula estadísticas de cuota y uso de almacenamiento."""
        total_bytes = cci_database.get_total_recordings_disk_usage()
        used_mb = round(total_bytes / (1024 * 1024), 2)
        max_mb = config.max_recordings_mb
        percent = min(100.0, round((used_mb / max(1, max_mb)) * 100.0, 1))

        return {
            "used_mb": used_mb,
            "max_quota_mb": max_mb,
            "percent_used": percent,
            "remaining_mb": max(0.0, max_mb - used_mb),
        }

    def open_in_system_player(self, recording_id: str) -> Dict[str, Any]:
        """Abre el archivo de video en el reproductor nativo del sistema operativo de forma segura."""
        rec = cci_database.get_gameplay_recording_by_id(recording_id)
        if not rec or not rec.get("local_path") or not os.path.exists(rec["local_path"]):
            return {"success": False, "error": "El archivo de video no existe en el disco."}

        path = rec["local_path"]
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            elif sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path], check=False)
            return {"success": True, "message": f"Abriendo {path} en el reproductor del sistema."}
        except Exception as exc:
            return {"success": False, "error": f"Error abriendo reproductor: {exc}"}
