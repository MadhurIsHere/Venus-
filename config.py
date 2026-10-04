"""
config.py — Venus global configuration
All tuneable parameters live here. Nothing is hard-coded elsewhere.
"""

import os

# ---------------------------------------------------------------------------
# MICROPHONE / CAPTURE
# ---------------------------------------------------------------------------
ALSA_DEVICE       = "plughw:adau7002,0"   # Working I2S device
CAPTURE_RATE      = 48000                  # Native working rate (DO NOT change to 16000)
CAPTURE_FORMAT    = "S32_LE"              # 32-bit signed little-endian
CAPTURE_CHANNELS  = 2                     # Stereo (INMP441 via ADAU7002)

# ---------------------------------------------------------------------------
# WHISPER SERVER
# ---------------------------------------------------------------------------
WHISPER_URL       = "http://127.0.0.1:8080/inference"
WHISPER_TIMEOUT   = 30        # seconds to wait for Whisper response

# ---------------------------------------------------------------------------
# VAD (Voice Activity Detection)
# All durations in seconds unless noted
# ---------------------------------------------------------------------------
VAD_CHUNK_FRAMES      = 2048       # frames per ALSA read chunk (~42 ms at 48k)
VAD_ENERGY_THRESHOLD  = None       # None → auto-calibrate on startup
VAD_CALIBRATION_SECS  = 1.5       # how long to listen for ambient noise level
VAD_ENERGY_MULTIPLIER = 3.0       # voice must be N× above ambient noise floor
VAD_MIN_SPEECH_SECS   = 0.40      # ignore bursts shorter than this
VAD_SILENCE_TIMEOUT   = 1.00      # end utterance after this much silence
VAD_MAX_UTTERANCE     = 30.0      # hard cap — avoid runaway recording
VAD_PRE_PADDING_SECS  = 0.20      # keep audio before voice detected (prevent clipping)
VAD_POST_PADDING_SECS = 0.30      # keep audio after silence (prevent clipping end)

# ---------------------------------------------------------------------------
# AUDIO CONVERSION (for Whisper)
# ---------------------------------------------------------------------------
WHISPER_RATE      = 16000
WHISPER_CHANNELS  = 1
WHISPER_FORMAT    = "s16"   # FFmpeg sample format

# ---------------------------------------------------------------------------
# TEMP FILES
# ---------------------------------------------------------------------------
TEMP_DIR          = "/tmp/venus"   # temporary WAV storage on Pi
TEMP_CAPTURE_FILE = os.path.join(TEMP_DIR, "utterance_raw.wav")
TEMP_WHISPER_FILE = os.path.join(TEMP_DIR, "utterance_16k.wav")

# ---------------------------------------------------------------------------
# GEMINI (fallback AI — loaded from environment)
# ---------------------------------------------------------------------------
GEMINI_MODEL      = "gemini-2.5-flash"
MEMORY_FILE       = "venus_memory.json"

# ---------------------------------------------------------------------------
# TTS (Phase 5 — Piper)
# ---------------------------------------------------------------------------
PIPER_EXECUTABLE  = os.path.expanduser("~/piper/piper")
PIPER_VOICE_MODEL = os.path.expanduser("~/piper/voices/en_US-lessac-medium.onnx")

# ---------------------------------------------------------------------------
# RGB (Phase 7)
# ---------------------------------------------------------------------------
RGB_ENABLED       = False   # Flip to True when hardware is connected
