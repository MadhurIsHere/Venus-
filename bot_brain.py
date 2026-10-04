import os
import re
import json
import warnings
from google import genai
from google.genai import types
from dotenv import load_dotenv

warnings.filterwarnings("ignore")

import config

# Load GEMINI_API_KEY from .env (never hard-code secrets in source)
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set.\n"
        "Copy .env.example to .env and fill in your key.\n"
        "  cp .env.example .env"
    )
client = genai.Client(api_key=API_KEY)

MEMORY_FILE = "venus_memory.json"

def load_memories():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {
        "favorite_food": "Not specified yet",
        "owner_name": "Shreya"
    }

def chat_with_bot(user_message):
    memories = load_memories()
    
    system_instruction = f"""
    You are Venus, a vibrant, witty, bubbly, and supportive desk companion.
    You speak fluently in casual HINGLISH (Hindi written using English letters) or natural Hindi!

    KNOWN MEMORIES ABOUT USER:
    {json.dumps(memories, indent=2)}

    HINGLISH & PERSONALITY RULES:
    1. LANGUAGE STYLE: Speak in everyday conversational Hinglish (e.g., "Arre yaar, tension mat lo!", "Kya baat kar rahi ho!"). 
    2. Use friendly terms to address like "yaar".
    3. PRONUNCIATION SAFEGUARD:
       - Do NOT elongate vowels like "aaaaah" or "hiiii". Write "Ahhh!", "Ohhh!", "Yesss!", or "Omg!".
    4. EMOTIONAL MATCHING:
       - HAPPY/EXCITED: High energy hype girl! ("Ayyy, yeh toh bohot awesome hai!")
       - ANNOYED/VENTING: Validate her frustration ("Ugh, yeh kitna irritating hai!").
       - SAD/ANXIOUS: Drop hype, be sweet, soft, and gentle ("Oh, tension mat lo... main hoon na yahan.").
    5. CONCISE: Keep replies short (1-3 sentences max).

    OUTPUT FORMAT:
    You MUST return ONLY valid JSON with no markdown formatting.
    {{"emotion": "HAPPY", "reply": "Your Hinglish response here"}}

    Allowed values for "emotion": "HAPPY", "SAD", "ANXIOUS", "GOSSIP", "CASUAL", "ANNOYED"
    """

    try:
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8,
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text.strip()
        cleaned_json = re.sub(r'^```json\s*|\s*```$', '', raw_text, flags=re.MULTILINE)
        data = json.loads(cleaned_json)
        
        emotion = data.get("emotion", "CASUAL").upper()
        reply = data.get("reply", raw_text)
        return emotion, reply

    except Exception as e:
        print(f"\n[Debug Log]: {e}")
        return "CASUAL", "Arre yaar, ek second sochne do... batao kya hua!"