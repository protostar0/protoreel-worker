#!/usr/bin/env python3
"""
ProtoReel Payload Generator with Video Integration

Generates video payloads using Pixabay (default) and Pexels videos mixed with AI-generated images.
Pixabay is the primary/default video source, with Pexels as an optional secondary provider.
Supports multiple video sources to provide better variety and coverage.

Workflow:
1. User provides topic/article
2. Extract keywords from topic
3. Search Pixabay (default) and Pexels for videos using keywords
4. Build large video pool from available sources (Pixabay prioritized)
5. Randomly select videos for each scene from the pool
6. Generate final payload with narration, subtitles, etc.

Usage:
    python tests/generate_protoreel_payload_with_pexels.py --topic "AI productivity tools"
    python tests/generate_protoreel_payload_with_pexels.py --url "https://example.com/article"
"""

import os
import sys
import json
import re
import random
import logging
import requests
import argparse
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass
from enum import Enum

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoSource(Enum):
    """Video source providers"""
    PEXELS = "pexels"
    PIXABAY = "pixabay"


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
    image_provider: str = "gemini"
    subtitle_enabled: bool = True
    global_subtitle_config: Optional[Dict[str, Any]] = None
    max_videos_per_keyword: int = 80
    max_pages_per_keyword: int = 3


class PexelsVideoSearch:
    """Handles Pexels API video searches"""
    
    BASE_URL = "https://api.pexels.com/videos"
    MAX_PER_PAGE = 80
    TIMEOUT = 30
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("PEXELS_API_KEY is required")
        self.api_key = api_key
        self.base_url = self.BASE_URL
        
    def search_videos(
        self, 
        query: str, 
        per_page: int = 15, 
        page: int = 1, 
        orientation: str = "portrait"
    ) -> List[Dict[str, Any]]:
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
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": min(per_page, self.MAX_PER_PAGE),
            "page": page,
            "orientation": orientation
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/search",
                headers=headers,
                params=params,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            for video in data.get("videos", []):
                video_files = video.get("video_files", [])
                if not video_files:
                    continue
                
                # Sort by quality (width/height) descending
                video_files.sort(
                    key=lambda x: x.get("width", 0) * x.get("height", 0), 
                    reverse=True
                )
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
                    "source": VideoSource.PEXELS.value,
                    "query": query
                })
            
            return videos
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pexels API request failed: {e}")
            raise RuntimeError(f"Pexels API request failed: {e}") from e
        except Exception as e:
            logger.error(f"Pexels API error: {e}")
            raise RuntimeError(f"Pexels API error: {e}") from e


class PixabayVideoSearch:
    """Handles Pixabay API video searches"""
    
    BASE_URL = "https://pixabay.com/api/videos"
    MAX_PER_PAGE = 200
    TIMEOUT = 30
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("PIXABAY_API_KEY is required")
        self.api_key = api_key
        self.base_url = self.BASE_URL
        
    def search_videos(
        self, 
        query: str, 
        per_page: int = 20, 
        page: int = 1,
        video_type: str = "all",
        orientation: str = "vertical"
    ) -> List[Dict[str, Any]]:
        """
        Search for videos on Pixabay
        
        Args:
            query: Search query/keyword
            per_page: Number of results per page (max 200)
            page: Page number
            video_type: all, film, animation
            orientation: all, horizontal, vertical
            
        Returns:
            List of video dictionaries with metadata
        """
        params = {
            "key": self.api_key,
            "q": query,
            "per_page": min(per_page, self.MAX_PER_PAGE),
            "page": page,
            "video_type": video_type,
            "orientation": orientation,
            "safesearch": "true"
        }
        
        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            for hit in data.get("hits", []):
                # Get best quality video
                videos_data = hit.get("videos", {})
                if not videos_data:
                    continue
                
                # Prefer high quality, then medium, then small
                best_video = None
                for quality in ["large", "medium", "small"]:
                    if quality in videos_data:
                        best_video = videos_data[quality]
                        break
                
                if not best_video:
                    continue
                
                videos.append({
                    "id": hit.get("id"),
                    "url": best_video.get("url"),
                    "width": best_video.get("width"),
                    "height": best_video.get("height"),
                    "duration": hit.get("duration"),
                    "thumbnail": hit.get("picture_id"),
                    "tags": hit.get("tags"),
                    "user": hit.get("user"),
                    "user_id": hit.get("user_id"),
                    "source": VideoSource.PIXABAY.value,
                    "query": query
                })
            
            return videos
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Pixabay API request failed: {e}")
            raise RuntimeError(f"Pixabay API request failed: {e}") from e
        except Exception as e:
            logger.error(f"Pixabay API error: {e}")
            raise RuntimeError(f"Pixabay API error: {e}") from e


class PayloadGeneratorWithPexels:
    """Main class for generating ProtoReel video payloads with video integration"""
    
    def __init__(self):
        """Initialize the payload generator with API keys"""
        self.perplexity_api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        # Initialize video search providers (Pixabay is default/primary)
        self.pexels = None
        self.pixabay = None
        
        # Initialize Pixabay first (default/primary provider)
        pixabay_api_key = os.environ.get("PIXABAY_API_KEY")
        if pixabay_api_key:
            try:
                self.pixabay = PixabayVideoSearch(pixabay_api_key)
                logger.info("Pixabay API initialized (default provider)")
            except Exception as e:
                logger.warning(f"Failed to initialize Pixabay: {e}")
        
        # Initialize Pexels as fallback/secondary provider
        pexels_api_key = os.environ.get("PEXELS_API_KEY")
        if pexels_api_key:
            try:
                self.pexels = PexelsVideoSearch(pexels_api_key)
                logger.info("Pexels API initialized (secondary provider)")
            except Exception as e:
                logger.warning(f"Failed to initialize Pexels: {e}")
        
        if not self.pexels and not self.pixabay:
            raise ValueError("At least one of PIXABAY_API_KEY (default) or PEXELS_API_KEY must be set")
    
    def contains_url(self, text: str) -> bool:
        """Check if text contains a URL"""
        url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
        return bool(re.search(url_pattern, text))
    
    def clean_subtitle_text(self, text: str) -> str:
        """Clean subtitle text by removing special characters"""
        cleaned = re.sub(r'[^\w\s.,!?;:\-\'"]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()
    
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
        
        prompt = f"""Extract {max_keywords} relevant keywords from the following text that would be useful for searching stock videos.

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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.5
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            keywords_text = data['choices'][0]['message']['content'].strip()
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            
            logger.info(f"Extracted keywords: {', '.join(keywords)}")
            return keywords[:max_keywords]
            
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}. Using fallback method.")
            # Fallback: simple keyword extraction
            words = re.findall(r'\b[a-z]{4,}\b', text.lower())
            stop_words = {
                'this', 'that', 'with', 'from', 'have', 'been', 'will', 
                'your', 'they', 'their', 'there', 'what', 'when', 'where'
            }
            keywords = [w for w in words if w not in stop_words][:max_keywords]
            return list(set(keywords))
    
    def get_perplexity_summary(self, prompt_text: str) -> str:
        """Get summary from Perplexity API for URL content"""
        if not self.perplexity_api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable not set")
        
        try:
            logger.info("Analyzing content with Perplexity API...")
            
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [{
                        "role": "user",
                        "content": f"You are an AI and automation tools expert. Analyze this prompt/topic: {prompt_text}. Provide a comprehensive summary that makes it easy to create social media posts from the output. Include relevant tool URLs and key insights."
                    }]
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if 'choices' not in data or len(data['choices']) == 0:
                raise ValueError("Invalid Perplexity response format")
            
            summary_content = data['choices'][0]['message']['content']
            logger.info("Perplexity analysis completed")
            return summary_content
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Perplexity API request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError("Invalid JSON response from Perplexity") from e
        except Exception as e:
            raise RuntimeError(f"Perplexity API error: {e}") from e
    
    def _fetch_videos_from_provider(
        self,
        provider: Any,
        keyword: str,
        max_pages: int = 3,
        per_page: int = 80
    ) -> List[Dict[str, Any]]:
        """
        Fetch videos from a provider for a keyword across multiple pages.
        Pages are fetched in random order to ensure different video selections across runs.
        """
        videos = []
        
        # Create page list and shuffle for randomness
        # This ensures different video fetching order even with same keywords
        pages = list(range(1, max_pages + 1))
        random.shuffle(pages)
        
        for page in pages:
            try:
                if provider == self.pexels:
                    page_videos = provider.search_videos(
                        query=keyword,
                        per_page=per_page,
                        page=page,
                        orientation="portrait"
                    )
                elif provider == self.pixabay:
                    page_videos = provider.search_videos(
                        query=keyword,
                        per_page=per_page,
                        page=page,
                        orientation="vertical"
                    )
                else:
                    continue
                
                videos.extend(page_videos)
                
                # If we got fewer results than per_page, we've reached the end
                if len(page_videos) < per_page:
                    break
                    
            except Exception as e:
                logger.warning(f"Error fetching page {page} for '{keyword}': {e}")
                continue
        
        return videos
    
    def build_video_pool(self, topic: str, config: PayloadConfig) -> List[Dict[str, Any]]:
        """
        Build a large pool of videos from all available providers
        
        Args:
            topic: Main topic/content
            config: Payload configuration
            
        Returns:
            List of video dictionaries from all providers
        """
        logger.info(f"Building video pool from topic: '{topic[:100]}...'")
        video_pool = []
        seen_urls: Set[str] = set()
        
        # Extract topic keywords
        try:
            topic_keywords = self.extract_keywords(topic, max_keywords=3)
            logger.info(f"Topic keywords: {', '.join(topic_keywords)}")
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}, using topic as-is")
            topic_keywords = [topic[:50]]
        
        # Fetch videos from all providers (Pixabay first as default, then Pexels as fallback)
        providers = []
        if self.pixabay:
            providers.append(self.pixabay)  # Default provider first
        if self.pexels:
            providers.append(self.pexels)  # Secondary provider
        
        # Shuffle keyword order for additional randomness across runs
        # This ensures different video fetching order even with same keywords
        shuffled_keywords = topic_keywords.copy()
        random.shuffle(shuffled_keywords)
        
        # Shuffle provider order for additional randomness
        shuffled_providers = providers.copy()
        random.shuffle(shuffled_providers)
        
        for keyword in shuffled_keywords:
            for provider in shuffled_providers:
                try:
                    logger.info(f"Searching {provider.__class__.__name__} for '{keyword}'...")
                    videos = self._fetch_videos_from_provider(
                        provider,
                        keyword,
                        max_pages=config.max_pages_per_keyword,
                        per_page=config.max_videos_per_keyword
                    )
                    
                    for video in videos:
                        video_url = video.get("url")
                        if video_url and video_url not in seen_urls:
                            seen_urls.add(video_url)
                            video_pool.append(video)
                            
                except Exception as e:
                    logger.warning(f"Error searching {provider.__class__.__name__} for '{keyword}': {e}")
                    continue
        
        # Shuffle pool for randomness
        random.shuffle(video_pool)
        logger.info(f"Collected {len(video_pool)} unique videos in pool")
        
        return video_pool
    
    def validate_video_url(self, video_url: str) -> bool:
        """
        Validate that a video URL is accessible
        
        Args:
            video_url: Video URL to validate
            
        Returns:
            True if URL is accessible, False otherwise
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Add provider-specific headers
            if 'pexels.com' in video_url.lower():
                headers['Referer'] = 'https://www.pexels.com/'
                pexels_api_key = os.environ.get("PEXELS_API_KEY")
                if pexels_api_key:
                    headers['Authorization'] = pexels_api_key
            
            # Use HEAD request for faster validation
            response = requests.head(video_url, headers=headers, timeout=10, allow_redirects=True)
            
            if response.status_code in [200, 302]:
                return True
            elif response.status_code == 403:
                # Try with GET request (sometimes HEAD is blocked but GET works)
                response_get = requests.get(
                    video_url, 
                    headers=headers, 
                    stream=True, 
                    timeout=10
                )
                return response_get.status_code == 200
            else:
                return False
                
        except Exception as e:
            logger.warning(f"Video validation failed: {e}")
            return False
    
    def generate_image_prompt_for_scene(self, narration_text: str) -> str:
        """
        Use OpenAI to generate a detailed image prompt based on scene narration
        
        Args:
            narration_text: Scene narration text
            
        Returns:
            Detailed image prompt
        """
        if not self.openai_api_key:
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
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.7
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                image_prompt = data['choices'][0]['message']['content'].strip()
                # Clean up the prompt
                image_prompt = image_prompt.strip('"').strip("'")
                return image_prompt
            
            # Fallback
            return (
                f"Create an Instagram Reels-style image that features dynamic visual content related to: "
                f"{narration_text[:150]}. Vertical 9:16 format, vibrant colors, engaging composition, "
                f"modern and eye-catching style."
            )
            
        except Exception as e:
            logger.warning(f"Image prompt generation failed: {e}")
            return (
                f"Create an Instagram Reels-style image that features dynamic visual content related to: "
                f"{narration_text[:150]}. Vertical 9:16 format, vibrant colors, engaging composition, "
                f"modern and eye-catching style."
            )
    
    def enrich_scenes_with_media(
        self,
        payload: Dict[str, Any],
        config: PayloadConfig,
        original_content: str = ""
    ) -> Dict[str, Any]:
        """
        Enrich each scene with media (video or image) based on topic.
        
        Simple approach:
        1. Fetch a large pool of videos from the main topic
        2. For each scene, randomly select from the pool (avoiding duplicates when possible)
        3. CTA scenes (last scene) ALWAYS use image
        4. If pool is exhausted, use image prompt
        
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
                logger.info("User requested: Use videos for all scenes")
        
        logger.info("Enriching scenes with media (video or image)...")
        
        # Step 1: Build large video pool from topic
        video_pool = self.build_video_pool(original_content or config.topic, config)
        
        enriched_scenes = []
        used_video_urls: Set[str] = set()
        total_scenes = len(payload['scenes'])
        video_count = 0
        
        for idx, scene in enumerate(payload['scenes']):
            narration_text = scene.get('narration_text', '')
            if not narration_text:
                logger.warning(f"Scene {idx + 1} has no narration_text, skipping media enrichment")
                enriched_scenes.append(scene)
                continue
            
            is_last_scene = (idx == total_scenes - 1)
            logger.info(f"Scene {idx + 1}: '{narration_text[:60]}...'")
            
            # CTA scene (last scene) ALWAYS uses image
            if is_last_scene:
                logger.info("CTA scene detected - always using image prompt")
                image_prompt = self.generate_image_prompt_for_scene(narration_text)
                enriched_scene = scene.copy()
                enriched_scene["type"] = "image"
                enriched_scene["prompt_image"] = image_prompt
                enriched_scenes.append(enriched_scene)
                continue
            
            # Step 2: Randomly select from video pool for this scene
            video_found = False
            
            # Check if we should try video (mixing strategy)
            should_try_video = True
            if not force_all_videos and total_scenes > 2:
                non_cta_scenes = total_scenes - 1
                max_videos = max(1, (non_cta_scenes * 2) // 3)
                if video_count >= max_videos:
                    should_try_video = False
                    logger.info(f"Mixing scenes: Already used {video_count}/{max_videos} videos, using image for variety")
            
            if should_try_video and video_pool:
                # Filter out already used videos (prefer unique, but allow repeats if pool is small)
                available_videos = [v for v in video_pool if v.get("url") not in used_video_urls]
                
                # Reshuffle available videos for extra randomness before selection
                if available_videos:
                    # Shuffle multiple times for better randomness across runs
                    for _ in range(2):
                        random.shuffle(available_videos)
                    # Use random.choice which is truly random each time
                    # This ensures different selections across runs with same keywords
                    selected_video = random.choice(available_videos)
                    selected_video_url = selected_video.get("url")
                else:
                    # Pool exhausted or all used - randomly select from pool (allow repeat)
                    # Reshuffle the entire pool for randomness before selecting
                    temp_pool = video_pool.copy()
                    random.shuffle(temp_pool)
                    selected_video = random.choice(temp_pool)
                    selected_video_url = selected_video.get("url")
                    logger.warning(f"All videos used, selecting random video (may repeat): {selected_video_url[:50]}...")
                
                if selected_video_url:
                    # Validate the selected video
                    logger.info("Validating selected video...")
                    if self.validate_video_url(selected_video_url):
                        logger.info(f"Selected and validated video for scene {idx + 1}")
                        
                        # Mark video as used
                        used_video_urls.add(selected_video_url)
                        
                        # Enrich scene with video
                        enriched_scene = scene.copy()
                        enriched_scene["type"] = "video"
                        enriched_scene["video_url"] = selected_video_url
                        enriched_scenes.append(enriched_scene)
                        video_found = True
                        video_count += 1
                    else:
                        logger.warning("Selected video failed validation, will use image instead")
            
            # If no valid video found, use image prompt instead
            if not video_found:
                logger.info(f"Using image prompt for scene {idx + 1}...")
                image_prompt = self.generate_image_prompt_for_scene(narration_text)
                
                enriched_scene = scene.copy()
                enriched_scene["type"] = "image"
                enriched_scene["prompt_image"] = image_prompt
                enriched_scenes.append(enriched_scene)
        
        payload['scenes'] = enriched_scenes
        logger.info(f"Enriched {len(enriched_scenes)} scenes with media:")
        logger.info(f"  Videos: {video_count}, Images: {len(enriched_scenes) - video_count}")
        
        return payload
    
    def generate_scenes_structure(
        self,
        content: str,
        config: PayloadConfig
    ) -> Dict[str, Any]:
        """
        Generate scenes structure with narration only (without media selection).
        
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
            logger.warning(f"Content truncated to {max_content_length} characters")
        
        # Build scene count instruction
        scene_count_instruction = (
            f"- Create exactly {config.scene_count} scenes."
            if config.scene_count
            else "- Create 3 to 5 scenes (default)."
        )
        
        prompt = f"""You are a senior social media marketing expert. Create a script structure for a vertical video designed for platforms like Instagram Reels, TikTok, or YouTube Shorts.

The video must be structured into scenes, totaling **30 to 50 seconds** of runtime.

{scene_count_instruction}
- If the user provides more than 6 scenes, use a maximum of 6 scenes.

**CRITICAL: The LAST scene MUST be a CTA (Call To Action) scene:**
- The final scene should encourage engagement with text like "Follow for more", "Like for more", "Save for later", or similar
- Use compelling CTA narration like: "Follow for more tips", "Like if this helped you", "Save this for later", "Share with someone who needs this", etc.
- Keep CTA narration short (15-25 words) and compelling
- **IMPORTANT**: CTA scene will ALWAYS use an AI-generated image (not video) for better control over CTA messaging

**IMPORTANT:**
- We will search for videos based on the main topic
- Videos will be randomly selected from a pool of relevant videos
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

**IMPORTANT:** Write narration that clearly describes visual content, as we'll use it to match with videos or generate images.

---

### ✍️ Subtitles
- **MANDATORY**: ALWAYS use `"subtitle": true` for **ALL scenes**
- **There are NO exceptions** — every scene must have subtitles enabled

---

### 📦 Output Format (JSON Only)

Return ONLY the following schema (without video_url or prompt_image - those will be added later):

{{
  "output_filename": "{config.output_filename or 'generated_video.mp4'}",
  "scenes": [
    {{
      "narration_text": "Voiceover text (at least 20 words) that clearly describes visual content.",
      "subtitle": true
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
{content}"""
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 2000,
                    "temperature": 0.7
                },
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            if 'choices' not in data or len(data['choices']) == 0:
                raise ValueError("Invalid OpenAI response format")
            
            content_text = data['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content_text, re.DOTALL)
            if json_match:
                content_text = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
                if json_match:
                    content_text = json_match.group(0)
            
            payload_json = json.loads(content_text)
            
            # Clean narration text
            for scene in payload_json.get('scenes', []):
                if 'narration_text' in scene:
                    original_text = scene['narration_text']
                    cleaned_text = self.clean_subtitle_text(original_text)
                    if original_text != cleaned_text:
                        logger.info(f"Cleaned narration text: '{original_text[:50]}...' -> '{cleaned_text[:50]}...'")
                    scene['narration_text'] = cleaned_text
                    
                # Remove duration if present (duration will be set by narration in worker)
                if 'duration' in scene:
                    del scene['duration']
            
            return payload_json
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenAI API request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Generated payload is not valid JSON: {e}") from e
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e
    
    def enhance_payload(self, payload: Dict[str, Any], config: PayloadConfig) -> Dict[str, Any]:
        """Enhance payload with optional parameters"""
        # Add logo if provided
        if config.logo_url:
            payload["logo"] = {
                "url": config.logo_url,
                "position": "bottom-right",
                "opacity": 0.6,
                "size": [200, 200],
                "show_in_all_scenes": True,
                "cta_screen": True
            }
            logger.info(f"Added logo: {config.logo_url}")
        
        # Add audio prompt URL if provided
        if config.audio_prompt_url:
            payload["audio_prompt_url"] = config.audio_prompt_url
            logger.info(f"Added audio prompt: {config.audio_prompt_url}")
        
        # Add background music if provided
        if config.background_music:
            payload["background_music"] = config.background_music
            payload["background_music_volume"] = config.background_music_volume
            logger.info(f"Added background music: {config.background_music}")
        
        # Add global subtitle config if provided
        if config.global_subtitle_config:
            payload["global_subtitle_config"] = config.global_subtitle_config
            logger.info("Added global subtitle config")
        
        return payload
    
    def generate_payload(self, config: PayloadConfig) -> Dict[str, Any]:
        """Main method to generate payload from configuration"""
        logger.info("Starting payload generation with video integration...")
        logger.info(f"Topic: {config.topic[:100]}{'...' if len(config.topic) > 100 else ''}")
        
        try:
            # Step 1: Get content (with or without Perplexity)
            has_url = config.url or self.contains_url(config.topic)
            
            if has_url:
                url_content = config.url or config.topic
                logger.info(f"URL detected: {url_content}")
                content = self.get_perplexity_summary(url_content)
            else:
                logger.info("Processing as plain text topic")
                content = config.topic
            
            # Step 2: Generate scenes structure with narration (without media)
            logger.info("Generating scenes structure with ChatGPT (narration only)...")
            payload_json = self.generate_scenes_structure(content, config)
            
            # Step 3: Enrich each scene with media (video or image) based on topic
            logger.info("Enriching scenes with media (searching video sources per topic)...")
            payload_json = self.enrich_scenes_with_media(payload_json, config, original_content=content)
            
            # Step 4: Enhance payload with optional parameters
            enhanced_payload = self.enhance_payload(payload_json, config)
            
            logger.info("Payload generation completed successfully!")
            return enhanced_payload
            
        except Exception as e:
            logger.error(f"Error generating payload: {e}", exc_info=True)
            raise


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Generate ProtoReel video payloads using Pexels and Pixabay videos mixed with AI images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from topic
  python generate_protoreel_payload_with_pexels.py --topic "AI productivity tools"
  
  # Generate from URL
  python generate_protoreel_payload_with_pexels.py --url "https://example.com/article"
  
  # Generate with logo and music
  python generate_protoreel_payload_with_pexels.py --topic "Trading tips" --logo "https://example.com/logo.png" --music "https://example.com/music.mp3"

Environment Variables Required:
  - PIXABAY_API_KEY: Your Pixabay API key (default/primary provider, get from https://pixabay.com/api/docs/)
  - PEXELS_API_KEY: Your Pexels API key (optional/secondary provider, get from https://www.pexels.com/api/)
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
    parser.add_argument("--audio-prompt", dest="audio_prompt", help="Audio prompt URL for voice cloning")
    parser.add_argument("--music", help="Background music URL")
    parser.add_argument("--music-volume", type=float, default=0.3, help="Background music volume (0.0-1.0)")
    parser.add_argument("--output", help="Output filename for the video")
    parser.add_argument("--scenes", type=int, help="Number of scenes (3-6)")
    parser.add_argument("--provider", choices=["gemini", "openai", "freepik"], default="gemini", help="Image generation provider")
    parser.add_argument("--no-subtitles", action="store_true", help="Disable subtitles")
    parser.add_argument("--max-videos", type=int, default=80, help="Max videos per keyword (default: 80)")
    parser.add_argument("--max-pages", type=int, default=3, help="Max pages per keyword (default: 3)")
    parser.add_argument("--save", help="Save payload to file (JSON)")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    # Check for required environment variables (Pixabay is default/primary)
    if not os.environ.get("PIXABAY_API_KEY") and not os.environ.get("PEXELS_API_KEY"):
        print("❌ Error: At least one of PIXABAY_API_KEY (default) or PEXELS_API_KEY environment variable must be set")
        print("   Get your API keys from:")
        print("   - Pixabay (default): https://pixabay.com/api/docs/")
        print("   - Pexels (optional): https://www.pexels.com/api/")
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
        max_videos_per_keyword=args.max_videos,
        max_pages_per_keyword=args.max_pages
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
