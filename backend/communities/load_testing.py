"""
backend/communities/load_testing.py
Harness de pruebas de carga y benchmarking sintético para CCI Communities.
Permite evaluar throughput (RPS), latencia promedio/p95 y tasa de error bajo concurrencia.
"""

import time
import concurrent.futures
from typing import Callable, Dict, Any, List


class LoadTestBenchmark:
    """Ejecutor de pruebas de carga sintética concurrente multihilo."""

    def __init__(self, concurrency: int = 10, total_requests: int = 100):
        self.concurrency = concurrency
        self.total_requests = total_requests

    def run_benchmark(self, request_fn: Callable[[], bool]) -> Dict[str, Any]:
        """
        Ejecuta total_requests invocaciones concurrentes de request_fn usando un ThreadPool.
        request_fn debe retornar True si la petición fue exitosa (2xx).
        Retorna estadísticas completas de rendimiento.
        """
        latencies: List[float] = []
        successes = 0
        failures = 0

        start_total = time.time()

        def worker_task():
            t0 = time.time()
            ok = False
            try:
                ok = bool(request_fn())
            except Exception:
                ok = False
            elapsed = time.time() - t0
            return ok, elapsed

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = [executor.submit(worker_task) for _ in range(self.total_requests)]
            for fut in concurrent.futures.as_completed(futures):
                ok, lat = fut.result()
                latencies.append(lat)
                if ok:
                    successes += 1
                else:
                    failures += 1

        total_time = time.time() - start_total
        latencies.sort()

        p50 = latencies[int(len(latencies) * 0.50)] if latencies else 0.0
        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0.0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0.0
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0
        rps = round(self.total_requests / total_time, 2) if total_time > 0 else 0.0

        return {
            "total_requests": self.total_requests,
            "concurrency": self.concurrency,
            "total_time_seconds": round(total_time, 3),
            "requests_per_second": rps,
            "success_count": successes,
            "failure_count": failures,
            "success_rate_percent": round((successes / self.total_requests) * 100, 2),
            "latency_avg_ms": round(avg_lat * 1000, 2),
            "latency_p50_ms": round(p50 * 1000, 2),
            "latency_p95_ms": round(p95 * 1000, 2),
            "latency_p99_ms": round(p99 * 1000, 2),
        }
