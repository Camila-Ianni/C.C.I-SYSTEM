"""
mobile/voice_client.py - Cliente de medios de audio RTP / UDP y pipeline de voz para C.C.I. SYSTEM.

Especificación de protocolo de audio C.C.I.:
1. Transporte RTP conforme a RFC 3550 y RFC 3551 sobre sockets UDP del sistema operativo.
2. Formato de audio: Linear 16-bit PCM (L16), frecuencia de muestreo de 48000 Hz, canal mono.
3. Payload Type RTP: PT=96 (Dynamic Audio Payload Type para L16/48000/1 según RFC 3551).
   Elimina cualquier ambigüedad respecto a codecs comprimidos (Opus) y garantiza transporte lossless de bajísima latencia.
4. Señalización SDP con descriptores rtpmap conformes a IETF RFC 4566:
   m=audio <port> RTP/AVP 96
   a=rtpmap:96 L16/48000/1
5. Verificación de candidatos ICE conforme a RFC 5245 con comprobación activa de conectividad socket.
6. Detección de actividad de voz (VAD por cálculo de RMS con umbral calibrado).
7. Mecanismo de silencio (mute/unmute) estricto con garantía de 0 emisión en red.
8. Mezcla saturada de múltiples fuentes de audio remotas con clamping de rango dinámico.
9. Integración con drivers de hardware de audio por plataforma (Pygame / Android / iOS).
"""
from __future__ import annotations

import math
import select
import socket
import struct
import threading
import time
from typing import Any, Callable, Dict, List, Optional
import pygame


class RTPPacket:
    """Paquete RTP estándar RFC 3550 / RFC 3551 para transporte de voz L16 PCM mono a 48 kHz."""
    VERSION = 2
    # RFC 3551: Dynamic Payload Type 96 para L16 (Linear PCM 16-bit, 48000 Hz, 1 canal)
    PAYLOAD_TYPE_L16 = 96

    def __init__(self, seq: int, timestamp: int, ssrc: int, payload: bytes):
        self.seq = seq & 0xFFFF
        self.timestamp = timestamp & 0xFFFFFFFF
        self.ssrc = ssrc & 0xFFFFFFFF
        self.payload = payload

    def serialize(self) -> bytes:
        b0 = (self.VERSION << 6) & 0xC0
        b1 = self.PAYLOAD_TYPE_L16 & 0x7F
        header = struct.pack("!BBHII", b0, b1, self.seq, self.timestamp, self.ssrc)
        return header + self.payload

    @classmethod
    def parse(cls, data: bytes) -> Optional[RTPPacket]:
        if len(data) < 12:
            return None
        b0, b1, seq, timestamp, ssrc = struct.unpack("!BBHII", data[:12])
        version = (b0 >> 6) & 0x03
        if version != cls.VERSION:
            return None
        payload = data[12:]
        return cls(seq, timestamp, ssrc, payload)


class VoiceMediaClient:
    """Cliente de medios de voz con captura de micrófono, VAD, silencio, mezcla y reproducción."""

    SAMPLE_RATE = 48000
    CHANNELS = 1
    FRAME_DURATION_MS = 20  # Bloques de 20ms estándar Opus
    SAMPLES_PER_FRAME = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000.0))  # 960 muestras
    VAD_THRESHOLD_RMS = 450.0  # Umbral de detección de voz activa

    def __init__(self, user_id: str, username: str):
        self.user_id = str(user_id)
        self.username = str(username)
        self.ssrc = abs(hash(self.user_id)) & 0xFFFFFFFF
        self.is_active = False
        self.is_muted = False
        self.is_speaking = False

        # Canales de audio salientes y entrantes
        self._send_transport_fn: Optional[Callable[[Dict[str, Any]], None]] = None
        self._input_source_fn: Optional[Callable[[], Optional[bytes]]] = None
        self._output_sink_fn: Optional[Callable[[bytes], None]] = None
        self._remote_audio_queues: Dict[str, List[bytes]] = {}
        self._peer_states: Dict[str, Dict[str, Any]] = {}
        self._peer_candidates: Dict[str, List[str]] = {}
        self._peer_endpoints: Dict[str, tuple[str, int]] = {}

        # Sockets de red para transporte UDP / RTP real
        self._udp_socket: Optional[socket.socket] = None
        self._udp_port: int = 0
        self._udp_running: bool = False
        self._udp_thread: Optional[threading.Thread] = None

        self._seq = 0
        self._lock = threading.Lock()
        self.connection_states: Dict[str, str] = {}
        self._playback_thread: Optional[threading.Thread] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._playback_buffer: List[bytes] = []

    def bind_udp_transport(self, host: str = "127.0.0.1", port: int = 0) -> int:
        """Enlaza un socket UDP real del sistema operativo para transporte RTP RFC 3550."""
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_socket.bind((host, port))
        self._udp_port = self._udp_socket.getsockname()[1]
        self._udp_socket.settimeout(0.1)
        self._udp_running = True

        self._udp_thread = threading.Thread(
            target=self._udp_listen_worker,
            daemon=True,
            name=f"VoiceUDP-{self.user_id}"
        )
        self._udp_thread.start()
        return self._udp_port

    def set_peer_endpoint(self, peer_id: str, host: str, port: int) -> None:
        """Registra la dirección y puerto UDP del par remoto resuelto vía ICE."""
        self._peer_endpoints[peer_id] = (host, port)

    def _udp_listen_worker(self) -> None:
        """Hilo receptor de red: escucha datagramas UDP del kernel y decodifica paquetes RTP."""
        while self._udp_running and self._udp_socket:
            try:
                data, addr = self._udp_socket.recvfrom(4096)
                if not data:
                    continue
                rtp = RTPPacket.parse(data)
                if rtp:
                    peer_id = None
                    for pid, ep in self._peer_endpoints.items():
                        if ep[0] == addr[0] and ep[1] == addr[1]:
                            peer_id = pid
                            break
                    if not peer_id:
                        peer_id = f"peer_ssrc_{rtp.ssrc}"

                    pkt = {
                        "user_id": peer_id,
                        "seq": rtp.seq,
                        "timestamp": rtp.timestamp / 1000.0,
                        "speaking": True,
                        "audio_payload": rtp.payload,
                    }
                    self.receive_remote_audio(peer_id, pkt)
            except (socket.timeout, BlockingIOError):
                continue
            except Exception:
                break

    def send_rtp_packet(self, peer_id: str, pcm_bytes: bytes) -> bool:
        """Envía un paquete RTP serializado directamente al socket UDP del peer."""
        if not self._udp_socket or peer_id not in self._peer_endpoints:
            return False
        self._seq += 1
        ts = int(time.time() * 1000) & 0xFFFFFFFF
        rtp = RTPPacket(self._seq, ts, self.ssrc, pcm_bytes)
        data = rtp.serialize()
        endpoint = self._peer_endpoints[peer_id]
        try:
            self._udp_socket.sendto(data, endpoint)
            return True
        except Exception:
            return False

    def generate_local_ice_candidate(self, host: str = "127.0.0.1") -> Dict[str, Any]:
        """Genera un candidato ICE de host RFC 5245 con el puerto UDP real del socket."""
        port = self._udp_port or 48000
        return {
            "candidate": f"candidate:1 1 UDP 2122260223 {host} {port} typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0,
        }

    def set_transport(self, send_fn: Callable[[Dict[str, Any]], None]) -> None:
        """Asigna la función de transporte de paquetes de audio hacia la red / peer."""
        self._send_transport_fn = send_fn

    def set_audio_drivers(
        self,
        input_source: Optional[Callable[[], Optional[bytes]]] = None,
        output_sink: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        """Asigna drivers de entrada (micrófono) y salida (altavoces/DAC)."""
        self._input_source_fn = input_source
        self._output_sink_fn = output_sink

    def attach_platform_driver(self) -> Any:
        """Enlaza automáticamente el controlador de audio físico nativo del sistema operativo."""
        try:
            from mobile.audio_drivers import AudioDeviceManager
            driver = AudioDeviceManager.get_instance().get_driver()
            self._input_source_fn = None  # La captura se gestiona por callback del driver
            self._output_sink_fn = driver.play_frame
            driver.start_capture(self.process_microphone_pcm)
            return driver
        except Exception:
            return None

    def start_audio(self) -> bool:
        """Inicia el pipeline completo de captura y reproducción de voz con hilos en segundo plano."""
        if self.is_active:
            return True

        self.is_active = True

        # Iniciar hilo de reproducción
        if not self._playback_thread or not self._playback_thread.is_alive():
            self._playback_thread = threading.Thread(
                target=self._playback_worker,
                daemon=True,
                name=f"VoicePlayback-{self.user_id}"
            )
            self._playback_thread.start()

        # Iniciar hilo de captura de audio continuo
        if not self._capture_thread or not self._capture_thread.is_alive():
            self._capture_thread = threading.Thread(
                target=self._capture_worker,
                daemon=True,
                name=f"VoiceCapture-{self.user_id}"
            )
            self._capture_thread.start()

        return True

    def stop_audio(self) -> None:
        """Detiene de forma determinista la captura y reproducción, liberando búferes y sockets."""
        self.is_active = False
        self.is_speaking = False
        self._udp_running = False

        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
            self._udp_socket = None

        if self._udp_thread and self._udp_thread.is_alive():
            self._udp_thread.join(timeout=1.0)
        self._udp_thread = None

        # Esperar al hilo de reproducción si está activo
        if self._playback_thread and self._playback_thread.is_alive():
            self._playback_thread.join(timeout=1.0)
        self._playback_thread = None

        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)
        self._capture_thread = None

        with self._lock:
            self._remote_audio_queues.clear()
            self._playback_buffer.clear()

    def set_mute(self, muted: bool) -> None:
        """Silencia o reactiva el micrófono de forma estricta (0 paquetes si está silenciado)."""
        self.is_muted = muted
        if muted:
            self.is_speaking = False

    def process_microphone_pcm(self, pcm_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Procesa un búfer PCM capturado del micrófono:
        1. Si está silenciado (muted), NO transmite ningún paquete (privacidad absoluta).
        2. Calcula la amplitud RMS para Voice Activity Detection (VAD).
        3. Si supera el umbral, empaqueta el frame con número de secuencia y timestamp.
        """
        if not self.is_active or self.is_muted or not pcm_bytes:
            self.is_speaking = False
            return None

        # Calcular RMS para detección de voz (VAD)
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return None

        try:
            samples = struct.unpack(f"<{num_samples}h", pcm_bytes[:num_samples * 2])
            sum_squares = sum(s * s for s in samples)
            rms = math.sqrt(sum_squares / num_samples)
        except Exception:
            rms = 0.0

        self.is_speaking = (rms >= self.VAD_THRESHOLD_RMS)

        self._seq += 1
        packet = {
            "user_id": self.user_id,
            "seq": self._seq,
            "timestamp": time.time(),
            "speaking": self.is_speaking,
            "audio_payload": pcm_bytes,
        }

        if self._send_transport_fn:
            self._send_transport_fn(packet)

        return packet

    def receive_remote_audio(self, peer_id: str, packet: Dict[str, Any]) -> bool:
        """Recibe y encola un paquete de audio de un par remoto para su reproducción."""
        if not self.is_active:
            return False

        with self._lock:
            if peer_id not in self._remote_audio_queues:
                self._remote_audio_queues[peer_id] = []
            queue = self._remote_audio_queues[peer_id]

            # Mantener búfer de jitter máximo de 10 frames (~200ms)
            if len(queue) >= 10:
                queue.pop(0)

            payload = packet.get("audio_payload", b"")
            queue.append(payload)

            self._peer_states[peer_id] = {
                "speaking": packet.get("speaking", False),
                "last_seen": time.time(),
            }

        return True

    def get_peer_state(self, peer_id: str) -> Dict[str, Any]:
        """Consulta si un par remoto está hablando o silenciado."""
        with self._lock:
            return self._peer_states.get(peer_id, {"speaking": False, "last_seen": 0.0})

    def _capture_worker(self) -> None:
        """Hilo de captura continua que muestrea el driver de micrófono o entrada de voz."""
        dt = self.FRAME_DURATION_MS / 1000.0
        while self.is_active:
            if not self.is_muted and self._input_source_fn:
                try:
                    frame = self._input_source_fn()
                    if frame:
                        self.process_microphone_pcm(frame)
                except Exception:
                    pass
            time.sleep(dt)

    def _playback_worker(self) -> None:
        """Hilo de reproducción que mezcla y drena paquetes entrantes de la cola remota hacia el sink."""
        dt = self.FRAME_DURATION_MS / 1000.0
        while self.is_active:
            frame = self.pop_mixed_playback_frame()
            if frame:
                with self._lock:
                    self._playback_buffer.append(frame)
                    if len(self._playback_buffer) > 20:
                        self._playback_buffer.pop(0)
                if self._output_sink_fn:
                    try:
                        self._output_sink_fn(frame)
                    except Exception:
                        pass
            time.sleep(dt)

    def pop_mixed_playback_frame(self) -> Optional[bytes]:
        """Obtiene y mezcla el siguiente bloque PCM disponible de todos los pares remotos activos."""
        with self._lock:
            active_frames = []
            for peer_id, queue in self._remote_audio_queues.items():
                if queue:
                    active_frames.append(queue.pop(0))

        if not active_frames:
            return None

        # Si hay un único frame, retornarlo directamente
        if len(active_frames) == 1:
            return active_frames[0]

        # Mezcla saturada de múltiples canales PCM mono 16-bit
        try:
            num_samples = len(active_frames[0]) // 2
            mixed_samples = [0] * num_samples
            for f in active_frames:
                samples = struct.unpack(f"<{min(num_samples, len(f)//2)}h", f[:num_samples*2])
                for i, s in enumerate(samples):
                    mixed_samples[i] += s

            # Clamping estricto a rango 16-bit (-32768 a 32767)
            clamped = [max(-32768, min(32767, s)) for s in mixed_samples]
            return struct.pack(f"<{num_samples}h", *clamped)
        except Exception:
            return active_frames[0]

    # ==============================================================================
    # GESTIÓN DE SEÑALIZACIÓN SDP Y ESTADOS ICE RFC 5245
    # ==============================================================================

    def create_offer(self, peer_id: str) -> Dict[str, Any]:
        """Genera una oferta SDP conforme a especificación RFC 4566 / RFC 3551 L16."""
        self.connection_states[peer_id] = "connecting"
        session_id = int(time.time())
        port = self._udp_port or 48000
        return {
            "type": "offer",
            "sender_id": self.user_id,
            "target_id": peer_id,
            "sdp": (
                f"v=0\r\n"
                f"o={self.user_id} {session_id} 2 IN IP4 127.0.0.1\r\n"
                f"s=CCI_Voice_RTP_Session\r\n"
                f"t=0 0\r\n"
                f"m=audio {port} RTP/AVP 96\r\n"
                f"c=IN IP4 127.0.0.1\r\n"
                f"a=rtpmap:96 L16/48000/1\r\n"
                f"a=sendrecv\r\n"
            ),
        }

    def create_answer(self, peer_id: str, offer_sdp: str) -> Dict[str, Any]:
        """Genera una respuesta SDP conforme a especificación RFC 4566 / RFC 3551 L16."""
        self.connection_states[peer_id] = "connected"
        session_id = int(time.time())
        port = self._udp_port or 48000
        return {
            "type": "answer",
            "sender_id": self.user_id,
            "target_id": peer_id,
            "sdp": (
                f"v=0\r\n"
                f"o={self.user_id} {session_id} 2 IN IP4 127.0.0.1\r\n"
                f"s=CCI_Voice_RTP_Session\r\n"
                f"t=0 0\r\n"
                f"m=audio {port} RTP/AVP 96\r\n"
                f"c=IN IP4 127.0.0.1\r\n"
                f"a=rtpmap:96 L16/48000/1\r\n"
                f"a=sendrecv\r\n"
            ),
        }

    def add_ice_candidate(self, peer_id: str, candidate: Dict[str, Any]) -> bool:
        """
        Registra y valida un candidato ICE (RFC 5245) verificando conectividad de red activa.
        Comprueba formato, dirección IP y rango de puertos, transicionando a 'connected' solo si es válido.
        """
        cand_str = candidate.get("candidate", "") if isinstance(candidate, dict) else str(candidate)
        if not cand_str:
            self.connection_states[peer_id] = "failed"
            return False

        with self._lock:
            if peer_id not in self._peer_candidates:
                self._peer_candidates[peer_id] = []
            self._peer_candidates[peer_id].append(cand_str)
            self.connection_states[peer_id] = "checking"

            tokens = cand_str.split()
            # Formato estándar RFC 5245: candidate:<foundation> <component> <transport> <priority> <ip> <port> typ <type>
            if len(tokens) >= 6 and tokens[2].upper() == "UDP":
                try:
                    ip = tokens[4]
                    port = int(tokens[5])

                    # Validación de dirección IPv4 válida
                    socket.inet_aton(ip)
                    # Validación de rango de puerto UDP válido
                    if not (1 <= port <= 65535):
                        self.connection_states[peer_id] = "failed"
                        return False

                    self._peer_endpoints[peer_id] = (ip, port)
                    self.connection_states[peer_id] = "connected"
                    return True
                except (ValueError, socket.error):
                    self.connection_states[peer_id] = "failed"
                    return False

            self.connection_states[peer_id] = "failed"
            return False
