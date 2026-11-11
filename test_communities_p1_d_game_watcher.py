"""test_communities_p1_d_game_watcher.py - Certificación E2E P1-D: Watcher real de juegos (launcher + procesos SO).

Verifica de punta a punta con backend Flask/Socket.IO real, Qt `OmniDashMainWindow`,
`CommunityController` y procesos reales del sistema operativo monitoreados con `psutil`:
1. Al abrir y cerrar un juego lanzado desde OmniDash (`launch_game` / `QProcess`),
   se reporta automáticamente `activity/game` (`started` / `stopped`) sin llamadas manuales
   y el amigo conectado recibe ambos eventos en tiempo real (Socket.IO + presencia + UI).
2. Al abrir y cerrar un proceso externo del SO (ej. emulador/runner con ROM del catálogo o
   regla de ejecutable) fuera de OmniDash, `GameProcessWatcher` (`psutil`) lo detecta y
   notifica `started` / `stopped` al amigo automáticamente sin duplicados.
3. Si un launcher inicia un proceso hijo y el wrapper finaliza primero, el estado activo se
   mantiene hasta que el proceso real del juego cierra en el SO.
4. Respeta privacidad (`private` / `invisible`) en amigos/feed y limpia watcher + juego activo en `shutdown()`.
"""
from __future__ import annotations

import gc
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["CCI_AUTO_START_BACKEND"] = "0"
os.environ["CCI_DISABLE_AUDIO_IO"] = "1"

from PySide6.QtWidgets import QApplication


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_until(app: QApplication, predicate, timeout: float = 6.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.03)
    app.processEvents()
    return bool(predicate())


class TestCommunitiesP1DGameWatcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls._tmp_dir = tempfile.TemporaryDirectory(prefix="cci_p1d_watcher_")
        cls.tmp_path = Path(cls._tmp_dir.name)

        cls._old_env = {
            k: os.environ.get(k)
            for k in ("CCI_DATABASE_PATH", "CCI_COMMUNITIES_DB_PATH", "CCI_SOUNDS_STORAGE_PATH")
        }
        os.environ["CCI_DATABASE_PATH"] = str(cls.tmp_path / "accounts.sqlite3")
        os.environ["CCI_COMMUNITIES_DB_PATH"] = str(cls.tmp_path / "communities.sqlite3")
        os.environ["CCI_SOUNDS_STORAGE_PATH"] = str(cls.tmp_path / "sounds")

        import cci_database
        from backend.communities.repository import CommunitiesRepository

        cci_database.init_db()
        CommunitiesRepository.reset_instance()

        import backend.server as server_mod

        cls.server_port = _free_port()
        cls.api_url = f"http://127.0.0.1:{cls.server_port}"

        def _serve():
            server_mod.socketio.run(
                server_mod.app,
                host="127.0.0.1",
                port=cls.server_port,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True,
                log_output=False,
            )

        threading.Thread(target=_serve, daemon=True).start()
        deadline = time.time() + 6.0
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", cls.server_port), timeout=0.15):
                    break
            except OSError:
                time.sleep(0.05)

        # Script simulador de juego vivo hasta señal de archivo o SIGTERM
        cls.sleep_game_script = cls.tmp_path / "fake_game_proc.py"
        cls.sleep_game_script.write_text(
            "import pathlib, signal, sys, time\n"
            "running = True\n"
            "def _stop(*_args):\n"
            "    global running\n"
            "    running = False\n"
            "signal.signal(signal.SIGTERM, _stop)\n"
            "stop_file = None\n"
            "for i, a in enumerate(sys.argv):\n"
            "    if a == '--stop-file' and i + 1 < len(sys.argv):\n"
            "        stop_file = pathlib.Path(sys.argv[i + 1])\n"
            "ready_file = None\n"
            "for i, a in enumerate(sys.argv):\n"
            "    if a == '--ready-file' and i + 1 < len(sys.argv):\n"
            "        ready_file = pathlib.Path(sys.argv[i + 1])\n"
            "if ready_file is not None:\n"
            "    ready_file.write_text('ready')\n"
            "while running:\n"
            "    if stop_file is not None and stop_file.exists():\n"
            "        break\n"
            "    time.sleep(0.03)\n",
            encoding="utf-8",
        )

        # Script simulador de retro_core_runner.py externo
        runner_dir = cls.tmp_path / "ext_runner"
        runner_dir.mkdir(parents=True, exist_ok=True)
        cls.ext_runner_script = runner_dir / "retro_core_runner.py"
        cls.ext_runner_script.write_text(
            cls.sleep_game_script.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        # Script wrapper que lanza un proceso hijo real y termina inmediatamente
        cls.child_script = cls.tmp_path / "child_game_target.py"
        cls.child_script.write_text(
            cls.sleep_game_script.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        cls.wrapper_script = cls.tmp_path / "launcher_wrapper.py"
        cls.wrapper_script.write_text(
            "import subprocess, sys, time\n"
            "subprocess.Popen(sys.argv[1:])\n"
            "time.sleep(0.25)\n",
            encoding="utf-8",
        )

    @classmethod
    def tearDownClass(cls):
        for k, v in cls._old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        cls._tmp_dir.cleanup()

    def setUp(self):
        self._controllers = []
        self._widgets = []
        self._procs = []

    def tearDown(self):
        for p in self._procs:
            try:
                if p.poll() is None:
                    p.terminate()
                    p.wait(timeout=2.0)
            except Exception:
                pass
        for w in self._widgets:
            try:
                w.close()
                w.deleteLater()
            except Exception:
                pass
        for c in self._controllers:
            try:
                c.shutdown()
                c.deleteLater()
            except Exception:
                pass
        self.app.processEvents()
        gc.collect()

    def _new_controller(self, tag: str, interval: float = 0.08, enable_watcher: bool = True):
        from backend.communities.desktop_client import CommunityController

        sess_file = self.tmp_path / f"sess_{tag}_{time.time_ns()}.json"
        ctrl = CommunityController(
            api_url=self.api_url,
            session_path=sess_file,
            heartbeat_interval_ms=0,
            enable_voice_audio_io=False,
            enable_game_watcher=enable_watcher,
            game_watch_interval_sec=interval,
        )
        self._controllers.append(ctrl)
        return ctrl

    def _register_friends(self, tag: str):
        ctrl_a = self._new_controller(f"a_{tag}")
        ctrl_b = self._new_controller(f"b_{tag}", enable_watcher=False)
        suffix = f"{tag}_{int(time.time() * 1000) % 100000}"
        u_a = f"player_a_{suffix}"
        u_b = f"friend_b_{suffix}"
        ctrl_a.register(f"{u_a}@cci.local", u_a, "Passw0rd!123")
        ctrl_b.register(f"{u_b}@cci.local", u_b, "Passw0rd!123")
        ok = _wait_until(
            self.app,
            lambda: ctrl_a.realtime.is_connected() and ctrl_b.realtime.is_connected(),
            timeout=5.0,
        )
        self.assertTrue(ok, "Ambos clientes deben conectarse por Socket.IO")

        ctrl_a.send_friend_request(u_b)
        ctrl_b.refresh_friends()
        self.assertTrue(ctrl_b.incoming_friend_requests)
        ctrl_b.respond_friend_request(ctrl_a.session.user_id, accept=True)
        ctrl_b.refresh_friends()
        return ctrl_a, ctrl_b, u_a, u_b

    def test_01_launcher_qprocess_emits_real_started_stopped_and_updates_friend_realtime(self):
        from omnidash_qt import CommunityExploreView, OmniDashMainWindow

        ctrl_a, ctrl_b, u_a, _u_b = self._register_friends("p1d_launch")

        events_b = []
        ctrl_b.realtime.activity_updated.connect(lambda ev: events_b.append(dict(ev)))
        presences_b = []
        ctrl_b.realtime.presence_updated.connect(lambda p: presences_b.append(dict(p)))

        friends_view_b = CommunityExploreView(controller=ctrl_b)
        self._widgets.append(friends_view_b)
        ctrl_b.refresh_friends()

        win_a = OmniDashMainWindow(controller=ctrl_a, auto_connect=False)
        self._widgets.append(win_a)

        stop_file = self.tmp_path / "launch_stop.flag"
        ready_file = self.tmp_path / "launch_ready.flag"
        for p in (stop_file, ready_file):
            if p.exists():
                p.unlink()

        win_a.launch_game({
            "id": "native_chrono_runner",
            "title": "Chrono Runner",
            "executable": [
                sys.executable,
                str(self.sleep_game_script),
                "--ready-file",
                str(ready_file),
                "--stop-file",
                str(stop_file),
            ],
        })

        self.assertTrue(
            _wait_until(self.app, lambda: ready_file.exists(), timeout=4.0),
            "QProcess de launch_game debe arrancar el ejecutable del juego",
        )
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(
                    e.get("event") == "started" and e.get("title") == "Chrono Runner"
                    for e in events_b
                ),
                timeout=5.0,
            ),
            f"El amigo B debe recibir evento Socket.IO started. Recibidos: {events_b}",
        )
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(
                    str(f.get("friend_id")) == ctrl_a.session.user_id
                    and f.get("current_game") == "Chrono Runner"
                    for f in ctrl_b.active_friends
                ),
                timeout=4.0,
            ),
            "La lista de amigos en tiempo real de B debe reflejar Chrono Runner",
        )
        self.assertTrue(
            any(
                p.get("user_id") == ctrl_a.session.user_id and p.get("activity_title") == "Chrono Runner"
                for p in presences_b
            ),
            "presence:updated debe propagar la actividad del juego al amigo",
        )

        # Verificar UI en FriendsExploreView de B
        self.app.processEvents()
        friend_texts = [
            friends_view_b.friends_list_box.itemAt(i).widget().text()
            for i in range(friends_view_b.friends_list_box.count())
            if friends_view_b.friends_list_box.itemAt(i).widget() is not None
        ]
        self.assertTrue(
            any("Chrono Runner" in t and u_a.upper() in t.upper() for t in friend_texts),
            f"Friends UI debe mostrar juego activo. Textos: {friend_texts}",
        )

        # Cerrar el proceso del juego -> sin llamadas manuales debe emitir stopped
        stop_file.write_text("quit", encoding="utf-8")
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(
                    e.get("event") == "stopped" and e.get("title") == "Chrono Runner"
                    for e in events_b
                ),
                timeout=5.0,
            ),
            f"El amigo B debe recibir evento Socket.IO stopped al cerrar el juego. Recibidos: {events_b}",
        )
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: all(
                    f.get("current_game") is None
                    for f in ctrl_b.active_friends
                    if str(f.get("friend_id")) == ctrl_a.session.user_id
                ),
                timeout=4.0,
            ),
            "La lista de amigos de B debe limpiar current_game tras cerrar el juego",
        )

        # Sin duplicados
        starts = [e for e in events_b if e.get("event") == "started" and e.get("title") == "Chrono Runner"]
        stops = [e for e in events_b if e.get("event") == "stopped" and e.get("title") == "Chrono Runner"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(stops), 1)

        # Confirmación persistida en API REST para amigo B
        friends_rest = ctrl_b.api.get_friends(ctrl_b.session.user_id)["friends"]
        row_a = next(f for f in friends_rest if str(f.get("friend_id")) == ctrl_a.session.user_id)
        self.assertIsNone(row_a.get("current_game"))

    def test_02_external_os_process_retro_runner_detected_via_psutil_without_launcher(self):
        ctrl_a, ctrl_b, _u_a, _u_b = self._register_friends("p1d_psutil")

        rom_dir = self.tmp_path / "roms" / "mame"
        rom_dir.mkdir(parents=True, exist_ok=True)
        rom_file = rom_dir / "mslug2.zip"
        rom_file.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

        ctrl_a.set_watched_games([
            {
                "id": "mame_mslug2",
                "title": "Metal Slug 2",
                "rom": str(rom_file),
                "core": "cores/fbneo_libretro.dylib",
            }
        ])

        events_b = []
        ctrl_b.realtime.activity_updated.connect(lambda ev: events_b.append(dict(ev)))

        ready_file = self.tmp_path / "ext_ready.flag"
        proc = subprocess.Popen(
            [
                sys.executable,
                str(self.ext_runner_script),
                "--rom",
                str(rom_file),
                "--title",
                "C.C.I. SYSTEM — Metal Slug 2 (60 FPS)",
                "--ready-file",
                str(ready_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._procs.append(proc)

        self.assertTrue(_wait_until(self.app, lambda: ready_file.exists(), timeout=4.0))
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(
                    e.get("event") == "started"
                    and e.get("game_id") == "mame_mslug2"
                    and e.get("title") == "Metal Slug 2"
                    for e in events_b
                ),
                timeout=5.0,
            ),
            f"Proceso externo retro_core_runner debe detectarse via psutil y notificar al amigo. Recibidos: {events_b}",
        )

        # Cerrar proceso externo en el SO
        proc.terminate()
        proc.wait(timeout=3.0)

        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(
                    e.get("event") == "stopped"
                    and e.get("game_id") == "mame_mslug2"
                    and e.get("title") == "Metal Slug 2"
                    for e in events_b
                ),
                timeout=5.0,
            ),
            f"Al cerrar proceso externo, amigo debe recibir stopped real. Recibidos: {events_b}",
        )
        starts = [e for e in events_b if e.get("event") == "started" and e.get("game_id") == "mame_mslug2"]
        stops = [e for e in events_b if e.get("event") == "stopped" and e.get("game_id") == "mame_mslug2"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(stops), 1)

    def test_03_launcher_child_process_tracking_and_custom_rule_dedup(self):
        from omnidash_qt import OmniDashMainWindow

        ctrl_a, ctrl_b, _u_a, _u_b = self._register_friends("p1d_child")
        events_b = []
        ctrl_b.realtime.activity_updated.connect(lambda ev: events_b.append(dict(ev)))

        win_a = OmniDashMainWindow(controller=ctrl_a, auto_connect=False)
        self._widgets.append(win_a)

        child_ready = self.tmp_path / "child_ready.flag"
        child_stop = self.tmp_path / "child_stop.flag"
        for p in (child_ready, child_stop):
            if p.exists():
                p.unlink()

        win_a.launch_game({
            "id": "wrapper_zelda",
            "title": "Zelda Wrapper",
            "executable": [
                sys.executable,
                str(self.wrapper_script),
                sys.executable,
                str(self.child_script),
                "--ready-file",
                str(child_ready),
                "--stop-file",
                str(child_stop),
            ],
        })

        self.assertTrue(_wait_until(self.app, lambda: child_ready.exists(), timeout=4.0))
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(e.get("event") == "started" and e.get("title") == "Zelda Wrapper" for e in events_b),
                timeout=5.0,
            )
        )
        # Esperar a que el wrapper finalice mientras el proceso hijo sigue vivo
        self.assertTrue(
            _wait_until(self.app, lambda: win_a._game_process is None, timeout=4.0),
            "El wrapper debe finalizar dejando vivo el proceso hijo",
        )
        time.sleep(0.25)
        self.app.processEvents()
        self.assertFalse(
            any(e.get("event") == "stopped" and e.get("title") == "Zelda Wrapper" for e in events_b),
            "No debe emitir stopped mientras el proceso hijo del juego siga vivo",
        )
        self.assertEqual(ctrl_a._active_game_title, "Zelda Wrapper")

        # Ahora cerrar el proceso hijo real -> debe emitir stopped
        child_stop.write_text("done", encoding="utf-8")
        self.assertTrue(
            _wait_until(
                self.app,
                lambda: any(e.get("event") == "stopped" and e.get("title") == "Zelda Wrapper" for e in events_b),
                timeout=5.0,
            ),
            "Debe emitir stopped cuando finaliza el proceso hijo real",
        )

    def test_04_privacy_and_clean_shutdown_while_game_running(self):
        ctrl_a, ctrl_b, _u_a, _u_b = self._register_friends("p1d_priv")
        events_b = []
        ctrl_b.realtime.activity_updated.connect(lambda ev: events_b.append(dict(ev)))

        ctrl_a.set_activity_visibility("private")
        ctrl_a.register_watched_game(
            game_id="secret_rpg",
            title="Secret RPG",
            cmdline_tokens=["--secret-rpg-token"],
        )

        ready_file = self.tmp_path / "priv_ready.flag"
        proc = subprocess.Popen(
            [
                sys.executable,
                str(self.sleep_game_script),
                "--secret-rpg-token",
                "--ready-file",
                str(ready_file),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._procs.append(proc)

        self.assertTrue(_wait_until(self.app, lambda: ready_file.exists(), timeout=4.0))
        self.assertTrue(
            _wait_until(self.app, lambda: ctrl_a._active_game_title == "Secret RPG", timeout=4.0),
            "El watcher local sí detecta el juego aunque la visibilidad sea privada",
        )
        time.sleep(0.25)
        self.app.processEvents()

        # Amigo NO debe ver juego privado ni recibir evento realtime
        self.assertEqual(events_b, [])
        friends_rest = ctrl_b.api.get_friends(ctrl_b.session.user_id)["friends"]
        row_a = next(f for f in friends_rest if str(f.get("friend_id")) == ctrl_a.session.user_id)
        self.assertIsNone(row_a.get("current_game"))

        # shutdown() mientras el juego sigue corriendo detiene el hilo del watcher y limpia estado
        ctrl_a.shutdown()
        self.assertFalse(ctrl_a.game_watcher.is_running())
        self.assertIsNone(ctrl_a._active_game_title)


if __name__ == "__main__":
    unittest.main(verbosity=2)
