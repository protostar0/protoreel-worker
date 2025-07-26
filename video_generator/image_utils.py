"""
Image utilities for ProtoVideo.
Handles downloading images and generating images from prompts.
"""
from typing import Optional
import os
import uuid
import requests
import logging
from video_generator.generate_image import generate_image_from_prompt as _generate_image_from_prompt
from video_generator.freepik_api import generate_image_from_prompt_freepik
from video_generator.gemini_api import generate_image_from_prompt_gemini
from video_generator.config import Config
from video_generator.performance_optimizer import cache_result

logger = logging.getLogger(__name__)
TEMP_DIR = Config.TEMP_DIR

def download_asset(url_or_path: str) -> str:
    """
    Download an asset from a URL or return the local path if it exists.
    Returns the local file path.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Downloading asset: {url_or_path}")
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        local_filename = os.path.join(TEMP_DIR, f"asset_{uuid.uuid4().hex}{os.path.splitext(url_or_path)[-1]}")
        try:
            r = requests.get(url_or_path, stream=True, timeout=60)
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"Downloaded asset to {local_filename}")
            return local_filename
        except Exception as e:
            logger.error(f"Failed to download asset: {url_or_path} ({e})")
            raise RuntimeError(f"[400] Failed to download asset: {url_or_path} ({e})")
    elif os.path.exists(url_or_path):
        logger.info(f"Using local asset: {url_or_path}")
        return url_or_path
    else:
        logger.error(f"Asset not found: {url_or_path}")
        raise RuntimeError(f"[400] Asset not found: {url_or_path}")

def generate_cache_key(prompt: str, api_key: str, out_path: str, provider: str = "openai") -> str:
    """Generate a cache key for image generation."""
    import hashlib
    key_data = f"{prompt}:{provider}:{api_key or 'none'}"
    return hashlib.md5(key_data.encode()).hexdigest()

@cache_result(generate_cache_key)
def generate_image_from_prompt(prompt: str, api_key: str, out_path: str, provider: str = "openai") -> str:
    """
    Generate an image from a text prompt using the specified provider API and save to out_path.
    Results are cached to avoid regenerating the same images.
    
    Args:
        prompt: Text prompt for image generation
        api_key: API key for the provider (ignored for gemini)
        out_path: Path to save the generated image
        provider: Image generation provider ("openai", "freepik", or "gemini")
        
    Returns:
        Path to the generated image
    """
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance("image_generation")
    def _generate_image_internal():
        logger.info(f"Generating image with {provider} API. Prompt: {prompt[:50]}...")
        
        if provider.lower() == "freepik":
            return generate_image_from_prompt_freepik(prompt, api_key, out_path)
        elif provider.lower() == "openai":
            return _generate_image_from_prompt(prompt, api_key, out_path)
        elif provider.lower() == "gemini":
            return generate_image_from_prompt_gemini(prompt, out_path)
        else:
            raise ValueError(f"Unsupported image generation provider: {provider}. Supported providers: openai, freepik, gemini")
    
    return _generate_image_internal() 