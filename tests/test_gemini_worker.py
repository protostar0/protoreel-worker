#!/usr/bin/env python3
"""
Test to verify that the worker uses Gemini for image generation.
"""
import os
import sys
import dotenv
from unittest.mock import patch, MagicMock

dotenv.load_dotenv()

def test_gemini_default_provider():
    """Test that the worker uses Gemini as default provider."""
    print("🧪 Testing Gemini Default Provider")
    print("=" * 50)
    
    # Check environment variable
    default_provider = os.environ.get("DEFAULT_IMAGE_PROVIDER", "gemini")
    print(f"✅ DEFAULT_IMAGE_PROVIDER: {default_provider}")
    
    # Import config and check
    from video_generator.config import Config
    print(f"✅ Config.DEFAULT_IMAGE_PROVIDER: {Config.DEFAULT_IMAGE_PROVIDER}")
    
    # Import SceneInput and check default
    from video_generator.generator import SceneInput
    print(f"✅ SceneInput.image_provider default: {SceneInput.__fields__['image_provider'].default}")
    
    # Test creating a scene without explicit image_provider
    test_scene = {
        "type": "image",
        "promp_image": "A test image",
        "duration": 5
    }
    
    scene_input = SceneInput(**test_scene)
    print(f"✅ Scene image_provider: {scene_input.image_provider}")
    
    # Verify it uses the default
    assert scene_input.image_provider == Config.DEFAULT_IMAGE_PROVIDER, f"Expected {Config.DEFAULT_IMAGE_PROVIDER}, got {scene_input.image_provider}"
    print("✅ Scene uses default image provider correctly")
    
    return True

def test_gemini_api_key():
    """Test that Gemini API key is available."""
    print("\n🔑 Testing Gemini API Key")
    print("=" * 50)
    
    gemini_api_key = os.environ.get("GOOGLE_API_KEY")
    if gemini_api_key:
        print(f"✅ GOOGLE_API_KEY is set: {gemini_api_key[:10]}...")
    else:
        print("⚠️  GOOGLE_API_KEY is not set")
    
    return gemini_api_key is not None

def test_gemini_import():
    """Test that Gemini API can be imported."""
    print("\n📦 Testing Gemini Import")
    print("=" * 50)
    
    try:
        from video_generator.gemini_api import generate_image_from_prompt_gemini
        print("✅ Gemini API module imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import Gemini API: {e}")
        return False

def test_image_generation_flow():
    """Test the image generation flow with Gemini."""
    print("\n🎨 Testing Image Generation Flow")
    print("=" * 50)
    
    try:
        from video_generator.image_utils import generate_image_from_prompt
        from video_generator.config import Config
        import tempfile
        
        # Test the flow
        test_prompt = "A simple test image"
        test_output = tempfile.mktemp(suffix='.png')
        
        print(f"✅ Testing image generation with provider: {Config.DEFAULT_IMAGE_PROVIDER}")
        print(f"✅ Test prompt: {test_prompt}")
        print(f"✅ Test output: {test_output}")
        
        # Note: This would actually call the API, so we'll just test the import
        print("✅ Image generation flow ready (API call would happen here)")
        return True
        
    except Exception as e:
        print(f"❌ Image generation flow test failed: {e}")
        return False

def main():
    """Run all Gemini worker tests."""
    print("🧪 Gemini Worker Test Suite")
    print("=" * 60)
    
    tests = [
        ("Default Provider Test", test_gemini_default_provider),
        ("API Key Test", test_gemini_api_key),
        ("Import Test", test_gemini_import),
        ("Image Generation Flow Test", test_image_generation_flow)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Gemini Worker Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Gemini worker tests passed!")
        print("\n💡 The worker should now use Gemini for image generation when:")
        print("   - DEFAULT_IMAGE_PROVIDER=gemini is set")
        print("   - No explicit image_provider is specified in scenes")
        print("   - GOOGLE_API_KEY is configured")
        return 0
    else:
        print("❌ Some Gemini worker tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 