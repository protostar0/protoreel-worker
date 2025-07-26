"""
Freepik API integration for image generation.
Handles image generation using Freepik's AI Mystic API.
"""
import os
import time
import requests
import logging
from typing import Optional, Dict, Any
from video_generator.config import Config

logger = logging.getLogger(__name__)

class FreepikAPI:
    """Freepik API client for image generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Freepik API client.
        
        Args:
            api_key: Freepik API key. If None, will try to get from FREEPIK_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("FREEPIK_API_KEY")
        if not self.api_key:
            raise ValueError("Freepik API key not provided and FREEPIK_API_KEY environment variable not set")
        
        self.base_url = "https://api.freepik.com/v1/ai/mystic"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'x-freepik-api-key': self.api_key
        }
    
    def generate_image(self, prompt: str, aspect_ratio: str = "classic_4_3", 
                      max_wait_time: int = 60, poll_interval: int = 2) -> str:
        """
        Generate an image using Freepik's AI Mystic API.
        
        Args:
            prompt: Text prompt for image generation
            aspect_ratio: Aspect ratio for the image (classic_4_3, square_1_1, etc.)
            max_wait_time: Maximum time to wait for generation (seconds)
            poll_interval: Time between status checks (seconds)
            
        Returns:
            URL of the generated image
            
        Raises:
            RuntimeError: If image generation fails or times out
        """
        logger.info(f"Generating image with Freepik API. Prompt: {prompt[:50]}...")
        
        # Step 1: Submit generation request
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            task_id = data.get("data", {}).get("task_id")
            
            if not task_id:
                raise RuntimeError(f"Failed to get task_id from Freepik API: {data}")
            
            logger.info(f"Freepik generation task created: {task_id}")
            
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to submit Freepik generation request: {e}")
        
        # Step 2: Poll for completion
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                status_response = requests.get(
                    f"{self.base_url}/{task_id}",
                    headers=self.headers,
                    timeout=30
                )
                status_response.raise_for_status()
                
                status_data = status_response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "COMPLETED":
                    generated_images = status_data.get("data", {}).get("generated", [])
                    if generated_images:
                        image_url = generated_images[0]
                        logger.info(f"Freepik image generation completed: {image_url}")
                        return image_url
                    else:
                        raise RuntimeError("Freepik generation completed but no images returned")
                
                elif status == "FAILED":
                    error_msg = status_data.get("data", {}).get("error", "Unknown error")
                    raise RuntimeError(f"Freepik generation failed: {error_msg}")
                
                elif status in ["CREATED", "PROCESSING"]:
                    logger.debug(f"Freepik generation status: {status}")
                    time.sleep(poll_interval)
                    continue
                
                else:
                    logger.warning(f"Unknown Freepik status: {status}")
                    time.sleep(poll_interval)
                    continue
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to check Freepik status: {e}")
                time.sleep(poll_interval)
                continue
        
        raise RuntimeError(f"Freepik image generation timed out after {max_wait_time} seconds")
    
    def download_generated_image(self, image_url: str, output_path: str) -> str:
        """
        Download a generated image from Freepik URL.
        
        Args:
            image_url: URL of the generated image
            output_path: Local path to save the image
            
        Returns:
            Path to the downloaded image
        """
        try:
            logger.info(f"Downloading Freepik image: {image_url}")
            response = requests.get(image_url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Freepik image downloaded to: {output_path}")
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to download Freepik image: {e}")


def generate_image_from_prompt_freepik(prompt: str, api_key: str, out_path: str) -> str:
    """
    Generate an image from a text prompt using Freepik API and save to out_path.
    
    Args:
        prompt: Text prompt for image generation
        api_key: Freepik API key
        out_path: Path to save the generated image
        
    Returns:
        Path to the generated image
    """
    try:
        freepik = FreepikAPI(api_key)
        
        # Generate image URL
        image_url = freepik.generate_image(prompt)
        
        # Download the image
        return freepik.download_generated_image(image_url, out_path)
        
    except Exception as e:
        logger.error(f"Freepik image generation failed: {e}")
        raise RuntimeError(f"Freepik image generation failed: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        logger.error("Usage: python -m video_generator.freepik_api 'your prompt here' [output_path]")
        sys.exit(1)
    
    prompt = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "generated_freepik_image.png"
    api_key = os.environ.get("FREEPIK_API_KEY")
    
    if not api_key:
        logger.error("Set FREEPIK_API_KEY env variable.")
        sys.exit(1)
    
    try:
        result_path = generate_image_from_prompt_freepik(prompt, api_key, out_path)
        logger.info(f"Freepik image saved to {result_path}")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1) 