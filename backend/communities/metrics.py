"""
backend/communities/metrics.py - Módulo de telemetría, métricas Prometheus y diagnóstico de salud.

NOTA DE ALCANCE OPERATIVO:
Los contadores e histogramas de `CommunityMetricsCollector` son de alcance por proceso
(`scope: "process_local"`, `persistent: False`) y se reinician al reciclar el worker.
Provee contadores de eventos, errores (`communities_api_errors_total`, `communities_db_errors_total`),
medidores de sesiones activas (`communities_voice_sessions_active`, `communities_streams_active`)
y latencia de API en formato estándar Prometheus (RFC 0001) y JSON.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List


class CommunityMetricsCollector:
    """Recolector por proceso en memoria compatible con Prometheus text format (RFC 0001)."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.start_time = time.time()
        self.process_id = os.getpid()
        self._counts = {
            "communities_created_total": 0,
            "communities_messages_total": 0,
            "communities_voice_joins_total": 0,
            "communities_streams_started_total": 0,
            "communities_soundboard_plays_total": 0,
            "communities_moderation_actions_total": 0,
            "communities_api_requests_total": 0,
            "communities_api_errors_total": 0,
            "communities_db_errors_total": 0,
        }
        self._gauges = {
            "communities_voice_sessions_active": 0,
            "communities_streams_active": 0,
        }
        self._latencies: List[float] = []
        self._max_latencies = 1000

    @classmethod
    def get_instance(cls) -> "CommunityMetricsCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def increment(self, metric_name: str, value: int = 1):
        with self._lock:
            if metric_name in self._counts:
                self._counts[metric_name] += value
            else:
                self._counts[metric_name] = value

    def record_error(self, category: str = "api", value: int = 1):
        key = "communities_db_errors_total" if category == "db" else "communities_api_errors_total"
        self.increment(key, value)

    def set_gauge(self, gauge_name: str, value: int):
        with self._lock:
            self._gauges[gauge_name] = max(0, int(value))

    def record_latency(self, latency_seconds: float):
        with self._lock:
            self._latencies.append(latency_seconds)
            if len(self._latencies) > self._max_latencies:
                self._latencies.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            uptime = round(now - self.start_time, 2)
            avg_lat = round(sum(self._latencies) / len(self._latencies), 5) if self._latencies else 0.0
            return {
                "scope": "process_local",
                "persistent": False,
                "pid": self.process_id,
                "uptime_seconds": uptime,
                "counters": dict(self._counts),
                "gauges": dict(self._gauges),
                "latency_sample_count": len(self._latencies),
                "avg_latency_seconds": avg_lat,
            }

    def format_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP communities_uptime_seconds Tiempo activo del proceso actual en segundos (process_local, non-persistent)",
                "# TYPE communities_uptime_seconds gauge",
                f"communities_uptime_seconds {round(time.time() - self.start_time, 2)}",
            ]
            for metric, val in self._counts.items():
                lines.append(f"# HELP {metric} Contador acumulado de eventos en el proceso actual")
                lines.append(f"# TYPE {metric} counter")
                lines.append(f"{metric} {val}")

            for gauge, val in self._gauges.items():
                lines.append(f"# HELP {gauge} Medidor instantaneo de sesiones activas")
                lines.append(f"# TYPE {gauge} gauge")
                lines.append(f"{gauge} {val}")

            if self._latencies:
                avg_lat = sum(self._latencies) / len(self._latencies)
                lines.append("# HELP communities_api_latency_seconds Latencia promedio de peticiones REST")
                lines.append("# TYPE communities_api_latency_seconds gauge")
                lines.append(f"communities_api_latency_seconds {avg_lat:.5f}")

            return "\n".join(lines) + "\n"
