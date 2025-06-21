import whisper
import os
import tempfile
import uuid

print("Testing Whisper setup...")

try:
    print("1. Loading Whisper model...")
    model = whisper.load_model("base")
    print("✅ Model loaded successfully")
    
    print("2. Testing model info...")
    print(f"   Model type: {type(model)}")
    
    print("3. Creating a test audio file...")
    # Create a dummy audio file for testing
    temp_dir = tempfile.gettempdir()
    test_audio_path = os.path.join(temp_dir, f"test_audio_{uuid.uuid4()}.wav")
    
    # Create a simple WAV file (1 second of silence)
    import wave
    import struct
    
    with wave.open(test_audio_path, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(16000)  # 16kHz
        # 1 second of silence
        silence = struct.pack('<h', 0) * 16000
        wav_file.writeframes(silence)
    
    print(f"✅ Test audio file created: {test_audio_path}")
    print(f"   File size: {os.path.getsize(test_audio_path)} bytes")
    
    print("4. Testing transcription...")
    abs_path = os.path.abspath(test_audio_path)
    print(f"   Using absolute path: {abs_path}")
    print(f"   File exists: {os.path.exists(abs_path)}")
    
    result = model.transcribe(abs_path)
    print("✅ Transcription completed")
    print(f"   Result: {result['text']}")
    
    # Cleanup
    os.remove(test_audio_path)
    print("✅ Test file cleaned up")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc() 