"""
audio/stt.py — Google Speech Recognition API Client

Sends a 16kHz mono S16 WAV file to Google's free STT API and returns
the transcription text. This provides excellent Hinglish support out of the box
with no local model required.

Usage:
    from audio.stt import transcribe
    text = transcribe("/tmp/venus/utterance_16k.wav")
    if text:
        print(f"[STT] {text}")
"""

import os
import sys
import speech_recognition as sr

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def transcribe(wav_path: str, delete_after: bool = True) -> str | None:
    """
    Pass a WAV file to Google Speech Recognition.

    Args:
        wav_path:     Path to a WAV file.
        delete_after: If True, delete wav_path after processing
                      to avoid accumulating temp files.

    Returns:
        Transcribed text string (stripped), or None on failure.
    """
    if not os.path.isfile(wav_path):
        print(f"[STT] ERROR: file not found: {wav_path}")
        return None

    recognizer = sr.Recognizer()
    text = None
    
    try:
        # Load the WAV file that our VAD module generated
        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            
            # Using language="en-IN" (Indian English) returns Hinglish in English letters!
            text = recognizer.recognize_google(audio_data, language="en-IN")
            
        if text:
            text = text.strip()
            
    except sr.UnknownValueError:
        # Google could not understand the audio (likely noise or silence)
        pass
    except sr.RequestError as e:
        print(f"[STT] ERROR: API Request failed; {e}")
    except Exception as e:
        print(f"[STT] Unexpected error: {e}")
        
    finally:
        # Always clean up the temp file
        if delete_after and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    return text if text else None


def check_server() -> bool:
    """
    Quick health-check: For Google STT, we just assume it's up if we have internet.
    """
    return True
