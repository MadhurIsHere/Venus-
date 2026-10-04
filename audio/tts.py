"""
audio/tts.py — Piper TTS Integration

Uses the extremely fast, offline, local Piper TTS engine.
Expects the piper binary to be at the root of the project in a folder called 'piper'.
"""

import os
import subprocess
import config

PIPER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "piper")
PIPER_EXEC = os.path.join(PIPER_DIR, "piper")

def is_installed() -> bool:
    return os.path.isfile(PIPER_EXEC)

def speak(text: str, wait: bool = True) -> bool:
    """
    Synthesize text to speech using Piper and play it immediately.
    
    Args:
        text: The string of text to speak
        wait: If True, blocks until speaking is finished.
        
    Returns:
        True if successful, False otherwise.
    """
    if not is_installed():
        print("[TTS] ERROR: Piper is not installed.")
        return False
        
    if not text.strip():
        return False
        
    model_path = os.path.join(PIPER_DIR, config.TTS_MODEL)
    if not os.path.isfile(model_path):
        print(f"[TTS] ERROR: Voice model not found at {model_path}")
        return False

    print(f"[TTS] Speaking: {text}", flush=True)

    try:
        # We pipe the text into Piper, and pipe Piper's raw audio output directly into aplay.
        # This gives us ultra-low latency streaming playback (starts playing before it finishes generating!)
        
        # Piper outputs 16-bit PCM at the model's sample rate (usually 22050Hz for standard voices)
        # We can extract the sample rate from the .json config file, but 22050 is safe for default en_US voices.
        
        piper_cmd = [
            PIPER_EXEC,
            "--model", model_path,
            "--output-raw"
        ]
        
        aplay_cmd = [
            "aplay",
            "-r", "22050",
            "-f", "S16_LE",
            "-t", "raw",
            "-q", "-"
        ]
        
        # Launch pipeline: echo text | piper | aplay
        piper_proc = subprocess.Popen(
            piper_cmd, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.DEVNULL
        )
        
        aplay_proc = subprocess.Popen(
            aplay_cmd, 
            stdin=piper_proc.stdout, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        # Allow piper to receive EOF when it finishes writing
        if piper_proc.stdout is not None:
            piper_proc.stdout.close()
            
        # Send text to Piper
        if piper_proc.stdin is not None:
            piper_proc.stdin.write(text.encode('utf-8'))
            piper_proc.stdin.close()
            
        if wait:
            aplay_proc.wait()
            
        return True
        
    except Exception as e:
        print(f"[TTS] Unexpected error: {e}")
        return False
