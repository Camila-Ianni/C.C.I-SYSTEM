"""
backend/communities/voice_engine.py - Motor de voz de escritorio (Desktop Voice Engine) para C.C.I. Communities.

Especificación y alcance (P1-A):
1. Transporte WebRTC real sobre LiveKit SFU (`livekit.rtc`) con AudioSource / LocalAudioTrack / AudioStream.
2. Captura de micrófono y reproducción mezclada de auriculares en tiempo real via `sounddevice` (PortAudio),
   48000 Hz, mono PCM 16-bit (`int16`, bloques de 20 ms / 960 muestras).
3. Controles efectivos sobre el track RTC:
   - Mute: `LocalAudioTrack.mute()` / `unmute()` y corte de envío de frames PCM.
   - Deafen (Sordo): mutea el micrófono y silencia/descarta el audio entrante de peers remotos.
   - VAD local por energía RMS + detección de hablantes activos desde LiveKit.
4. Métricas reales obtenidas desde WebRTC `get_rtc_stats()` (RTT ms, jitter ms, packet loss %);
   permanecen en `None` cuando no hay transporte RTC activo.
5. Fallback honesto a modo solo señalización si el servidor LiveKit SFU no es alcanzable o falla el handshake.
"""
from __future__ import annotations

import asyncio
import math
import os
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

import numpy as np


def _get_livekit_rtc() -> Any:
    """Importa `livekit.rtc` de forma diferida para no cargar librerías nativas al inicio."""
    try:
        import livekit.rtc as mod
        return mod
    except Exception:  # pragma: no cover - fallback defensivo si falta la librería nativa
        return None


def _get_sounddevice() -> Any:
    """Importa `sounddevice` (PortAudio) sólo cuando se abre audio hardware real."""
    try:
        import sounddevice as mod
        return mod
    except Exception:  # pragma: no cover - fallback si no hay PortAudio en entorno headless
        return None


class DesktopVoiceEngine:
    """Motor de voz WebRTC (LiveKit SFU) + captura/playout PCM 48kHz para escritorio."""

    SAMPLE_RATE = 48000
    CHANNELS = 1
    FRAME_MS = 20
    FRAME_SAMPLES = (SAMPLE_RATE * FRAME_MS) // 1000  # 960 muestras por 20 ms
    VAD_RMS_THRESHOLD = 450.0

    _instance: Optional[DesktopVoiceEngine] = None

    @classmethod
    def get_instance(cls, user_id: str = "", username: str = "") -> DesktopVoiceEngine:
        if cls._instance is None:
            cls._instance = DesktopVoiceEngine(user_id=user_id, username=username)
        elif user_id and cls._instance.user_id != str(user_id):
            cls._instance.set_identity(user_id=str(user_id), username=str(username or user_id))
        return cls._instance

    def __init__(
        self,
        user_id: str = "",
        username: str = "",
        enable_audio_io: Optional[bool] = None,
    ):
        self.user_id = str(user_id)
        self.username = str(username)
        self._default_enable_audio_io = enable_audio_io

        self.is_connected = False
        self.active_community_id: Optional[str] = None
        self.active_channel_name: Optional[str] = None
        self.active_token_info: Optional[Dict[str, Any]] = None

        self.is_muted = False
        self.is_deafened = False
        self.is_speaking = False
        self._can_publish = True

        # Métricas reales únicamente (None mientras no haya transporte RTC de audio activo)
        self.latency_ms: Optional[float] = None
        self.jitter_ms: Optional[float] = None
        self.packet_loss_pct: Optional[float] = None
        self.media_transport_active: bool = False
        self.transport_protocol = "LiveKit WebRTC SFU (Signaling)"
        self.last_error: Optional[str] = None
        self.audio_io_active: bool = False

        # Estado de Streaming WebRTC de pantalla/juego (P1-B)
        self.is_screen_sharing: bool = False
        self.screen_share_source_id: Optional[str] = None
        self.screen_share_width: int = 0
        self.screen_share_height: int = 0
        self.screen_share_fps: int = 30
        self.screen_tx_frames: int = 0
        self.screen_rx_frames: int = 0
        self.remote_screen_active: bool = False

        # Callbacks opcionales hacia Desktop Controller / UI
        self.on_participants_changed: Optional[Callable[[List[Dict[str, Any]]], None]] = None
        self.on_state_changed: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_remote_audio_frame: Optional[Callable[[str, np.ndarray, int, int], None]] = None
        self.on_remote_screen_audio_frame: Optional[Callable[[str, np.ndarray, int, int], None]] = None
        self.on_remote_video_frame: Optional[Callable[[str, int, int, bytes], None]] = None
        self.on_remote_stream_ended: Optional[Callable[[str], None]] = None

        self._lock = threading.RLock()
        self._participants: Dict[str, Dict[str, Any]] = {}

        # Estado LiveKit asyncio en hilo dedicado
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._loop_ready = threading.Event()
        self._room: Any = None
        self._audio_source: Any = None
        self._local_track: Any = None
        self._local_pub: Any = None
        self._outbound_queue: Deque[np.ndarray] = deque(maxlen=25)
        self._outbound_wakeup: Optional[asyncio.Event] = None
        self._sender_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None
        self._subscriber_tasks: Dict[str, asyncio.Task] = {}
        self._subscriber_streams: Dict[str, Any] = {}
        self._stop_rtc = False

        # Estado RTC de video y audio de pantalla/juego (P1-B)
        self._video_source: Any = None
        self._video_track: Any = None
        self._video_pub: Any = None
        self._video_frame_queue: Deque[tuple[int, int, bytes]] = deque(maxlen=4)
        self._video_wakeup: Optional[asyncio.Event] = None
        self._video_sender_task: Optional[asyncio.Task] = None
        self._video_frame_provider: Optional[Callable[[], Optional[tuple[int, int, bytes]]]] = None
        self._screen_window_widget: Any = None
        self._screen_has_audio: bool = False
        self._screen_audio_source: Any = None
        self._screen_audio_track: Any = None
        self._screen_audio_pub: Any = None
        self._screen_audio_queue: Deque[np.ndarray] = deque(maxlen=30)
        self._screen_audio_wakeup: Optional[asyncio.Event] = None
        self._screen_audio_sender_task: Optional[asyncio.Task] = None
        self._video_subscriber_tasks: Dict[str, tuple[str, asyncio.Task]] = {}
        self._video_subscriber_streams: Dict[str, Any] = {}
        self._remote_video_frames: Dict[str, tuple[int, int, bytes]] = {}

        # Audio I/O (PortAudio via sounddevice) y buffers de mezcla por peer
        self._input_stream: Any = None
        self._output_stream: Any = None
        self._playout_lock = threading.Lock()
        self._playout_queues: Dict[str, Deque[np.ndarray]] = {}
        self._tx_frames_sent: int = 0
        self._rx_frames_received: int = 0

    def set_identity(self, user_id: str, username: str) -> None:
        """Actualiza la identidad autenticada del usuario local sin simular peers."""
        self.user_id = str(user_id)
        self.username = str(username)

    def _should_open_audio_io(self, enable_audio_io: Optional[bool]) -> bool:
        if os.getenv("CCI_DISABLE_AUDIO_IO", "").strip().lower() in ("1", "true", "yes"):
            return False
        if enable_audio_io is not None:
            want = bool(enable_audio_io)
        elif self._default_enable_audio_io is not None:
            want = bool(self._default_enable_audio_io)
        elif os.getenv("QT_QPA_PLATFORM", "").strip().lower() == "offscreen":
            # En pruebas offscreen headless sin petición explícita no abrimos hardware de micro/bocinas
            want = False
        else:
            want = True
        return want and (_get_sounddevice() is not None)

    def connect(
        self,
        community_id: str,
        channel_name: str,
        token_info: Optional[Dict[str, Any]] = None,
        enable_audio_io: Optional[bool] = None,
        connect_timeout: float = 4.0,
    ) -> bool:
        """Conecta el motor de voz al canal y establece sesión WebRTC real contra LiveKit SFU."""
        self.disconnect()

        with self._lock:
            self.is_connected = True
            self.active_community_id = community_id
            self.active_channel_name = channel_name
            self.active_token_info = dict(token_info) if isinstance(token_info, dict) else token_info
            self.last_error = None
            self.latency_ms = None
            self.jitter_ms = None
            self.packet_loss_pct = None
            self.media_transport_active = False
            self._tx_frames_sent = 0
            self._rx_frames_received = 0
            self._can_publish = bool(
                (token_info or {}).get("can_publish", True) if isinstance(token_info, dict) else True
            )

            self._participants = {}
            if self.user_id:
                self._participants[self.user_id] = {
                    "user_id": self.user_id,
                    "username": self.username or self.user_id,
                    "is_speaking": self.is_speaking,
                    "is_muted": self.is_muted or not self._can_publish,
                    "is_deafened": self.is_deafened,
                    "is_local": True,
                }

        lk_url = str((token_info or {}).get("url") or "").strip() if isinstance(token_info, dict) else ""
        lk_token = str((token_info or {}).get("token") or "").strip() if isinstance(token_info, dict) else ""
        lk_rtc = _get_livekit_rtc() if (lk_url and lk_token) else None

        if lk_rtc is not None and lk_url and lk_token:
            try:
                self._connect_livekit(
                    url=lk_url,
                    token=lk_token,
                    can_publish=self._can_publish,
                    connect_timeout=connect_timeout,
                )
                with self._lock:
                    self.media_transport_active = True
                    self.transport_protocol = "LiveKit WebRTC SFU (Opus/PCM 48kHz)"
                if self._should_open_audio_io(enable_audio_io):
                    self._start_audio_io()
            except Exception as exc:
                self._teardown_rtc()
                with self._lock:
                    self.media_transport_active = False
                    self.last_error = str(exc)
                    self.transport_protocol = "Signaling Only (LiveKit SFU unreachable)"
        else:
            with self._lock:
                self.media_transport_active = False
                self.transport_protocol = "Signaling Only (No LiveKit credentials)"

        self._notify_state_changed()
        self._notify_participants_changed()
        return True

    def _ensure_event_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is not None and self._loop.is_running():
            return self._loop

        self._loop_ready.clear()
        self._stop_rtc = False

        def _runner() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            self._loop_ready.set()
            try:
                loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                loop.close()

        t = threading.Thread(target=_runner, daemon=True, name="CCI-LiveKitVoice")
        t.start()
        self._loop_thread = t
        self._loop_ready.wait(timeout=3.0)
        assert self._loop is not None
        return self._loop

    def _connect_livekit(
        self,
        url: str,
        token: str,
        can_publish: bool,
        connect_timeout: float,
    ) -> None:
        lk_rtc = _get_livekit_rtc()
        if lk_rtc is None:
            raise RuntimeError("livekit.rtc no disponible.")
        loop = self._ensure_event_loop()

        async def _connect_coro() -> None:
            room = lk_rtc.Room(loop=loop)
            self._room = room
            self._outbound_wakeup = asyncio.Event()

            @room.on("participant_connected")
            def _on_part_conn(participant: Any) -> None:
                self._upsert_remote_participant(participant)

            @room.on("participant_disconnected")
            def _on_part_disc(participant: Any) -> None:
                pid = str(getattr(participant, "identity", "") or "")
                with self._lock:
                    self._participants.pop(pid, None)
                    had_video = pid in self._remote_video_frames
                    self._remote_video_frames.pop(pid, None)
                    self.remote_screen_active = bool(self._remote_video_frames)
                with self._playout_lock:
                    self._playout_queues.pop(pid, None)
                self._notify_participants_changed()
                if had_video and self.on_remote_stream_ended is not None:
                    try:
                        self.on_remote_stream_ended(pid)
                    except Exception:
                        pass

            @room.on("track_subscribed")
            def _on_track_sub(track: Any, publication: Any, participant: Any) -> None:
                kind = getattr(track, "kind", None)
                if kind == lk_rtc.TrackKind.KIND_AUDIO:
                    self._start_remote_audio_reader(track, publication, participant)
                elif kind == lk_rtc.TrackKind.KIND_VIDEO:
                    self._start_remote_video_reader(track, publication, participant)

            @room.on("track_unsubscribed")
            def _on_track_unsub(track: Any, publication: Any, participant: Any) -> None:
                sid = str(getattr(track, "sid", "") or getattr(publication, "sid", "") or "")
                kind = getattr(track, "kind", None)
                pid = str(getattr(participant, "identity", "") or "")
                if kind == lk_rtc.TrackKind.KIND_VIDEO:
                    self._stop_remote_video_reader(sid, pid=pid)
                else:
                    self._stop_remote_audio_reader(sid)
                    with self._playout_lock:
                        self._playout_queues.pop(pid, None)

            @room.on("track_muted")
            def _on_track_muted(participant: Any, publication: Any) -> None:
                pid = str(getattr(participant, "identity", "") or "")
                if pid and pid != self.user_id:
                    with self._lock:
                        if pid in self._participants:
                            self._participants[pid]["is_muted"] = True
                            self._participants[pid]["is_speaking"] = False
                    self._notify_participants_changed()

            @room.on("track_unmuted")
            def _on_track_unmuted(participant: Any, publication: Any) -> None:
                pid = str(getattr(participant, "identity", "") or "")
                if pid and pid != self.user_id:
                    with self._lock:
                        if pid in self._participants:
                            self._participants[pid]["is_muted"] = False
                    self._notify_participants_changed()

            @room.on("active_speakers_changed")
            def _on_speakers(speakers: List[Any]) -> None:
                speaking_ids = {str(getattr(s, "identity", "") or "") for s in (speakers or [])}
                with self._lock:
                    for uid, p in self._participants.items():
                        if p.get("is_local"):
                            continue
                        p["is_speaking"] = (uid in speaking_ids) and not p.get("is_muted", False)
                self._notify_participants_changed()

            @room.on("disconnected")
            def _on_room_disconnected(reason: Any) -> None:
                if not self._stop_rtc:
                    with self._lock:
                        self.media_transport_active = False
                        self.transport_protocol = f"Disconnected ({reason})"
                    self._notify_state_changed()

            opts = lk_rtc.RoomOptions(
                auto_subscribe=True,
                dynacast=False,
                connect_timeout=max(1.0, float(connect_timeout)),
            )
            await room.connect(url, token, options=opts)

            # Sincronizar participantes remotos que ya estaban en la sala
            for rp in list(room.remote_participants.values()):
                self._upsert_remote_participant(rp)
                for pub in list(getattr(rp, "track_publications", {}).values()):
                    trk = getattr(pub, "track", None)
                    kind = getattr(trk, "kind", None) if trk is not None else None
                    if kind == lk_rtc.TrackKind.KIND_AUDIO:
                        self._start_remote_audio_reader(trk, pub, rp)
                    elif kind == lk_rtc.TrackKind.KIND_VIDEO:
                        self._start_remote_video_reader(trk, pub, rp)

            if can_publish:
                source = lk_rtc.AudioSource(
                    self.SAMPLE_RATE,
                    self.CHANNELS,
                    queue_size_ms=250,
                    loop=loop,
                )
                track = lk_rtc.LocalAudioTrack.create_audio_track("microphone", source)
                pub_opts = lk_rtc.TrackPublishOptions(
                    source=lk_rtc.TrackSource.SOURCE_MICROPHONE,
                )
                pub = await room.local_participant.publish_track(track, pub_opts)
                self._audio_source = source
                self._local_track = track
                self._local_pub = pub
                if self.is_muted or self.is_deafened:
                    track.mute()
                self._sender_task = loop.create_task(self._outbound_sender_loop())

            self._stats_task = loop.create_task(self._stats_poll_loop())

        fut = asyncio.run_coroutine_threadsafe(_connect_coro(), loop)
        fut.result(timeout=float(connect_timeout) + 2.0)

    def _upsert_remote_participant(self, participant: Any) -> None:
        pid = str(getattr(participant, "identity", "") or "")
        if not pid or pid == self.user_id:
            return
        pname = str(getattr(participant, "name", "") or pid)
        lk_rtc = _get_livekit_rtc()
        muted = False
        for pub in list(getattr(participant, "track_publications", {}).values()):
            if lk_rtc is not None and getattr(pub, "kind", None) == lk_rtc.TrackKind.KIND_AUDIO:
                muted = bool(getattr(pub, "muted", False))
                break
        with self._lock:
            prev = self._participants.get(pid, {})
            self._participants[pid] = {
                "user_id": pid,
                "username": pname,
                "is_speaking": bool(prev.get("is_speaking", False)) and not muted,
                "is_muted": muted,
                "is_deafened": bool(prev.get("is_deafened", False)),
                "is_local": False,
            }
        self._notify_participants_changed()

    def _start_remote_audio_reader(self, track: Any, publication: Any, participant: Any) -> None:
        loop = self._loop
        lk_rtc = _get_livekit_rtc()
        if loop is None or lk_rtc is None:
            return
        sid = str(getattr(track, "sid", "") or getattr(publication, "sid", "") or id(track))
        if sid in self._subscriber_tasks:
            return
        pid = str(getattr(participant, "identity", "") or sid)
        is_screenshare_audio = (
            getattr(publication, "source", None) == lk_rtc.TrackSource.SOURCE_SCREENSHARE_AUDIO
        )
        stream = lk_rtc.AudioStream.from_track(
            track=track,
            loop=loop,
            sample_rate=self.SAMPLE_RATE,
            num_channels=self.CHANNELS,
            frame_size_ms=self.FRAME_MS,
        )
        self._subscriber_streams[sid] = stream

        async def _reader() -> None:
            try:
                async for event in stream:
                    if self._stop_rtc:
                        break
                    frame = getattr(event, "frame", None)
                    if frame is None:
                        continue
                    if self.is_deafened:
                        with self._playout_lock:
                            self._playout_queues.pop(pid, None)
                        continue
                    pcm = np.frombuffer(frame.data, dtype=np.int16).copy()
                    playout_key = f"{pid}:screen" if is_screenshare_audio else pid
                    with self._playout_lock:
                        q = self._playout_queues.get(playout_key)
                        if q is None:
                            q = deque(maxlen=15)
                            self._playout_queues[playout_key] = q
                        # Trocear en bloques exactos de FRAME_SAMPLES para mixer estable
                        for off in range(0, len(pcm), self.FRAME_SAMPLES):
                            chunk = pcm[off:off + self.FRAME_SAMPLES]
                            if len(chunk) < self.FRAME_SAMPLES:
                                padded = np.zeros(self.FRAME_SAMPLES, dtype=np.int16)
                                padded[:len(chunk)] = chunk
                                chunk = padded
                            q.append(chunk)
                    self._rx_frames_received += 1
                    sr, nch = int(frame.sample_rate), int(frame.num_channels)
                    cb = self.on_remote_screen_audio_frame if (is_screenshare_audio and self.on_remote_screen_audio_frame is not None) else self.on_remote_audio_frame
                    if cb is not None:
                        try:
                            cb(pid, pcm, sr, nch)
                        except Exception:
                            pass
                    if is_screenshare_audio and self.on_remote_audio_frame is not None and cb is not self.on_remote_audio_frame:
                        try:
                            self.on_remote_audio_frame(pid, pcm, sr, nch)
                        except Exception:
                            pass
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            finally:
                try:
                    await stream.aclose()
                except Exception:
                    pass
                self._subscriber_streams.pop(sid, None)
                self._subscriber_tasks.pop(sid, None)

        self._subscriber_tasks[sid] = loop.create_task(_reader())

    def _stop_remote_audio_reader(self, sid: str) -> None:
        task = self._subscriber_tasks.pop(sid, None)
        if task is not None and not task.done():
            task.cancel()
        stream = self._subscriber_streams.pop(sid, None)
        if stream is not None and self._loop and self._loop.is_running():
            try:
                self._loop.create_task(stream.aclose())
            except Exception:
                pass

    def _start_remote_video_reader(self, track: Any, publication: Any, participant: Any) -> None:
        loop = self._loop
        lk_rtc = _get_livekit_rtc()
        if loop is None or lk_rtc is None:
            return
        sid = str(getattr(track, "sid", "") or getattr(publication, "sid", "") or id(track))
        if sid in self._video_subscriber_tasks:
            return
        pid = str(getattr(participant, "identity", "") or sid)
        stream = lk_rtc.VideoStream.from_track(
            track=track,
            loop=loop,
            format=lk_rtc.VideoBufferType.RGBA,
            capacity=4,
        )
        self._video_subscriber_streams[sid] = stream
        with self._lock:
            self.remote_screen_active = True

        async def _reader() -> None:
            try:
                async for event in stream:
                    if self._stop_rtc:
                        break
                    frame = getattr(event, "frame", None)
                    if frame is None:
                        continue
                    w, h = int(getattr(frame, "width", 0)), int(getattr(frame, "height", 0))
                    raw = bytes(getattr(frame, "data", b""))
                    if w <= 0 or h <= 0 or len(raw) < w * h * 4:
                        continue
                    rgba = raw[: w * h * 4]
                    with self._lock:
                        self._remote_video_frames[pid] = (w, h, rgba)
                        self.remote_screen_active = True
                        self.screen_rx_frames += 1
                    cb = self.on_remote_video_frame
                    if cb is not None:
                        try:
                            cb(pid, w, h, rgba)
                        except Exception:
                            pass
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            finally:
                try:
                    await stream.aclose()
                except Exception:
                    pass
                self._video_subscriber_streams.pop(sid, None)
                self._video_subscriber_tasks.pop(sid, None)
                with self._lock:
                    self._remote_video_frames.pop(pid, None)
                    self.remote_screen_active = bool(self._remote_video_frames)

        self._video_subscriber_tasks[sid] = (pid, loop.create_task(_reader()))

    def _stop_remote_video_reader(self, sid: str, pid: str = "") -> None:
        entry = self._video_subscriber_tasks.pop(sid, None)
        if entry is not None:
            stored_pid, task = entry
            if not pid:
                pid = stored_pid
            if task is not None and not task.done():
                task.cancel()
        stream = self._video_subscriber_streams.pop(sid, None)
        if stream is not None and self._loop and self._loop.is_running():
            try:
                self._loop.create_task(stream.aclose())
            except Exception:
                pass
        if pid:
            with self._lock:
                self._remote_video_frames.pop(pid, None)
                self.remote_screen_active = bool(self._remote_video_frames)
            if self.on_remote_stream_ended is not None:
                try:
                    self.on_remote_stream_ended(pid)
                except Exception:
                    pass

    async def _drain_audio_queue_loop(
        self,
        queue_obj: Deque[np.ndarray],
        wakeup_attr: str,
        source_attr: str,
        respect_mute: bool = True,
    ) -> None:
        lk_rtc = _get_livekit_rtc()
        wakeup = getattr(self, wakeup_attr, None)
        if wakeup is None or lk_rtc is None:
            return
        while not self._stop_rtc:
            await wakeup.wait()
            wakeup.clear()
            while queue_obj and not self._stop_rtc:
                src = getattr(self, source_attr, None)
                if src is None or (respect_mute and (self.is_muted or self.is_deafened)):
                    queue_obj.clear()
                    break
                pcm = queue_obj.popleft()
                if len(pcm) != self.FRAME_SAMPLES:
                    fixed = np.zeros(self.FRAME_SAMPLES, dtype=np.int16)
                    take = min(len(pcm), self.FRAME_SAMPLES)
                    fixed[:take] = pcm[:take]
                    pcm = fixed
                frame = lk_rtc.AudioFrame(
                    pcm.tobytes(),
                    self.SAMPLE_RATE,
                    self.CHANNELS,
                    self.FRAME_SAMPLES,
                )
                try:
                    await src.capture_frame(frame)
                    self._tx_frames_sent += 1
                except Exception:
                    break

    async def _outbound_sender_loop(self) -> None:
        await self._drain_audio_queue_loop(
            self._outbound_queue, "_outbound_wakeup", "_audio_source", respect_mute=True
        )

    async def _screen_audio_sender_loop(self) -> None:
        await self._drain_audio_queue_loop(
            self._screen_audio_queue, "_screen_audio_wakeup", "_screen_audio_source", respect_mute=False
        )

    async def _video_sender_loop(self) -> None:
        lk_rtc = _get_livekit_rtc()
        wakeup = self._video_wakeup
        if wakeup is None or lk_rtc is None:
            return
        from backend.communities.stream_adapter import capture_source_rgba, resize_rgba_frame

        while not self._stop_rtc and self._video_source is not None:
            fps = max(1, int(self.screen_share_fps or 30))
            interval = 1.0 / float(fps)
            try:
                await asyncio.wait_for(wakeup.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            wakeup.clear()
            if self._stop_rtc or self._video_source is None:
                break

            frame_tuple: Optional[tuple[int, int, bytes]] = None
            if self._video_frame_queue:
                frame_tuple = self._video_frame_queue.popleft()
            elif self._video_frame_provider is not None:
                try:
                    frame_tuple = self._video_frame_provider()
                except Exception:
                    frame_tuple = None
            elif self.screen_share_source_id:
                frame_tuple = capture_source_rgba(
                    source_id=self.screen_share_source_id,
                    target_width=self.screen_share_width or 1280,
                    target_height=self.screen_share_height or 720,
                    window_widget=self._screen_window_widget,
                )

            if frame_tuple is None:
                continue
            fw, fh, rgba = frame_tuple
            tw = self.screen_share_width or fw
            th = self.screen_share_height or fh
            if fw != tw or fh != th or len(rgba) != tw * th * 4:
                fw, fh, rgba = resize_rgba_frame(fw, fh, rgba, tw, th)
            if len(rgba) != fw * fh * 4:
                continue
            try:
                vf = lk_rtc.VideoFrame(fw, fh, lk_rtc.VideoBufferType.RGBA, rgba)
                self._video_source.capture_frame(vf)
                self.screen_tx_frames += 1
            except Exception:
                pass

    async def _stats_poll_loop(self) -> None:
        while not self._stop_rtc and self._room is not None:
            try:
                await asyncio.sleep(1.0)
                if self._stop_rtc or self._room is None:
                    break
                stats = await self._room.get_rtc_stats()
                rtt_ms: Optional[float] = None
                jitter_ms: Optional[float] = None
                loss_pct: Optional[float] = None
                for entry in list(getattr(stats, "publisher_stats", [])) + list(getattr(stats, "subscriber_stats", [])):
                    which = entry.WhichOneof("stats")
                    if which == "candidate_pair":
                        cp = entry.candidate_pair
                        if getattr(cp, "current_round_trip_time", 0.0) > 0:
                            rtt_ms = round(float(cp.current_round_trip_time) * 1000.0, 2)
                    elif which == "inbound_rtp":
                        inb = entry.inbound
                        if getattr(inb, "jitter", 0.0) >= 0:
                            jitter_ms = round(float(inb.jitter) * 1000.0, 2)
                        rec = int(getattr(inb, "packets_received", 0))
                        lost = max(0, int(getattr(inb, "packets_lost", 0)))
                        if rec + lost > 0:
                            loss_pct = round((lost / (rec + lost)) * 100.0, 2)
                if rtt_ms is not None or jitter_ms is not None or loss_pct is not None:
                    with self._lock:
                        if rtt_ms is not None:
                            self.latency_ms = rtt_ms
                        if jitter_ms is not None:
                            self.jitter_ms = jitter_ms
                        if loss_pct is not None:
                            self.packet_loss_pct = loss_pct
                    self._notify_state_changed()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def _enqueue_audio_samples(
        self,
        samples: np.ndarray,
        queue: Deque[np.ndarray],
        wakeup: Optional[asyncio.Event],
    ) -> bool:
        arr = np.asarray(samples, dtype=np.int16).reshape(-1)
        if arr.size == 0 or self._loop is None or wakeup is None:
            return False
        for off in range(0, arr.size, self.FRAME_SAMPLES):
            chunk = arr[off:off + self.FRAME_SAMPLES]
            if chunk.size < self.FRAME_SAMPLES:
                padded = np.zeros(self.FRAME_SAMPLES, dtype=np.int16)
                padded[:chunk.size] = chunk
                chunk = padded
            queue.append(chunk.copy())
        try:
            self._loop.call_soon_threadsafe(wakeup.set)
            return True
        except Exception:
            return False

    def push_pcm_frame(self, samples: np.ndarray) -> bool:
        """Inyecta un frame PCM int16 (48kHz mono) hacia LiveKit SFU y actualiza VAD local.

        Respeta mute/deafen/can_publish inmediatamente (no envía audio cuando está silenciado).
        """
        arr = np.asarray(samples, dtype=np.int16).reshape(-1)
        if arr.size == 0:
            return False

        # Cálculo RMS para VAD local incluso antes de descartar por mute
        rms = math.sqrt(float(np.mean(arr.astype(np.float64) ** 2))) if arr.size else 0.0
        speaking_now = (not self.is_muted) and (not self.is_deafened) and self._can_publish and (rms >= self.VAD_RMS_THRESHOLD)
        if speaking_now != self.is_speaking:
            self.set_speaking(speaking_now)

        if self.is_muted or self.is_deafened or not self._can_publish:
            return False
        if not self.media_transport_active:
            return False
        return self._enqueue_audio_samples(arr, self._outbound_queue, self._outbound_wakeup)

    def push_screen_audio_frame(self, samples: np.ndarray) -> bool:
        """Inyecta audio de pantalla/juego PCM int16 (48kHz mono) hacia LiveKit SFU."""
        if (
            not self.is_screen_sharing
            or not self._screen_has_audio
            or not self.media_transport_active
            or self._screen_audio_source is None
        ):
            return False
        return self._enqueue_audio_samples(samples, self._screen_audio_queue, self._screen_audio_wakeup)

    def push_video_frame(self, width: int, height: int, rgba_bytes: bytes) -> bool:
        """Inyecta un frame RGBA capturado hacia el track WebRTC de compartir pantalla."""
        if (
            not self.is_screen_sharing
            or not self.media_transport_active
            or self._loop is None
            or self._video_wakeup is None
            or self._video_source is None
        ):
            return False
        if not rgba_bytes or int(width) <= 0 or int(height) <= 0:
            return False
        self._video_frame_queue.append((int(width), int(height), bytes(rgba_bytes)))
        try:
            self._loop.call_soon_threadsafe(self._video_wakeup.set)
            return True
        except Exception:
            return False

    def get_latest_remote_video_frame(
        self, participant_id: Optional[str] = None
    ) -> Optional[tuple[str, int, int, bytes]]:
        """Obtiene el último frame RGBA recibido de pantalla/juego remoto."""
        with self._lock:
            if participant_id:
                item = self._remote_video_frames.get(str(participant_id))
                if item is None:
                    return None
                return (str(participant_id), item[0], item[1], item[2])
            for pid in reversed(list(self._remote_video_frames.keys())):
                item = self._remote_video_frames.get(pid)
                if item is not None:
                    return (pid, item[0], item[1], item[2])
            return None

    async def _publish_screen_share_coro(
        self,
        width: int,
        height: int,
        fps: int,
        with_audio: bool,
        max_bitrate: int,
    ) -> str:
        lk_rtc = _get_livekit_rtc()
        room = self._room
        if lk_rtc is None or room is None:
            raise RuntimeError("LiveKit Room no conectado")

        await self._unpublish_screen_share_coro()

        vsrc = lk_rtc.VideoSource(int(width), int(height), is_screencast=True)
        vtrack = lk_rtc.LocalVideoTrack.create_video_track("screen-video", vsrc)
        vopts = lk_rtc.TrackPublishOptions(
            source=lk_rtc.TrackSource.SOURCE_SCREENSHARE,
            simulcast=False,
            video_codec=lk_rtc.VideoCodec.VP8,
            video_encoding=lk_rtc.VideoEncoding(
                max_bitrate=max(250_000, int(max_bitrate)),
                max_framerate=max(1, int(fps)),
            ),
        )
        vpub = await room.local_participant.publish_track(vtrack, vopts)
        pub_sid = str(getattr(vpub, "sid", "") or "")
        if not pub_sid:
            try:
                await vsrc.aclose()
            except Exception:
                pass
            raise RuntimeError("LiveKit SFU no confirmó SID de track de pantalla")

        self._video_source = vsrc
        self._video_track = vtrack
        self._video_pub = vpub
        self._video_wakeup = asyncio.Event()
        self._video_frame_queue.clear()

        if with_audio:
            asrc = lk_rtc.AudioSource(self.SAMPLE_RATE, self.CHANNELS, queue_size_ms=200)
            atrack = lk_rtc.LocalAudioTrack.create_audio_track("screen-audio", asrc)
            aopts = lk_rtc.TrackPublishOptions(source=lk_rtc.TrackSource.SOURCE_SCREENSHARE_AUDIO)
            apub = await room.local_participant.publish_track(atrack, aopts)
            if not getattr(apub, "sid", None):
                try:
                    await room.local_participant.unpublish_track(pub_sid)
                except Exception:
                    pass
                try:
                    await vsrc.aclose()
                    await asrc.aclose()
                except Exception:
                    pass
                self._video_source = None
                self._video_track = None
                self._video_pub = None
                raise RuntimeError("LiveKit SFU no confirmó SID de audio de pantalla")
            self._screen_audio_source = asrc
            self._screen_audio_track = atrack
            self._screen_audio_pub = apub
            self._screen_audio_wakeup = asyncio.Event()
            self._screen_audio_queue.clear()
            self._screen_audio_sender_task = asyncio.create_task(self._screen_audio_sender_loop())

        self._video_sender_task = asyncio.create_task(self._video_sender_loop())
        return pub_sid

    async def _unpublish_screen_share_coro(self) -> None:
        if self._video_sender_task and not self._video_sender_task.done():
            self._video_sender_task.cancel()
        self._video_sender_task = None

        if self._screen_audio_sender_task and not self._screen_audio_sender_task.done():
            self._screen_audio_sender_task.cancel()
        self._screen_audio_sender_task = None

        self._video_frame_queue.clear()
        self._screen_audio_queue.clear()
        self._video_wakeup = None
        self._screen_audio_wakeup = None

        room = self._room
        for pub_attr in ("_video_pub", "_screen_audio_pub"):
            pub = getattr(self, pub_attr, None)
            setattr(self, pub_attr, None)
            if room is not None and pub is not None and getattr(pub, "sid", None):
                try:
                    await room.local_participant.unpublish_track(pub.sid)
                except Exception:
                    pass

        self._video_track = None
        self._screen_audio_track = None

        for src_attr in ("_video_source", "_screen_audio_source"):
            src = getattr(self, src_attr, None)
            setattr(self, src_attr, None)
            if src is not None:
                try:
                    await src.aclose()
                except Exception:
                    pass

    def start_screen_share(
        self,
        source_id: str = "screen:0",
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        with_audio: bool = False,
        max_bitrate: int = 2_500_000,
        frame_provider: Optional[Callable[[], Optional[tuple[int, int, bytes]]]] = None,
        window_widget: Any = None,
        timeout: float = 5.0,
    ) -> bool:
        """Publica un track real de pantalla/ventana (+ audio opcional) en LiveKit SFU."""
        if (
            not self.media_transport_active
            or self._room is None
            or self._loop is None
            or not self._loop.is_running()
            or not self._can_publish
        ):
            with self._lock:
                self.is_screen_sharing = False
                self.last_error = "Transporte LiveKit RTC no activo o sin permiso para publicar pantalla"
            self._notify_state_changed()
            return False

        w = max(16, int(width or 1280))
        h = max(16, int(height or 720))
        fps_val = max(1, min(60, int(fps or 30)))

        with self._lock:
            self.screen_share_source_id = str(source_id or "screen:0")
            self.screen_share_width = w
            self.screen_share_height = h
            self.screen_share_fps = fps_val
            self.screen_tx_frames = 0
            self._video_frame_provider = frame_provider
            self._screen_window_widget = window_widget
            self._screen_has_audio = bool(with_audio)

        try:
            fut = asyncio.run_coroutine_threadsafe(
                self._publish_screen_share_coro(w, h, fps_val, bool(with_audio), int(max_bitrate)),
                self._loop,
            )
            pub_sid = fut.result(timeout=max(1.0, float(timeout)))
            with self._lock:
                self.is_screen_sharing = bool(pub_sid)
                self.last_error = None
            self._notify_state_changed()
            return bool(pub_sid)
        except Exception as exc:
            self.stop_screen_share()
            with self._lock:
                self.is_screen_sharing = False
                self.last_error = f"Error publicando pantalla RTC: {exc}"
            self._notify_state_changed()
            return False

    def stop_screen_share(self, timeout: float = 3.0) -> bool:
        """Detiene y despublica los tracks LiveKit de pantalla/juego."""
        loop = self._loop
        if loop is not None and loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._unpublish_screen_share_coro(), loop)
                fut.result(timeout=max(0.5, float(timeout)))
            except Exception:
                pass
        with self._lock:
            self.is_screen_sharing = False
            self.screen_share_source_id = None
            self.screen_share_width = 0
            self.screen_share_height = 0
            self.screen_tx_frames = 0
            self._video_frame_provider = None
            self._screen_window_widget = None
            self._screen_has_audio = False
        self._notify_state_changed()
        return True

    def _start_audio_io(self) -> None:
        sd = _get_sounddevice()
        if sd is None:
            return
        self._stop_audio_io()

        def _in_cb(indata, frames, time_info, status):
            if self._stop_rtc:
                return
            try:
                self.push_pcm_frame(indata[:, 0])
            except Exception:
                pass

        def _out_cb(outdata, frames, time_info, status):
            outdata.fill(0)
            if self._stop_rtc or self.is_deafened:
                return
            mixed = np.zeros(frames, dtype=np.int32)
            with self._playout_lock:
                for q in self._playout_queues.values():
                    if not q:
                        continue
                    chunk = q.popleft()
                    take = min(frames, len(chunk))
                    mixed[:take] += chunk[:take].astype(np.int32)
            np.clip(mixed, -32768, 32767, out=mixed)
            outdata[:frames, 0] = mixed.astype(np.int16)

        try:
            if self._can_publish:
                self._input_stream = sd.InputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype="int16",
                    blocksize=self.FRAME_SAMPLES,
                    callback=_in_cb,
                )
                self._input_stream.start()
        except Exception:
            self._input_stream = None

        try:
            self._output_stream = sd.OutputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="int16",
                blocksize=self.FRAME_SAMPLES,
                callback=_out_cb,
            )
            self._output_stream.start()
        except Exception:
            self._output_stream = None

        self.audio_io_active = bool(self._input_stream or self._output_stream)

    def _stop_audio_io(self) -> None:
        for attr in ("_input_stream", "_output_stream"):
            st = getattr(self, attr, None)
            setattr(self, attr, None)
            if st is not None:
                try:
                    st.stop()
                except Exception:
                    pass
                try:
                    st.close()
                except Exception:
                    pass
        self.audio_io_active = False

    def _teardown_rtc(self) -> None:
        self._stop_rtc = True
        self._stop_audio_io()
        self._outbound_queue.clear()
        self._screen_audio_queue.clear()
        self._video_frame_queue.clear()
        with self._playout_lock:
            self._playout_queues.clear()

        loop = self._loop
        thread = self._loop_thread
        if loop is not None and loop.is_running():
            async def _cleanup() -> None:
                await self._unpublish_screen_share_coro()
                if self._sender_task and not self._sender_task.done():
                    self._sender_task.cancel()
                if self._stats_task and not self._stats_task.done():
                    self._stats_task.cancel()
                for sid in list(self._subscriber_tasks.keys()):
                    t = self._subscriber_tasks.pop(sid, None)
                    if t and not t.done():
                        t.cancel()
                for sid in list(self._subscriber_streams.keys()):
                    st = self._subscriber_streams.pop(sid, None)
                    if st:
                        try:
                            await st.aclose()
                        except Exception:
                            pass
                for sid in list(self._video_subscriber_tasks.keys()):
                    item = self._video_subscriber_tasks.pop(sid, None)
                    if item and item[1] and not item[1].done():
                        item[1].cancel()
                for sid in list(self._video_subscriber_streams.keys()):
                    vst = self._video_subscriber_streams.pop(sid, None)
                    if vst:
                        try:
                            await vst.aclose()
                        except Exception:
                            pass
                room = self._room
                self._room = None
                pub = self._local_pub
                self._local_pub = None
                self._local_track = None
                if room is not None:
                    if pub is not None:
                        try:
                            await room.local_participant.unpublish_track(pub.sid)
                        except Exception:
                            pass
                    try:
                        await room.disconnect()
                    except Exception:
                        pass
                src = self._audio_source
                self._audio_source = None
                if src is not None:
                    try:
                        await src.aclose()
                    except Exception:
                        pass

            try:
                fut = asyncio.run_coroutine_threadsafe(_cleanup(), loop)
                fut.result(timeout=2.5)
            except Exception:
                pass
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass

        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        self._loop = None
        self._loop_thread = None
        self._outbound_wakeup = None
        self._sender_task = None
        self._stats_task = None
        self._video_wakeup = None
        self._screen_audio_wakeup = None
        self._video_sender_task = None
        self._screen_audio_sender_task = None
        self._video_frame_provider = None
        self._screen_window_widget = None
        with self._lock:
            self.is_screen_sharing = False
            self.remote_screen_active = False
            self._remote_video_frames.clear()

    def sync_remote_participants(self, participants: List[Dict[str, Any]]) -> None:
        """Sincroniza la lista de participantes reales reportados por backend/SFU."""
        with self._lock:
            updated: Dict[str, Dict[str, Any]] = {}
            if self.is_connected and self.user_id:
                updated[self.user_id] = {
                    "user_id": self.user_id,
                    "username": self.username or self.user_id,
                    "is_speaking": self.is_speaking,
                    "is_muted": self.is_muted,
                    "is_deafened": self.is_deafened,
                    "is_local": True,
                }
            for p in participants or []:
                uid = str(p.get("user_id") or "")
                if not uid or uid == self.user_id:
                    continue
                updated[uid] = {
                    "user_id": uid,
                    "username": str(p.get("username") or uid),
                    "is_speaking": bool(p.get("is_speaking", False)),
                    "is_muted": bool(p.get("is_muted", False)),
                    "is_deafened": bool(p.get("is_deafened", False)),
                    "is_local": False,
                }
            self._participants = updated
        self._notify_participants_changed()

    def disconnect(self) -> bool:
        """Desconecta el motor de voz, cierra streams WebRTC/audio y reinicia métricas."""
        self._teardown_rtc()
        with self._lock:
            self.is_connected = False
            self.media_transport_active = False
            self.active_community_id = None
            self.active_channel_name = None
            self.active_token_info = None
            self.is_speaking = False
            self.is_screen_sharing = False
            self.screen_share_source_id = None
            self.screen_share_width = 0
            self.screen_share_height = 0
            self.screen_tx_frames = 0
            self.screen_rx_frames = 0
            self.remote_screen_active = False
            self._remote_video_frames.clear()
            self.latency_ms = None
            self.jitter_ms = None
            self.packet_loss_pct = None
            self.last_error = None
            self.transport_protocol = "LiveKit WebRTC SFU (Signaling)"
            self._participants.clear()
        self._notify_participants_changed()
        self._notify_state_changed()
        return True

    def _apply_local_track_mute(self) -> None:
        should_mute = bool(self.is_muted or self.is_deafened)
        if should_mute:
            self._outbound_queue.clear()
        track = self._local_track
        loop = self._loop
        if track is None or loop is None or not loop.is_running():
            return

        done = threading.Event() if threading.current_thread() is not self._loop_thread else None

        def _toggle() -> None:
            try:
                if should_mute:
                    track.mute()
                else:
                    track.unmute()
            except Exception:
                pass
            src = self._audio_source
            if should_mute and src is not None:
                try:
                    src.clear_queue()
                except Exception:
                    pass
            if done is not None:
                done.set()

        try:
            loop.call_soon_threadsafe(_toggle)
            if done is not None:
                done.wait(timeout=0.5)
        except Exception:
            pass

    def set_mute(self, muted: Optional[bool] = None) -> bool:
        """Alterna o establece el silencio del micrófono sobre el track RTC activo."""
        with self._lock:
            if muted is None:
                self.is_muted = not self.is_muted
            else:
                self.is_muted = bool(muted)

            if self.is_muted:
                self.is_speaking = False

            if self.user_id in self._participants:
                self._participants[self.user_id]["is_muted"] = self.is_muted
                self._participants[self.user_id]["is_speaking"] = self.is_speaking

        self._apply_local_track_mute()
        self._notify_participants_changed()
        self._notify_state_changed()
        return self.is_muted

    def set_deafen(self, deafened: Optional[bool] = None) -> bool:
        """Alterna o establece el estado ensordecido (mutea track RTC y corta reproducción)."""
        with self._lock:
            if deafened is None:
                self.is_deafened = not self.is_deafened
            else:
                self.is_deafened = bool(deafened)

            if self.is_deafened:
                self.is_muted = True
                self.is_speaking = False
            else:
                self.is_muted = False

            if self.user_id in self._participants:
                self._participants[self.user_id]["is_deafened"] = self.is_deafened
                self._participants[self.user_id]["is_muted"] = self.is_muted
                self._participants[self.user_id]["is_speaking"] = self.is_speaking

        if self.is_deafened:
            with self._playout_lock:
                self._playout_queues.clear()

        self._apply_local_track_mute()
        self._notify_participants_changed()
        self._notify_state_changed()
        return self.is_deafened

    def set_speaking(self, speaking: bool) -> bool:
        """Establece si el usuario local está hablando (VAD). Si está silenciado, permanece en False."""
        with self._lock:
            if self.is_muted or self.is_deafened:
                self.is_speaking = False
            else:
                self.is_speaking = bool(speaking)

            if self.user_id in self._participants:
                self._participants[self.user_id]["is_speaking"] = self.is_speaking

        self._notify_participants_changed()
        return self.is_speaking

    def list_participants(self) -> List[Dict[str, Any]]:
        """Devuelve la lista actual de participantes con sus estados de voz."""
        with self._lock:
            return [dict(p) for p in self._participants.values()]

    def get_diagnostics(self) -> Dict[str, Any]:
        """Devuelve métricas técnicas del transporte de audio en tiempo real."""
        with self._lock:
            return {
                "is_connected": self.is_connected,
                "media_transport_active": self.media_transport_active,
                "audio_io_active": self.audio_io_active,
                "channel": self.active_channel_name,
                "community_id": self.active_community_id,
                "protocol": self.transport_protocol,
                "sample_rate_hz": self.SAMPLE_RATE,
                "channels": self.CHANNELS,
                "latency_ms": self.latency_ms,
                "jitter_ms": self.jitter_ms,
                "packet_loss_pct": self.packet_loss_pct,
                "is_muted": self.is_muted,
                "is_deafened": self.is_deafened,
                "is_speaking": self.is_speaking,
                "can_publish": self._can_publish,
                "tx_frames": self._tx_frames_sent,
                "rx_frames": self._rx_frames_received,
                "is_screen_sharing": self.is_screen_sharing,
                "remote_screen_active": self.remote_screen_active,
                "screen_share_source_id": self.screen_share_source_id,
                "screen_share_width": self.screen_share_width,
                "screen_share_height": self.screen_share_height,
                "screen_share_fps": self.screen_share_fps,
                "screen_tx_frames": self.screen_tx_frames,
                "screen_rx_frames": self.screen_rx_frames,
                "participant_count": len(self._participants),
                "last_error": self.last_error,
            }

    def _notify_participants_changed(self) -> None:
        cb = self.on_participants_changed
        if cb is not None:
            try:
                cb(self.list_participants())
            except Exception:
                pass

    def _notify_state_changed(self) -> None:
        cb = self.on_state_changed
        if cb is not None:
            try:
                cb(self.get_diagnostics())
            except Exception:
                pass
