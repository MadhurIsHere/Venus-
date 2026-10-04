import speech_recognition as sr

# Phonetic variations Google STT produces when hearing "Venus" or "Hi Venus"
PHONETIC_TRIGGERS = [
    "venus", "hi venus", "hey venus", "hay venus", "hi ven", 
    "vinash", "veena", "haven's", "heinis", "veenus", "nilesh", "high venus", "binus", "beenas"
]

def listen_to_user(prompt_message="[Listening...]"):
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.energy_threshold = 300  # Microphone sensitivity
    
    with sr.Microphone() as source:
        print(f"\n{prompt_message}")
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
            print("[Processing voice...]")
            text = recognizer.recognize_google(audio).lower()
            print(f"Captured Speech: '{text}'")
            return text
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError as e:
            print(f"[Mic Error]: {e}")
            return None

def check_for_wake_word(text):
    """Checks if any phonetic variation of 'Venus' was spoken."""
    if not text:
        return False
    for trigger in PHONETIC_TRIGGERS:
        if trigger in text:
            return True
    return False

if __name__ == "__main__":
    print("=== TESTING VENUS LISTENER ===")
    speech = listen_to_user("Say 'Hi Venus' into your mic...")
    if speech and check_for_wake_word(speech):
        print("Venus Wake Triggered Successfully!")