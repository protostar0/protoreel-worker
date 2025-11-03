#!/usr/bin/env python3
"""
ProtoReel Payload Generator with Pexels Video Integration

Generates video payloads using Pexels videos mixed with AI-generated images.
Workflow:
1. User provides topic/article
2. Extract keywords from topic
3. Search Pexels for videos using keywords
4. Send Pexels results to ChatGPT
5. ChatGPT selects best videos and creates mixed payload (videos + images)
6. Generate final payload with narration, subtitles, etc.

Usage:
    python tests/generate_protoreel_payload_with_pexels.py --topic "AI productivity tools"
    python tests/generate_protoreel_payload_with_pexels.py --url "https://www.coindesk.com/markets/2025/11/01/bitcoin-s-red-october-what-happened-to-the-widely-anticipated-uptober-crypto-rally"
    python tests/generate_protoreel_payload_with_pexels.py --topic "Trading tips" --logo "https://example.com/logo.png"
"""

import os
import sys
import json
import re
import requests
import argparse
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class PayloadConfig:
    """Configuration for payload generation"""
    topic: str
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
    max_pexels_results: int = 20  # Maximum Pexels videos to fetch per keyword
    pexels_videos_per_scene: int = 5  # How many Pexels results to show ChatGPT per scene

class PexelsVideoSearch:
    """Handles Pexels API video searches"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pexels.com/videos"
        
    def search_videos(self, query: str, per_page: int = 15, page: int = 1, orientation: str = "portrait") -> List[Dict[str, Any]]:
        """
        Search for videos on Pexels
        
        Args:
            query: Search query/keyword
            per_page: Number of results per page (max 80)
            page: Page number
            orientation: portrait, landscape, or square
            
        Returns:
            List of video dictionaries with metadata
        """
        headers = {
            "Authorization": self.api_key
        }
        
        params = {
            "query": query,
            "per_page": min(per_page, 80),
            "page": page,
            "orientation": orientation
        }
        
        try:
            # Pexels API format: Authorization header with API key directly (no "Bearer")
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Pexels API Error: {response.status_code} - {response.text}")
            
            data = response.json()
            videos = []
            
            for video in data.get("videos", []):
                # Extract best quality video file (prefer HD, then SD)
                video_files = video.get("video_files", [])
                if not video_files:
                    continue
                
                # Sort by quality (width/height) descending
                video_files.sort(key=lambda x: x.get("width", 0) * x.get("height", 0), reverse=True)
                best_video = video_files[0]
                
                videos.append({
                    "id": video.get("id"),
                    "url": best_video.get("link"),
                    "width": best_video.get("width"),
                    "height": best_video.get("height"),
                    "duration": video.get("duration"),
                    "thumbnail": video.get("image"),
                    "photographer": video.get("photographer"),
                    "photographer_url": video.get("photographer_url"),
                    "pexels_url": video.get("url"),
                    "query": query  # Store which keyword found this
                })
            
            return videos
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Pexels API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Pexels API error: {str(e)}")

class PayloadGeneratorWithPexels:
    """Main class for generating ProtoReel video payloads with Pexels videos"""
    
    def __init__(self):
        self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        pexels_api_key = os.environ.get("PEXELS_API_KEY")
        
        if not pexels_api_key:
            raise ValueError("PEXELS_API_KEY environment variable not set")
        
        self.pexels = PexelsVideoSearch(pexels_api_key)
        
    def contains_url(self, text: str) -> bool:
        """Check if text contains a URL"""
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
        return bool(re.search(url_pattern, text))
    
    def clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text by removing special characters"""
        cleaned = re.sub(r'[^\w\s.,!?;:\-\'"]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        return cleaned
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        Extract keywords from text using OpenAI
        
        Args:
            text: Input text to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            List of keyword strings
        """
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Truncate if too long
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        prompt = f"""Extract {max_keywords} relevant keywords from the following text that would be useful for searching stock videos on Pexels.
        
Focus on:
- Nouns (people, objects, concepts)
- Action verbs (running, working, creating)
- Descriptive terms (modern, professional, urban)
- Context words (business, nature, technology)

Text:
{text}

Return ONLY a comma-separated list of keywords, nothing else.
Example format: keyword1, keyword2, keyword3"""
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 100,
                    "temperature": 0.5
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API Error: {response.status_code}")
            
            data = response.json()
            keywords_text = data['choices'][0]['message']['content'].strip()
            
            # Parse keywords
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            
            print(f"🔑 Extracted keywords: {', '.join(keywords)}")
            return keywords[:max_keywords]
            
        except Exception as e:
            print(f"⚠️  Keyword extraction failed: {e}. Using fallback method.")
            # Fallback: simple keyword extraction
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            # Remove common stop words
            stop_words = {'this', 'that', 'with', 'from', 'have', 'been', 'will', 'your', 'they', 'their', 'there'}
            keywords = [w for w in words if w not in stop_words][:max_keywords]
            return list(set(keywords))
    
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
    
    def validate_pexels_video_url(self, video_url: str) -> bool:
        """
        Validate that a Pexels video URL is accessible and working
        
        Args:
            video_url: Pexels video URL to validate
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            # Prepare headers for Pexels
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://www.pexels.com/'
            }
            
            # Add API key if available
            pexels_api_key = os.environ.get("PEXELS_API_KEY")
            if pexels_api_key:
                headers['Authorization'] = pexels_api_key
            
            # Use HEAD request for faster validation (don't download the file)
            response = requests.head(video_url, headers=headers, timeout=10, allow_redirects=True)
            
            # Check if status is 200 (OK) or 302 (redirect to valid resource)
            if response.status_code in [200, 302]:
                return True
            elif response.status_code == 403:
                # Try with GET request to verify (sometimes HEAD is blocked but GET works)
                response_get = requests.get(video_url, headers=headers, stream=True, timeout=10)
                if response_get.status_code == 200:
                    return True
                return False
            else:
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"    ⚠️  Validation error for {video_url[:50]}...: {e}")
            return False
        except Exception as e:
            print(f"    ⚠️  Unexpected validation error: {e}")
            return False
    
    def search_pexels_for_scenes(self, keywords: List[str], config: PayloadConfig) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search Pexels for videos using keywords (without validation for speed)
        
        Args:
            keywords: List of keywords to search
            config: Payload configuration
            
        Returns:
            Dictionary mapping keywords to video results
        """
        print(f"🎬 Searching Pexels for videos with {len(keywords)} keywords...")
        
        keyword_videos = {}
        for keyword in keywords:
            try:
                print(f"  📹 Searching for: '{keyword}'...")
                videos = self.pexels.search_videos(
                    query=keyword,
                    per_page=config.max_pexels_results,
                    orientation="portrait"  # 9:16 aspect ratio for Reels
                )
                keyword_videos[keyword] = videos
                print(f"    ✅ Found {len(videos)} videos")
            except Exception as e:
                print(f"    ⚠️  Error searching '{keyword}': {e}")
                keyword_videos[keyword] = []
        
        return keyword_videos
    
    def generate_video_payload_with_pexels(
        self, 
        content: str, 
        pexels_videos: Dict[str, List[Dict[str, Any]]],
        config: PayloadConfig
    ) -> Dict[str, Any]:
        """
        Generate video payload using OpenAI API with Pexels video selection
        
        Args:
            content: Topic/article content
            pexels_videos: Dictionary of keywords -> video lists
            config: Payload configuration
            
        Returns:
            Generated payload JSON
        """
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
        
        # Format Pexels videos for ChatGPT
        pexels_video_list = []
        for keyword, videos in pexels_videos.items():
            for video in videos[:config.pexels_videos_per_scene]:  # Limit per keyword
                pexels_video_list.append({
                    "keyword": keyword,
                    "url": video["url"],
                    "width": video.get("width", 0),
                    "height": video.get("height", 0),
                    "duration": video.get("duration", 0),
                    "thumbnail": video.get("thumbnail", ""),
                    "photographer": video.get("photographer", ""),
                    "id": video.get("id", 0)
                })
        
        # Build prompt for ChatGPT
        prompt = f"""You are a senior social media marketing expert. Create a script for a vertical video designed for platforms like Instagram Reels, TikTok, or YouTube Shorts.

The video must be structured into scenes, totaling **30 to 50 seconds** of runtime.

{scene_count_instruction}
- If the user provides more than 6 scenes, use a maximum of 6 scenes.

**CRITICAL: The LAST scene MUST be a CTA (Call To Action) scene:**
- The final scene should encourage engagement with text like "Follow for more", "Like for more", "Save for later", or similar
- Use compelling CTA narration like: "Follow for more tips", "Like if this helped you", "Save this for later", "Share with someone who needs this", etc.
- The CTA scene should preferably be an AI-generated image with clear text overlay encouraging engagement
- Keep CTA narration short (15-25 words) and compelling

**IMPORTANT: Mix Pexels videos and AI-generated images strategically:**
- Use Pexels videos for: dynamic action, real-world footage, B-roll, background scenes
- Use AI-generated images for: specific concepts, branded content, text-heavy visuals, abstract ideas, CTA scenes
- Vary between videos and images to keep the video engaging

Each scene should include:

---

### 🎙️ 1. Narration Text (`narration_text`) - **REQUIRED FOR ALL SCENES**

**CRITICAL: EVERY scene (both video AND image scenes) MUST include `narration_text`.**

- This is the voiceover for the scene.
- **MANDATORY**: Every scene must have narration text, regardless of whether it's a video or image scene.
- Must be at least 20 words.
- Use only standard English letters, numbers, and punctuation (.,!?).
- No emojis, special characters, currency symbols, or accented letters.
- Style must vary depending on the scene type:
  - **Hook** scenes: bold, curiosity-driven, energetic.
  - **Benefit** scenes: educational, value-driven, persuasive.
  - **Social Proof** scenes: credible, user-focused, testimonial-like.
  - **CTA** scenes: short, directive, compelling, with engagement prompts like "Follow for more", "Like for more", "Save for later"

---

### 🎬 2. Scene Type & Media

For EACH scene, choose ONE of these options:

#### Option A: Use Pexels Video
- Set `"type": "video"`
- Set `"video_url"` to one of the Pexels video URLs provided below
- **MUST include `narration_text`** (required for all scenes)
- DO NOT set `prompt_image` if using video
- Choose videos that match the narration and scene intent
- Prioritize higher quality videos (higher resolution)
- Ensure video orientation matches vertical (portrait) format
- **ALWAYS set `"subtitle": true` for video scenes** — videos should always have subtitles

#### Option B: Use AI-Generated Image
- Set `"type": "image"`
- Set `"prompt_image"` with a detailed, vivid image prompt
- **MUST include `narration_text`** (required for all scenes)
- **ALWAYS set `"subtitle": true`** — all image scenes must have subtitles
- DO NOT set `video_url` if using image
- Write a **very specific, photorealistic image prompt** in English
- Begin with: "Create an Instagram Reels-style image that features..."
- Describe: environment, mood, lighting, camera perspective, people (if needed)
- Make the visual **clean, focused, and eye-catching** for short-form content
- **You may include text overlay in the image**, such as callouts or bold headlines
- **CRITICAL - Text Overlay Rules**:
  - Text overlay MUST be **small** and positioned at the **very top** of the image
  - Use small, compact text that takes minimal space (not large or prominent)
  - Place it in the **upper 20%** of the image frame
  - Keep it minimal and unobtrusive so it doesn't interfere with subtitles at the bottom
  - Subtitles will appear at the bottom, so ensure text overlay stays at the top and is small
- Scene-specific intent:
  - **Hook**: Dynamic, attention-grabbing, emotional impact.
  - **Benefit**: Realistic product focus, clear visuals of outcome/value.
  - **Proof**: Visuals of transformation, happy customers, or app results.
  - **CTA**: Actionable composition — phone screen, button, tap animation, with small text overlay at top like "Follow for more", "Like for more", "Save for later"

---

### ✍️ 3. Subtitles
- **MANDATORY**: ALWAYS use `"subtitle": true` for **ALL scenes** (both video and image scenes)
- **There are NO exceptions** — every scene must have subtitles enabled
- **Text overlay handling**: If an image includes text overlay, make the text **small and positioned at the very top** of the image so it doesn't interfere with subtitles at the bottom
- Subtitles will appear at the bottom of the video, so any text overlay must be small and in the upper portion

---

### 📦 Output Format (JSON Only)

Return ONLY the following schema:

{{
  "output_filename": "{config.output_filename or 'generated_video.mp4'}",
  "scenes": [
    {{
      "type": "video",  // OR "image"
      "video_url": "https://pexels.com/...",  // IF type is "video", use one from Pexels list below (REQUIRED for video scenes)
      "prompt_image": "Create an Instagram Reels-style image...",  // IF type is "image" (REQUIRED for image scenes)
      "narration_text": "Voiceover text (at least 20 words).",  // REQUIRED FOR ALL SCENES (both video and image)
      "subtitle": true  // ALWAYS true for ALL scenes (both video and image) - MANDATORY
    }}
  ],
  "post_description": "A social caption with hashtags (1-2 hook lines, a value, CTA, and relevant hashtags)"
}}

**REMINDERS**: 
1. Every scene MUST have `narration_text` - this is not optional. Both video and image scenes require narration.
2. Every scene MUST have `"subtitle": true` - this is mandatory for all scenes (both video and image).
3. If image scenes include text overlay, make it SMALL and place it at the TOP to avoid interference with subtitles at the bottom.

---

### 🧠 Example Narration + Media Selection

#### ✅ Example 1: Video Scene with Subtitle
**Narration:**
"Discover the most powerful AI tools that are transforming how we work and create content in 2024."

**Scene:**
- Type: `"video"`
- Video URL: Use one from Pexels list that matches "AI tools" or "technology"
- Subtitle: `true` (ALWAYS true for videos)

#### ✅ Example 2: Image Scene with Small Text Overlay (Subtitle Enabled)
**Narration:** (REQUIRED - note how image scenes also have narration)
"Ever wondered how creators are scaling their brands with just a few clicks? This new tool changes everything in seconds."

**Scene:**
- Type: `"image"`
- Narration Text: `"Ever wondered how creators are scaling their brands with just a few clicks? This new tool changes everything in seconds."` (REQUIRED)
- Prompt Image: "Create an Instagram Reels-style image that features a young content creator in a bright modern studio holding a smartphone with a success graph on screen, ring light glowing, soft natural daylight from the window, vertical 9:16 format, shallow depth of field, vibrant tones, with a **small, compact text overlay at the very top** of the image (upper 20%): 'Grow in Seconds' — keep text small so subtitle at bottom doesn't interfere."
- Subtitle: `true` (ALWAYS true - text overlay is small and at top, subtitle at bottom - no interference)

#### ✅ Example 3: Image Scene with Subtitle (Small Text at Top)
**Narration:** (REQUIRED - every image scene must have narration)
"These productivity hacks will save you hours every single day."

**Scene:**
- Type: `"image"`
- Narration Text: `"These productivity hacks will save you hours every single day."` (REQUIRED)
- Prompt Image: "Create an Instagram Reels-style image that features a clean workspace with a laptop, organized desk items, and morning sunlight. Vertical 9:16 format. Include a **small, minimal callout text at the very top** of the image (upper portion): 'Pro Tip' — keep it small and compact. Subtitle will appear at bottom."
- Subtitle: `true` (ALWAYS true for all scenes - small text overlay at top, subtitle at bottom - no overlap)

---

### 🎬 Available Pexels Videos

Choose from these videos when creating video scenes. Use the `video_url` field exactly as shown:

{json.dumps(pexels_video_list[:50], indent=2)}  // Limit to top 50 videos

**Selection criteria:**
- Match video content to narration and scene purpose
- Prefer higher resolution videos (check width/height)
- Ensure videos are portrait/vertical orientation (9:16)
- Mix videos and images for visual variety

---

### 🎯 Final Scene Requirements

**MANDATORY**: The LAST scene in the video MUST be a CTA scene:
- Narration should encourage engagement: "Follow for more tips", "Like if this helped you", "Save this post for later", "Share with someone who needs this", etc.
- Scene type: Prefer AI-generated image with text overlay for better control over CTA messaging
- Image prompt should include small text overlay at the top (upper 20%) with phrases like:
  - "Follow for more"
  - "Like for more"
  - "Save for later"
  - "Share this"
  - "Follow me"
- Keep CTA narration short (15-25 words) and compelling
- Make the visual appealing and action-oriented
- Subtitle: `true` (ALWAYS true for all scenes including CTA)
- Text overlay must be small and at the top to avoid interference with subtitles at the bottom

---

**Topic/Content**:
{content}
"""
        
        try:
            print("🎬 Generating video payload with OpenAI (selecting Pexels videos)...")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 3000,
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
            
            # Try to extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', payload_content, re.DOTALL)
            if json_match:
                payload_content = json_match.group(0)
            
            # Try to parse as JSON to validate
            try:
                payload_json = json.loads(payload_content)
                
                # Validate selected video URLs (only check videos ChatGPT chose)
                payload_json = self.validate_selected_video_urls(payload_json)
                
                return payload_json
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
                print(f"Raw response: {payload_content[:500]}...")
                raise Exception(f"Generated payload is not valid JSON: {e}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def generate_scenes_structure(
        self, 
        content: str, 
        config: PayloadConfig
    ) -> Dict[str, Any]:
        """
        Generate scenes structure with narration only (without media selection).
        Media (videos/images) will be enriched later based on each scene's narration.
        
        Args:
            content: Topic/article content
            config: Payload configuration
            
        Returns:
            Payload JSON with scenes structure (narration only, no media yet)
        """
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
        
        # Build prompt for ChatGPT - generate scenes structure with narration only
        prompt = f"""You are a senior social media marketing expert. Create a script structure for a vertical video designed for platforms like Instagram Reels, TikTok, or YouTube Shorts.

The video must be structured into scenes, totaling **30 to 50 seconds** of runtime.

{scene_count_instruction}
- If the user provides more than 6 scenes, use a maximum of 6 scenes.

**CRITICAL: The LAST scene MUST be a CTA (Call To Action) scene:**
- The final scene should encourage engagement with text like "Follow for more", "Like for more", "Save for later", or similar
- Use compelling CTA narration like: "Follow for more tips", "Like if this helped you", "Save this for later", "Share with someone who needs this", etc.
- Keep CTA narration short (15-25 words) and compelling
- **IMPORTANT**: CTA scene will ALWAYS use an AI-generated image (not Pexels video) for better control over CTA messaging

**IMPORTANT:**
- We will search for Pexels videos based on each scene's narration keywords
- If a relevant video is found for a scene, we'll use it; otherwise, we'll generate an AI image
- Focus on creating compelling narration that clearly describes what should be shown visually

---

### 🎙️ Narration Text (`narration_text`) - **REQUIRED FOR ALL SCENES**

**CRITICAL: EVERY scene MUST include `narration_text`.**
- This is the voiceover for the scene.
- **MANDATORY**: Every scene must have narration text.
- Must be at least 20 words.
- Use only standard English letters, numbers, and punctuation (.,!?).
- No emojis, special characters, currency symbols, or accented letters.
- Style must vary depending on the scene type:
  - **Hook** scenes: bold, curiosity-driven, energetic.
  - **Benefit** scenes: educational, value-driven, persuasive.
  - **Social Proof** scenes: credible, user-focused, testimonial-like.
  - **CTA** scenes: short, directive, compelling, with engagement prompts like "Follow for more", "Like for more", "Save for later"

**IMPORTANT:** Write narration that clearly describes visual content, as we'll use it to search for matching videos:
- For video scenes: Describe the action, environment, or subject matter clearly (e.g., "A person working at a laptop in a modern office", "Hands typing on a keyboard with code on screen")
- For image scenes: Describe the visual concept (e.g., "A futuristic workspace with AI elements", "Abstract design with trending colors")

---

### ✍️ Subtitles
- **MANDATORY**: ALWAYS use `"subtitle": true` for **ALL scenes**
- **There are NO exceptions** — every scene must have subtitles enabled

---

### 📦 Output Format (JSON Only)

Return ONLY the following schema (without video_url or prompt_image - those will be added later based on scene narration):

{{
  "output_filename": "{config.output_filename or 'generated_video.mp4'}",
  "scenes": [
    {{
      "narration_text": "Voiceover text (at least 20 words) that clearly describes visual content.",  // REQUIRED FOR ALL SCENES
      "subtitle": true  // ALWAYS true for ALL scenes - MANDATORY
    }}
  ],
  "post_description": "A social caption with hashtags (1-2 hook lines, a value, CTA, and relevant hashtags)"
}}

**REMINDERS**: 
1. Every scene MUST have `narration_text` - this is not optional.
2. Every scene MUST have `"subtitle": true` - this is mandatory.
3. Write narration that clearly describes visual content (for video/image matching).

---

**Topic/Content**:
{content}
"""
        
        try:
            print("🎬 Generating scenes structure with OpenAI (narration only)...")
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
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
            print("✅ OpenAI scenes structure generated successfully")
            
            # Try to extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', payload_content, re.DOTALL)
            if json_match:
                payload_content = json_match.group(0)
            
            # Try to parse as JSON to validate
            try:
                payload_json = json.loads(payload_content)
                return payload_json
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON parse error: {e}")
                print(f"Raw response: {payload_content[:500]}...")
                raise Exception(f"Generated payload is not valid JSON: {e}")
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def select_best_video_for_scene(
        self,
        narration_text: str,
        candidate_videos: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Use OpenAI to select the best video from candidates based on scene narration.
        
        Args:
            narration_text: Scene narration text
            candidate_videos: List of candidate video dictionaries with url, width, height, etc.
            
        Returns:
            Best video URL if selected, None otherwise
        """
        if not candidate_videos:
            return None
        
        if not self.openai_api_key:
            # Fallback: return first valid video
            return candidate_videos[0].get("url")
        
        # Format videos for ChatGPT (limit to 5 for faster processing)
        video_list = []
        for video in candidate_videos[:5]:  # Limit to 5 candidates for faster AI selection
            video_list.append({
                "url": video.get("url", ""),
                "width": video.get("width", 0),
                "height": video.get("height", 0),
            })
        
        prompt = f"""You are a video content expert. Select the best Pexels video that matches the scene's narration.

**Scene Narration:**
"{narration_text}"

**Available Pexels Videos:**
{json.dumps(video_list, indent=2)}

**Task:**
1. Analyze the scene narration to understand what visual content is needed
2. Select the ONE video URL that best matches the narration's intent, mood, and visual content
3. Consider: action, environment, mood, subject matter, and overall visual theme

**Response Format:**
Return ONLY the video URL that best matches the narration. No explanation needed.
Example: https://videos.pexels.com/video-files/123456/example_2160_3840_24fps.mp4

If none of the videos match well, respond with "NONE"."""
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3  # Lower temperature for more consistent selection
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    selected_url = data['choices'][0]['message']['content'].strip()
                    # Clean up response (remove quotes, etc.)
                    selected_url = selected_url.strip('"\'').strip()
                    
                    if selected_url.upper() == "NONE":
                        return None
                    
                    # Verify the selected URL is in our candidates
                    for video in candidate_videos:
                        if video.get("url") == selected_url:
                            return selected_url
                    
                    # If exact match not found, try to find similar URL
                    for video in candidate_videos:
                        if selected_url in video.get("url", ""):
                            return video.get("url")
            
            # Fallback: return first candidate
            return candidate_videos[0].get("url")
            
        except Exception as e:
            print(f"    ⚠️  Video selection via OpenAI failed: {e}, using first valid video")
            # Fallback: return first candidate
            return candidate_videos[0].get("url") if candidate_videos else None
    
    def generate_image_prompt_for_scene(
        self,
        narration_text: str
    ) -> str:
        """
        Use OpenAI to generate a detailed, specific image prompt based on scene narration.
        
        Args:
            narration_text: Scene narration text
            
        Returns:
            Detailed image prompt
        """
        if not self.openai_api_key:
            # Fallback: basic prompt
            return (
                f"Create an Instagram Reels-style image that features dynamic visual content related to: "
                f"{narration_text[:150]}. Vertical 9:16 format, vibrant colors, engaging composition, "
                f"modern and eye-catching style."
            )
        
        prompt = f"""You are a visual content expert. Create a detailed, specific image prompt for an AI image generator based on the scene narration.

**Scene Narration:**
"{narration_text}"

**Task:**
Create a detailed, vivid image prompt that visualizes the content described in the narration. The prompt should be:
- Very specific and descriptive
- Include visual elements, mood, lighting, composition
- Appropriate for Instagram Reels/TikTok (vertical 9:16 format)
- Engaging and eye-catching
- Begin with: "Create an Instagram Reels-style image that features..."

**Requirements:**
- Start with: "Create an Instagram Reels-style image that features..."
- Describe: what's in the image, environment, mood, lighting, camera perspective
- Include: people/objects/subjects mentioned in narration
- Format: Vertical 9:16 aspect ratio
- Style: Modern, vibrant, engaging, social media optimized

**Response Format:**
Return ONLY the image prompt text. No explanation or extra text."""
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 200,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    image_prompt = data['choices'][0]['message']['content'].strip()
                    # Clean up response (remove quotes, etc.)
                    image_prompt = image_prompt.strip('"\'').strip()
                    return image_prompt
            
            # Fallback
            return (
                f"Create an Instagram Reels-style image that features dynamic visual content related to: "
                f"{narration_text[:150]}. Vertical 9:16 format, vibrant colors, engaging composition, "
                f"modern and eye-catching style."
            )
            
        except Exception as e:
            print(f"    ⚠️  Image prompt generation via OpenAI failed: {e}, using basic prompt")
            # Fallback
            return (
                f"Create an Instagram Reels-style image that features dynamic visual content related to: "
                f"{narration_text[:150]}. Vertical 9:16 format, vibrant colors, engaging composition, "
                f"modern and eye-catching style."
            )
    
    def check_video_relevance(
        self,
        narration_text: str,
        video_url: str
    ) -> bool:
        """
        Use AI to check if a video is relevant to the scene narration.
        Uses lenient matching - only rejects clearly irrelevant videos.
        
        Args:
            narration_text: Scene narration text
            video_url: Video URL to check
            
        Returns:
            True if video is relevant, False otherwise
        """
        if not self.openai_api_key:
            # Fallback: assume video is relevant if we got this far
            return True
        
        try:
            prompt = f"""You are a video content expert. Determine if a Pexels video is relevant to the scene narration.

**Scene Narration:**
"{narration_text}"

**Video URL:**
{video_url}

**Task:**
Analyze if the video content matches the scene narration's intent, mood, and visual content.
- Consider: action, environment, subject matter, mood, theme
- Be LENIENT: Accept videos that are even loosely related
- Only reject if the video is CLEARLY unrelated or completely off-topic
- Example: If narration is about "crypto trading", accept videos about: trading, finance, technology, business, computers, etc.
- Only reject if video is about completely unrelated topics (e.g., nature, animals when talking about business)

**Response Format:**
Return ONLY "YES" if the video is relevant (even loosely), or "NO" if it's clearly unrelated.
Example: YES or NO"""
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 10,
                    "temperature": 0.3
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    result = data['choices'][0]['message']['content'].strip().upper()
                    # Check if result contains "YES" (more lenient)
                    return "YES" in result.upper()
            
            # Fallback: assume relevant
            return True
            
        except Exception as e:
            print(f"    ⚠️  Video relevance check failed: {e}, assuming relevant")
            return True  # Fallback: assume relevant
    
    def enrich_scenes_with_media(
        self, 
        payload: Dict[str, Any], 
        config: PayloadConfig,
        original_content: str = ""
    ) -> Dict[str, Any]:
        """
        Enrich each scene with media (video or image) based on scene's narration.
        For each scene:
        1. CTA scenes (last scene) ALWAYS use image
        2. Extract keywords from narration (max 2 keywords)
        3. Search Pexels for videos matching keywords
        4. Collect candidate videos (limit to 5 for AI selection)
        5. Use OpenAI to select best video and check relevance
        6. Track used videos to avoid duplicates across scenes
        7. Mix videos and images (not all videos)
        8. If video not relevant or no video found → use image prompt
        
        Args:
            payload: Payload with scenes structure (narration only)
            config: Payload configuration
            original_content: Original content/topic to check for user instructions
            
        Returns:
            Payload with enriched scenes (video_url or prompt_image added)
        """
        if 'scenes' not in payload:
            return payload
        
        # Check if user wants all videos
        force_all_videos = False
        if original_content:
            content_lower = original_content.lower()
            if any(phrase in content_lower for phrase in [
                "use video for all scenes", "all scenes videos", "only videos",
                "use videos only", "all video scenes", "pexels videos only"
            ]):
                force_all_videos = True
                print("🎬 User requested: Use videos for all scenes")
        
        print("\n🎨 Enriching scenes with media (video or image)...")
        enriched_scenes = []
        used_video_urls = set()  # Track used videos to avoid duplicates
        total_scenes = len(payload['scenes'])
        video_count = 0  # Track how many videos we've used
        
        for idx, scene in enumerate(payload['scenes']):
            narration_text = scene.get('narration_text', '')
            if not narration_text:
                print(f"  ⚠️  Scene {idx + 1} has no narration_text, skipping media enrichment")
                enriched_scenes.append(scene)
                continue
            
            is_last_scene = (idx == total_scenes - 1)  # CTA scene (always image)
            
            print(f"\n  📹 Scene {idx + 1}: '{narration_text[:60]}...'")
            
            # CTA scene (last scene) ALWAYS uses image
            if is_last_scene:
                print("    🎯 CTA scene detected - always using image prompt")
                image_prompt = self.generate_image_prompt_for_scene(narration_text)
                enriched_scene = scene.copy()
                enriched_scene["type"] = "image"
                enriched_scene["prompt_image"] = image_prompt
                enriched_scenes.append(enriched_scene)
                continue
            
            # Extract keywords from this scene's narration (limit to 2 keywords)
            try:
                keywords = self.extract_keywords(narration_text, max_keywords=2)
                print(f"    🔑 Keywords for scene {idx + 1}: {', '.join(keywords)}")
            except Exception as e:
                print(f"    ⚠️  Keyword extraction failed for scene {idx + 1}: {e}")
                keywords = []
            
            # Collect candidate videos (limit search to get fewer, better results)
            candidate_videos = []
            video_found = False
            
            # Try to find video (unless we need to mix and already have too many videos)
            # Mix strategy: Prefer videos but ensure variety (not all videos)
            should_try_video = True
            if not force_all_videos and total_scenes > 2:
                # Mix videos and images: try to use videos for at least 1/3 of scenes (but not all)
                # For 5 scenes (excluding CTA): can use 2-3 videos max
                non_cta_scenes = total_scenes - 1  # Exclude CTA scene
                max_videos = max(1, (non_cta_scenes * 2) // 3)  # Use up to 2/3 videos for variety
                if video_count >= max_videos:
                    should_try_video = False
                    print(f"    🎨 Mixing scenes: Already used {video_count}/{max_videos} videos, using image for variety")
            
            if should_try_video and keywords:
                print(f"    🔍 Searching Pexels with {len(keywords)} keywords...")
                
                # Search with each keyword and collect valid videos (limit per keyword)
                for keyword in keywords:
                    try:
                        videos = self.pexels.search_videos(
                            query=keyword,
                            per_page=5,  # Reduced from 10 to 5 for faster searches
                            orientation="portrait"
                        )
                        
                        # Collect videos (skip validation for speed - will validate only selected ones)
                        for video in videos:
                            video_url = video.get("url")
                            if video_url:
                                # Skip if already used in another scene
                                if video_url not in used_video_urls:
                                    # Avoid duplicates in candidate list
                                    if not any(v.get("url") == video_url for v in candidate_videos):
                                        candidate_videos.append(video)
                        
                    except Exception as e:
                        print(f"    ⚠️  Error searching Pexels for '{keyword}': {e}")
                        continue
                
                # Limit candidate list to 5 videos for faster AI selection
                candidate_videos = candidate_videos[:5]
                
                if candidate_videos:
                    print(f"    ✅ Found {len(candidate_videos)} candidate videos...")
                    
                    # Use OpenAI to select best video from small candidate list
                    print("    🤖 Selecting best video using AI based on narration...")
                    selected_video_url = self.select_best_video_for_scene(narration_text, candidate_videos)
                    
                    if selected_video_url:
                        # Validate only the selected video
                        if self.validate_pexels_video_url(selected_video_url):
                            # Check if video is relevant to the scene (lenient check)
                            print("    🔍 Checking if video is relevant to scene narration...")
                            is_relevant = self.check_video_relevance(narration_text, selected_video_url)
                            
                            if is_relevant:
                                print(f"    ✅ Selected relevant video for scene {idx + 1}")
                                
                                # Mark video as used to avoid duplicates
                                used_video_urls.add(selected_video_url)
                                
                                # Enrich scene with video
                                enriched_scene = scene.copy()
                                enriched_scene["type"] = "video"
                                enriched_scene["video_url"] = selected_video_url
                                enriched_scenes.append(enriched_scene)
                                video_found = True
                                video_count += 1
                            else:
                                print("    ❌ Video not relevant to scene, will use image instead")
                                # Try to find another video from remaining candidates
                                # Remove the rejected video and try next best
                                remaining_candidates = [v for v in candidate_videos if v.get("url") != selected_video_url]
                                if remaining_candidates:
                                    print("    🔄 Trying next best video from candidates...")
                                    selected_video_url = self.select_best_video_for_scene(narration_text, remaining_candidates)
                                    if selected_video_url and self.validate_pexels_video_url(selected_video_url):
                                        is_relevant_retry = self.check_video_relevance(narration_text, selected_video_url)
                                        if is_relevant_retry:
                                            print(f"    ✅ Selected alternative relevant video for scene {idx + 1}")
                                            used_video_urls.add(selected_video_url)
                                            enriched_scene = scene.copy()
                                            enriched_scene["type"] = "video"
                                            enriched_scene["video_url"] = selected_video_url
                                            enriched_scenes.append(enriched_scene)
                                            video_found = True
                                            video_count += 1
                        else:
                            print("    ❌ Selected video failed validation, will use image instead")
            
            # If no valid/relevant video found, use image prompt instead
            if not video_found:
                print(f"    🖼️  Using image prompt for scene {idx + 1}...")
                
                # Generate detailed image prompt using OpenAI
                image_prompt = self.generate_image_prompt_for_scene(narration_text)
                
                enriched_scene = scene.copy()
                enriched_scene["type"] = "image"
                enriched_scene["prompt_image"] = image_prompt
                enriched_scenes.append(enriched_scene)
        
        payload['scenes'] = enriched_scenes
        print(f"\n✅ Enriched {len(enriched_scenes)} scenes with media:")
        print(f"   📹 Videos: {video_count}")
        print(f"   🖼️  Images: {len(enriched_scenes) - video_count}")
        return payload
    
    def validate_selected_video_urls(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate video URLs that ChatGPT selected in the payload.
        Converts invalid video scenes to image scenes.
        
        Args:
            payload: Generated payload from ChatGPT
            
        Returns:
            Payload with validated/replaced video scenes
        """
        if 'scenes' not in payload:
            return payload
        
        print("\n🔍 Validating selected video URLs (only checking videos ChatGPT chose)...")
        validated_scenes = []
        invalid_count = 0
        
        for idx, scene in enumerate(payload['scenes']):
            # Only validate scenes with video_url
            if scene.get('type') == 'video' and scene.get('video_url'):
                video_url = scene['video_url']
                print(f"  📹 Validating scene {idx + 1} video URL...")
                
                if self.validate_pexels_video_url(video_url):
                    print(f"    ✅ Valid: Scene {idx + 1} video is accessible")
                    validated_scenes.append(scene)
                else:
                    print(f"    ❌ Invalid: Scene {idx + 1} video URL is not accessible (403/404)")
                    print(f"    🔄 Converting scene {idx + 1} from video to image scene...")
                    invalid_count += 1
                    
                    # Convert invalid video scene to image scene
                    # Keep narration but generate image prompt based on narration
                    converted_scene = {
                        "type": "image",
                        "narration_text": scene.get("narration_text", "Visual content for this scene"),
                        "prompt_image": f"Create an Instagram Reels-style image that features dynamic visual content related to: {scene.get('narration_text', 'visual content')[:100]}. Vertical 9:16 format, vibrant colors, engaging composition.",
                        "subtitle": scene.get("subtitle", True)
                    }
                    
                    validated_scenes.append(converted_scene)
                    print(f"    ✅ Converted scene {idx + 1} to image scene")
            else:
                # Keep non-video scenes as-is
                validated_scenes.append(scene)
        
        if invalid_count > 0:
            print(f"\n⚠️  Converted {invalid_count} invalid video scene(s) to image scenes")
        else:
            print("\n✅ All selected video URLs are valid")
        
        payload['scenes'] = validated_scenes
        return payload
    
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
                    
                # Remove duration if present (duration will be set by narration in worker)
                if 'duration' in scene:
                    del scene['duration']
        
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
            print("✅ Added global subtitle config")
        
        return enhanced_payload
    
    def generate_payload(self, config: PayloadConfig) -> Dict[str, Any]:
        """Main method to generate payload from configuration"""
        print("🚀 Starting payload generation with Pexels integration...")
        print(f"📝 Topic: {config.topic[:100]}{'...' if len(config.topic) > 100 else ''}")
        
        try:
            # Step 1: Get content (with or without Perplexity)
            has_url = config.url or self.contains_url(config.topic)
            
            if has_url:
                url_content = config.url or config.topic
                print(f"🔗 URL detected: {url_content}")
                content = self.get_perplexity_summary(url_content)
            else:
                print("📄 Processing as plain text topic")
                content = config.topic
            
            # Step 2: Generate scenes structure with narration (without media)
            print("\n🤖 Generating scenes structure with ChatGPT (narration only)...")
            payload_json = self.generate_scenes_structure(content, config)
            
            # Step 3: Enrich each scene with media (video or image) based on scene's narration
            print("\n🎨 Enriching scenes with media (searching Pexels per scene)...")
            payload_json = self.enrich_scenes_with_media(payload_json, config, original_content=content)
            
            # Step 4: Enhance payload with optional parameters
            enhanced_payload = self.enhance_payload(payload_json, config)
            
            print("\n🎉 Payload generation completed successfully!")
            return enhanced_payload
            
        except Exception as e:
            print(f"❌ Error generating payload: {e}")
            raise

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Generate ProtoReel video payloads using Pexels videos mixed with AI images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from topic
  python generate_protoreel_payload_with_pexels.py --topic "AI productivity tools"
  
  # Generate from URL
  python generate_protoreel_payload_with_pexels.py --url "https://example.com/article"
  
  # Generate with logo and music
  python generate_protoreel_payload_with_pexels.py --topic "Trading tips" --logo "https://example.com/logo.png" --music "https://example.com/music.mp3"
  
  # Generate with custom parameters
  python generate_protoreel_payload_with_pexels.py --topic "Tech news" --scenes 4 --output "tech_news.mp4"
  
Environment Variables Required:
  - PEXELS_API_KEY: Your Pexels API key (get from https://www.pexels.com/api/)
  - OPENAI_API_KEY: Your OpenAI API key
  - PERPLEXITY_API_KEY: (Optional) For URL analysis
        """
    )
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--topic", help="Topic or article text for video generation")
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
    parser.add_argument("--max-pexels", type=int, default=20, help="Max Pexels results per keyword (default: 20)")
    parser.add_argument("--pexels-per-scene", type=int, default=5, help="Pexels videos shown to ChatGPT per scene (default: 5)")
    parser.add_argument("--save", help="Save payload to file (JSON)")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if not os.environ.get("PEXELS_API_KEY"):
        print("❌ Error: PEXELS_API_KEY environment variable not set")
        print("   Get your API key from: https://www.pexels.com/api/")
        sys.exit(1)
    
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    
    # Create configuration
    config = PayloadConfig(
        topic=args.topic or args.url,
        url=args.url,
        logo_url=args.logo,
        audio_prompt_url=args.audio_prompt,
        background_music=args.music,
        background_music_volume=args.music_volume,
        output_filename=args.output,
        scene_count=args.scenes,
        image_provider=args.provider,
        subtitle_enabled=not args.no_subtitles,
        max_pexels_results=args.max_pexels,
        pexels_videos_per_scene=args.pexels_per_scene
    )
    
    # Generate payload
    try:
        generator = PayloadGeneratorWithPexels()
        payload = generator.generate_payload(config)
        
        # Output result
        if args.save:
            with open(args.save, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2 if args.pretty else None, ensure_ascii=False)
            print(f"\n💾 Payload saved to: {args.save}")
        else:
            if args.pretty:
                print("\n" + "="*50)
                print("GENERATED PAYLOAD:")
                print("="*50 + "\n")
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(json.dumps(payload, ensure_ascii=False))
                
    except Exception as e:
        print(f"❌ Failed to generate payload: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
