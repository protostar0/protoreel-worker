#!/usr/bin/env python3
"""
Video generation module using LumaAI API.
This module handles generating video scenes from text prompts using LumaAI's video generation service.
"""

import os
import time
import requests
import tempfile
from typing import Optional
from video_generator.logging_utils import get_logger

logger = get_logger()

def generate_video_from_prompt(
    prompt: str, 
    duration: str = "5s", 
    resolution: str = "720p", 
    aspect_ratio: str = "9:16",
    model: str = "ray-2",
    task_id: Optional[str] = None
) -> str:
    """
    Generate a video from a text prompt using LumaAI API.
    
    Args:
        prompt: Text description of the video to generate
        duration: Video duration (e.g., "5s", "10s")
        resolution: Video resolution (e.g., "720p", "1080p")
        aspect_ratio: Video aspect ratio (e.g., "9:16", "16:9", "1:1")
        model: LumaAI model to use (default: "ray-2")
        task_id: Task ID for logging
        
    Returns:
        Path to the generated video file
        
    Raises:
        RuntimeError: If video generation fails or API key is missing
    """
    try:
        # Check if LumaAI API key is available
        api_key = os.environ.get("LUMAAI_API_KEY")
        if not api_key:
            raise RuntimeError("LUMAAI_API_KEY environment variable not set")
        
        logger.info(f"Generating video from prompt using LumaAI: {prompt[:100]}...", extra={"task_id": task_id})
        logger.info(f"Video settings: duration={duration}, resolution={resolution}, aspect_ratio={aspect_ratio}, model={model}", extra={"task_id": task_id})
        
        # Import LumaAI client
        try:
            from lumaai import LumaAI
        except ImportError:
            raise RuntimeError("LumaAI Python package not installed. Install with: pip install lumaai")
        
        # Initialize LumaAI client
        client = LumaAI(auth_token=api_key)
        
        # Create video generation request
        logger.info("Sending video generation request to LumaAI...", extra={"task_id": task_id})
        generation = client.generations.create(
            prompt=prompt,
            model=model,
            resolution=resolution,
            duration=duration,
            aspect_ratio=aspect_ratio
        )
        
        logger.info(f"Video generation started with ID: {generation.id}", extra={"task_id": task_id})
        
        # Wait for generation to complete
        completed = False
        max_wait_time = 300  # 5 minutes max wait time
        start_time = time.time()
        
        while not completed:
            if time.time() - start_time > max_wait_time:
                raise RuntimeError(f"Video generation timed out after {max_wait_time} seconds")
            
            # Check generation status
            generation = client.generations.get(id=generation.id)
            
            if generation.state == "completed":
                completed = True
                logger.info("Video generation completed successfully", extra={"task_id": task_id})
            elif generation.state == "failed":
                failure_reason = getattr(generation, 'failure_reason', 'Unknown error')
                raise RuntimeError(f"Video generation failed: {failure_reason}")
            elif generation.state in ["pending", "processing","dreaming"]:
                logger.info(f"Video generation in progress... (state: {generation.state})", extra={"task_id": task_id})
                time.sleep(5)  # Wait 5 seconds before checking again
            else:
                logger.warning(f"Unknown generation state: {generation.state}", extra={"task_id": task_id})
                time.sleep(5)
        
        # Get the video URL
        video_url = generation.assets.video
        if not video_url:
            raise RuntimeError("No video URL received from LumaAI")
        
        logger.info(f"Video generated successfully: {video_url}", extra={"task_id": task_id})
        
        # Download the video
        logger.info("Downloading generated video...", extra={"task_id": task_id})
        response = requests.get(video_url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Save to temporary file
        temp_dir = os.environ.get("TEMP_DIR", tempfile.gettempdir())
        video_filename = f"lumaai_video_{generation.id}.mp4"
        video_path = os.path.join(temp_dir, video_filename)
        
        with open(video_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        logger.info(f"Video downloaded successfully to: {video_path}", extra={"task_id": task_id})
        return video_path
        
    except Exception as e:
        logger.error(f"Failed to generate video from prompt: {e}", exc_info=True, extra={"task_id": task_id})
        raise RuntimeError(f"Video generation failed: {e}")

def get_video_duration_seconds(duration_str: str) -> int:
    """
    Convert duration string (e.g., "5s", "10s") to seconds.
    
    Args:
        duration_str: Duration string in format like "5s", "10s"
        
    Returns:
        Duration in seconds as integer
    """
    try:
        # Remove 's' and convert to int
        seconds = int(duration_str.replace('s', ''))
        return max(1, seconds)  # Ensure minimum 1 second
    except (ValueError, AttributeError):
        logger.warning(f"Invalid duration format: {duration_str}, using default 5 seconds")
        return 5

def validate_video_settings(
    resolution: str, 
    aspect_ratio: str, 
    duration: str
) -> tuple[str, str, str]:
    """
    Validate and normalize video generation settings.
    
    Args:
        resolution: Video resolution
        aspect_ratio: Video aspect ratio
        duration: Video duration
        
    Returns:
        Tuple of (normalized_resolution, normalized_aspect_ratio, normalized_duration)
    """
    # Validate resolution
    valid_resolutions = ["720p", "1080p", "1440p"]
    if resolution not in valid_resolutions:
        logger.warning(f"Invalid resolution: {resolution}, using default 720p")
        resolution = "720p"
    
    # Validate aspect ratio
    valid_aspect_ratios = ["9:16", "16:9", "1:1", "4:3", "3:4"]
    if aspect_ratio not in valid_aspect_ratios:
        logger.warning(f"Invalid aspect ratio: {aspect_ratio}, using default 9:16")
        aspect_ratio = "9:16"
    
    # Validate duration
    try:
        duration_seconds = get_video_duration_seconds(duration)
        duration = f"{duration_seconds}s"
    except Exception:
        logger.warning(f"Invalid duration: {duration}, using default 5s")
        duration = "5s"
    
    return resolution, aspect_ratio, duration 