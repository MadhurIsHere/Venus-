# 🌟 Venus Desk Companion

Venus is a lightning-fast, highly conversational, and sassy AI desk companion built specifically for the **Raspberry Pi 5**. She listens passively for her wake word, understands natural conversational **Hinglish** (Hindi + English), and replies out loud with near-zero latency using a fully local text-to-speech engine.

---

## 🚀 Features

- **👂 Always-on Wake Word:** Powered by [openWakeWord](https://github.com/dscripka/openWakeWord), running entirely locally via ONNX. (Currently defaults to `Alexa`, custom `Venus` model coming soon!).
- **🎙️ I2S Microphone Support:** Uses custom ALSA integration to capture crystal clear 48kHz audio directly from an INMP441 MEMS microphone (via ADAU7002).
- **⚡ Custom VAD (Voice Activity Detection):** Energy-based VAD calibrated dynamically to room noise, ensuring she only records when you are actually speaking.
- **📝 Hinglish STT:** Uses Google Speech Recognition tuned to `en-IN` to perfectly transcribe mixed Hindi and English sentences into Latin script.
- **🧠 Gemini Brain:** Powered by `gemini-1.5-flash-8b` for ultra-fast, witty, and emotionally aware responses based on persistent user memory.
- **🗣️ Ultra-low Latency TTS:** Uses [Piper TTS](https://github.com/rhasspy/piper) with direct Pipewire (`pw-play`) streaming to speak her responses through Bluetooth speakers *while* the audio is still generating.

---

## 🛠️ Hardware Requirements

- **Raspberry Pi 5** (Tested on Pi OS Bookworm with Pipewire)
- **Microphone:** INMP441 I2S microphone (or similar) connected to GPIO pins.
- **Speaker:** Bluetooth speaker (or HDMI/USB audio).

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/MadhurIsHere/Venus-.git
cd Venus-
```

### 2. Set up the Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Install Piper TTS (Local Voice)
Venus uses a standalone Piper binary for maximum speed on the Pi's ARM architecture.
```bash
# Download and extract the aarch64 binary
wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz
tar -xf piper_linux_aarch64.tar.gz
rm piper_linux_aarch64.tar.gz

# Download the default female voice model
cd piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kathleen/low/en_US-kathleen-low.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kathleen/low/en_US-kathleen-low.onnx.json
cd ..
```

### 4. Configure your API Keys
Copy the example environment file and add your Google Gemini API key:
```bash
cp .env.example .env
nano .env  # Add your GEMINI_API_KEY
```

---

## 🎮 How to Run

1. **Activate the environment:**
   ```bash
   source venv/bin/activate
   ```
2. **Start Venus:**
   ```bash
   python3 main.py
   ```

**Usage:**
- Venus will calibrate to your room's background noise for 1.5 seconds on startup. Stay quiet!
- Say the wake word: **"Alexa"**
- You will see `[WAKE WORD DETECTED]`. Ask her a question in English or Hinglish!
- She will process your voice, think, and speak the reply directly to your Bluetooth speaker.

---

## 🗂️ Project Structure

- `main.py` - The main loop that connects all modules (Wake Word -> VAD -> STT -> Brain -> TTS).
- `bot_brain.py` - Connects to the Gemini API and enforces Venus's sassy Hinglish personality.
- `config.py` - All tuneable parameters (Thresholds, device names, AI models).
- `audio/capture.py` - Raw 48kHz S32_LE ALSA audio capture from the I2S microphone.
- `audio/vad.py` - Dynamic energy-based Voice Activity Detection.
- `audio/wakeword.py` - Wraps openWakeWord (ONNX) to listen for the trigger phrase.
- `audio/stt.py` - Google Speech-to-Text integration.
- `audio/tts.py` - Local Piper text-to-speech piped directly into `pw-play`.
