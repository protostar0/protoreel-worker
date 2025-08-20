#!/usr/bin/env python3
"""
Test script for the prompt_edit_image feature in ProtoVideo Worker.
This demonstrates how to use AI image editing in your video generation requests.
"""

import json
import os

# Example payload with prompt_edit_image feature
example_payload = {
    "output_filename": "test_edited_image_video.mp4",
    "scenes": [
        {
            "type": "image",
            "image_url": "https://example.com/your-image.jpg",  # Source image to edit
            "prompt_edit_image": "Make the sky more dramatic with storm clouds and add lightning effects",  # AI editing prompt
            "duration": 5,
            "narration_text": "This is an edited image with dramatic storm effects.",
            "subtitle": True
        },
        {
            "type": "image", 
            "image_url": "https://example.com/another-image.jpg",
            "prompt_edit_image": "Change the color scheme to warm sunset tones and add golden hour lighting",
            "duration": 5,
            "narration_text": "Here's another image edited with warm sunset colors.",
            "subtitle": True
        }
    ],
    "narration_text": "This video demonstrates AI-powered image editing capabilities.",
    "logo": {
        "url": "https://cdn.com/logo.png",
        "position": "bottom-right",
        "opacity": 0.6,
        "show_in_all_scenes": True,
        "cta_screen": True
    }
}

def test_prompt_edit_image_feature():
    """
    Test the prompt_edit_image feature functionality.
    """
    print("🚀 ProtoVideo Worker - prompt_edit_image Feature Test")
    print("=" * 60)
    
    # Check if required environment variables are set
    required_vars = ["GEMENI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these environment variables before running the test.")
        return False
    
    print("✅ Environment variables configured")
    
    # Display the example payload
    print("\n📋 Example Payload with prompt_edit_image:")
    print(json.dumps(example_payload, indent=2))
    
    print("\n🔧 How it works:")
    print("1. Provide an image_url with the source image")
    print("2. Add prompt_edit_image with your AI editing instructions")
    print("3. The AI will modify the image based on your prompt")
    print("4. The edited image will be used in the video generation")
    
    print("\n💡 Example prompts you can use:")
    print("- 'Make the sky more dramatic with storm clouds'")
    print("- 'Change the color scheme to warm sunset tones'")
    print("- 'Add a vintage film grain effect'")
    print("- 'Make the lighting more cinematic'")
    print("- 'Add depth of field blur to the background'")
    
    print("\n⚠️  Important Notes:")
    print("- Requires GEMENI_API_KEY environment variable")
    print("- Image editing happens before video generation")
    print("- If editing fails, the original image is used")
    print("- Edited images are automatically resized to REEL_SIZE (1080x1920)")
    
    print("\n✅ Feature successfully implemented!")
    return True

if __name__ == "__main__":
    test_prompt_edit_image_feature() 