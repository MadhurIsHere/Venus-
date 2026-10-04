"""
audio/capture.py — ALSA microphone capture via arecord subprocess

Streams audio from plughw:adau7002,0 in 48kHz / S32_LE / stereo.
Writes raw PCM chunks to a thread-safe queue for VAD consumption.

Usage:
    from audio.capture import AlsaCapture
    cap = AlsaCapture()
    cap.start()
    try:
        while True:
            chunk = cap.read()   # blocks until a chunk is available
            ...                  # process chunk bytes
    finally:
        cap.stop()
"""

import subprocess
import threading
import queue
import sys
import os

# Add project root to path so config is importable regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class AlsaCapture:
    """
    Spawns arecord as a subprocess and streams PCM data into a queue.

    Each item in the queue is a bytes object containing
    config.VAD_CHUNK_FRAMES * config.CAPTURE_CHANNELS * 4  bytes
    (4 bytes per S32 sample).
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=200)
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Bytes per chunk: frames × channels × bytes_per_sample (S32 = 4)
        self.chunk_bytes = config.VAD_CHUNK_FRAMES * config.CAPTURE_CHANNELS * 4

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the arecord subprocess and the reader thread."""
        if self._proc is not None:
            raise RuntimeError("AlsaCapture already running")

        cmd = [
            "arecord",
            "-D", config.ALSA_DEVICE,
            "-f", config.CAPTURE_FORMAT,
            "-r", str(config.CAPTURE_RATE),
            "-c", str(config.CAPTURE_CHANNELS),
            "--buffer-size=4096",   # smaller ALSA buffer → lower latency
            "-t", "raw",            # raw PCM to stdout, no WAV header
            "-q",                   # quiet: suppress progress messages
        ]

        self._stop_event.clear()
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,              # unbuffered
        )

        self._thread = threading.Thread(
            target=self._reader_loop,
            name="alsa-reader",
            daemon=True,
        )
        self._thread.start()
        print(f"[Capture] Started — device={config.ALSA_DEVICE} "
              f"rate={config.CAPTURE_RATE} fmt={config.CAPTURE_FORMAT} "
              f"ch={config.CAPTURE_CHANNELS}")

    def stop(self):
        """Stop capture cleanly."""
        self._stop_event.set()
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        print("[Capture] Stopped")

    def read(self, timeout: float = 2.0) -> bytes | None:
        """
        Block until a PCM chunk is available and return it.
        Returns None on timeout (allows caller to check stop conditions).
        """
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _reader_loop(self):
        """Read exact-sized chunks from arecord stdout and enqueue them."""
        proc = self._proc
        while not self._stop_event.is_set():
            try:
                data = proc.stdout.read(self.chunk_bytes)
            except Exception:
                break

            if not data:
                # arecord exited unexpectedly
                print("[Capture] WARNING: arecord stdout closed unexpectedly")
                break

            if len(data) < self.chunk_bytes:
                # Partial read at end of stream — discard
                break

            # Drop oldest chunk if consumer is too slow (prevents unbounded growth)
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass

            self._queue.put(data)
