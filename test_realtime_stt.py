#!/usr/bin/env python3
"""
test_realtime_stt.py — Phase 1 milestone test
=============================================
Demonstrates the full real-time audio pipeline:

    INMP441 → ADAU7002 → ALSA → arecord (48k S32 stereo)
        → VAD (energy-based, auto-calibrated)
        → ffmpeg (→ 16k S16 mono WAV)
        → Whisper server (HTTP /inference)
        → [STT] text printed to terminal

Expected output when working:
    [Capture] Started — device=plughw:adau7002,0 rate=48000 ...
    [VAD] Calibrating ambient noise level (1.5s)...
    [VAD] Ambient RMS=0.00123  threshold=0.00369
    Listening...

    [VAD] VOICE DETECTED
    [VAD] End of utterance — converting...
    [Transcribing]
    [STT] Hello Venus, how are you?

    Listening...

Prerequisites:
    1. Whisper server must be running:
         cd ~/whisper.cpp
         ./build/bin/whisper-server \\
             -m models/ggml-base.en.bin \\
             -t 4 \\
             --host 127.0.0.1 \\
             --port 8080

    2. Install Python deps:
         pip install requests python-dotenv

Run:
    python3 test_realtime_stt.py

Press Ctrl+C to stop.
"""

import sys
import os
import signal
import time

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from audio.capture import AlsaCapture
from audio.vad import VoiceActivityDetector
from audio import stt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def banner(msg: str):
    width = 60
    print("\n" + "─" * width)
    print(f"  {msg}")
    print("─" * width)


def check_prerequisites() -> bool:
    """Verify STT service is ready before we start."""
    print("[Init] Checking STT API...", end=" ", flush=True)
    if stt.check_server():
        print("✓ reachable")
        return True
    else:
        print("✗ UNREACHABLE")
        return False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run():
    banner("VENUS — Real-time STT Test (Phase 1)")
    print(f"  Device  : {config.ALSA_DEVICE}")
    print(f"  Capture : {config.CAPTURE_RATE}Hz / {config.CAPTURE_FORMAT} / {config.CAPTURE_CHANNELS}ch")
    print(f"  Whisper : {config.WHISPER_URL}")

    if not check_prerequisites():
        sys.exit(1)

    # Setup signal handler for clean Ctrl+C exit
    stop_flag = {"value": False}

    def _sigint(sig, frame):
        print("\n\n[Shutting down Venus STT loop]")
        stop_flag["value"] = True

    signal.signal(signal.SIGINT, _sigint)

    # Start ALSA capture
    capture = AlsaCapture()
    capture.start()

    # Create and calibrate VAD
    vad = VoiceActivityDetector()
    vad.calibrate(capture)

    print("\nListening... (Speak into the microphone, press Ctrl+C to stop)\n")

    # ----------------------------------------------------------------
    # Main transcription loop
    # ----------------------------------------------------------------
    utterance_count = 0
    import concurrent.futures
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _do_transcribe(w_path):
        print("[Transcribing]", flush=True)
        text = stt.transcribe(w_path, delete_after=True)
        if text:
            print(f"[STT] {text}\n")
        else:
            print("[STT] (no speech recognised)\n")
        print("Listening...\n", flush=True)

    while not stop_flag["value"]:
        chunk = capture.read(timeout=1.0)

        if chunk is None:
            # Timeout — just loop; allows Ctrl+C to be caught promptly
            if not capture.is_running():
                print("[ERROR] arecord process died unexpectedly. Exiting.")
                break
            continue

        # Feed chunk to VAD
        wav_path = vad.process(chunk)

        if wav_path is not None:
            utterance_count += 1
            # Run STT in the background so we don't block the audio pipeline
            executor.submit(_do_transcribe, wav_path)

    # Clean up
    capture.stop()
    executor.shutdown(wait=False)
    banner(f"Session ended — {utterance_count} utterance(s) transcribed")


if __name__ == "__main__":
    run()
