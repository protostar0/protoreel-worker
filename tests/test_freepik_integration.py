#!/usr/bin/env python3
"""
Test script to verify Freepik API integration for image generation.
"""

import os
import sys
import tempfile
import dotenv
from video_generator.freepik_api import FreepikAPI, generate_image_from_prompt_freepik

def test_freepik_api():
    """Test Freepik API integration."""
    print("Testing Freepik API integration...")
    
    # Load environment variables
    dotenv.load_dotenv()
    
    # Check if API key is available
    api_key = os.environ.get("FREEPIK_API_KEY")
    if not api_key:
        print("❌ FREEPIK_API_KEY environment variable not set")
        print("   Please set FREEPIK_API_KEY to test Freepik integration")
        return False
    
    try:
        # Test 1: Initialize API client
        print("✓ Testing API client initialization...")
        freepik = FreepikAPI(api_key)
        print("  ✓ FreepikAPI client created successfully")
        
        # Test 2: Generate image
        print("\n✓ Testing image generation...")
        test_prompt = "A beautiful sunset over mountains"
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            output_path = tmp_file.name
        
        try:
            # Test the generation function
            result_path = generate_image_from_prompt_freepik(test_prompt, api_key, output_path)
            
            if os.path.exists(result_path):
                file_size = os.path.getsize(result_path)
                print(f"  ✓ Image generated successfully")
                print(f"  ✓ File saved to: {result_path}")
                print(f"  ✓ File size: {file_size} bytes")
                
                # Clean up
                os.unlink(result_path)
                return True
            else:
                print("  ❌ Image file not found after generation")
                return False
                
        except Exception as e:
            print(f"  ❌ Image generation failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Freepik API test failed: {e}")
        return False

def test_provider_selection():
    """Test that the provider selection works correctly."""
    print("\nTesting provider selection...")
    
    # Test with different providers
    providers = ["openai", "freepik"]
    
    for provider in providers:
        print(f"  Testing {provider} provider...")
        
        # Check if API key is available for this provider
        if provider == "freepik":
            api_key = os.environ.get("FREEPIK_API_KEY")
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            print(f"    ⚠️  {provider.upper()}_API_KEY not set, skipping test")
            continue
        
        print(f"    ✓ {provider} API key available")
    
    print("  ✓ Provider selection test completed")

if __name__ == "__main__":
    try:
        # Test Freepik API
        freepik_success = test_freepik_api()
        
        # Test provider selection
        test_provider_selection()
        
        if freepik_success:
            print("\n🎉 Freepik integration test passed!")
        else:
            print("\n❌ Freepik integration test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1) 