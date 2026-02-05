# stt.py
import time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from voice.tts import is_speaking

SAMPLE_RATE = 16000
RECORD_SECONDS = 5

model = WhisperModel("small", device="cpu", compute_type="int8")

def listen_and_transcribe():
    """Simple listen and transcribe"""
    
    # Wait for TTS to finish
    if is_speaking():
        print("⏳ Waiting for TTS to finish...")
        while is_speaking():
            time.sleep(0.1)
    
    # Extra delay to ensure audio device is free
    time.sleep(0.3)
    
    print("🎤 Listening...")
    
    # Record
    try:
        audio = sd.rec(
            int(RECORD_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32'
        )
        sd.wait()
    except Exception as e:
        print(f"Recording error: {e}")
        return None
    
    # Quick volume check
    if np.max(np.abs(audio)) < 0.01:
        return None
    
    # Transcribe
    try:
        audio_flat = audio.flatten()
        segments, info = model.transcribe(
            audio_flat,
            language="en",
            vad_filter=True
        )
        
        text = " ".join([segment.text.strip() for segment in segments]).strip()
        
        if len(text) < 2:
            return None
        
        return text
        
    except Exception as e:
        print(f"Transcription error: {e}")
        return None