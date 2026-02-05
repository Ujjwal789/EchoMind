# tts.py - USING EDGE TTS
import asyncio
import threading
import time
import pygame
from io import BytesIO
import edge_tts

# Initialize pygame mixer
pygame.mixer.init()

# Speaking state
_is_speaking = False
_lock = threading.Lock()
_last_speech_end_time = 0
_current_loop = None

def is_speaking():
    """Check if TTS is speaking"""
    with _lock:
        return _is_speaking

def get_last_speech_end_time():
    """Get when TTS last finished speaking"""
    with _lock:
        return _last_speech_end_time

async def _async_speak(text, voice="en-US-AriaNeural"):
    """Async function to generate and play speech"""
    global _is_speaking, _last_speech_end_time
    
    # Set speaking flag
    with _lock:
        _is_speaking = True
    
    try:
        print(f"🗣️  Speaking: '{text[:50]}...'" if len(text) > 50 else f"🗣️  Speaking: '{text}'")
        
        # Create TTS instance
        communicate = edge_tts.Communicate(text, voice)
        
        # Generate audio
        audio_data = BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        # Reset buffer position
        audio_data.seek(0)
        
        # Load and play with pygame
        pygame.mixer.music.load(audio_data)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)
        
        # Update end time
        with _lock:
            _is_speaking = False
            _last_speech_end_time = time.time()
        
        print(f"✅ Finished speaking at {_last_speech_end_time:.2f}")
        
    except Exception as e:
        print(f"TTS Error: {e}")
        with _lock:
            _is_speaking = False
            _last_speech_end_time = time.time()

def _run_async_speak(text):
    """Run async speak in a new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_async_speak(text))
    finally:
        loop.close()

def speak(text: str, voice="en-US-AriaNeural"):
    """Blocking TTS using Edge TTS"""
    if not text or not isinstance(text, str):
        return
    
    text = text.strip()
    if not text:
        return
    
    # Don't start new speech if already speaking
    if is_speaking():
        print("⚠️  Already speaking, skipping...")
        return
    
    # Run in a thread to avoid blocking
    thread = threading.Thread(
        target=_run_async_speak,
        args=(text,),
        daemon=True
    )
    thread.start()
    
    # Wait a moment for speech to start
    time.sleep(0.2)

def wait_until_finished(timeout=30):
    """Wait for TTS to finish speaking"""
    start = time.time()
    while is_speaking():
        if time.time() - start > timeout:
            print("⚠️  TTS timeout!")
            break
        time.sleep(0.1)

def list_voices():
    """List available Edge TTS voices"""
    async def _list_voices():
        voices = await edge_tts.list_voices()
        for voice in voices:
            if 'en-' in voice['ShortName']:
                print(f"{voice['ShortName']}: {voice['Gender']} - {voice['Locale']}")
    
    asyncio.run(_list_voices())

# Optional: Test different voices
AVAILABLE_VOICES = [
    "en-US-AriaNeural",      # Female, expressive
    "en-US-GuyNeural",       # Male, clear
    "en-US-JennyNeural",     # Female, friendly
    "en-GB-SoniaNeural",     # British female
    "en-GB-RyanNeural",      # British male
]