"""Test TTS module"""
import sys
import os
sys.path.insert(0, r'e:\AI-Voice-Agent\backend')

print("Testing TTS...")
from app.tts.coqui_tts import synthesize_speech
import wave

# Test TTS generation
test_text = "Hello, this is a test of the text to speech system."
output_file = r"e:\AI-Voice-Agent\backend\test_tts.wav"

print(f"Generating speech: '{test_text}'")
synthesize_speech(test_text, output_file)

if os.path.exists(output_file):
    print(f"✓ Audio file created: {output_file}")
    
    # Check audio properties
    with wave.open(output_file, 'r') as w:
        sample_rate = w.getframerate()
        channels = w.getnchannels()
        duration = w.getnframes() / w.getframerate()
        
        print(f"✓ Sample rate: {sample_rate} Hz")
        print(f"✓ Channels: {channels} (mono)")
        print(f"✓ Duration: {duration:.2f} seconds")
        print(f"✓ Format: Compatible with Asterisk telephony")
else:
    print("✗ Audio file was not created")

print("\nTTS test complete!")
