import asyncio
import pygame
import edge_tts

async def speak_really(text, rate="+0%", pitch="+45Hz", filename="test.mp3"):
    voice = "en-US-AvaNeural"
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(filename)

def play_audio(file_path):
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.quit()

async def main():
    print("\nTesting Ultra-Excited Pitch (+45Hz): 'Wait... REALLY?!'")
    await speak_really("Wait... REALLY?! No way!", rate="+5%", pitch="+45Hz", filename="really_super_excited.mp3")
    play_audio("really_super_excited.mp3")

if __name__ == "__main__":
    asyncio.run(main())