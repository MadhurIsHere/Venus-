"""
audio/wakeword.py — openWakeWord Integration

Listens for a wake word like "alexa", "hey_jarvis", or a custom "venus" model.
Since OpenWakeWord expects 16kHz mono S16 audio, we manually decimate and
convert the 48kHz stereo S32 chunks coming from ALSA in real-time.
"""

import os
import sys
import struct
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

try:
    import openwakeword
    from openwakeword.model import Model
except ImportError:
    openwakeword = None


class WakeWordDetector:
    def __init__(self, model_name: str | None = None):
        """
        Initialize the Wake Word Engine.
        """
        if openwakeword is None:
            raise RuntimeError("openwakeword is not installed. Run: pip install openwakeword tflite-runtime")
            
        # OpenWakeWord 0.6.0 removed bundled models. We will download it ourselves.
        target_model = model_name or config.WAKE_WORD_MODEL
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", f"{target_model}.tflite")
        
        if not os.path.exists(model_path) and target_model == "alexa":
            print(f"[WakeWord] Downloading {target_model} model...", flush=True)
            import urllib.request
            url = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/alexa_v0.1.tflite"
            urllib.request.urlretrieve(url, model_path)
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}. Please train your custom model and place it here!")

        # Initialize the model using purely positional arguments.
        # This completely bypasses the openWakeWord 0.6.0 `@re_arg` kwargs bug on Python 3.13.
        # Args: wakeword_models, class_mapping_dicts, enable_speex_noise_suppression, 
        #       vad_threshold, custom_verifier_models, custom_verifier_threshold, inference_framework
        self.oww_model = Model([model_path], [], False, 0.0, {}, 0.1, "tflite")
        
        # OpenWakeWord returns predictions in a dictionary keyed by the internal model name
        self._internal_name = list(self.oww_model.models.keys())[0]
        
    def process(self, chunk_s32_bytes: bytes) -> bool:
        """
        Takes a 48kHz S32_LE stereo chunk, converts it to 16kHz S16 mono,
        and feeds it to openWakeWord. 
        
        Returns True if the wake word was detected in this chunk.
        """
        if not chunk_s32_bytes:
            return False
            
        # 1. Unpack 48kHz S32 stereo
        num_frames = len(chunk_s32_bytes) // 8
        if num_frames == 0:
            return False
            
        fmt = f"<{num_frames * 2}i"
        try:
            samples_s32 = struct.unpack(fmt, chunk_s32_bytes)
        except struct.error:
            return False
            
        # 2. Extract left channel (stride 2)
        left_s32 = samples_s32[::2]
        
        # 3. Decimate 48kHz -> 16kHz (take every 3rd sample)
        decimated_s32 = left_s32[::3]
        
        # 4. Convert S32 to S16 (divide by 65536)
        # S32 range is roughly ±2 billion. S16 is ±32768.
        samples_s16 = [int(s / 65536.0) for s in decimated_s32]
        
        # 5. Convert to numpy array as required by openWakeWord
        audio_data = np.array(samples_s16, dtype=np.int16)
        
        # 6. Predict!
        prediction = self.oww_model.predict(audio_data)
        
        score = prediction[self._internal_name]
        if score > config.WAKE_WORD_THRESHOLD:
            # We must reset the state after detection so it doesn't trigger continuously
            self.oww_model.reset()
            return True
            
        return False
