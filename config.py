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
# IMPORTANT: Use ggml-base.bin (multilingual) NOT ggml-base.en.bin (English only)
# Start server with:
#   ./build/bin/whisper-server -m models/ggml-base.bin -t 4 --host 127.0.0.1 --port 8080
# Download multilingual model:
#   bash models/download-ggml-model.sh base
WHISPER_URL       = "http://127.0.0.1:8080/inference"
WHISPER_TIMEOUT   = 30        # seconds to wait for Whisper response

# ---------------------------------------------------------------------------
# WAKE WORD (Phase 2)
# ---------------------------------------------------------------------------
WAKE_WORD_MODEL     = "alexa"     # Default built-in model (alexa, hey_jarvis). We will change to "venus" later!
WAKE_WORD_THRESHOLD = 0.5         # 0.0 to 1.0 — lower = more sensitive, higher = less false positives

# ---------------------------------------------------------------------------
# TTS (Phase 3)
# ---------------------------------------------------------------------------
TTS_MODEL = "en_US-kathleen-low.onnx"   # Default Piper voice model (requires matching .json file)

# ---------------------------------------------------------------------------
# VAD (Voice Activity Detection)
# All durations in seconds unless noted
# ---------------------------------------------------------------------------
VAD_CHUNK_FRAMES      = 512        # frames per ALSA read chunk (must match arecord period-size)
VAD_ENERGY_THRESHOLD  = None       # None → auto-calibrate on startup
VAD_CALIBRATION_SECS  = 1.5       # how long to listen for ambient noise level
VAD_ENERGY_MULTIPLIER = 2.0       # voice must be N× above ambient noise floor (lowered to catch softer speech)
VAD_MIN_SPEECH_SECS   = 0.40      # ignore bursts shorter than this
VAD_SILENCE_TIMEOUT   = 2.00      # end utterance after this much silence (raised so pauses don't cut off)
VAD_MAX_UTTERANCE     = 30.0      # hard cap — avoid runaway recording
VAD_PRE_PADDING_SECS  = 0.5      # keep audio before voice detected (prevent clipping)
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
GEMINI_MODEL      = "gemini-3.7-flash"
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
