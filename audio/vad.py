"""
audio/vad.py — Energy-based Voice Activity Detection

Consumes raw PCM chunks from AlsaCapture, detects speech segments,
resamples them to 16kHz mono via ffmpeg, and yields WAV file paths
ready for the Whisper server.

State machine:
    SILENCE  → (energy > threshold)  → SPEECH
    SPEECH   → (silence > timeout)   → SILENCE  (emit utterance)
    SPEECH   → (duration > max)      → SILENCE  (emit utterance, hard cap)

Usage:
    from audio.vad import VoiceActivityDetector

    vad = VoiceActivityDetector()
    vad.calibrate(capture)       # optional: auto-set energy threshold

    while True:
        chunk = capture.read()
        wav_path = vad.process(chunk)
        if wav_path:
            # an utterance is ready at wav_path
            text = stt.transcribe(wav_path)
"""

import os
import struct
import subprocess
import tempfile
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# Ensure temp directory exists
os.makedirs(config.TEMP_DIR, exist_ok=True)


def _pcm_s32_stereo_to_energy(raw_bytes: bytes) -> float:
    """
    Convert a chunk of S32_LE stereo PCM bytes to a normalised RMS energy
    value in range [0, 1], using AC-coupled (DC-bias-removed) RMS.

    Why AC-coupled?
    The INMP441 / ADAU7002 I²S stream often has a large DC offset baked
    into the raw S32 values. Using plain RMS measures that DC component
    instead of actual audio energy, making the threshold impossibly high.
    Subtracting the mean (DC) before computing RMS isolates real audio.
    Only the left channel is used for efficiency.
    """
    # 8 bytes per stereo frame: 2 × 4-byte S32 samples
    num_frames = len(raw_bytes) // 8
    if num_frames == 0:
        return 0.0

    fmt = f"<{num_frames * 2}i"
    try:
        all_samples = struct.unpack(fmt, raw_bytes[:num_frames * 8])
    except struct.error:
        return 0.0

    left_samples = all_samples[::2]   # stride-2 → left channel only
    n = len(left_samples)

    # Subtract DC offset (mean) so the metric reflects actual audio energy
    mean = sum(left_samples) / n
    variance = sum((s - mean) ** 2 for s in left_samples) / n
    ac_rms = variance ** 0.5

    # Normalise against S32 max
    scale = 2_147_483_647.0
    return ac_rms / scale


class VoiceActivityDetector:
    """
    Energy-based VAD that accumulates speech frames and emits utterances.
    """

    # Internal states
    _SILENCE = "SILENCE"
    _SPEECH  = "SPEECH"

    def __init__(self, threshold: float | None = None):
        """
        Args:
            threshold: Normalised energy threshold [0, 1].
                       If None, you must call calibrate() or set_threshold().
        """
        self._threshold  = threshold or config.VAD_ENERGY_THRESHOLD or 0.01
        self._state      = self._SILENCE

        # Timing (track in chunk counts, convert at read time)
        self._chunk_duration = config.VAD_CHUNK_FRAMES / config.CAPTURE_RATE   # seconds per chunk

        # Pre-padding ring buffer: keep last N chunks before speech detected
        self._pre_pad_chunks = max(1, int(
            config.VAD_PRE_PADDING_SECS / self._chunk_duration
        ))
        self._pre_buffer: list[bytes] = []

        # Post-silence counter
        self._silence_chunks = 0
        self._silence_limit  = max(1, int(
            config.VAD_SILENCE_TIMEOUT / self._chunk_duration
        ))

        # Speech buffer
        self._speech_buffer: list[bytes] = []
        self._speech_duration = 0.0    # seconds of voiced audio accumulated

        # Min speech threshold
        self._min_speech_chunks = max(1, int(
            config.VAD_MIN_SPEECH_SECS / self._chunk_duration
        ))

        # Timestamp for hard cap
        self._speech_start_time: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self, capture, duration: float | None = None) -> float:
        """
        Listen to ambient noise for `duration` seconds and set the energy
        threshold automatically as:  ambient_ac_rms × VAD_ENERGY_MULTIPLIER

        Uses AC-coupled (DC-removed) RMS so the INMP441/ADAU7002 DC offset
        does not inflate the baseline measurement.

        Args:
            capture: An AlsaCapture instance that is already started.
            duration: Seconds to sample. Defaults to config.VAD_CALIBRATION_SECS.

        Returns:
            The calibrated threshold value.
        """
        duration = duration or config.VAD_CALIBRATION_SECS
        print(f"[VAD] Calibrating ambient noise level ({duration:.1f}s) — stay quiet...", flush=True)

        total_energy = 0.0
        count = 0
        deadline = time.monotonic() + duration

        while time.monotonic() < deadline:
            chunk = capture.read(timeout=1.0)
            if chunk is None:
                continue
            total_energy += _pcm_s32_stereo_to_energy(chunk)
            count += 1

        if count == 0:
            print("[VAD] WARNING: no audio received during calibration — using default threshold")
            return self._threshold

        ambient_rms = total_energy / count
        candidate = ambient_rms * config.VAD_ENERGY_MULTIPLIER

        # Sanity check: if threshold > 1.0 it can never be exceeded.
        # This usually means the I²S stream has residual DC or odd encoding.
        # Fall back to a fixed minimum that works well for MEMS mics.
        FALLBACK_THRESHOLD = 0.01
        if candidate >= 0.95 or ambient_rms < 1e-9:
            print(
                f"[VAD] Calibration result unusual "
                f"(ambient={ambient_rms:.5f}, candidate={candidate:.5f}).\n"
                f"[VAD] Falling back to fixed threshold={FALLBACK_THRESHOLD}. "
                f"Adjust VAD_ENERGY_THRESHOLD in config.py if needed."
            )
            self._threshold = FALLBACK_THRESHOLD
        else:
            self._threshold = candidate
            # Guard: never set threshold so low that ambient noise triggers it
            self._threshold = max(self._threshold, 0.001)

        print(f"[VAD] Ambient RMS={ambient_rms:.5f}  threshold={self._threshold:.5f}  "
              f"(from {count} chunks)")
        return self._threshold

    def set_threshold(self, threshold: float):
        self._threshold = threshold

    def process(self, raw_chunk: bytes) -> str | None:
        """
        Feed one raw PCM chunk (S32_LE stereo, 48kHz).

        Returns:
            str: Path to a 16kHz mono S16 WAV file if an utterance is ready.
            None: No complete utterance yet.
        """
        energy = _pcm_s32_stereo_to_energy(raw_chunk)

        if self._state == self._SILENCE:
            # Maintain rolling pre-pad buffer
            self._pre_buffer.append(raw_chunk)
            if len(self._pre_buffer) > self._pre_pad_chunks:
                self._pre_buffer.pop(0)

            if energy >= self._threshold:
                # Transition to SPEECH
                self._state = self._SPEECH
                self._speech_buffer = list(self._pre_buffer)  # include pre-pad
                self._silence_chunks = 0
                self._speech_duration = len(self._pre_buffer) * self._chunk_duration
                self._speech_start_time = time.monotonic()
                print("[VAD] VOICE DETECTED", flush=True)

        elif self._state == self._SPEECH:
            self._speech_buffer.append(raw_chunk)
            self._speech_duration += self._chunk_duration

            if energy < self._threshold:
                self._silence_chunks += 1
            else:
                self._silence_chunks = 0

            # Hard cap: utterance too long
            hard_cap_hit = (time.monotonic() - self._speech_start_time) >= config.VAD_MAX_UTTERANCE
            silence_done = self._silence_chunks >= self._silence_limit

            if silence_done or hard_cap_hit:
                # Add a post-pad of silence (already in buffer from silence chunks)
                utterance_chunks = list(self._speech_buffer)
                self._state = self._SILENCE
                self._speech_buffer = []
                self._pre_buffer = []
                self._silence_chunks = 0

                # Reject utterances that are too short
                if len(utterance_chunks) < self._min_speech_chunks:
                    print("[VAD] Utterance too short — discarded", flush=True)
                    return None

                print("[VAD] End of utterance — converting...", flush=True)
                return self._convert_utterance(utterance_chunks)

        return None

    def reset(self):
        """Reset state machine — call if you want to abort current utterance."""
        self._state = self._SILENCE
        self._speech_buffer = []
        self._pre_buffer = []
        self._silence_chunks = 0

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _convert_utterance(self, chunks: list[bytes]) -> str | None:
        """
        Write raw PCM to a temp file, convert to 16kHz mono S16 WAV
        via ffmpeg, and return the path to the converted file.
        """
        raw_data = b"".join(chunks)

        # Write raw PCM to temp file (no WAV header — pipe as raw)
        try:
            with tempfile.NamedTemporaryFile(
                dir=config.TEMP_DIR,
                suffix="_raw.pcm",
                delete=False,
            ) as raw_f:
                raw_f.write(raw_data)
                raw_path = raw_f.name

            out_path = raw_path.replace("_raw.pcm", "_16k.wav")

            # ffmpeg: raw S32 stereo 48k → 16k mono S16 WAV
            cmd = [
                "ffmpeg", "-y",
                "-f", "s32le",
                "-ar", str(config.CAPTURE_RATE),
                "-ac", str(config.CAPTURE_CHANNELS),
                "-i", raw_path,
                "-ac", str(config.WHISPER_CHANNELS),
                "-ar", str(config.WHISPER_RATE),
                "-sample_fmt", config.WHISPER_FORMAT,
                out_path,
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )

            os.unlink(raw_path)   # delete raw PCM immediately

            if result.returncode != 0:
                print(f"[VAD] ffmpeg error: {result.stderr.decode(errors='replace')}")
                return None

            return out_path

        except Exception as e:
            print(f"[VAD] Conversion error: {e}")
            return None
