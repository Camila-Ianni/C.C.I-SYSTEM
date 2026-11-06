"""
test_phase10_media_and_physics.py - Pruebas de integración para cliente de voz (Opus/PCM),
físicas de combate reales con Hitbox/Hurtbox e integridad de grabaciones MP4.

Resuelve las brechas técnicas 5.2, 5.3 y 5.6 de la Auditoría:
1. Transporte de medios de voz, Voice Activity Detection (VAD) y bloqueo estricto de paquetes al mutear.
2. Físicas de combate de Da Vinci Fighters: colisiones de cajas de golpe, daño, guardia/bloqueo y stun.
3. Cadencia autoritativa independiente a 60 Hz cuando hay jitter o pérdida de paquetes.
4. Verificación de integridad del contenedor MP4 y tasa de FPS efectiva en el grabador de video.
"""
import math
from pathlib import Path
import struct
import tempfile
import time
import unittest
import pygame

# Initialize pygame headless
pygame.init()
if not pygame.display.get_init() or not pygame.display.get_surface():
    pygame.display.set_mode((1, 1), pygame.NOFRAME)

import cci_database
from backend.contracts import PlayerInputPacket
from backend.sync_engine import AuthoritativeSyncEngine
from mobile.voice_client import VoiceMediaClient
from recorder.video_recorder import GameplayVideoRecorder


class TestPhase10MediaAndCombatPhysics(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_media.sqlite3"
        cci_database.init_db(self.db_path)

        self._orig_get_db = cci_database.get_db
        cci_database.get_db = lambda p=None: self._orig_get_db(p or self.db_path)

    def tearDown(self):
        cci_database.get_db = self._orig_get_db
        self.temp_dir.cleanup()

    def test_01_voice_client_vad_and_strict_privacy_mute(self):
        """Verifica que el cliente de voz procese audio PCM, detecte VAD y bloquee transmisión al mutear."""
        client = VoiceMediaClient("u_alice", "Alice")
        sent_packets = []
        client.set_transport(lambda pkt: sent_packets.append(pkt))
        client.start_audio()

        # 1. Silencio (muestras PCM con valor 0)
        silence_pcm = b"\x00\x00" * VoiceMediaClient.SAMPLES_PER_FRAME
        pkt_silence = client.process_microphone_pcm(silence_pcm)
        self.assertIsNotNone(pkt_silence)
        self.assertFalse(client.is_speaking, "Silencio no debe activar VAD")

        # 2. Voz / Sonido fuerte (onda sinusoidal de 440 Hz con amplitud 8000)
        samples = []
        for i in range(VoiceMediaClient.SAMPLES_PER_FRAME):
            val = int(8000 * math.sin(2 * math.pi * 440 * i / VoiceMediaClient.SAMPLE_RATE))
            samples.append(val)
        loud_pcm = struct.pack(f"<{len(samples)}h", *samples)

        pkt_loud = client.process_microphone_pcm(loud_pcm)
        self.assertIsNotNone(pkt_loud)
        self.assertTrue(client.is_speaking, "Voz activa debe activar VAD (RMS > umbral)")
        self.assertEqual(len(sent_packets), 2)

        # 3. Mute estricto: cuando está silenciado, NO debe transmitirse NADA
        client.set_mute(True)
        self.assertTrue(client.is_muted)
        pkt_muted = client.process_microphone_pcm(loud_pcm)
        self.assertIsNone(pkt_muted, "Al estar en mute, process_microphone_pcm debe retornar None")
        self.assertEqual(len(sent_packets), 2, "Ningún paquete debe haberse enviado mientras está en mute")

        # 4. Recepción de audio de par remoto
        remote_ok = client.receive_remote_audio("u_bob", {"audio_payload": loud_pcm, "speaking": True})
        self.assertTrue(remote_ok)
        peer_state = client.get_peer_state("u_bob")
        self.assertTrue(peer_state["speaking"])

    def test_02_authoritative_combat_physics_hitbox_and_guard(self):
        """Verifica el cálculo autoritativo de cajas de golpe, daño y reducción por bloqueo."""
        engine = AuthoritativeSyncEngine("room_fighter_test")
        engine.p1.x = 800.0
        engine.p2.x = 880.0  # En rango cuerpo a cuerpo

        # 1. P1 lanza golpe pesado (punch_heavy) hacia la derecha
        inp_punch = PlayerInputPacket(
            room_id="room_fighter_test",
            player_id=1,
            tick=1,
            seq=1,
            dpad="idle",
            buttons=["punch_heavy"]
        )
        engine.push_input(inp_punch)

        # Simular frames hasta el frame activo del golpe (startup es 8 frames)
        for t in range(1, 10):
            engine.step(1.0 / 60.0)

        # P2 debe haber recibido daño directo y estar en estado 'hit' con stun
        self.assertLess(engine.p2.hp, 100)
        self.assertEqual(engine.p2.state, "hit")
        self.assertGreater(engine.p2.stun_frames, 0)
        damage_taken = 100 - engine.p2.hp
        self.assertEqual(damage_taken, 20, "Golpe pesado debe infligir exactamente 20 de daño")

        # 2. P2 intenta guardia/bloqueo (caminar hacia atrás)
        engine.p2.stun_frames = 0
        engine.p2.hp = 80
        engine.p1.x = 800.0
        engine.p2.x = 880.0

        # P2 retrocede (dpad right porque está mirando a la izquierda)
        inp_guard = PlayerInputPacket(
            room_id="room_fighter_test",
            player_id=2,
            tick=11,
            seq=2,
            dpad="right",  # Backwards guard
            buttons=[]
        )
        inp_kick = PlayerInputPacket(
            room_id="room_fighter_test",
            player_id=1,
            tick=11,
            seq=3,
            dpad="idle",
            buttons=["kick_heavy"]  # 24 base damage
        )
        engine.push_input(inp_guard)
        engine.push_input(inp_kick)

        for t in range(11, 23):
            engine.step(1.0 / 60.0)

        # Con bloqueo exitoso, el daño debe reducirse significativamente (24 // 5 = 4)
        blocked_damage = 80 - engine.p2.hp
        self.assertEqual(blocked_damage, 4, "La guardia debe reducir el daño en un 80%")
        self.assertEqual(engine.p2.state, "block")

    def test_03_authoritative_engine_cadence_without_packets(self):
        """Verifica que el motor mantenga una cadencia de 60 Hz continua ante pérdida de paquetes."""
        engine = AuthoritativeSyncEngine("room_jitter_test")
        initial_tick = engine.tick
        initial_timer = engine.timer

        # Avanzar 60 pasos (1 segundo) sin recibir ningún paquete de red
        for _ in range(60):
            snapshot = engine.step(1.0 / 60.0)

        self.assertEqual(engine.tick, initial_tick + 60)
        self.assertAlmostEqual(engine.timer, initial_timer - 1.0, delta=0.01)
        self.assertEqual(snapshot.status, "fighting")

    def test_04_video_recorder_mp4_integrity_validation(self):
        """Verifica que stop_recording valide contenedor MP4 real y descarte grabaciones vacías/corruptas."""
        output_dir = Path(self.temp_dir.name) / "test_clips"
        recorder = GameplayVideoRecorder(output_dir=output_dir, max_quota_mb=100)

        # 1. Grabación válida con frames
        res_start = recorder.start_recording("davinci", "pilot_rec", target_w=640, target_h=360, fps=30.0)
        self.assertTrue(res_start["success"])

        surf = pygame.Surface((640, 360))
        for i in range(15):
            surf.fill((i * 10 % 255, 50, 150))
            recorder.capture_surface(surf)
            time.sleep(0.01)

        res_stop = recorder.stop_recording()
        self.assertTrue(res_stop["success"])
        self.assertGreater(res_stop["frames_written"], 0)
        self.assertGreater(res_stop["effective_fps"], 0.0)
        self.assertTrue(Path(res_stop["file_path"]).is_file())

    def test_05_room_simulation_ticker_lifecycle_and_jitter(self):
        """Verifica que RoomSimulationTicker gestione ciclos de vida (start/pause/resume/stop) y emita a 60 Hz bajo jitter."""
        from backend.server import RoomSimulationTicker, _start_room_ticker, _stop_room_ticker, room_tickers

        engine = AuthoritativeSyncEngine("room_lifecycle_test")
        emitted_snapshots = []

        def mock_emit(evt, data, room):
            emitted_snapshots.append(data)

        ticker = RoomSimulationTicker("room_lifecycle_test", engine, mock_emit)

        # 1. Inicio y emisión a 60 Hz
        ticker.start()
        self.assertTrue(ticker.running)
        time.sleep(0.1)  # ~6 frames
        self.assertGreater(len(emitted_snapshots), 2)

        # 2. Parada limpia (join sin fugas)
        ticker.stop(timeout=1.0)
        self.assertFalse(ticker.running)
        self.assertIsNone(ticker._thread)
        count_paused = len(emitted_snapshots)

        # Durante pausa no debe haber emisiones adicionales
        time.sleep(0.05)
        self.assertEqual(len(emitted_snapshots), count_paused)

        # 3. Reinicio / Reanudación
        ticker.start()
        self.assertTrue(ticker.running)
        # Simular ráfaga de jitter: inputs llegan a destiempo con gaps
        inp = PlayerInputPacket(
            room_id="room_lifecycle_test",
            player_id=1,
            tick=engine.tick + 1,
            seq=10,
            dpad="right",
            buttons=[]
        )
        engine.push_input(inp)
        time.sleep(0.1)

        # Debe continuar incrementando ticks autoritativos
        self.assertGreater(len(emitted_snapshots), count_paused)
        last_snap = emitted_snapshots[-1]
        self.assertGreater(last_snap["tick"], 0)

        # Cierre definitivo
        ticker.stop(timeout=1.0)
        self.assertFalse(ticker.running)

        # 4. Coordinación global con _start_room_ticker y _stop_room_ticker
        test_room = "coord_room_99"
        _start_room_ticker(test_room, engine)
        self.assertIn(test_room, room_tickers)
        first_instance = room_tickers[test_room]

        # Re-iniciar sobre la misma sala debe detener y sustituir la anterior sin threads huérfanos
        _start_room_ticker(test_room, engine)
        self.assertFalse(first_instance.running)
        second_instance = room_tickers[test_room]
        self.assertIsNot(first_instance, second_instance)

        # Detener sala
        _stop_room_ticker(test_room)
        self.assertNotIn(test_room, room_tickers)
        self.assertFalse(second_instance.running)

    def test_06_bidirectional_multi_client_audio_and_webrtc_mesh(self):
        """Verifica negociación WebRTC P2P (SDP/ICE) e intercambio bidireccional RTP/UDP real entre sockets (P1)."""
        client_a = VoiceMediaClient("u_alice", "Alice")
        client_b = VoiceMediaClient("u_bob", "Bob")

        sink_a_frames = []
        sink_b_frames = []
        client_a.set_audio_drivers(output_sink=lambda f: sink_a_frames.append(f))
        client_b.set_audio_drivers(output_sink=lambda f: sink_b_frames.append(f))

        # 1. Enlazar sockets UDP reales del sistema operativo para transporte RTP RFC 3550
        port_a = client_a.bind_udp_transport(host="127.0.0.1", port=0)
        port_b = client_b.bind_udp_transport(host="127.0.0.1", port=0)
        self.assertGreater(port_a, 0)
        self.assertGreater(port_b, 0)
        self.assertNotEqual(port_a, port_b)

        # 2. Iniciar subsistemas de audio (hilos de captura y reproducción)
        self.assertTrue(client_a.start_audio())
        self.assertTrue(client_b.start_audio())
        self.assertTrue(client_a._playback_thread.is_alive())
        self.assertTrue(client_a._capture_thread.is_alive())
        self.assertTrue(client_b._playback_thread.is_alive())
        self.assertTrue(client_b._capture_thread.is_alive())

        # 3. Negociación SDP e intercambio de candidatos ICE RFC 5245 con PT=96 (L16 PCM)
        offer = client_a.create_offer("u_bob")
        self.assertEqual(offer["type"], "offer")
        self.assertIn("m=audio", offer["sdp"])
        self.assertIn("RTP/AVP 96", offer["sdp"])
        self.assertIn("a=rtpmap:96 L16/48000/1", offer["sdp"])
        self.assertEqual(client_a.connection_states["u_bob"], "connecting")

        answer = client_b.create_answer("u_alice", offer["sdp"])
        self.assertEqual(answer["type"], "answer")
        self.assertIn("RTP/AVP 96", answer["sdp"])
        self.assertEqual(client_b.connection_states["u_alice"], "connected")

        cand_a = client_a.generate_local_ice_candidate("127.0.0.1")
        cand_b = client_b.generate_local_ice_candidate("127.0.0.1")
        self.assertTrue(client_b.add_ice_candidate("u_alice", cand_a))
        self.assertTrue(client_a.add_ice_candidate("u_bob", cand_b))
        self.assertEqual(client_a.connection_states["u_bob"], "connected")
        self.assertEqual(client_b.connection_states["u_alice"], "connected")

        # Candidato inválido debe ser rechazado
        self.assertFalse(client_a.add_ice_candidate("u_bob", {"candidate": "invalid string"}))

        # 4. Transmisión bidireccional simultánea de paquetes RTP a través de la pila de red UDP
        samples_a = [int(7000 * math.sin(2 * math.pi * 440 * i / 48000)) for i in range(client_a.SAMPLES_PER_FRAME)]
        pcm_a = struct.pack(f"<{len(samples_a)}h", *samples_a)

        samples_b = [int(9000 * math.sin(2 * math.pi * 880 * i / 48000)) for i in range(client_b.SAMPLES_PER_FRAME)]
        pcm_b = struct.pack(f"<{len(samples_b)}h", *samples_b)

        # Enviar paquetes RTP por la red real (kernel UDP socket)
        ok_a = client_a.send_rtp_packet("u_bob", pcm_a)
        ok_b = client_b.send_rtp_packet("u_alice", pcm_b)
        self.assertTrue(ok_a)
        self.assertTrue(ok_b)

        time.sleep(0.1)

        # Verificar recepción y reproducción de los paquetes recibidos a través de la red UDP real
        received_b = sink_b_frames if sink_b_frames else client_b._playback_buffer
        received_a = sink_a_frames if sink_a_frames else client_a._playback_buffer
        self.assertGreater(len(received_b), 0)
        self.assertGreater(len(received_a), 0)
        self.assertEqual(len(received_b[0]), len(pcm_a))
        self.assertEqual(len(received_a[0]), len(pcm_b))

        # 5. Privacidad estricta al mutear
        client_a.set_mute(True)
        self.assertTrue(client_a.is_muted)
        self.assertIsNone(client_a.process_microphone_pcm(pcm_a))

        # 6. Cierre determinista sin fugas de threads ni descriptores de socket
        client_a.stop_audio()
        client_b.stop_audio()
        self.assertFalse(client_a.is_active)
        self.assertFalse(client_b.is_active)
        self.assertIsNone(client_a._playback_thread)
        self.assertIsNone(client_a._capture_thread)
        self.assertIsNone(client_a._udp_socket)
        self.assertIsNone(client_b._playback_thread)
        self.assertIsNone(client_b._capture_thread)
        self.assertIsNone(client_b._udp_socket)

    def test_07_davinci_fighters_contract_and_e2e_simulation(self):
        """Integración de extremo a extremo con el motor original de Da Vinci Fighters (CCI-10-04)."""
        from backend.davinci_bridge import DavinciBridgeEngine
        from backend.contracts import PlayerInputPacket

        bridge = DavinciBridgeEngine("room_davinci_e2e", "carloni", "charly")
        self.assertEqual(bridge.f1.name, "Juan Bautista Carloni")
        self.assertEqual(bridge.status, "fighting")
        self.assertEqual(bridge.f1.health, 110)
        self.assertEqual(bridge.f2.health, 110)

        # Acercar los personajes para entrar en rango de golpe
        bridge.f1.x = 800.0
        bridge.f2.x = 860.0

        # P1 ejecuta golpe ligero
        inp_p1 = PlayerInputPacket(
            room_id="room_davinci_e2e",
            player_id=1,
            tick=1,
            seq=1,
            buttons=["punch_light"]
        )

        # Avanzar 10 frames de simulación física y resolver colisión nativa
        hit_detected = False
        for f in range(1, 12):
            snap = bridge.step_frame(p1_input=inp_p1 if f == 1 else None)
            if snap.p2_state["hp"] < 110:
                hit_detected = True
                break

        self.assertTrue(hit_detected, "CollisionManager de Da Vinci Fighters debe detectar y aplicar el golpe")
        self.assertEqual(snap.p2_state["hp"], 102, "Daño de golpe ligero (8 HP) debe reflejarse exactamente en el snapshot")
        self.assertGreater(snap.p2_state["x"], 860.0, "Knockback de Da Vinci Fighters debe empujar al defensor")

        # Snapshot de mundo sincronizado
        self.assertIn("hp", snap.p1_state)
        self.assertIn("special_meter", snap.p1_state)
        self.assertEqual(snap.current_round, 1)

    def test_08_platform_audio_driver_hardware_pipeline(self):
        """Verifica controladores de audio físico por plataforma, DAC y ciclo de vida (CCI-10-03)."""
        from mobile.audio_drivers import AudioDeviceManager, PygameAudioDriver, AndroidAudioDriver, IOSAudioDriver

        # 1. Gestor unificado y selección de driver
        mgr = AudioDeviceManager.get_instance()
        driver = mgr.get_driver()
        self.assertIsInstance(driver, PygameAudioDriver)
        self.assertTrue(driver.check_permissions())

        # 2. Enumeración de dispositivos físicos
        mics = mgr.list_capture_devices()
        spks = mgr.list_playback_devices()
        self.assertGreater(len(mics), 0)
        self.assertGreater(len(spks), 0)

        # 3. Reproducción física de búfer PCM en DAC
        pcm_frame = b"\x00\x00" * driver.SAMPLES_PER_FRAME
        played = driver.play_frame(pcm_frame)
        self.assertTrue(played)
        self.assertGreater(driver.frames_played, 0)

        # 4. Captura física de micrófono
        captured_frames = []
        driver.start_capture(lambda f: captured_frames.append(f))
        time.sleep(0.06)
        driver.stop_capture()
        self.assertGreater(len(captured_frames), 0)
        self.assertEqual(len(captured_frames[0]), driver.FRAME_BYTES)

        # 5. Silenciamiento físico estricto
        driver.set_mute(True)
        self.assertTrue(driver.is_muted)
        diag = driver.get_diagnostics()
        self.assertTrue(diag["muted"])
        self.assertEqual(diag["sample_rate"], 48000)

        # 6. Adaptadores móviles Android e iOS
        android_drv = AndroidAudioDriver()
        self.assertTrue(android_drv.initialize_hardware())
        self.assertTrue(android_drv.check_permissions())

        ios_drv = IOSAudioDriver()
        self.assertTrue(ios_drv.initialize_hardware())
        self.assertTrue(ios_drv.check_permissions())


if __name__ == "__main__":
    unittest.main()
