#!/usr/bin/env python3
"""
main.py — VENUS DESK COMPANION (Full Pipeline)
==============================================
This is the fully integrated main loop for Venus.
It connects the Ears (VAD + Wake Word + STT), Brain (Gemini), and Mouth (Piper).

Usage:
    python3 main.py
"""

import sys
import os
import signal
import concurrent.futures

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from audio.capture import AlsaCapture
from audio.vad import VoiceActivityDetector
from audio.wakeword import WakeWordDetector
from audio import stt
from audio import tts
import bot_brain

def banner(msg: str):
    width = 60
    print("\n" + "─" * width)
    print(f"  {msg}")
    print("─" * width)

def run():
    banner("VENUS IS WAKING UP...")

    # Setup signal handler for clean Ctrl+C exit
    stop_flag = {"value": False}
    def _sigint(sig, frame):
        print("\n\n[Shutting down Venus...]")
        stop_flag["value"] = True
    signal.signal(signal.SIGINT, _sigint)

    # 1. Start ALSA capture
    capture = AlsaCapture()
    capture.start()

    # 2. Calibrate VAD
    vad = VoiceActivityDetector()
    calibrated_threshold = vad.calibrate(capture)

    # 3. Load Wake Word
    wakeword = WakeWordDetector()

    # 4. Prepare background thread for AI so audio pipeline never blocks
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    # State Machine
    STATE_ASLEEP = "ASLEEP"
    STATE_AWAKE  = "AWAKE"
    current_state = STATE_ASLEEP

    def _process_utterance(wav_file_path):
        """Runs in background: STT -> Gemini -> TTS"""
        print("[Brain] Transcribing...", flush=True)
        user_text = stt.transcribe(wav_file_path, delete_after=True)
        
        if not user_text:
            print("[Brain] (Heard nothing)\n")
            print("Listening for wake word...", flush=True)
            return

        print(f"\n[You]: {user_text}")
        
        # Ask Gemini
        print("[Brain] Thinking...", flush=True)
        emotion, reply_text = bot_brain.chat_with_bot(user_text)
        
        print(f"[Venus ({emotion})]: {reply_text}\n")
        
        # Speak it out loud
        tts.speak(reply_text, wait=True)
        
        print("Listening for wake word...", flush=True)

    print("\nVenus is ready! (Say 'alexa' to wake her up, press Ctrl+C to stop)\n")

    # MAIN LOOP
    while not stop_flag["value"]:
        chunk = capture.read(timeout=1.0)

        if chunk is None:
            if not capture.is_running():
                print("[ERROR] arecord process died unexpectedly.")
                break
            continue

        if current_state == STATE_ASLEEP:
            # Feed audio to wake word detector
            if wakeword.process(chunk):
                print("\n[WAKE WORD DETECTED] What's up? (Listening...)")
                current_state = STATE_AWAKE
                # Re-initialize VAD with calibrated threshold
                vad = VoiceActivityDetector(threshold=calibrated_threshold)
                # Play a little ping sound (optional, we can just let her listen)
                
        elif current_state == STATE_AWAKE:
            # Feed audio to VAD
            wav_path = vad.process(chunk)

            if wav_path is not None:
                # Finished speaking! Go back to sleep immediately.
                current_state = STATE_ASLEEP
                # Send the wav file to the brain in the background
                executor.submit(_process_utterance, wav_path)

    # Clean up
    capture.stop()
    executor.shutdown(wait=False)
    banner("Venus powered off.")

if __name__ == "__main__":
    run()
