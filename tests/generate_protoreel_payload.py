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
        
        prompt = f"""You are a social media marketing specialist. Create a script for a social media video based on the topic below.
The video must be structured into scenes, with a total length between 30 to 50 seconds.
{scene_count_instruction}
- If the user specifies more than 6 scenes, create only 6 scenes maximum.
Each scene should include the following:
1. Image prompt (prompt_image): A highly detailed, photo-realistic image description written in English. It must avoid any content related to violence, sexual content, hate, self-harm, illegal activity, sensitive political material, or graphic realism. The image must depict the subject with creative, educational, or abstract qualities suitable for general audiences.
2. Narration text: At least 20 words per scene. This will be the voiceover script. Use only standard letters, numbers, spaces, and basic punctuation (periods, commas, question marks, exclamation marks). Avoid special characters, symbols, emojis, or non-ASCII characters.
3. Scene type: Always "image".
4. Subtitles enabled: "subtitle": true.

Description: {content}

Return your response ONLY in JSON format following this schema:

{{
  "output_filename": "{config.output_filename or 'generated_video.mp4'}",
  "scenes": [
    {{
      "type": "image",
      "narration_text": "Voiceover text (at least 20 words).",
      "prompt_image": "Detailed image description in English, photorealistic, high resolution, neutral and creative.",
      "subtitle": true
    }}
  ]
}}

Extra Instructions for Better Images:
- Be specific about the environment, mood, lighting, and camera perspective (e.g., "wide-angle shot of a bustling coffee shop with soft morning sunlight").
- Include colors, textures, and visual elements related to the topic.
- If people are shown, describe their appearance and clothing neutrally (e.g., "diverse group of professionals in casual attire").
- Mention the background context to make it visually rich (e.g., "city skyline at sunset behind a rooftop garden").

Subtitle Text Requirements:
- Use only standard English letters, numbers, spaces, and basic punctuation (.,!?;:-'").
- Avoid emojis, special symbols, currency signs, mathematical symbols, or any non-ASCII characters.
- Keep sentences clear and readable for voice synthesis.
- Use proper capitalization and punctuation for natural speech flow.

Example PromptImage (Good):
"A bright, sunlit co-working space with large glass windows, green indoor plants, modern laptops on wooden desks, and a diverse group of professionals collaborating enthusiastically, captured in ultra-realistic detail, sharp focus, soft natural lighting."

Example Narration Text (Good):
"Welcome to the world of AI productivity tools that are revolutionizing how we work and manage our daily tasks efficiently."
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