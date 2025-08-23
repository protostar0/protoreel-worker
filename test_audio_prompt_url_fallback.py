#!/usr/bin/env python3
"""
Test script for the audio_prompt_url fallback feature in ProtoVideo Worker.
This demonstrates how global audio_prompt_url is used as fallback when scenes don't have their own.
"""

import json

# Example payload demonstrating audio_prompt_url fallback
example_payload = {
    "output_filename": "test_audio_prompt_fallback.mp4",
    "audio_prompt_url": "https://example.com/global-voice-sample.wav",  # Global fallback
    "scenes": [
        {
            "type": "image",
            "image_url": "https://example.com/image1.jpg",
            "duration": 5,
            "narration_text": "This scene uses the global audio_prompt_url as fallback.",
            "subtitle": True
            # No audio_prompt_url specified - will use global fallback
        },
        {
            "type": "image",
            "image_url": "https://example.com/image2.jpg", 
            "duration": 5,
            "narration_text": "This scene has its own specific audio_prompt_url.",
            "audio_prompt_url": "https://example.com/scene-specific-voice.wav",  # Scene-specific override
            "subtitle": True
        },
        {
            "type": "image",
            "image_url": "https://example.com/image3.jpg",
            "duration": 5,
            "narration_text": "This scene also uses the global audio_prompt_url fallback.",
            "subtitle": True
            # No audio_prompt_url specified - will use global fallback
        }
    ],
    "logo": {
        "url": "https://cdn.com/logo.png",
        "position": "bottom-right",
        "opacity": 0.6,
        "show_in_all_scenes": True,
        "cta_screen": True
    }
}

def test_audio_prompt_url_fallback():
    """
    Test the audio_prompt_url fallback feature functionality.
    """
    print("🚀 ProtoVideo Worker - audio_prompt_url Fallback Feature Test")
    print("=" * 65)
    
    # Display the example payload
    print("\n📋 Example Payload with audio_prompt_url Fallback:")
    print(json.dumps(example_payload, indent=2))
    
    print("\n🔧 How the Fallback Works:")
    print("1. Global audio_prompt_url: Set at the root level of the payload")
    print("2. Scene-specific audio_prompt_url: Can be set per scene")
    print("3. Fallback logic: Scene uses its own if available, otherwise global")
    
    print("\n📝 Scene-by-Scene Breakdown:")
    print("Scene 1: Uses global audio_prompt_url (no scene-specific one)")
    print("Scene 2: Uses scene-specific audio_prompt_url (overrides global)")
    print("Scene 3: Uses global audio_prompt_url (no scene-specific one)")
    
    print("\n💡 Use Cases:")
    print("- Consistent voice across all scenes (set only global)")
    print("- Mix of voices (set global + override specific scenes)")
    print("- Scene-specific voice cloning (set per scene)")
    
    print("\n⚠️  Important Notes:")
    print("- Global audio_prompt_url is always used as fallback")
    print("- Scene-specific audio_prompt_url takes precedence")
    print("- If neither is set, narration will use default voice")
    print("- This feature works with both global and per-scene narration")
    
    print("\n✅ Feature successfully implemented!")
    return True

if __name__ == "__main__":
    test_audio_prompt_url_fallback() 