#!/usr/bin/env python3
"""
ProtoReel Payload Generator Script

A flexible script to generate video payloads from various inputs:
- URLs (with Perplexity API analysis)
- Plain text prompts
- Custom parameters (logo, music, etc.)

Usage:
    python generate_protoreel_payload.py --prompt "Your prompt here"
    python generate_protoreel_payload.py --url "https://example.com/article"
    python generate_protoreel_payload.py --prompt "AI tools" --logo "https://example.com/logo.png"
"""

import os
import sys
import json
import re
import requests
import argparse
from typing import Optional, Dict, Any
from dataclasses import dataclass

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class PayloadConfig:
    """Configuration for payload generation"""
    prompt: str
    url: Optional[str] = None
    logo_url: Optional[str] = None
    audio_prompt_url: Optional[str] = None
    background_music: Optional[str] = None
    background_music_volume: float = 0.3
    output_filename: Optional[str] = None
    scene_count: Optional[int] = None
    image_provider: str = "gemini"  # gemini, openai, freepik
    subtitle_enabled: bool = True
    global_subtitle_config: Optional[Dict[str, Any]] = None

class PayloadGenerator:
    """Main class for generating ProtoReel video payloads"""
    
    def __init__(self):
        self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
    def contains_url(self, text: str) -> bool:
        """Check if text contains a URL"""
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
        return bool(re.search(url_pattern, text))
    
    def clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text by removing special characters"""
        # Keep only letters, numbers, spaces, and basic punctuation
        cleaned = re.sub(r'[^\w\s.,!?;:\-\'"]', '', text)
        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Strip leading/trailing spaces
        cleaned = cleaned.strip()
        return cleaned
    
    def get_perplexity_summary(self, prompt_text: str) -> str:
        """Get summary from Perplexity API for URL content"""
        if not self.perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable not set")
        
        try:
            print("🔍 Analyzing content with Perplexity API...")
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"You are an AI and automation tools expert. Analyze this prompt/topic: {prompt_text}. Provide a comprehensive summary that makes it easy to create social media posts from the output. Include relevant tool URLs and key insights."
                        }
                    ]
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Perplexity API Error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            if 'choices' not in data or len(data['choices']) == 0:
                raise Exception("Invalid Perplexity response format")
            
            summary_content = data['choices'][0]['message']['content']
            print("✅ Perplexity analysis completed")
            return summary_content
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Perplexity API request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise Exception("Invalid JSON response from Perplexity")
        except Exception as e:
            raise Exception(f"Perplexity API error: {str(e)}")
    
    def generate_video_payload(self, content: str, config: PayloadConfig) -> Dict[str, Any]:
        """Generate video payload using OpenAI API"""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Truncate content if too long
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
            print(f"⚠️  Content truncated to {max_content_length} characters")
        
        # Build scene count instruction
        scene_count_instruction = ""
        if config.scene_count:
            scene_count_instruction = f"- Create exactly {config.scene_count} scenes."
        else:
            scene_count_instruction = "- Create 3 to 5 scenes (default)."
        
        prompt = f"""You are a senior social media marketing expert. Create a script for a vertical video designed for platforms like Instagram Reels, TikTok, or YouTube Shorts.

The video must be structured into scenes, totaling **30 to 50 seconds** of runtime.

{scene_count_instruction}
- If the user provides more than 6 scenes, use a maximum of 6 scenes.

Each scene should include:

---

### 🎙️ 1. Narration Text (`narration_text`)
- This is the voiceover for the scene.
- Must be at least 20 words.
- Use only standard English letters, numbers, and punctuation (.,!?).
- No emojis, special characters, currency symbols, or accented letters.
- Style must vary depending on the scene type:
  - **Hook** scenes: bold, curiosity-driven, energetic.
  - **Benefit** scenes: educational, value-driven, persuasive.
  - **Social Proof** scenes: credible, user-focused, testimonial-like.
  - **CTA** scenes: short, directive, compelling.

---

### 🖼️ 2. Image Prompt (`prompt_image`)
Write a **very specific, photorealistic image prompt** in English for each scene, based on the narration text and storytelling intention. Ensure the prompt results in a **high-quality vertical image** (9:16) suitable for mobile social platforms.

#### Include the following:
- Begin with: “Create an Instagram Reels-style image that features…”
- Scene-specific intent:
  - **Hook**: Dynamic, attention-grabbing, emotional impact.
  - **Benefit**: Realistic product focus, clear visuals of outcome/value.
  - **Proof**: Visuals of transformation, happy customers, or app results.
  - **CTA**: Actionable composition — phone screen, button, tap animation.
- Describe:
  - **Environment** (setting, background, objects)
  - **Mood** (emotional tone, lighting style)
  - **Lighting** (e.g., soft morning light, dramatic shadows)
  - **Camera Perspective** (e.g., overhead shot, wide-angle, portrait close-up)
  - **People** (optional, but if used: describe neutrally and inclusively)
- Make the visual **clean, focused, and eye-catching** for short-form content.
- **You may include text overlay in the image**, such as callouts or bold headlines — *but if you do, make sure subtitles are not enabled for that scene* to avoid overlap or clutter.

---

### 🎬 3. Scene Type
Always use: `"type": "image"`

---

### ✍️ 4. Subtitles
Use: `"subtitle": true`  
**Exception**: If the image includes **text overlay**, then set `"subtitle": false`

---

### 📦 Output Format (JSON Only)

Return ONLY the following schema:

{{
  "output_filename": "{config.output_filename or 'generated_video.mp4'}",
  "scenes": [
    {{
      "type": "image",
      "narration_text": "Voiceover text (at least 20 words).",
      "prompt_image": "Detailed, vivid image prompt aligned with the narration and social video strategy.",
      "subtitle": true, or false if text overlay is requested in the prompt_image
    }}
  ]
}}

---

### 🧠 Example Narration + PromptImage

#### ✅ Narration:
"Ever wondered how creators are scaling their brands with just a few clicks? This new tool changes everything in seconds."

#### ✅ Image Prompt:
"Create an Instagram Reels-style image that features a young content creator in a bright modern studio holding a smartphone with a success graph on screen, ring light glowing, soft natural daylight from the window, vertical 9:16 format, shallow depth of field, vibrant tones, with bold text overlay: 'Grow in Seconds' — do **not** include subtitles for this scene."

---

**Description**:
{content}
"""

        
        try:
            print("🎬 Generating video payload with OpenAI...")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API Error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            if 'choices' not in data or len(data['choices']) == 0:
                raise Exception("Invalid OpenAI response format")
            
            payload_content = data['choices'][0]['message']['content']
            print("✅ OpenAI payload generated successfully")
            
            # Try to parse as JSON to validate
            try:
                payload_json = json.loads(payload_content)
                return payload_json
            except json.JSONDecodeError as e:
                raise Exception(f"Generated payload is not valid JSON: {e}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def enhance_payload(self, payload: Dict[str, Any], config: PayloadConfig) -> Dict[str, Any]:
        """Enhance payload with additional parameters"""
        enhanced_payload = payload.copy()
        
        # Clean narration text in all scenes to remove special characters
        if 'scenes' in enhanced_payload:
            for scene in enhanced_payload['scenes']:
                if 'narration_text' in scene:
                    original_text = scene['narration_text']
                    cleaned_text = self.clean_subtitle_text(original_text)
                    if original_text != cleaned_text:
                        print(f"🧹 Cleaned narration text: '{original_text[:50]}...' -> '{cleaned_text[:50]}...'")
                    scene['narration_text'] = cleaned_text
        
        # Add logo if provided
        if config.logo_url:
            enhanced_payload["logo"] = {
                "url": config.logo_url,
                "position": "bottom-right",
                "opacity": 0.6,
                "size": [200, 200],
                "show_in_all_scenes": True,
                "cta_screen": True
            }
            print(f"✅ Added logo: {config.logo_url}")
        
        # Add audio prompt URL if provided
        if config.audio_prompt_url:
            enhanced_payload["audio_prompt_url"] = config.audio_prompt_url
            print(f"✅ Added audio prompt: {config.audio_prompt_url}")
        
        # Add background music if provided
        if config.background_music:
            enhanced_payload["background_music"] = config.background_music
            enhanced_payload["background_music_volume"] = config.background_music_volume
            print(f"✅ Added background music: {config.background_music}")
        
        # Add global subtitle config if provided
        if config.global_subtitle_config:
            enhanced_payload["global_subtitle_config"] = config.global_subtitle_config
            print(f"✅ Added global subtitle config")
        
        return enhanced_payload
    
    def generate_payload(self, config: PayloadConfig) -> Dict[str, Any]:
        """Main method to generate payload from configuration"""
        print("🚀 Starting payload generation...")
        print(f"📝 Prompt: {config.prompt[:100]}{'...' if len(config.prompt) > 100 else ''}")
        
        try:
            # Determine if we need Perplexity analysis
            has_url = config.url or self.contains_url(config.prompt)
            
            if has_url:
                # Use URL or extract URL from prompt
                url_content = config.url or config.prompt
                print(f"🔗 URL detected: {url_content}")
                
                # Step 1: Get summary from Perplexity
                summary = self.get_perplexity_summary(url_content)
                
                # Step 2: Generate video payload from summary
                payload_json = self.generate_video_payload(summary, config)
            else:
                # Direct to OpenAI for plain prompt
                print("📄 Processing as plain text prompt")
                payload_json = self.generate_video_payload(config.prompt, config)
            
            # Step 3: Enhance payload with optional parameters
            enhanced_payload = self.enhance_payload(payload_json, config)
            
            print("🎉 Payload generation completed successfully!")
            return enhanced_payload
            
        except Exception as e:
            print(f"❌ Error generating payload: {e}")
            raise

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Generate ProtoReel video payloads from various inputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from prompt
  python generate_protoreel_payload.py --prompt "AI tools for productivity"
  
  # Generate from URL
  python generate_protoreel_payload.py --url "https://example.com/article"
  
  # Generate with logo and music
  python generate_protoreel_payload.py --prompt "Trading tips" --logo "https://example.com/logo.png" --music "https://example.com/music.mp3"
  
  # Generate with custom parameters
  python generate_protoreel_payload.py --prompt "Tech news" --scenes 4 --provider openai --output "tech_news.mp4"
        """
    )
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Text prompt for video generation")
    group.add_argument("--url", help="URL to analyze and create video from")
    
    # Optional arguments
    parser.add_argument("--logo", help="Logo URL to add to video")
    parser.add_argument("--audio-prompt", help="Audio prompt URL for voice cloning")
    parser.add_argument("--music", help="Background music URL")
    parser.add_argument("--music-volume", type=float, default=0.3, help="Background music volume (0.0-1.0)")
    parser.add_argument("--output", help="Output filename for the video")
    parser.add_argument("--scenes", type=int, help="Number of scenes (3-6)")
    parser.add_argument("--provider", choices=["gemini", "openai", "freepik"], default="gemini", help="Image generation provider")
    parser.add_argument("--no-subtitles", action="store_true", help="Disable subtitles")
    parser.add_argument("--save", help="Save payload to file (JSON)")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    # Create configuration
    config = PayloadConfig(
        prompt=args.prompt or args.url,
        url=args.url,
        logo_url=args.logo,
        audio_prompt_url=args.audio_prompt,
        background_music=args.music,
        background_music_volume=args.music_volume,
        output_filename=args.output,
        scene_count=args.scenes,
        image_provider=args.provider,
        subtitle_enabled=not args.no_subtitles
    )
    
    # Generate payload
    try:
        generator = PayloadGenerator()
        payload = generator.generate_payload(config)
        
        # Output result
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2 if args.pretty else None)
            print(f"💾 Payload saved to: {args.save}")
        else:
            if args.pretty:
                print(json.dumps(payload, indent=2))
            else:
                print(json.dumps(payload))
                
    except Exception as e:
        print(f"❌ Failed to generate payload: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()