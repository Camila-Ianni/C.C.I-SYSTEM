"""
backend/communities/metrics.py - Módulo de telemetría, métricas Prometheus y diagnóstico de salud.

Provee contadores, medidores de concurrencia e histogramas para observabilidad:
- communities_messages_total
- communities_voice_sessions_active
- communities_streams_active
- communities_soundboard_plays_total
- communities_moderation_actions_total
- communities_api_requests_total
- communities_api_latency_seconds
"""

import time
import threading
from typing import Dict, Any, List


class CommunityMetricsCollector:
    """Recolector en memoria de métricas compatible con Prometheus text format (RFC 0001)."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.start_time = time.time()
        self._counts = {
            "communities_created_total": 0,
            "communities_messages_total": 0,
            "communities_voice_joins_total": 0,
            "communities_streams_started_total": 0,
            "communities_soundboard_plays_total": 0,
            "communities_moderation_actions_total": 0,
            "communities_api_requests_total": 0,
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
                "uptime_seconds": uptime,
                "counters": dict(self._counts),
                "latency_sample_count": len(self._latencies),
                "avg_latency_seconds": avg_lat,
            }

    def format_prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP communities_uptime_seconds Tiempo activo del servicio en segundos",
                "# TYPE communities_uptime_seconds gauge",
                f"communities_uptime_seconds {round(time.time() - self.start_time, 2)}",
            ]
            for metric, val in self._counts.items():
                lines.append(f"# HELP {metric} Contador acumulado de eventos")
                lines.append(f"# TYPE {metric} counter")
                lines.append(f"{metric} {val}")

            if self._latencies:
                avg_lat = sum(self._latencies) / len(self._latencies)
                lines.append("# HELP communities_api_latency_seconds Latencia promedio de peticiones REST")
                lines.append("# TYPE communities_api_latency_seconds gauge")
                lines.append(f"communities_api_latency_seconds {avg_lat:.5f}")

            return "\n".join(lines) + "\n"
