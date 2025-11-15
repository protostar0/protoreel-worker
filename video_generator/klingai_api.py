#!/usr/bin/env python3
"""
KlingAI API integration module.
This module handles generating video scenes from text prompts or images using KlingAI's video generation service.
"""

import os
import time
import json
import requests
import tempfile
try:
    import jwt
except ImportError as exc:
    raise ImportError("PyJWT is required for KlingAI API. Install it with: pip install PyJWT") from exc
from typing import Optional, List, Dict, Any
from video_generator.logging_utils import get_logger

logger = get_logger()

# KlingAI API endpoint
KLINGAI_API_BASE_URL = os.environ.get("KLINGAI_API_BASE_URL", "https://api-singapore.klingai.com/v1")

def encode_jwt_token(access_key: str, secret_key: str) -> str:
    """
    Generate JWT token for KlingAI API authentication.
    
    Args:
        access_key: KlingAI access key (iss)
        secret_key: KlingAI secret key (for signing)
        
    Returns:
        JWT token string
    """
    headers = {
        "alg": "HS256",
        "typ": "JWT"
    }
    
    payload = {
        "iss": access_key,
        "exp": int(time.time()) + 1800,  # Valid for 30 minutes
        "nbf": int(time.time()) - 5  # Starts 5 seconds ago
    }
    
    token = jwt.encode(payload, secret_key, headers=headers, algorithm="HS256")
    return token

def get_klingai_auth_token() -> str:
    """
    Get KlingAI JWT authentication token from environment variables.
    
    Returns:
        JWT token string
        
    Raises:
        RuntimeError: If required environment variables are not set
    """
    access_key = os.environ.get("KLINGAI_ACCESS_KEY")
    secret_key = os.environ.get("KLINGAI_SECRET_KEY")
    
    if not access_key:
        raise RuntimeError("KLINGAI_ACCESS_KEY environment variable not set")
    if not secret_key:
        raise RuntimeError("KLINGAI_SECRET_KEY environment variable not set")
    
    return encode_jwt_token(access_key, secret_key)

def generate_video_from_prompt(
    prompt: str,
    image_url: Optional[str] = None,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    model: str = "kling-v1",
    negative_prompt: str = "",
    cfg_scale: float = 0.5,
    mode: str = "pro",
    static_mask: Optional[str] = None,
    dynamic_masks: Optional[List[Dict[str, Any]]] = None,
    task_id: Optional[str] = None
) -> str:
    """
    Generate a video from a text prompt (and optionally an image) using KlingAI API.
    
    Args:
        prompt: Text description of the video to generate
        image_url: Required image URL for image2video generation
        duration: Video duration in seconds (default: 5)
        aspect_ratio: Video aspect ratio (e.g., "9:16", "16:9", "1:1")
        model: KlingAI model to use (default: "kling-v1")
        negative_prompt: Negative prompt (not currently used in API)
        cfg_scale: Classifier-free guidance scale (default: 0.5)
        mode: Generation mode - "pro" or "fast" (default: "pro")
        static_mask: Optional static mask URL
        dynamic_masks: Optional list of dynamic masks with trajectories
        task_id: Task ID for logging
        
    Returns:
        Path to the generated video file
        
    Raises:
        RuntimeError: If video generation fails or API key is missing
    """
    try:
        # Generate JWT token for authentication
        auth_token = get_klingai_auth_token()
        
        # For image2video, image_url is required
        if not image_url:
            raise ValueError("image_url is required for KlingAI image2video generation")
        
        generation_type = "image2video"
        logger.info(f"Generating video from {generation_type} using KlingAI: {prompt[:100]}...", extra={"task_id": task_id})
        logger.info(f"Video settings: duration={duration}s, aspect_ratio={aspect_ratio}, model={model}, mode={mode}", extra={"task_id": task_id})
        
        # Prepare API request
        url = f"{KLINGAI_API_BASE_URL}/videos/image2video"
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Prepare request payload according to KlingAI API
        payload = {
            "model_name": model,
            "mode": mode,
            "duration": str(duration),  # API expects string
            "image": image_url,
            "prompt": prompt,
            "cfg_scale": cfg_scale
        }
        
        # Add optional parameters
        if static_mask:
            payload["static_mask"] = static_mask
        
        if dynamic_masks:
            payload["dynamic_masks"] = dynamic_masks
        
        logger.info("Sending video generation request to KlingAI...", extra={"task_id": task_id})
        logger.info(f"KlingAI request payload: {json.dumps(payload, indent=2)}", extra={"task_id": task_id})
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        # Check response status and handle errors
        if not response.ok:
            try:
                error_response = response.json()
                error_code = error_response.get("code", "unknown")
                error_message = error_response.get("message", "Unknown error")
                request_id = error_response.get("request_id", "N/A")
                
                logger.error(
                    f"KlingAI API error (status {response.status_code}, code {error_code}): {error_message} (request_id: {request_id})",
                    extra={"task_id": task_id}
                )
                
                # Provide more specific error messages based on error code
                if error_code == 1102:
                    raise RuntimeError(f"KlingAI account balance insufficient: {error_message}. Please top up your account.")
                elif response.status_code == 429:
                    raise RuntimeError(f"KlingAI rate limit or balance issue (code {error_code}): {error_message}")
                else:
                    raise RuntimeError(f"KlingAI API error (code {error_code}): {error_message}")
            except RuntimeError:
                # Re-raise RuntimeError as-is (already formatted)
                raise
            except Exception:
                # If JSON parsing fails, log raw response
                logger.error(f"KlingAI API error response (non-JSON, status {response.status_code}): {response.text[:500]}", extra={"task_id": task_id})
                response.raise_for_status()  # This will raise HTTPError
        
        response_data = response.json()
        
        # Check for API errors in successful HTTP response
        if response_data.get("code") != 0:
            error_code = response_data.get("code", "unknown")
            error_message = response_data.get("message", "Unknown error")
            raise RuntimeError(f"KlingAI API error (code {error_code}): {error_message}")
        
        data = response_data.get("data", {})
        klingai_task_id = data.get("task_id")
        if not klingai_task_id:
            raise RuntimeError(f"KlingAI API did not return a task_id: {response_data}")
        
        logger.info(f"KlingAI video generation started with task ID: {klingai_task_id}", extra={"task_id": task_id})
        
        # Poll for status
        completed = False
        max_wait_time = 600  # 10 minutes max wait time
        start_time = time.time()
        poll_interval = 5  # Check every 5 seconds
        max_retries = 3  # Retry failed status checks up to 3 times
        log_interval = 30  # Log at most every 30 seconds
        
        # Track status for reduced logging
        last_logged_status = None
        last_log_time = 0
        
        status_url = f"{KLINGAI_API_BASE_URL}/videos/image2video/{klingai_task_id}"
        
        while not completed:
            if time.time() - start_time > max_wait_time:
                raise RuntimeError(f"KlingAI video generation timed out after {max_wait_time} seconds")
            
            # Retry logic for status polling to handle connection issues
            status_data = None
            for retry_attempt in range(max_retries):
                try:
                    status_response = requests.get(status_url, headers=headers, timeout=30)
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    break  # Success, exit retry loop
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                        requests.exceptions.RequestException) as e:
                    if retry_attempt < max_retries - 1:
                        wait_time = (retry_attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                        logger.warning(
                            f"Status check failed (attempt {retry_attempt + 1}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s...",
                            extra={"task_id": task_id}
                        )
                        time.sleep(wait_time)
                    else:
                        # Last attempt failed, raise the error
                        logger.error(
                            f"Status check failed after {max_retries} attempts: {e}",
                            exc_info=True,
                            extra={"task_id": task_id}
                        )
                        raise RuntimeError(f"KlingAI status check failed after {max_retries} retries: {e}") from e
            
            if status_data is None:
                raise RuntimeError("Failed to get status from KlingAI API after retries")
            
            # Check for API errors in status response
            if status_data.get("code") != 0:
                error_message = status_data.get("message", "Unknown error")
                raise RuntimeError(f"KlingAI API error: {error_message}")
            
            data = status_data.get("data", {})
            current_status = data.get("task_status")
            
            # Track status changes to reduce logging
            current_time = time.time()
            status_changed = current_status != last_logged_status
            time_to_log = (current_time - last_log_time) >= log_interval
            
            if current_status == "succeed":
                completed = True
                logger.info("KlingAI video generation completed successfully", extra={"task_id": task_id})
                
                # Extract video URL from response
                task_result = data.get("task_result", {})
                videos = task_result.get("videos", [])
                
                if not videos or len(videos) == 0:
                    raise RuntimeError("No video URL received from KlingAI upon completion")
                
                video_url = videos[0].get("url")
                if not video_url:
                    raise RuntimeError("No video URL in KlingAI response")
                    
            elif current_status == "failed":
                failure_reason = data.get("task_status_msg", "Unknown error")
                raise RuntimeError(f"KlingAI video generation failed: {failure_reason}")
            elif current_status in ["submitted", "processing"]:
                # Only log on status change or every 30 seconds
                if status_changed or time_to_log:
                    logger.info(f"KlingAI video generation in progress... (status: {current_status})", extra={"task_id": task_id})
                    last_logged_status = current_status
                    last_log_time = current_time
                time.sleep(poll_interval)
            else:
                # Always log unknown status
                logger.warning(f"Unknown KlingAI generation status: {current_status}", extra={"task_id": task_id})
                last_logged_status = current_status
                last_log_time = current_time
                time.sleep(poll_interval)
        
        logger.info(f"Video generated successfully: {video_url}", extra={"task_id": task_id})
        
        # Download the video
        logger.info("Downloading generated video from KlingAI...", extra={"task_id": task_id})
        download_response = requests.get(video_url, stream=True, timeout=120)
        download_response.raise_for_status()
        
        temp_dir = os.environ.get("TEMP_DIR", tempfile.gettempdir())
        video_filename = f"klingai_video_{klingai_task_id}.mp4"
        video_path = os.path.join(temp_dir, video_filename)
        
        with open(video_path, 'wb') as file:
            for chunk in download_response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        logger.info(f"Video downloaded successfully to: {video_path}", extra={"task_id": task_id})
        return video_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"KlingAI API request failed: {e}", exc_info=True, extra={"task_id": task_id})
        raise RuntimeError(f"KlingAI API request failed: {e}") from e
    except Exception as e:
        logger.error(f"Failed to generate video from prompt using KlingAI: {e}", exc_info=True, extra={"task_id": task_id})
        raise RuntimeError(f"KlingAI video generation failed: {e}") from e

def validate_klingai_settings(
    duration: int,
    aspect_ratio: str,
    model: str
) -> tuple[int, str, str]:
    """
    Validate and normalize KlingAI video generation settings.
    
    Args:
        duration: Video duration in seconds
        aspect_ratio: Video aspect ratio
        model: KlingAI model name
        
    Returns:
        Tuple of (normalized_duration, normalized_aspect_ratio, normalized_model)
    """
    # Validate duration
    if duration < 1:
        logger.warning(f"Invalid duration: {duration}, using minimum 1 second")
        duration = 1
    elif duration > 30:
        logger.warning(f"Duration {duration}s exceeds maximum 30s, using 30 seconds")
        duration = 30
    
    # Validate aspect ratio
    valid_aspect_ratios = ["9:16", "16:9", "1:1", "4:3", "3:4"]
    if aspect_ratio not in valid_aspect_ratios:
        logger.warning(f"Invalid aspect ratio: {aspect_ratio}, using default 9:16")
        aspect_ratio = "9:16"
    
    # Validate model - map "kling" to "kling-v1" for API compatibility
    if model == "kling":
        logger.info("Model 'kling' mapped to 'kling-v1' for API compatibility")
        model = "kling-v1"
    
    valid_models = ["kling-v1", "kling-1.5", "kling-1.6", "kling-2.0", "kling-2.1", "kling-2.1-master", "kling-2.5"]
    if model not in valid_models:
        logger.warning(f"Invalid model: {model}, using default kling-v1")
        model = "kling-v1"
    
    return duration, aspect_ratio, model
