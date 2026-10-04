import asyncio
import os
import pygame
import edge_tts
import psutil
from bot_brain import chat_with_bot
from listen_venus import listen_to_user, check_for_wake_word

def print_ram_usage(tag=""):
    process = psutil.Process(os.getpid())
    ram_mb = process.memory_info().rss / (1024 * 1024)
    print(f"📊 [RAM Usage {tag}]: {ram_mb:.2f} MB")

# VOICE PROFILES tuned for Swara Neural Hindi Voice
VOICE_PROFILES = {
    "HAPPY":   {"pitch": "+15Hz", "rate": "+5%"},    
    "GOSSIP":  {"pitch": "+18Hz", "rate": "+8%"},   
    "CASUAL":  {"pitch": "+8Hz",  "rate": "+0%"},    
    "ANNOYED": {"pitch": "+5Hz",  "rate": "+2%"},    
    "SAD":     {"pitch": "-5Hz",  "rate": "-10%"},   
    "ANXIOUS": {"pitch": "+0Hz",  "rate": "-8%"}     
}

async def text_to_speech(text, emotion="CASUAL", output_file="response.mp3"):
    voice = "hi-IN-SwaraNeural"
    profile = VOICE_PROFILES.get(emotion, VOICE_PROFILES["CASUAL"])
    
    communicate = edge_tts.Communicate(
        text=text, 
        voice=voice,
        rate=profile["rate"],
        pitch=profile["pitch"]
    )
    await communicate.save(output_file)

def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()

def start_voice_session():
    print("\n" + "="*50)
    print("      VENUS DESK COMPANION (HINGLISH) IS ONLINE!  ")
    print("      (Say 'Exit' or 'Quit' to stop)              ")
    print("="*50 + "\n")
    
    print_ram_usage("At Startup")
    
    greeting = "Heyyy bestie! I'm Venus! Kya chal raha hai aaj?"
    print(f"Venus [GOSSIP]: {greeting}")
    asyncio.run(text_to_speech(greeting, emotion="GOSSIP", output_file="greeting.mp3"))
    play_audio("greeting.mp3")

    while True:
        user_speech = listen_to_user("🎤 Speak to Venus now...")
        
        if not user_speech:
            continue

        print(f"\nYou said: {user_speech}")
        
        if any(word in user_speech for word in ["exit", "quit", "bye"]):
            farewell = "Bye babe! Apna khayal rakhna!"
            print(f"Venus: {farewell}")
            asyncio.run(text_to_speech(farewell, emotion="CASUAL", output_file="farewell.mp3"))
            play_audio("farewell.mp3")
            break

        # Process message with Venus AI Brain
        emotion, bot_reply = chat_with_bot(user_speech)
        print(f"Venus [{emotion}]: {bot_reply}")
        
        # Play audio response
        asyncio.run(text_to_speech(bot_reply, emotion=emotion, output_file="temp_voice.mp3"))
        play_audio("temp_voice.mp3")
        
        # Track memory usage after each conversation turn
        print_ram_usage("After Turn")

if __name__ == "__main__":
    start_voice_session()