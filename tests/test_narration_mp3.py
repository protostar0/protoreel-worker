#!/usr/bin/env python3
"""
Test script to generate narration with audio_prompt_url and return MP3 file.
"""
import os
import sys
import dotenv
import tempfile
import numpy as np
import torch
import torchaudio as ta
from video_generator.audio_utils import generate_narration

def create_test_audio_file():
    """Create a test audio file for testing."""
    # Create a simple test audio file
    sample_rate = 16000
    duration = 3.0  # 3 seconds
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate a simple sine wave
    audio_data = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz sine wave
    
    # Convert to torch tensor
    audio_tensor = torch.tensor(audio_data, dtype=torch.float32).unsqueeze(0)
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    ta.save(temp_file.name, audio_tensor, sample_rate)
    return temp_file.name

def test_narration_with_prompt_url():
    """Test narration generation with audio_prompt_url and return MP3."""
    print("🎵 Testing Narration Generation with Audio Prompt URL")
    print("=" * 50)
    
    # Create a test audio file
    test_audio_path = create_test_audio_file()
    
    try:
        # Test with file:// URL
        file_url = f"https://pub-b3d68bfabb5742dabcd0275d1b282f2a.r2.dev/fce24158.wav"
        print(f"📁 Using audio prompt URL: {file_url}")
        
        test_text = "This is a test narration with audio prompt. The voice should match the provided audio sample."
        print(f"📝 Text to narrate: {test_text}")
        
        # Generate narration with audio prompt
        result_path = generate_narration(test_text, audio_prompt_url=file_url)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ Narration generated successfully!")
            print(f"📁 MP3 file saved to: {result_path}")
            print(f"📊 File size: {file_size} bytes")
            print(f"🎵 File extension: {os.path.splitext(result_path)[1]}")
            
            # Verify it's an MP3 file
            if result_path.endswith('.mp3'):
                print("✅ File is MP3 format")
            else:
                print("⚠️  File is not MP3 format")
            
            # Keep the file for inspection (don't delete)
            print(f"💾 MP3 file preserved at: {result_path}")
            return result_path
        else:
            print("❌ Generated narration file not found")
            return None
            
    except Exception as e:
        print(f"❌ Narration generation failed: {e}")
        return None
    finally:
        # Cleanup test audio file
        if os.path.exists(test_audio_path):
            os.remove(test_audio_path)
            print(f"🗑️  Cleaned up test audio file: {test_audio_path}")

def test_narration_without_prompt_url():
    """Test narration generation without audio_prompt_url (default voice)."""
    print("\n🎵 Testing Narration Generation without Audio Prompt URL")
    print("=" * 50)
    
    try:
        test_text = "This is a test narration without audio prompt. It should use the default voice."
        print(f"📝 Text to narrate: {test_text}")
        
        # Generate narration without audio prompt
        result_path = generate_narration(test_text)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ Narration generated successfully!")
            print(f"📁 MP3 file saved to: {result_path}")
            print(f"📊 File size: {file_size} bytes")
            print(f"🎵 File extension: {os.path.splitext(result_path)[1]}")
            
            # Verify it's an MP3 file
            if result_path.endswith('.mp3'):
                print("✅ File is MP3 format")
            else:
                print("⚠️  File is not MP3 format")
            
            # Keep the file for inspection (don't delete)
            print(f"💾 MP3 file preserved at: {result_path}")
            return result_path
        else:
            print("❌ Generated narration file not found")
            return None
            
    except Exception as e:
        print(f"❌ Narration generation failed: {e}")
        return None

if __name__ == "__main__":
    dotenv.load_dotenv()
    
    print("🎵 Narration Generation Test with Audio Prompt URL")
    print("=" * 60)
    
    try:
        # Test 1: With audio prompt URL
        mp3_with_prompt = test_narration_with_prompt_url()
        
        # Test 2: Without audio prompt URL (default voice)
        mp3_without_prompt = test_narration_without_prompt_url()
        
        print("\n" + "=" * 60)
        print("📋 Test Results Summary:")
        print(f"   With audio prompt: {'✅ Success' if mp3_with_prompt else '❌ Failed'}")
        print(f"   Without audio prompt: {'✅ Success' if mp3_without_prompt else '❌ Failed'}")
        
        if mp3_with_prompt and mp3_without_prompt:
            print("\n🎉 Both tests passed! MP3 files generated successfully.")
            print(f"📁 With prompt MP3: {mp3_with_prompt}")
            print(f"📁 Without prompt MP3: {mp3_without_prompt}")
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1) 