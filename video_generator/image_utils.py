"""
Image utilities for ProtoVideo.
Handles downloading images and generating images from prompts.
"""
import os
import uuid
import requests
import logging
import time
from video_generator.generate_image import generate_image_from_prompt as _generate_image_from_prompt
from video_generator.freepik_api import generate_image_from_prompt_freepik
from video_generator.gemini_api import generate_image_from_prompt_gemini
from video_generator.config import Config
from video_generator.performance_optimizer import cache_result

logger = logging.getLogger(__name__)
TEMP_DIR = Config.TEMP_DIR

def is_video_url(url: str) -> bool:
    """Check if URL is a video file based on extension or domain"""
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.m4v']
    url_lower = url.lower()
    
    # Check extension
    if any(url_lower.endswith(ext) for ext in video_extensions):
        return True
    
    # Check common video domains
    video_domains = ['videos.pexels.com', 'video', 'vimeo', 'youtube']
    if any(domain in url_lower for domain in video_domains):
        return True
    
    return False

def is_pexels_url(url: str) -> bool:
    """Check if URL is from Pexels"""
    url_lower = url.lower()
    return 'pexels.com' in url_lower or 'pexels' in url_lower

def download_asset(url_or_path: str, max_retries: int = 3) -> str:
    """
    Download an asset from a URL or return the local path if it exists.
    Returns the local file path.
    
    Args:
        url_or_path: URL or local file path
        max_retries: Maximum number of retry attempts for downloads
        
    Returns:
        Local file path to the downloaded asset
    """
    logger.info(f"Downloading asset: {url_or_path}")
    
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        local_filename = os.path.join(TEMP_DIR, f"asset_{uuid.uuid4().hex}{os.path.splitext(url_or_path)[-1]}")
        
        # Determine if this is a video (larger files need longer timeout)
        is_video = is_video_url(url_or_path)
        
        # Set timeout based on file type
        # Videos: 300 seconds (5 minutes) for connect, 600 seconds (10 minutes) for read
        # Images: 60 seconds connect, 120 seconds read
        if is_video:
            connect_timeout = 300  # 5 minutes
            read_timeout = 600     # 10 minutes
            chunk_size = 65536     # 64KB chunks for faster video downloads
            logger.info(f"Detected video file, using extended timeouts: connect={connect_timeout}s, read={read_timeout}s")
        else:
            connect_timeout = 60   # 1 minute
            read_timeout = 120     # 2 minutes
            chunk_size = 8192      # 8KB chunks for images
            logger.info(f"Detected image/other file, using standard timeouts: connect={connect_timeout}s, read={read_timeout}s")
        
        timeout = (connect_timeout, read_timeout)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries} for {url_or_path}")
                
                # Prepare headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # Add Referer header for Pexels videos (required to avoid 403 Forbidden)
                if is_pexels_url(url_or_path):
                    headers['Referer'] = 'https://www.pexels.com/'
                    # Also try with API key if available
                    pexels_api_key = os.environ.get("PEXELS_API_KEY")
                    if pexels_api_key:
                        headers['Authorization'] = pexels_api_key
                    logger.info("Added Pexels-specific headers (Referer and Authorization) for download")
                
                # Use stream=True for large files
                r = requests.get(
                    url_or_path, 
                    stream=True, 
                    timeout=timeout,
                    headers=headers
                )
                r.raise_for_status()
                
                # Check content length if available (for progress tracking)
                total_size = r.headers.get('content-length')
                if total_size:
                    total_size = int(total_size)
                    logger.info(f"Downloading file of size: {total_size / (1024*1024):.2f} MB")
                
                downloaded_size = 0
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            # Log progress for large files
                            if total_size and downloaded_size % (10 * 1024 * 1024) == 0:  # Every 10MB
                                progress = (downloaded_size / total_size) * 100
                                logger.info(f"Download progress: {progress:.1f}% ({downloaded_size / (1024*1024):.2f} MB)")
                
                # Verify file was downloaded (check file size)
                if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
                    file_size = os.path.getsize(local_filename)
                    logger.info(f"Successfully downloaded asset to {local_filename} ({file_size / (1024*1024):.2f} MB)")
                    return local_filename
                else:
                    raise RuntimeError(f"Downloaded file is empty or doesn't exist: {local_filename}")
                    
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors (403, 404, etc.)
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                error_msg = str(e)
                
                if status_code == 403:
                    # 403 Forbidden - authentication or access issue
                    if is_pexels_url(url_or_path):
                        error_msg = f"403 Forbidden: Pexels video URL requires proper authentication. Ensure PEXELS_API_KEY is set and the video URL is valid. URL: {url_or_path}"
                    else:
                        error_msg = f"403 Forbidden: Access denied to {url_or_path}. The resource may require authentication or the URL may be invalid."
                    
                    logger.error(f"HTTP 403 Forbidden on attempt {attempt + 1}/{max_retries}: {error_msg}")
                    # Don't retry 403 errors as they won't succeed without proper auth
                    raise RuntimeError(f"[403] Failed to download asset (authentication required): {url_or_path}")
                
                elif status_code == 404:
                    error_msg = f"404 Not Found: The resource at {url_or_path} does not exist or has been removed."
                    logger.error(f"HTTP 404 Not Found on attempt {attempt + 1}/{max_retries}: {error_msg}")
                    # Don't retry 404 errors
                    raise RuntimeError(f"[404] Failed to download asset (not found): {url_or_path}")
                
                else:
                    logger.warning(f"HTTP error {status_code} on attempt {attempt + 1}/{max_retries}: {e}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logger.info(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Download failed after {max_retries} attempts with HTTP {status_code}")
                        raise RuntimeError(f"[{status_code}] Failed to download asset after {max_retries} attempts: {url_or_path} ({error_msg})")
                        
            except requests.exceptions.Timeout as e:
                logger.warning(f"Download timeout on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Download failed after {max_retries} attempts due to timeout")
                    raise RuntimeError(f"[400] Failed to download asset after {max_retries} attempts (timeout): {url_or_path}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Download error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff: wait 2^attempt seconds
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Download failed after {max_retries} attempts: {e}")
                    raise RuntimeError(f"[400] Failed to download asset after {max_retries} attempts: {url_or_path} ({e})")
                    
            except Exception as e:
                logger.error(f"Unexpected error during download: {e}")
                # Clean up partial file
                if os.path.exists(local_filename):
                    try:
                        os.remove(local_filename)
                    except OSError:
                        pass
                raise RuntimeError(f"[400] Failed to download asset: {url_or_path} ({e})")
        
        # If we get here, all retries failed
        raise RuntimeError(f"[400] Failed to download asset after {max_retries} attempts: {url_or_path}")
    elif os.path.exists(url_or_path):
        logger.info(f"Using local asset: {url_or_path}")
        return url_or_path
    else:
        logger.error(f"Asset not found: {url_or_path}")
        raise RuntimeError(f"[400] Asset not found: {url_or_path}")

def generate_cache_key(prompt: str, api_key: str, out_path: str, provider: str = "openai", 
                      scene_context: dict = None, video_context: dict = None) -> str:
    """Generate a cache key for image generation."""
    import hashlib
    import json
    
    # Include context in cache key for better differentiation
    context_data = ""
    if scene_context:
        context_data += f":scene_{scene_context.get('scene_index', 0)}_{scene_context.get('total_scenes', 1)}"
    if video_context:
        # Include a hash of video context to avoid very long cache keys
        video_context_str = json.dumps(video_context, sort_keys=True)
        context_data += f":video_{hashlib.md5(video_context_str.encode()).hexdigest()[:8]}"
    
    key_data = f"{prompt}:{provider}:{api_key or 'none'}{context_data}"
    return hashlib.md5(key_data.encode()).hexdigest()

@cache_result(generate_cache_key)
def generate_image_from_prompt(prompt: str, api_key: str, out_path: str, provider: str = "gemini", 
                             scene_context: dict = None, video_context: dict = None) -> str:
    """
    Generate an image from a text prompt using the specified provider API and save to out_path.
    Results are cached to avoid regenerating the same images.
    
    Args:
        prompt: Text prompt for image generation
        api_key: API key for the provider (ignored for gemini)
        out_path: Path to save the generated image
        provider: Image generation provider ("openai", "freepik", or "gemini")
        scene_context: Additional context about the scene (scene_index, total_scenes, etc.)
        video_context: Context about the entire video (theme, narration_text, etc.)
        
    Returns:
        Path to the generated image
    """
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance("image_generation")
    def _generate_image_internal():
        logger.info(f"Generating image with {provider} API. Prompt: {prompt[:50]}...")
        
        # Define fallback providers in order of preference
        fallback_providers = []
        if provider.lower() == "gemini":
            fallback_providers = ["openai", "freepik"]
        elif provider.lower() == "openai":
            fallback_providers = ["gemini", "freepik"]
        elif provider.lower() == "freepik":
            fallback_providers = ["openai", "gemini"]
        
        # Try primary provider first
        providers_to_try = [provider.lower()] + fallback_providers
        
        last_error = None
        for attempt_provider in providers_to_try:
            try:
                logger.info(f"Attempting image generation with {attempt_provider} API")
                
                if attempt_provider == "freepik":
                    return generate_image_from_prompt_freepik(prompt, api_key, out_path)
                elif attempt_provider == "openai":
                    return _generate_image_from_prompt(prompt, api_key, out_path)
                elif attempt_provider == "gemini":
                    return generate_image_from_prompt_gemini(prompt, out_path, 
                                                           scene_context=scene_context, 
                                                           video_context=video_context)
                else:
                    raise ValueError(f"Unsupported image generation provider: {attempt_provider}")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"Image generation failed with {attempt_provider}: {e}")
                
                # If this is not the last provider, try the next one
                if attempt_provider != providers_to_try[-1]:
                    logger.info(f"Falling back to next provider...")
                    continue
                else:
                    # This was the last provider, raise the error
                    logger.error(f"All image generation providers failed. Last error: {e}")
                    raise RuntimeError(f"Image generation failed with all providers. Last error: {e}")
        
        # This should never be reached, but just in case
        raise RuntimeError(f"Image generation failed: {last_error}")
    
    return _generate_image_internal() 