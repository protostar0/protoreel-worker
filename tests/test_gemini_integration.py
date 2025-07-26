#!/usr/bin/env python3
"""
Test script to verify Gemini API integration for image generation.
"""

import os
import sys
import dotenv
from video_generator.gemini_api import generate_image_from_prompt_gemini

def test_gemini_api():
    """Test Gemini API integration."""
    print("Testing Gemini API integration...")
    
    # Load environment variables
    dotenv.load_dotenv()
    
    try:
        # Test image generation
        print("✓ Testing image generation...")
        test_prompt = "Steel factory, clothing store, aluminum production, showing tariffs effectively, photorealistic, educational style"
        
        # Set output path to the desired result directory
        result_dir = "/Users/abdelhakkherroubi/Work/BOTS/ProtoVideo/video-api-serverless/result"
        os.makedirs(result_dir, exist_ok=True)
        output_path = os.path.join(result_dir, "gemini_test_image.png")
        
        try:
            # Test the generation function
            result_path = generate_image_from_prompt_gemini(test_prompt, output_path)
            
            if os.path.exists(result_path):
                file_size = os.path.getsize(result_path)
                print(f"  ✓ Image generated successfully")
                print(f"  ✓ File saved to: {result_path}")
                print(f"  ✓ File size: {file_size} bytes")
                
                # Do not delete the file so user can inspect it
                return True
            else:
                print("  ❌ Image file not found after generation")
                return False
                
        except Exception as e:
            print(f"  ❌ Image generation failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Gemini API test failed: {e}")
        return False

if __name__ == "__main__":
    try:
        success = test_gemini_api()
        if success:
            print("\n🎉 Gemini integration test passed!")
        else:
            print("\n❌ Gemini integration test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1) 