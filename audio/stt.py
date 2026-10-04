"""
audio/stt.py — Whisper server HTTP client

Sends a 16kHz mono S16 WAV file to the local Whisper server and returns
the transcription text.

Whisper server must already be running:
    cd ~/whisper.cpp
    ./build/bin/whisper-server \\
        -m models/ggml-base.en.bin \\
        -t 4 \\
        --host 127.0.0.1 \\
        --port 8080

Usage:
    from audio.stt import transcribe
    text = transcribe("/tmp/venus/utterance_16k.wav")
    if text:
        print(f"[STT] {text}")
"""

import os
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def transcribe(wav_path: str, delete_after: bool = True) -> str | None:
    """
    POST a WAV file to the Whisper inference server.

    Args:
        wav_path:     Path to a 16kHz / mono / S16 WAV file.
        delete_after: If True, delete wav_path after successful transcription
                      to avoid accumulating temp files.

    Returns:
        Transcribed text string (stripped), or None on failure.
    """
    if not os.path.isfile(wav_path):
        print(f"[STT] ERROR: file not found: {wav_path}")
        return None

    try:
        with open(wav_path, "rb") as f:
            files = {"file": (os.path.basename(wav_path), f, "audio/wav")}
            # language="hi" → Whisper uses Hindi/Hinglish mode (handles mixed Hindi+English)
            # Set to None or remove for pure auto-detect
            data  = {"language": "hi"}
            response = requests.post(
                config.WHISPER_URL,
                files=files,
                data=data,
                timeout=config.WHISPER_TIMEOUT,
            )

        response.raise_for_status()

        data = response.json()

        # Whisper server returns {"text": "...", ...}
        text = data.get("text", "").strip()

        # Filter Whisper's special output tags that indicate no real speech:
        # [BLANK_AUDIO] = silence, (singing ...) / (music) = background noise
        NOISE_TAGS = {
            "[blank_audio]",
            "[silence]",
        }
        NOISE_PREFIXES = ("(singing", "(music", "(applause", "(noise", "(foreign")

        text_lower = text.lower()
        if text_lower in NOISE_TAGS or text_lower.startswith(NOISE_PREFIXES):
            text = ""

        if delete_after:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

        return text if text else None

    except requests.exceptions.ConnectionError:
        print("[STT] ERROR: Cannot connect to Whisper server. "
              "Is it running on 127.0.0.1:8080?")
        return None
    except requests.exceptions.Timeout:
        print(f"[STT] ERROR: Whisper server timed out after {config.WHISPER_TIMEOUT}s")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"[STT] HTTP error from Whisper server: {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"[STT] Failed to parse Whisper response: {e}")
        return None
    except Exception as e:
        print(f"[STT] Unexpected error: {e}")
        return None


def check_server() -> bool:
    """
    Quick health-check: can we reach the Whisper server?
    Returns True if the server is reachable, False otherwise.
    """
    try:
        # Hit the root endpoint — Whisper server serves a basic page there
        r = requests.get(
            config.WHISPER_URL.replace("/inference", "/"),
            timeout=3,
        )
        return r.status_code < 500
    except Exception:
        return False
