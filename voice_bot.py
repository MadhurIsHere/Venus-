import asyncio
import pygame
import edge_tts
from bot_brain import chat_with_bot

async def text_to_speech(text, output_file="response.mp3"):
    # Expressive female voice
    voice = "en-US-AvaNeural"
    
    # Adjust pitch (+12Hz) and rate (+15%) using edge-tts standard parameters
    communicate = edge_tts.Communicate(
        text=text, 
        voice=voice,
        rate="-5%",
        pitch="+45Hz"
    )
    await communicate.save(output_file)

def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()

def talk_to_vibebot(user_message):
    print(f"\nUser: {user_message}")
    
    bot_reply = chat_with_bot(user_message)
    print(f"VibeBot: {bot_reply}")
    
    asyncio.run(text_to_speech(bot_reply, "temp_voice.mp3"))
    play_audio("temp_voice.mp3")

if __name__ == "__main__":
    test_input = "I just got an A on my exam!"
    talk_to_vibebot(test_input)