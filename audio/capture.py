"""
audio/capture.py — ALSA microphone capture via arecord subprocess

Streams audio from plughw:adau7002,0 in 48kHz / S32_LE / stereo.
Writes raw PCM chunks to a thread-safe queue for VAD consumption.

Key fix: arecord buffers stdout when piped. We use `stdbuf -o0` to
force unbuffered writes so chunks arrive immediately.

Usage:
    from audio.capture import AlsaCapture
    cap = AlsaCapture()
    cap.start()          # blocks ~1s for warm-up
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
import time
import shutil

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
        # Use 1024 frames (~21ms) for low-latency, responsive chunk delivery
        self._chunk_frames = min(config.VAD_CHUNK_FRAMES, 1024)
        self.chunk_bytes = self._chunk_frames * config.CAPTURE_CHANNELS * 4

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, warmup_secs: float = 1.0):
        """
        Start the arecord subprocess and the reader thread.

        Args:
            warmup_secs: Seconds to wait after starting arecord before
                         returning — lets the ALSA device settle and
                         fills the pipe with initial data so calibration
                         doesn't see an empty queue.
        """
        if self._proc is not None:
            raise RuntimeError("AlsaCapture already running")

        # stdbuf -o0 forces arecord to write stdout unbuffered.
        # Without this, the kernel pipe buffer holds data until full
        # (64 KB) before delivering any chunks — calibration sees nothing.
        use_stdbuf = shutil.which("stdbuf") is not None

        cmd = []
        if use_stdbuf:
            cmd += ["stdbuf", "-o0"]

        cmd += [
            "arecord",
            "-D", config.ALSA_DEVICE,
            "-f", config.CAPTURE_FORMAT,
            "-r", str(config.CAPTURE_RATE),
            "-c", str(config.CAPTURE_CHANNELS),
            "-t", "raw",   # raw PCM to stdout, no WAV header
            # Note: --buffer-size omitted — can conflict with raw pipe mode
        ]

        self._stop_event.clear()
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,   # capture stderr so we can report errors
            bufsize=0,                 # unbuffered Python-side
        )

        self._thread = threading.Thread(
            target=self._reader_loop,
            name="alsa-reader",
            daemon=True,
        )
        self._thread.start()

        stdbuf_note = "with stdbuf" if use_stdbuf else "WITHOUT stdbuf (install coreutils if missing)"
        print(f"[Capture] Started {stdbuf_note} — device={config.ALSA_DEVICE} "
              f"rate={config.CAPTURE_RATE} fmt={config.CAPTURE_FORMAT} "
              f"ch={config.CAPTURE_CHANNELS} chunk={self._chunk_frames}frames")

        # Warm-up: give arecord time to open the ALSA device and start
        # flowing data into the pipe before calibration reads from the queue.
        if warmup_secs > 0:
            print(f"[Capture] Warming up ({warmup_secs:.1f}s)...", flush=True)
            time.sleep(warmup_secs)

        # Check if arecord died during warm-up (wrong device, permissions, etc.)
        if self._proc.poll() is not None:
            stderr_out = self._proc.stderr.read().decode(errors="replace").strip()
            raise RuntimeError(
                f"arecord exited immediately (code {self._proc.returncode}).\n"
                f"stderr: {stderr_out}\n"
                f"Check device with: arecord -l"
            )

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
