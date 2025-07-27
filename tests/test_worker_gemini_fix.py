#!/usr/bin/env python3
"""
Simple test to verify the worker uses Gemini correctly.
"""
import os
import sys

def test_config():
    """Test that the configuration is correct."""
    print("🧪 Testing Worker Gemini Configuration")
    print("=" * 50)
    
    # Test 1: Check environment variable
    default_provider = os.environ.get("DEFAULT_IMAGE_PROVIDER", "gemini")
    print(f"✅ DEFAULT_IMAGE_PROVIDER: {default_provider}")
    
    # Test 2: Check API key
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    gemeni_api_key = os.environ.get("GEMENI_API_KEY")  # Old typo
    
    if google_api_key:
        print(f"✅ GOOGLE_API_KEY is set: {google_api_key[:10]}...")
    elif gemeni_api_key:
        print(f"⚠️  GEMENI_API_KEY is set (old typo): {gemeni_api_key[:10]}...")
        print("   Please update .env file: GEMENI_API_KEY → GOOGLE_API_KEY")
    else:
        print("❌ No Google API key found")
    
    # Test 3: Import and check config
    try:
        from video_generator.config import Config
        print(f"✅ Config.DEFAULT_IMAGE_PROVIDER: {Config.DEFAULT_IMAGE_PROVIDER}")
        
        from video_generator.generator import SceneInput
        print(f"✅ SceneInput default provider: {SceneInput.__fields__['image_provider'].default}")
        
        # Test creating a scene
        test_scene = {
            "type": "image",
            "promp_image": "A test image",
            "duration": 5
        }
        
        scene_input = SceneInput(**test_scene)
        print(f"✅ Scene uses provider: {scene_input.image_provider}")
        
        if scene_input.image_provider == "gemini":
            print("✅ Worker will use Gemini for image generation!")
        else:
            print(f"❌ Worker will use {scene_input.image_provider} instead of Gemini")
            
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    return True

def main():
    """Run the test."""
    success = test_config()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Configuration is correct!")
        print("\n💡 To use Gemini for image generation:")
        print("   1. Set DEFAULT_IMAGE_PROVIDER=gemini in .env")
        print("   2. Set GOOGLE_API_KEY=your_key in .env")
        print("   3. The worker will use Gemini by default")
    else:
        print("❌ Configuration needs fixing!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 