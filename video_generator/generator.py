"""
Core video generation logic for ProtoVideo.
Handles orchestration, scene rendering, and helpers.
"""
from typing import List, Optional, Dict, Any, Union
import os
import uuid
import tempfile
import logging
import gc
from moviepy import (
    ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, TextClip, CompositeAudioClip
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut, MultiplyColor
from moviepy.audio.AudioClip import AudioClip, concatenate_audioclips
from video_generator.image_utils import download_asset, generate_image_from_prompt
from video_generator.audio_utils import generate_narration
from video_generator.captacity_integration import generate_captacity_subtitles_compatible
from video_generator.cleanup_utils import cleanup_files, upload_to_r2
from video_generator.logging_utils import get_logger
from video_generator.config import Config
from video_generator.background_utils import composite_video_with_blurred_background_safe, cleanup_blurred_background_files
from pydantic import BaseModel, Field, field_validator
import time

logger = get_logger()

REEL_SIZE = Config.REEL_SIZE

class TextOverlay(BaseModel):
    content: str
    position: str = "center"  # top, top-left, top-right, center, bottom, bottom-left, bottom-right
    fontsize: int = 36
    color: str = "white"
    stroke_color: str = "black"
    stroke_width: int = 2
    font: Optional[str] = None  # Use None for default font
    padding: int = 20  # Padding from edges in pixels
    animation_type: str = "none"  # fade_in, fade_out, fade_in_out, none
    preset: Optional[str] = None  # title, subtitle, caption, callout, watermark

class LogoConfig(BaseModel):
    url: str
    position: str = "bottom-right"  # top-left, top-right, bottom-left, bottom-right, center
    opacity: float = 0.6
    show_in_all_scenes: bool = True
    cta_screen: bool = True  # Show on call-to-action screen
    size: Optional[tuple] = None  # (width, height) in pixels, auto-scaled if None
    margin: Optional[int] = None  # Margin from edges in pixels
    
    @field_validator('margin', mode='before')
    @classmethod
    def set_default_margin(cls, v):
        return v if v is not None else 20

def add_logo_to_clip(video_clip, logo_config: LogoConfig, task_id: Optional[str] = None) -> Any:
    """
    Add a logo to a video clip with specified positioning and opacity.
    
    Args:
        video_clip: MoviePy video clip to add logo to
        logo_config: Logo configuration object
        task_id: Task ID for logging
        
    Returns:
        Video clip with logo overlay
    """
    try:
        from PIL import Image
        import requests
        from io import BytesIO
        
        logger.info(f"Adding logo to video clip: {logo_config.url}", extra={"task_id": task_id})
        
        # Download logo image
        response = requests.get(logo_config.url, timeout=30)
        response.raise_for_status()
        logo_img = Image.open(BytesIO(response.content))
        
        # Convert to RGBA if not already
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')
        
        # Resize logo if size is specified, otherwise auto-scale
        if logo_config.size:
            logo_img = logo_img.resize(logo_config.size, Image.Resampling.LANCZOS)
        else:
            # Auto-scale logo to reasonable size (max 15% of video dimensions)
            max_width = int(video_clip.w * 0.20)
            max_height = int(video_clip.h * 0.20)
            logger.info(f"Logo size: {max_width}x{max_height}", extra={"task_id": task_id})
            logo_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Apply opacity
        if logo_config.opacity < 1.0:
            alpha = logo_img.split()[3]
            alpha = alpha.point(lambda x: int(x * logo_config.opacity))
            logo_img.putalpha(alpha)
        
        # Save logo to temporary file
        temp_logo_path = os.path.join(Config.TEMP_DIR, f"logo_{uuid.uuid4().hex}.png")
        logo_img.save(temp_logo_path, "PNG")
        
        # Create MoviePy clip from logo
        logo_clip = ImageClip(temp_logo_path)
        
        # Calculate position based on logo_config.position
        video_w, video_h = video_clip.size
        logo_w, logo_h = logo_clip.size
        margin = logo_config.margin or 20  # Use default margin if None
        
        if logo_config.position == "top-left":
            x, y = margin, margin
        elif logo_config.position == "top-right":
            x, y = video_w - logo_w - margin, margin
        elif logo_config.position == "bottom-left":
            x, y = margin, video_h - logo_h - margin
        elif logo_config.position == "bottom-right":
            x, y = video_w - logo_w - margin, video_h - logo_h - margin
        elif logo_config.position == "center":
            x, y = (video_w - logo_w) // 2, (video_h - logo_h) // 2
        else:
            # Default to bottom-right if invalid position
            x, y = video_w - logo_w - margin, video_h - logo_h - margin
            logger.warning(f"Invalid logo position '{logo_config.position}', defaulting to bottom-right", extra={"task_id": task_id})
        
        # Set position and duration
        logo_clip = logo_clip.with_position((x, y)).with_duration(video_clip.duration)
        
        # Composite logo over video
        result_clip = CompositeVideoClip([video_clip, logo_clip])
        
        # Clean up temporary logo file
        try:
            os.remove(temp_logo_path)
        except Exception as e:
            logger.warning(f"Failed to remove temporary logo file: {e}", extra={"task_id": task_id})
        
        logger.info(f"Logo added successfully to position {logo_config.position}", extra={"task_id": task_id})
        return result_clip
        
    except Exception as e:
        logger.error(f"Failed to add logo to video clip: {e}", exc_info=True, extra={"task_id": task_id})
        # Return original clip if logo addition fails
        return video_clip

def edit_image_with_prompt(image_url: str, prompt: str, task_id: Optional[str] = None) -> str:
    """
    Edit an existing image using Gemini AI based on a text prompt.
    
    Args:
        image_url: URL of the image to edit
        prompt: Text prompt describing the desired modifications
        task_id: Task ID for logging
        
    Returns:
        Path to the edited image file
    """
    try:
        from PIL import Image
        import requests
        from io import BytesIO
        import google.genai as genai
        from google.genai import types
        
        logger.info(f"Editing image with Gemini AI. Prompt: {prompt[:100]}...", extra={"task_id": task_id})
        
        # Check if Gemini API key is available
        api_key = os.environ.get("GEMENI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMENI_API_KEY environment variable not set")
        
        # Download the source image
        logger.info(f"Downloading source image from: {image_url}", extra={"task_id": task_id})
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        source_image = Image.open(BytesIO(response.content))
        
        # Convert to RGB if necessary (Gemini expects RGB)
        if source_image.mode != 'RGB':
            source_image = source_image.convert('RGB')
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Prepare the prompt for image editing
        edit_prompt = f"Edit this image according to the following instructions: {prompt}. Maintain the same aspect ratio and composition while applying the requested changes."
        
        # Generate edited image
        logger.info("Sending image editing request to Gemini AI...", extra={"task_id": task_id})
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[edit_prompt, source_image],
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE']
            )
        )
        
        # Extract the edited image from response
        edited_image = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data is not None:
                edited_image = Image.open(BytesIO(part.inline_data.data))
                break
        
        if not edited_image:
            raise RuntimeError("No edited image received from Gemini AI")
        
        # Resize to match REEL_SIZE for consistency
        edited_image = edited_image.resize(REEL_SIZE, Image.Resampling.LANCZOS)
        
        # Save edited image to temporary file
        temp_edited_path = os.path.join(Config.TEMP_DIR, f"edited_image_{uuid.uuid4().hex}.png")
        edited_image.save(temp_edited_path, "PNG")
        
        logger.info(f"Image edited successfully and saved to: {temp_edited_path}", extra={"task_id": task_id})
        return temp_edited_path
        
    except Exception as e:
        logger.error(f"Failed to edit image with Gemini AI: {e}", exc_info=True, extra={"task_id": task_id})
        raise RuntimeError(f"Image editing failed: {e}")

class SceneInput(BaseModel):
    scene_id: Optional[str] = None  # Unique identifier for scene tracking
    type: str
    image_url: Optional[str] = None
    prompt_image: Optional[str] = None
    prompt_edit_image: Optional[str] = None  # AI prompt to edit existing image
    image_provider: Optional[str] = Config.DEFAULT_IMAGE_PROVIDER  # "openai", "freepik", or "gemini"
    video_url: Optional[str] = None  # URL to existing video file
    prompt_video: Optional[str] = None  # AI prompt to generate video using LumaAI or KlingAI
    prompt_video_image: Optional[str] = None  # Optional image URL for image+text-to-video (KlingAI only)
    video_provider: Optional[str] = None  # Video generation provider ("lumaai" or "klingai"). Defaults to Config.DEFAULT_VIDEO_PROVIDER
    video_resolution: Optional[str] = "720p"  # Video resolution (720p, 1080p, 1440p) - LumaAI only
    video_aspect_ratio: Optional[str] = "9:16"  # Video aspect ratio (9:16, 16:9, 1:1, 4:3, 3:4)
    video_duration: Optional[str] = "5s"  # Video duration (5s, 10s, etc.)
    video_model: Optional[str] = None  # Model to use (LumaAI: "ray-2", KlingAI: "kling", "kling-2.0", etc.)
    narration: Optional[str] = None
    narration_text: Optional[str] = None
    audio_prompt_url: Optional[str] = None
    music: Optional[str] = None
    music_volume: Optional[float] = 0.25  # Volume for background music (0.0 to 1.0)
    duration: int
    text: Optional[TextOverlay] = None
    subtitle: bool = False
    subtitle_config: Optional[Dict[str, Any]] = None  # Per-scene subtitle configuration
    logo: Optional[LogoConfig] = None  # Per-scene logo configuration
    # Animation configuration
    animation_mode: Optional[Union[str, List[str]]] = None  # Animation mode(s) for image scenes
    animation_preset: Optional[str] = None  # Predefined animation preset
    animation_darken_factor: Optional[float] = 0.5  # Darkening factor (0.0 to 1.0)
    animation_drift_px: Optional[int] = 60  # Pixels for drift motion
    animation_osc_px: Optional[int] = 40  # Amplitude for oscillation
    # Transition configuration
    transition_type: Optional[str] = None  # Transition type for this scene
    transition_duration: Optional[float] = 1.0  # Transition duration in seconds
    """
    image_provider:
        - "openai": Use OpenAI DALL-E
        - "freepik": Use Freepik AI Mystic
        - "gemini": Use Google Gemini
    
    prompt_edit_image:
        - AI prompt to modify existing image from image_url
        - Uses Gemini AI to edit the image based on the prompt
    """

def generate_scene_id(scene: dict, scene_idx: int, task_id: Optional[str] = None) -> str:
    """
    Generate a unique scene_id for tracking purposes.
    If scene_id is already provided, use it. Otherwise, generate one automatically.
    
    Args:
        scene: Scene dictionary from payload
        scene_idx: Index of the scene (0-based)
        task_id: Task ID for logging
        
    Returns:
        Unique scene_id string
    """
    # If scene_id is already provided, use it
    if scene.get("scene_id"):
        logger.info(f"Using provided scene_id: {scene['scene_id']}", extra={"task_id": task_id})
        return scene["scene_id"]
    
    # Generate automatic scene_id based on scene content and index
    scene_type = scene.get("type", "unknown")
    scene_content = ""
    
    # Try to create meaningful identifier from scene content
    if scene.get("prompt_image"):
        # Use first few words of image prompt
        scene_content = scene["prompt_image"][:30].replace(" ", "_").lower()
    elif scene.get("prompt_video"):
        # Use first few words of video prompt
        scene_content = scene["prompt_video"][:30].replace(" ", "_").lower()
    elif scene.get("image_url"):
        # Use filename from URL
        import os
        scene_content = os.path.basename(scene["image_url"]).split(".")[0]
    elif scene.get("video_url"):
        # Use filename from URL
        import os
        scene_content = os.path.basename(scene["video_url"]).split(".")[0]
    elif scene.get("narration_text"):
        # Use first few words of narration
        scene_content = scene["narration_text"][:20].replace(" ", "_").lower()
    
    # Clean up content (remove special characters)
    import re
    scene_content = re.sub(r'[^a-zA-Z0-9_-]', '', scene_content)
    
    # Generate scene_id
    if scene_content:
        scene_id = f"{scene_type}_{scene_idx+1}_{scene_content}"
    else:
        scene_id = f"{scene_type}_{scene_idx+1}"
    
    logger.info(f"Generated scene_id: {scene_id}", extra={"task_id": task_id})
    return scene_id

def render_scene(scene: SceneInput, use_global_narration: bool = False, task_id: Optional[str] = None, 
                scene_context: dict = None, video_context: dict = None, audio_prompt_url: Optional[str] = None,
                global_subtitle_config: dict = None) -> (str, List[str]):
    """
    Render a single scene (image or video) with optional narration, music, and subtitles.
    Returns the path to the rendered scene video and a list of temp files to clean up.
    
    Args:
        scene: Scene input data
        use_global_narration: Whether to use global narration
        task_id: Task ID for logging
        scene_context: Additional context about the scene (scene_index, total_scenes, etc.)
        video_context: Context about the entire video (theme, narration_text, etc.)
        audio_prompt_url: Audio prompt URL to use as fallback if scene doesn't have one
        global_subtitle_config: Global subtitle configuration to use as fallback
    """
    scene_id = getattr(scene, 'scene_id', 'unknown')
    logger.info(f"Rendering scene [{scene_id}]: {scene}", extra={"task_id": task_id})
    temp_files = []
    video_clip = None
    audio_clips = []
    
    # Initialize narration variables for all scene types
    narration_path = None
    narration_audio = None
    
    # Handle narration for all scene types
    if not use_global_narration:
        if scene.narration:
            try:
                logger.info(f"Downloading narration asset: {scene.narration}", extra={"task_id": task_id})
                narration_path = download_asset(scene.narration)
                temp_files.append(narration_path)
                logger.info(f"Added narration from file: {narration_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.error(f"Failed to download narration asset: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        elif scene.narration_text:
            try:
                # Use scene audio_prompt_url if set, else use the passed audio_prompt_url as fallback
                scene_audio_prompt_url = getattr(scene, 'audio_prompt_url', None)
                final_audio_prompt_url = scene_audio_prompt_url or audio_prompt_url
                logger.info(f"Generating narration from text. scene_audio_prompt_url={scene_audio_prompt_url}, fallback_audio_prompt_url={audio_prompt_url}, final_audio_prompt_url={final_audio_prompt_url}", extra={"task_id": task_id})
                narration_path = generate_narration(text=scene.narration_text, audio_prompt_url=final_audio_prompt_url)
                logger.info(f"Added narration from text: {narration_path}", extra={"task_id": task_id})
                
                # Verify the file exists before trying to load it
                if not os.path.exists(narration_path):
                    raise FileNotFoundError(f"Narration file was not created: {narration_path}")
                
                # Retry logic for loading the audio file
                max_retries = 3
                retry_delay = 0.1  # 100ms
                
                for attempt in range(max_retries):
                    try:
                        from moviepy.audio.io.AudioFileClip import AudioFileClip
                        narration_audio = AudioFileClip(narration_path)
                        silence = AudioClip(lambda t: 0, duration=0.5, fps=44100)
                        # Don't modify the scene dictionary here - duration will be handled in render_scene
                        narration_audio.close()
                        break
                    except FileNotFoundError as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1}: Narration file not found, retrying in {retry_delay}s: {e}", extra={"task_id": task_id})
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"Failed to load narration audio after {max_retries} attempts: {e}", exc_info=True, extra={"task_id": task_id})
                            raise
                    except Exception as e:
                        logger.error(f"Failed to load narration audio: {e}", exc_info=True, extra={"task_id": task_id})
                        raise
            except Exception as e:
                logger.error(f"Failed to generate narration: {e}", exc_info=True, extra={"task_id": task_id})
                raise
    
    # Handle image or video
    if scene.type == "image":
        image_path = None
        if scene.image_url:
            try:
                logger.info(f"[{scene_id}] Downloading image asset: {scene.image_url}", extra={"task_id": task_id})
                image_path = download_asset(scene.image_url)
                temp_files.append(image_path)
                logger.info(f"[{scene_id}] Added image from file: {image_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.error(f"Failed to download image asset: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        elif scene.prompt_image:
            # Determine which API to use based on provider
            provider = getattr(scene, 'image_provider', Config.DEFAULT_IMAGE_PROVIDER).lower()
            
            if provider == "freepik":
                api_key = os.environ.get("FREEPIK_API_KEY")
                if not api_key:
                    logger.error("FREEPIK_API_KEY environment variable not set.", extra={"task_id": task_id})
                    raise RuntimeError("FREEPIK_API_KEY environment variable not set.")
            elif provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OPENAI_API_KEY environment variable not set.", extra={"task_id": task_id})
                    raise RuntimeError("OPENAI_API_KEY environment variable not set.")
            elif provider == "gemini":
                api_key = None  # Gemini does not require an API key here
            else:
                logger.error(f"Unsupported image provider: {provider}", extra={"task_id": task_id})
                raise RuntimeError(f"Unsupported image provider: {provider}")
            
            # For OpenAI images, save to ./tmp and don't delete
            if provider == "openai":
                # Create ./tmp directory if it doesn't exist
                tmp_dir = "./tmp"
                os.makedirs(tmp_dir, exist_ok=True)
                out_path = os.path.join(tmp_dir, f"openai_generated_{uuid.uuid4().hex}.png")
            else:
                out_path = os.path.join(tempfile.gettempdir(), f"generated_{uuid.uuid4().hex}.png")
            
            try:
                # Note: Product images will be analyzed by GPT-4 Vision in generate_image_from_prompt
                # to enhance the prompt with actual visual details from the product images
                enhanced_prompt = scene.prompt_image
                
                # Get product images from video_context (will be used by GPT-4 Vision for analysis)
                product_images = None
                if video_context and isinstance(video_context, dict):
                    product_images = video_context.get('product_images', [])
                    if product_images and isinstance(product_images, list) and len(product_images) > 0:
                        logger.info(f"[{scene_id}] Found {len(product_images)} product image(s) in video_context - will be analyzed with GPT-4 Vision", extra={"task_id": task_id})
                
                logger.info(f"[{scene_id}] Generating image from prompt using {provider}: {enhanced_prompt[:100]}...", extra={"task_id": task_id})
                image_path = generate_image_from_prompt(enhanced_prompt, api_key, out_path, provider=provider, scene_context=scene_context, video_context=video_context)
                
                # Only add to temp_files if not OpenAI (keep OpenAI images)
                if provider != "openai":
                    temp_files.append(image_path)
                    logger.info(f"Generated image from prompt: {image_path}", extra={"task_id": task_id})
                else:
                    logger.info(f"[{scene_id}] ✅ OpenAI image saved to: {os.path.abspath(image_path)}", extra={"task_id": task_id})
                
                # Store generated image path for potential use in video generation
                generated_image_path = image_path
            except Exception as e:
                logger.error(f"Image generation failed: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        else:
            logger.error("Image URL/path or prompt_image required for image scene.", extra={"task_id": task_id})
            raise ValueError("Image URL/path or prompt_image required for image scene.")
        
        # Handle image editing if prompt_edit_image is provided
        if scene.prompt_edit_image and image_path:
            try:
                logger.info(f"Editing image with AI prompt: {scene.prompt_edit_image[:100]}...", extra={"task_id": task_id})
                edited_image_path = edit_image_with_prompt(scene.image_url, scene.prompt_edit_image, task_id)
                temp_files.append(edited_image_path)
                image_path = edited_image_path  # Use the edited image for video creation
                logger.info(f"Image edited successfully, using edited version: {image_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Image editing failed, using original image: {e}", extra={"task_id": task_id})
                # Continue with original image if editing fails
        
        # --- Set duration from narration if available, otherwise use scene duration ---
        # For image scenes, prefer narration duration to ensure exact sync (no silence padding)
        duration = scene.duration
        if narration_path and not use_global_narration:
            try:
                from moviepy import AudioFileClip
                narration_clip_temp = AudioFileClip(narration_path)
                narration_duration = narration_clip_temp.duration
                narration_clip_temp.close()
                
                # Use narration duration for image scenes to avoid silence padding
                if narration_duration > 0:
                    duration = narration_duration
                    logger.info(f"Using narration duration for image scene: {duration:.2f}s (scene duration was {scene.duration}s)", extra={"task_id": task_id})
                else:
                    logger.warning(f"Narration duration is 0, using scene duration: {scene.duration}s", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Could not get narration duration, using scene duration {scene.duration}s: {e}", extra={"task_id": task_id})
                # Fall back to scene duration if we can't get narration duration
        try:
            logger.info(f"Creating ImageClip for {image_path}", extra={"task_id": task_id})
            
            # Import animation utilities
            from video_generator.animation_utils import create_animated_image_clip, validate_animation_mode, get_animation_preset
            
            # Determine animation mode
            animation_mode = None
            if scene.animation_preset:
                animation_mode = get_animation_preset(scene.animation_preset)
                logger.info(f"Using animation preset: {scene.animation_preset} -> {animation_mode}", extra={"task_id": task_id})
            elif scene.animation_mode:
                animation_mode = scene.animation_mode
                logger.info(f"Using custom animation mode: {animation_mode}", extra={"task_id": task_id})
            
            # Validate animation mode if provided
            if animation_mode and not validate_animation_mode(animation_mode):
                logger.warning(f"Invalid animation mode {animation_mode}, using random animation", extra={"task_id": task_id})
                animation_mode = None
            
            # Get animation parameters
            darken_factor = getattr(scene, 'animation_darken_factor', 0)
            drift_px = getattr(scene, 'animation_drift_px', 60)
            osc_px = getattr(scene, 'animation_osc_px', 40)
            
            # Create animated image clip
            video_clip = create_animated_image_clip(
                image_path=image_path,
                duration=duration,
                reel_size=REEL_SIZE,
                mode=animation_mode,  # None = random animation
                background_color=(0, 0, 0),
                darken_factor=darken_factor,
                drift_px=drift_px,
                osc_px=osc_px,
                task_id=task_id
            )
            
        except Exception as e:
            logger.error(f"Failed to create or process ImageClip: {e}", exc_info=True, extra={"task_id": task_id})
            raise
            
    elif scene.type == "video":
        # First, determine the target duration based on narration if available
        target_duration = None
        if narration_path and not use_global_narration:
            try:
                from moviepy import AudioFileClip
                narration_clip = AudioFileClip(narration_path)
                target_duration = narration_clip.duration
                narration_clip.close()  # Close to free memory
                logger.info(f"Target duration set from narration: {target_duration} seconds", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Failed to get narration duration, using scene duration: {e}", extra={"task_id": task_id})
        
        # Handle video generation from prompt using LumaAI or KlingAI
        if scene.prompt_video:
            try:
                from video_generator.generate_video import generate_video_from_prompt, validate_video_settings
                
                # Get provider (default from config or scene-specific)
                provider = getattr(scene, 'video_provider', None) or Config.DEFAULT_VIDEO_PROVIDER
                provider = provider.lower()
                
                # Get video settings
                resolution = getattr(scene, 'video_resolution', '720p')
                aspect_ratio = getattr(scene, 'video_aspect_ratio', '9:16')
                video_duration = getattr(scene, 'video_duration', '5s')
                
                # Get model (provider-specific defaults)
                if provider == "klingai":
                    model = getattr(scene, 'video_model', None) or "kling-v1"
                else:  # lumaai
                    model = getattr(scene, 'video_model', None) or "ray-2"
                
                # Validate and normalize video settings (for LumaAI)
                if provider == "lumaai":
                    resolution, aspect_ratio, video_duration = validate_video_settings(resolution, aspect_ratio, video_duration)
                
                # E-commerce workflow: If prompt_image is provided, generate image first
                # Then use that generated image for video generation
                # Note: prompt_video_image is no longer used - we use product_images from video_context instead
                image_url = None
                generated_image_path = None
                
                if scene.prompt_image and provider == "klingai":
                    # Generate image from prompt_image with product images as reference
                    logger.info(f"[{scene_id}] E-commerce workflow: Generating image from prompt_image first", extra={"task_id": task_id})
                    
                    # Determine image provider (default to openai for e-commerce)
                    image_provider = getattr(scene, 'image_provider', 'openai').lower()
                    
                    if image_provider == "openai":
                        api_key = os.environ.get("OPENAI_API_KEY")
                        if not api_key:
                            logger.error("OPENAI_API_KEY environment variable not set.", extra={"task_id": task_id})
                            raise RuntimeError("OPENAI_API_KEY environment variable not set.")
                    elif image_provider == "freepik":
                        api_key = os.environ.get("FREEPIK_API_KEY")
                        if not api_key:
                            logger.error("FREEPIK_API_KEY environment variable not set.", extra={"task_id": task_id})
                            raise RuntimeError("FREEPIK_API_KEY environment variable not set.")
                    elif image_provider == "gemini":
                        api_key = None
                    else:
                        logger.error(f"Unsupported image provider: {image_provider}", extra={"task_id": task_id})
                        raise RuntimeError(f"Unsupported image provider: {image_provider}")
                    
                    # Note: Product images will be analyzed by GPT-4 Vision in generate_image_from_prompt
                    # to enhance the prompt with actual visual details from the product images
                    enhanced_prompt = scene.prompt_image
                    
                    # Get product images from video_context (will be used by GPT-4 Vision for analysis)
                    product_images = []
                    if video_context and isinstance(video_context, dict):
                        context_product_images = video_context.get('product_images', [])
                        if context_product_images and isinstance(context_product_images, list):
                            product_images = [img for img in context_product_images if img]
                            logger.info(f"[{scene_id}] Found {len(product_images)} product image(s) in video_context - will be analyzed with GPT-4 Vision", extra={"task_id": task_id})
                    
                    # Generate image - save to ./tmp for OpenAI images (don't delete)
                    # Force OpenAI for e-commerce workflow (required for GPT-4 Vision product image analysis)
                    if image_provider != "openai":
                        logger.warning(f"[{scene_id}] E-commerce workflow requires OpenAI for product image analysis. Overriding {image_provider} to openai.", extra={"task_id": task_id})
                        image_provider = "openai"
                        api_key = os.environ.get("OPENAI_API_KEY")
                        if not api_key:
                            raise RuntimeError("OPENAI_API_KEY environment variable not set for e-commerce workflow.")
                    
                    if image_provider == "openai":
                        # Create ./tmp directory if it doesn't exist
                        tmp_dir = "./tmp"
                        os.makedirs(tmp_dir, exist_ok=True)
                        out_path = os.path.join(tmp_dir, f"openai_generated_{uuid.uuid4().hex}.png")
                        logger.info(f"[{scene_id}] Generating image using OpenAI (e-commerce workflow with product image analysis): {enhanced_prompt[:100]}...", extra={"task_id": task_id})
                        generated_image_path = generate_image_from_prompt(
                            enhanced_prompt, 
                            api_key, 
                            out_path, 
                            provider=image_provider, 
                            scene_context=scene_context, 
                            video_context=video_context
                        )
                        # Don't add to temp_files for OpenAI - keep the image
                        logger.info(f"[{scene_id}] ✅ OpenAI image saved to: {os.path.abspath(generated_image_path)}", extra={"task_id": task_id})
                    else:
                        # For other providers, use temp directory and add to temp_files
                        out_path = os.path.join(tempfile.gettempdir(), f"generated_{uuid.uuid4().hex}.png")
                        logger.info(f"[{scene_id}] Generating image from prompt using {image_provider}: {enhanced_prompt[:100]}...", extra={"task_id": task_id})
                        generated_image_path = generate_image_from_prompt(
                            enhanced_prompt, 
                            api_key, 
                            out_path, 
                            provider=image_provider, 
                            scene_context=scene_context, 
                            video_context=video_context
                        )
                        temp_files.append(generated_image_path)
                        logger.info(f"[{scene_id}] Generated image for video: {generated_image_path}", extra={"task_id": task_id})
                    
                    # Upload generated image to R2 to get a URL for KlingAI
                    if generated_image_path and os.path.exists(generated_image_path):
                        try:
                            from video_generator.cleanup_utils import upload_to_r2
                            bucket_name = Config.R2_BUCKET_NAME
                            image_filename = f"generated_images/{task_id or 'temp'}/{os.path.basename(generated_image_path)}"
                            uploaded_url = upload_to_r2(generated_image_path, bucket_name, image_filename)
                            
                            if uploaded_url:
                                image_url = uploaded_url
                                logger.info(f"[{scene_id}] Uploaded generated image to R2: {image_url}", extra={"task_id": task_id})
                            else:
                                logger.warning(f"[{scene_id}] Failed to upload image to R2, using local path (may not work with KlingAI)", extra={"task_id": task_id})
                                # Fallback: if R2 upload fails, we can't use local path with KlingAI
                                # So we'll proceed without image_url
                        except Exception as e:
                            logger.warning(f"[{scene_id}] Failed to upload generated image to R2: {e}. Proceeding without image URL.", extra={"task_id": task_id})
                            # Continue without image_url if upload fails
                
                generation_type = "image+text-to-video" if image_url and provider == "klingai" else "text-to-video"
                logger.info(f"Generating video from {generation_type} using {provider}: {scene.prompt_video[:100]}...", extra={"task_id": task_id})
                
                video_path = generate_video_from_prompt(
                    prompt=scene.prompt_video,
                    image_url=image_url,
                    duration=video_duration,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                    model=model,
                    provider=provider,
                    task_id=task_id
                )
                temp_files.append(video_path)
                logger.info(f"Video generated successfully: {video_path}", extra={"task_id": task_id})
                
                # Create video clip from generated video
                from moviepy import VideoFileClip
                video_clip = VideoFileClip(video_path)
                
                # Set duration based on target duration or video duration
                if target_duration:
                    duration = target_duration
                    logger.info(f"Using narration duration: {duration} seconds", extra={"task_id": task_id})
                else:
                    duration = video_clip.duration
                    logger.info(f"Using video duration: {duration} seconds", extra={"task_id": task_id})
                
            except Exception as e:
                logger.error(f"Video generation failed: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        elif scene.video_url:
            # Use existing video file
            try:
                logger.info(f"Downloading video asset: {scene.video_url}", extra={"task_id": task_id})
                video_path = download_asset(scene.video_url)
                temp_files.append(video_path)
                logger.info(f"Added video from file: {video_path}", extra={"task_id": task_id})
                
                # Create video clip from downloaded video
                from moviepy import VideoFileClip
                video_clip = VideoFileClip(video_path)
                # Set duration based on target duration or scene/video duration
                if target_duration:
                    duration = target_duration
                    logger.info(f"Using narration duration: {duration} seconds", extra={"task_id": task_id})
                else:
                    duration = scene.duration or video_clip.duration
                    logger.info(f"Using scene/video duration: {duration} seconds", extra={"task_id": task_id})
                
            except Exception as e:
                logger.error(f"Failed to download video asset: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        else:
            logger.error("Video prompt or video URL required for video scene.", extra={"task_id": task_id})
            raise ValueError("Video prompt or video URL required for video scene.")
            
        # Resize video to match REEL_SIZE with blurred background if needed
        try:
            logger.info(f"Processing video clip: original size {video_clip.w}x{video_clip.h}, target size {REEL_SIZE[0]}x{REEL_SIZE[1]}", extra={"task_id": task_id})
            
            # Validate video clip before processing
            if video_clip.w <= 0 or video_clip.h <= 0:
                logger.error(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}", extra={"task_id": task_id})
                raise ValueError(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}")
            
            # Use safe blurred background compositing to avoid mask issues
            video_clip = composite_video_with_blurred_background_safe(
                video_clip, 
                REEL_SIZE, 
                blur_radius=20,  # Moderate blur
                background_opacity=0.3,  # Subtle background
                max_zoom_factor=2.5,  # Maximum zoom before using blurred background
                task_id=task_id
            )
            
            logger.info(f"Video processed with blurred background: final size {video_clip.w}x{video_clip.h}", extra={"task_id": task_id})
            
        except Exception as e:
            logger.error(f"Failed to process video clip with blurred background: {e}", exc_info=True, extra={"task_id": task_id})
            # Fallback to simple resizing if blurred background fails
            try:
                logger.warning("Falling back to simple video resizing", extra={"task_id": task_id})
                # Ensure we have a valid video clip for fallback
                if video_clip.w > 0 and video_clip.h > 0:
                    video_clip = video_clip.resized(height=REEL_SIZE[1])
                    if video_clip.w > REEL_SIZE[0]:
                        video_clip = video_clip.resized(width=REEL_SIZE[0])
                else:
                    logger.error("Video clip has invalid dimensions, cannot proceed", extra={"task_id": task_id})
                    raise ValueError("Video clip has invalid dimensions")
            except Exception as fallback_e:
                logger.error(f"Fallback resizing also failed: {fallback_e}", exc_info=True, extra={"task_id": task_id})
                raise
        
        # Handle video duration adjustment based on target duration
        if target_duration and target_duration > video_clip.duration:
            logger.info(f"Narration longer than video ({target_duration}s > {video_clip.duration}s), looping video", extra={"task_id": task_id})
            # Calculate how many loops we need
            loops_needed = int(target_duration / video_clip.duration) + 1
            video_clips = [video_clip] * loops_needed
            video_clip = concatenate_videoclips(video_clips)
            # Trim to exact target duration
            video_clip = video_clip.subclipped(0, target_duration)
            logger.info(f"Video looped {loops_needed} times to cover narration duration", extra={"task_id": task_id})
        elif target_duration and target_duration < video_clip.duration:
            logger.info(f"Narration shorter than video ({target_duration}s < {video_clip.duration}s), trimming video", extra={"task_id": task_id})
            video_clip = video_clip.subclipped(0, target_duration)
            
    else:
        logger.error(f"Unsupported scene type: {scene.type}", extra={"task_id": task_id})
        raise ValueError(f"Unsupported scene type: {scene.type}")
        
    # Add narration audio
    if not use_global_narration:
        if narration_path:
            try:
                logger.info(f"Adding narration audio to video clip.", extra={"task_id": task_id})
                narration_clip = AudioFileClip(narration_path)
                
                # For image scenes: always match video duration to narration (no padding, no extension)
                # This ensures exact sync with no silence gaps
                if scene.type == "image":
                    if narration_clip.duration != video_clip.duration:
                        # Adjust video clip duration to exactly match narration
                        video_clip = video_clip.with_duration(narration_clip.duration)
                        logger.info(f"Image scene: adjusted video duration to match narration exactly: {narration_clip.duration:.2f}s", extra={"task_id": task_id})
                    narration_padded = narration_clip
                else:
                    # For video scenes: handle duration mismatch
                    if narration_clip.duration < video_clip.duration:
                        # Narration is shorter - pad with silence to match video duration
                        silence = AudioClip(lambda t: 0, duration=video_clip.duration - narration_clip.duration)
                        narration_padded = CompositeAudioClip([
                            narration_clip,
                            silence.with_start(narration_clip.duration)
                        ])
                        narration_padded = narration_padded.with_duration(video_clip.duration)
                        logger.info(f"Video scene: narration padded with silence: {narration_clip.duration}s -> {video_clip.duration}s", extra={"task_id": task_id})
                    else:
                        # Narration is longer - video scenes already handled looping above
                        # Use the full narration duration
                        narration_padded = narration_clip
                        logger.info(f"Video scene: using full narration duration: {narration_clip.duration:.2f}s", extra={"task_id": task_id})
                
                video_clip = video_clip.with_audio(narration_padded)
                logger.info(f"Audio synchronized: video={video_clip.duration}s, narration={narration_padded.duration}s", extra={"task_id": task_id})
                
            except Exception as e:
                logger.error(f"Failed to add narration audio: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        # Add per-scene subtitles if requested
        if (
            getattr(scene, 'subtitle', False)
            and narration_path
            and scene.narration_text
        ):
            try:
                logger.info(f"Generating subtitles for scene narration.", extra={"task_id": task_id})
                
                # Get subtitle configuration from scene or use global config as fallback
                subtitle_config = getattr(scene, 'subtitle_config', {}) or {}
                
                # If scene doesn't have subtitle config, use global config
                if not subtitle_config and global_subtitle_config:
                    subtitle_config = global_subtitle_config
                    logger.info(f"Using global subtitle config for scene", extra={"task_id": task_id})
                
                # Extract subtitle parameters with defaults
                font = subtitle_config.get('font', 'Bangers-Regular.ttf')
                font_size = subtitle_config.get('font_size', 110)
                font_color = subtitle_config.get('font_color', 'white')
                stroke_color = subtitle_config.get('stroke_color', 'black')
                stroke_width = subtitle_config.get('stroke_width', 4)
                highlight_current_word = subtitle_config.get('highlight_current_word', True)
                word_highlight_color = subtitle_config.get('word_highlight_color', 'yellow')
                line_count = subtitle_config.get('line_count', 2)
                position = subtitle_config.get('position', 'middle')
                
                logger.info(f"Subtitle config: font={font}, size={font_size}, color={font_color}, position={position}, highlight={highlight_current_word}", extra={"task_id": task_id})
                
                subtitle_clips = generate_captacity_subtitles_compatible(
                    narration_path, video_clip,
                    font=font,
                    font_size=font_size,
                    font_color=font_color,
                    stroke_color=stroke_color,
                    stroke_width=stroke_width,
                    highlight_current_word=highlight_current_word,
                    word_highlight_color=word_highlight_color,
                    line_count=line_count,
                    position=position,
                    task_id=task_id
                )
                video_clip = CompositeVideoClip([video_clip] + subtitle_clips)
                logger.info("Subtitles added for scene narration.", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Subtitle generation failed for scene: {e}", exc_info=True, extra={"task_id": task_id})
        
        # Add text overlay if configured
        if scene.text:
            try:
                logger.info(f"Adding text overlay to scene: '{scene.text.content}'", extra={"task_id": task_id})
                
                from video_generator.captacity_text_overlay import (
                    add_captacity_text_overlay_to_clip, 
                    validate_text_position, 
                    get_text_preset
                )
                
                # Validate text position
                if not validate_text_position(scene.text.position):
                    logger.warning(f"Invalid text position '{scene.text.position}', using center", extra={"task_id": task_id})
                    scene.text.position = "center"
                
                # Get text configuration
                if scene.text.preset:
                    # Use preset configuration
                    preset_config = get_text_preset(scene.text.preset)
                    text_config = {
                        "position": preset_config["position"],
                        "font_size": preset_config["font_size"],
                        "color": preset_config["color"],
                        "stroke_color": preset_config["stroke_color"],
                        "stroke_width": preset_config["stroke_width"],
                        "padding": preset_config.get("padding", 20),
                        "opacity": preset_config.get("opacity", 1.0)
                    }
                    logger.info(f"Using text preset: {scene.text.preset}", extra={"task_id": task_id})
                else:
                    # Use custom configuration
                    text_config = {
                        "position": scene.text.position,
                        "font_size": scene.text.fontsize,
                        "color": scene.text.color,
                        "stroke_color": scene.text.stroke_color,
                        "stroke_width": scene.text.stroke_width,
                        "font": scene.text.font,
                        "padding": getattr(scene.text, 'padding', 20),
                        "opacity": getattr(scene.text, 'opacity', 1.0)
                    }
                
                # Add text overlay to video clip
                video_clip = add_captacity_text_overlay_to_clip(
                    video_clip=video_clip,
                    text=scene.text.content,
                    position=text_config["position"],
                    font_size=text_config["font_size"],
                    color=text_config["color"],
                    stroke_color=text_config["stroke_color"],
                    stroke_width=text_config["stroke_width"],
                    font=text_config.get("font", None),
                    padding=text_config.get("padding", 20),
                    opacity=text_config.get("opacity", 1.0),
                    task_id=task_id
                )
                
                logger.info("Text overlay added to scene successfully.", extra={"task_id": task_id})
                
            except Exception as e:
                logger.warning(f"Text overlay generation failed for scene: {e}", exc_info=True, extra={"task_id": task_id})
        
        # Add logo if configured for this scene
        if scene.logo:
            try:
                scene_type = scene.type
                logger.info(f"Adding logo to {scene_type} scene: {scene.logo.url}", extra={"task_id": task_id})
                logger.info(f"Logo configuration: position={scene.logo.position}, opacity={scene.logo.opacity}, margin={scene.logo.margin}", extra={"task_id": task_id})
                
                # Apply logo to the video clip
                video_clip = add_logo_to_clip(video_clip, scene.logo, task_id)
                
                logger.info(f"Logo added to {scene_type} scene successfully", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Failed to add logo to {scene.type} scene: {e}", exc_info=True, extra={"task_id": task_id})
                # Continue without logo if it fails
        
        # Handle music
        if scene.music:
            try:
                logger.info(f"Downloading music asset: {scene.music}", extra={"task_id": task_id})
                music_path = download_asset(scene.music)
                temp_files.append(music_path)
                audio_clips.append(AudioFileClip(music_path).with_volume_scaled(0.3).with_duration(scene.duration))
                logger.info(f"Added background music: {music_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.error(f"Failed to download or process music: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        # Mix audio
        if audio_clips:
            try:
                logger.info(f"Mixing {len(audio_clips)} audio tracks for scene.", extra={"task_id": task_id})
                composite_audio = CompositeAudioClip(audio_clips)
                video_clip = video_clip.with_audio(composite_audio)
            except Exception as e:
                logger.error(f"Failed to mix audio tracks: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        scene_output = os.path.join(Config.TEMP_DIR, f"scene_{uuid.uuid4().hex}.mp4")
        try:
            logger.info(f"Exporting scene to {scene_output}", extra={"task_id": task_id})
            
            # Use simple, reliable codec settings for scene rendering
            codec = "libx264"  # Default reliable codec
            
            # Use optimal threads for encoding
            threads = min(Config.SCENE_RENDERING_THREADS, os.cpu_count() or 4)
            
            video_clip.write_videofile(
                scene_output,
                fps=24,
                codec=codec,
                audio_codec="aac",
                temp_audiofile=f"{scene_output}.temp_audio.m4a",
                remove_temp=True,
                logger=None,
                threads=threads,
                preset=Config.SCENE_RENDERING_PRESET,
                bitrate=Config.FFMPEG_BITRATE,
                ffmpeg_params=['-crf', str(Config.FFMPEG_CRF)] if Config.FFMPEG_CRF else None
            )
            temp_files.append(scene_output)
            video_clip.close()
            del video_clip
            gc.collect()
            logger.info(f"Scene rendered and saved: {scene_output}", extra={"task_id": task_id})
            return scene_output, temp_files
        except Exception as e:
            logger.error(f"Failed to export scene video: {e}", exc_info=True, extra={"task_id": task_id})
            raise

def generate_video_core(request_dict, task_id=None):
    import copy
    from video_generator.cleanup_utils import cleanup_files
    from video_generator.performance_optimizer import get_performance_optimizer, monitor_performance
    
    # Initialize performance monitoring
    optimizer = get_performance_optimizer()
    if task_id:
        optimizer.start_performance_monitoring(task_id)
    
    # Log hardware settings for debugging
    Config.log_hardware_settings()
    
    # Run batch optimizations for better performance
    optimizer.batch_optimize()
    
    @monitor_performance("video_generation_total")
    def _generate_video_internal():
        request = copy.deepcopy(request_dict)
        
        # Normalize field names: convert video_prompt -> prompt_video and image_prompt -> prompt_image
        # This handles payloads from e-commerce config generator that use different field names
        if "scenes" in request:
            for scene in request["scenes"]:
                # Convert image_prompt to prompt_image if needed
                if 'image_prompt' in scene and 'prompt_image' not in scene:
                    scene['prompt_image'] = scene.pop('image_prompt')
                
                # Convert video_prompt to prompt_video if needed
                if 'video_prompt' in scene and 'prompt_video' not in scene:
                    scene['prompt_video'] = scene.pop('video_prompt')
        temp_files = []
        scene_files = []
        use_global_narration = bool(request.get("narration_text"))
        narration_path = None
        narration_duration = None
        global_audio_prompt_url = request.get("audio_prompt_url")
        clips = []
        final_clip = None
        output_path = None
        
        try:
            # Generate global narration if needed
            if use_global_narration:
                try:
                    # Memory optimization before narration generation
                    optimizer.optimize_memory()
                    logger.info("Memory optimized before narration generation", extra={"task_id": task_id})
                    
                    logger.info(f"Generating global narration.", extra={"task_id": task_id})
                    narration_path = generate_narration(request["narration_text"], audio_prompt_url=global_audio_prompt_url)
                    temp_files.append(narration_path)
                    from moviepy.audio.io.AudioFileClip import AudioFileClip
                    narration_clip = AudioFileClip(narration_path)
                    narration_duration = narration_clip.duration
                    num_scenes = len(request["scenes"])
                    if num_scenes > 0:
                        per_scene_duration = narration_duration / num_scenes
                        for scene in request["scenes"]:
                            scene["duration"] = int(round(per_scene_duration))
                    
                    # Memory optimization after narration generation
                    optimizer.optimize_memory()
                    logger.info("Memory optimized after narration generation", extra={"task_id": task_id})
                    
                except Exception as e:
                    logger.error(f"Failed to generate global narration: {e}", exc_info=True, extra={"task_id": task_id})
                    raise
            
            # Handle global logo configuration
            global_logo = None
            if request.get("logo"):
                try:
                    global_logo = LogoConfig(**request["logo"])
                    logger.info(f"Global logo configured: {global_logo.url} at position {global_logo.position}", extra={"task_id": task_id})
                except Exception as e:
                    logger.warning(f"Invalid global logo configuration: {e}", extra={"task_id": task_id})
                    global_logo = None
            
            # Handle global subtitle configuration
            global_subtitle_config = request.get("global_subtitle_config", {})
            if global_subtitle_config:
                logger.info(f"Global subtitle config: {global_subtitle_config}", extra={"task_id": task_id})
            else:
                logger.info("No global subtitle config found", extra={"task_id": task_id})
            
            # Handle global transition configuration
            global_transition_config = request.get("global_transition_config", {})
            global_transition_type = global_transition_config.get("transition_type", "crossfade")
            global_transition_duration = global_transition_config.get("transition_duration", 1.0)
            
            if global_transition_config:
                logger.info(f"Global transition config: type={global_transition_type}, duration={global_transition_duration}s", extra={"task_id": task_id})
            else:
                logger.info("No global transition config found, using defaults", extra={"task_id": task_id})
            
            # Check if this is an e-commerce workflow (has product_images)
            is_ecommerce = bool(request.get("product_images") and len(request.get("product_images", [])) > 0)
            
            # Process scenes in parallel if multiple scenes (unless e-commerce workflow)
            if len(request["scenes"]) > 1 and not is_ecommerce:
                logger.info(f"Processing {len(request['scenes'])} scenes in parallel", extra={"task_id": task_id})
                
                # Debug: Log each scene before processing
                for idx, scene in enumerate(request["scenes"]):
                    logger.info(f"Scene {idx+1}: type={scene.get('type')}, narration_text={scene.get('narration_text', 'None')[:50]}...", extra={"task_id": task_id})
                
                # Check if any scenes use KlingAI
                has_klingai = any(
                    scene.get('video_provider', '').lower() == 'klingai' or 
                    scene.get('prompt_video') and scene.get('video_provider', '').lower() == 'klingai'
                    for scene in request["scenes"]
                )
                
                if has_klingai:
                    logger.info("KlingAI detected in scenes - limiting concurrent processing to 3 for KlingAI scenes", extra={"task_id": task_id})
                    scene_results = _process_scenes_with_klingai_limit(
                        request["scenes"],
                        process_scene_parallel,
                        optimizer,
                        use_global_narration=use_global_narration,
                        global_audio_prompt_url=global_audio_prompt_url,
                        global_subtitle_config=global_subtitle_config,
                        task_id=task_id
                    )
                else:
                    logger.info(f"Starting parallel processing of {len(request['scenes'])} scenes - order will be preserved", extra={"task_id": task_id})
                    scene_results = optimizer.parallel_process_scenes(
                        request["scenes"], 
                        process_scene_parallel, 
                        use_global_narration=use_global_narration,
                        global_audio_prompt_url=global_audio_prompt_url,
                        global_subtitle_config=global_subtitle_config,
                        task_id=task_id
                    )
                
                # Debug: Log results
                logger.info(f"Scene processing results: {len(scene_results)} successful scenes", extra={"task_id": task_id})
                
                # IMPORTANT: Parallel processing doesn't preserve order, so we need to sort by scene index
                # scene_results contains (scene_file, files_to_clean) tuples
                # We need to extract the scene index from the process_scene_parallel function
                
                # Sort results by scene index to maintain original order
                scene_results.sort(key=lambda x: x[2])  # Sort by scene index (3rd element)
                
                # Extract results in correct order
                for scene_file, files_to_clean, scene_index in scene_results:
                    scene_files.append(scene_file)
                    temp_files.extend(files_to_clean)
                    logger.info(f"Added scene {scene_index + 1} to final video", extra={"task_id": task_id})
            else:
                # Process scenes sequentially (single scene OR e-commerce workflow)
                if is_ecommerce:
                    logger.info(f"E-commerce workflow detected ({len(request.get('product_images', []))} product images) - processing {len(request['scenes'])} scenes sequentially", extra={"task_id": task_id})
                else:
                    logger.info(f"Processing {len(request['scenes'])} scenes sequentially", extra={"task_id": task_id})
                
                # Debug: Log each scene before processing
                for idx, scene in enumerate(request["scenes"]):
                    logger.info(f"Scene {idx+1}: type={scene.get('type')}, narration_text={scene.get('narration_text', 'None')[:50]}...", extra={"task_id": task_id})
                
                for idx, scene in enumerate(request["scenes"]):
                    try:
                        logger.info(f"Processing scene {idx+1}/{len(request['scenes'])}", extra={"task_id": task_id})
                        
                        # Create scene context
                        scene_context = {
                            "scene_index": idx,
                            "total_scenes": len(request["scenes"]),
                            "duration": scene.get("duration", 10),
                            "scene_type": scene.get("type", "image")
                        }
                        
                        # Create video context
                        video_context = {
                            "narration_text": request.get("narration_text"),
                            "theme": request.get("scenes"),
                            "output_filename": request.get("output_filename"),
                            "product_images": request.get("product_images", [])  # For e-commerce workflow
                        }
                        
                        # Apply global logo if no per-scene logo is configured
                        if global_logo and global_logo.show_in_all_scenes and not scene.get("logo"):
                            scene["logo"] = global_logo.dict()
                            logger.info(f"Applied global logo to scene {idx+1}", extra={"task_id": task_id})
                        
                        scene_file, files_to_clean = process_scene_sequential(
                            scene, idx, use_global_narration, global_audio_prompt_url, task_id,
                            scene_context=scene_context, video_context=video_context,
                            global_subtitle_config=global_subtitle_config
                        )
                        scene_files.append(scene_file)
                        temp_files.extend(files_to_clean)
                        
                        # Memory optimization after each scene (configurable frequency)
                        if Config.ENABLE_MEMORY_OPTIMIZATION and idx % Config.MEMORY_CLEANUP_INTERVAL == 0:
                            optimizer.optimize_memory()
                            logger.info(f"Memory optimized after scene {idx+1}", extra={"task_id": task_id})
                        
                    except Exception as e:
                        logger.error(f"Failed to process scene {idx+1}: {e}", exc_info=True, extra={"task_id": task_id})
                        raise
            
            # Optimize memory after scene processing
            optimizer.optimize_memory()
            
            # Remove additional memory optimization between scenes to reduce overhead
            # for i, scene_file in enumerate(scene_files):
            #     if i > 0:  # Skip first scene
            #         optimizer.optimize_memory()
            #         logger.info(f"Memory optimized after scene {i+1}", extra={"task_id": task_id})
            
            # Concatenate video clips with transitions
            from moviepy import VideoFileClip
            from video_generator.transition_utils import concatenate_with_transitions, validate_transition_type
            
            try:
                logger.info(f"Loading scene video clips for concatenation.", extra={"task_id": task_id})
                clips = [VideoFileClip(f) for f in scene_files]
                logger.info(f"Concatenating {len(clips)} scene clips with transitions.", extra={"task_id": task_id})
                
                # Generate output filename
                output_filename = request['output_filename']
                if task_id:
                    output_filename = f"{task_id}_{output_filename}"
                output_path = os.path.join(Config.OUTPUT_DIR, output_filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                logger.info(f"Exporting final video to {output_path}", extra={"task_id": task_id})
                
                # Use transitions if configured
                if len(clips) > 1 and global_transition_type != "none":
                    if validate_transition_type(global_transition_type):
                        final_clip = concatenate_with_transitions(
                            clips, 
                            transition_type=global_transition_type,
                            transition_duration=global_transition_duration,
                            task_id=task_id
                        )
                    else:
                        logger.warning(f"Invalid transition type {global_transition_type}, using simple concatenation", extra={"task_id": task_id})
                        from moviepy import concatenate_videoclips
                        final_clip = concatenate_videoclips(clips, method="compose")
                else:
                    # No transitions needed
                    from moviepy import concatenate_videoclips
                    final_clip = concatenate_videoclips(clips, method="compose")
                
                # Enforce Instagram Reels duration limits
                min_duration = 3
                max_duration = 90
                if final_clip.duration < min_duration:
                    logger.warning(f"Final video duration {final_clip.duration:.2f}s is less than {min_duration}s. Padding with black frames.", extra={"task_id": task_id})
                    from moviepy import ColorClip
                    pad_duration = min_duration - final_clip.duration
                    black_clip = ColorClip(size=final_clip.size, color=(0,0,0), duration=pad_duration)
                    final_clip = concatenate_videoclips([final_clip, black_clip], method="compose")
                elif final_clip.duration > max_duration:
                    logger.warning(f"Final video duration {final_clip.duration:.2f}s exceeds {max_duration}s. Trimming.", extra={"task_id": task_id})
                    # Trim before adding logo to avoid CompositeVideoClip.subclip() issue
                    try:
                        final_clip = final_clip.subclip(0, max_duration)
                    except AttributeError:
                        # If subclip() doesn't work (e.g., CompositeVideoClip from padding), use with_duration()
                        logger.warning("subclip() failed, using with_duration() as fallback", extra={"task_id": task_id})
                        final_clip = final_clip.with_duration(max_duration)
                
                # Add final logo if global logo is configured and cta_screen is enabled
                # Note: Logo is added AFTER trimming to avoid CompositeVideoClip.subclip() issues
                if global_logo and global_logo.cta_screen:
                    try:
                        logger.info(f"Adding final logo to concatenated video: {global_logo.url}", extra={"task_id": task_id})
                        final_clip = add_logo_to_clip(final_clip, global_logo, task_id)
                        logger.info("Final logo added to concatenated video successfully", extra={"task_id": task_id})
                    except Exception as e:
                        logger.warning(f"Failed to add final logo to concatenated video: {e}", exc_info=True, extra={"task_id": task_id})
                        # Continue without logo if it fails
                
                # Export final video
                # Use simple, reliable codec settings
                codec = "libx264"  # Default reliable codec
                
                # Use optimal threads for encoding
                threads = min(Config.FINAL_VIDEO_THREADS, os.cpu_count() or 4)
                
                # Validate final clip before export
                if not final_clip or final_clip.duration <= 0:
                    raise ValueError(f"Invalid final clip: duration={getattr(final_clip, 'duration', 0)}")
                
                logger.info(f"Exporting final video: duration={final_clip.duration:.2f}s, fps={Config.FPS}", extra={"task_id": task_id})
                
                # Add error handling for final video export
                try:
                    # Use a writable temp directory for audio file
                    temp_audio_path = os.path.join(Config.TEMP_DIR, f"temp-audio-{task_id or 'final'}.m4a")
                    
                    final_clip.write_videofile(
                        output_path,
                        fps=Config.FPS,
                        codec=codec,
                        audio_codec='aac',
                        temp_audiofile=temp_audio_path,
                        remove_temp=True,
                        logger=None,
                        threads=threads,
                        preset=Config.FINAL_VIDEO_PRESET,
                        bitrate=Config.FFMPEG_BITRATE,
                        ffmpeg_params=['-crf', str(Config.FFMPEG_CRF)] if Config.FFMPEG_CRF else None
                    )
                    logger.info(f"Final video exported successfully: {output_path}", extra={"task_id": task_id})
                except Exception as export_error:
                    logger.error(f"Failed to export final video: {export_error}", exc_info=True, extra={"task_id": task_id})
                    # Try to get more info about the clips
                    for i, clip in enumerate(clips):
                        try:
                            logger.info(f"Clip {i}: duration={getattr(clip, 'duration', 'N/A')}, size={getattr(clip, 'size', 'N/A')}", extra={"task_id": task_id})
                        except Exception as clip_info_error:
                            logger.error(f"Failed to get clip {i} info: {clip_info_error}", extra={"task_id": task_id})
                    raise
                
                # Clean up clips
                for clip in clips:
                    clip.close()
                if final_clip:
                    final_clip.close()
                
                # Upload to R2
                bucket_name = Config.R2_BUCKET_NAME
                object_key = f"videos/{task_id}/{os.path.basename(output_path)}"
                r2_url = upload_to_r2(output_path, bucket_name, object_key)
                
                # Clean up temporary files
                cleanup_files(temp_files + scene_files)
                cleanup_blurred_background_files()
                
                # Prepare result with video URL and metadata
                result = {
                    "r2_url": r2_url,
                    "local_path": output_path,
                    "duration": final_clip.duration if final_clip else 0,
                    "performance_report": optimizer.get_performance_report()
                }
                
                # Add post_description if it exists in the original request
                if request.get("post_description"):
                    result["post_description"] = request["post_description"]
                    logger.info(f"Added post_description to result", extra={"task_id": task_id})
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to concatenate video clips: {e}", exc_info=True, extra={"task_id": task_id})
                raise
                
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True, extra={"task_id": task_id})
            # Clean up on failure
            cleanup_files(temp_files + scene_files)
            cleanup_blurred_background_files()
            raise
    
    return _generate_video_internal()

def _process_scenes_with_klingai_limit(scenes, process_func, optimizer, **kwargs):
    """
    Process scenes with a limit of 3 concurrent KlingAI video generations.
    KlingAI scenes are processed in batches of 3, while other scenes can be processed normally.
    """
    from concurrent.futures import ThreadPoolExecutor
    from video_generator.logging_utils import get_logger
    
    logger = get_logger()
    task_id = kwargs.get('task_id')
    
    # Separate scenes into KlingAI and non-KlingAI groups
    klingai_scenes = []
    other_scenes = []
    
    for idx, scene in enumerate(scenes):
        # Normalize field names if needed (video_prompt -> prompt_video)
        if 'video_prompt' in scene and 'prompt_video' not in scene:
            scene['prompt_video'] = scene.pop('video_prompt')
        
        is_klingai = (
            scene.get('video_provider', '').lower() == 'klingai' and 
            scene.get('prompt_video')  # Only if it actually needs video generation
        )
        if is_klingai:
            klingai_scenes.append((idx, scene))
        else:
            other_scenes.append((idx, scene))
    
    logger.info(
        f"Separated scenes: {len(klingai_scenes)} KlingAI scenes, {len(other_scenes)} other scenes",
        extra={"task_id": task_id}
    )
    
    results = []
    KLINGAI_MAX_CONCURRENT = 3
    
    # Process KlingAI scenes in batches of 3
    if klingai_scenes:
        logger.info(
            f"Processing {len(klingai_scenes)} KlingAI scenes in batches of {KLINGAI_MAX_CONCURRENT}",
            extra={"task_id": task_id}
        )
        
        # Process KlingAI scenes in batches
        for batch_start in range(0, len(klingai_scenes), KLINGAI_MAX_CONCURRENT):
            batch = klingai_scenes[batch_start:batch_start + KLINGAI_MAX_CONCURRENT]
            batch_num = (batch_start // KLINGAI_MAX_CONCURRENT) + 1
            total_batches = (len(klingai_scenes) + KLINGAI_MAX_CONCURRENT - 1) // KLINGAI_MAX_CONCURRENT
            
            logger.info(
                f"Processing KlingAI batch {batch_num}/{total_batches} ({len(batch)} scenes)",
                extra={"task_id": task_id}
            )
            
            # Create a limited executor for this batch
            with ThreadPoolExecutor(max_workers=KLINGAI_MAX_CONCURRENT) as klingai_executor:
                futures = []
                for scene_idx, scene in batch:
                    future = klingai_executor.submit(process_func, scene, scene_idx, **kwargs)
                    futures.append((future, scene_idx))
                
                # Wait for all in this batch to complete
                for future, scene_idx in futures:
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(
                            f"KlingAI scene {scene_idx} processing failed: {e}",
                            extra={"task_id": task_id}
                        )
                        raise
    
    # Process other scenes in parallel (no limit)
    if other_scenes:
        logger.info(
            f"Processing {len(other_scenes)} non-KlingAI scenes in parallel",
            extra={"task_id": task_id}
        )
        
        # Use the optimizer's executor for non-KlingAI scenes
        futures = []
        for scene_idx, scene in other_scenes:
            future = optimizer.executor.submit(process_func, scene, scene_idx, **kwargs)
            futures.append((future, scene_idx))
        
        # Wait for all non-KlingAI scenes to complete
        for future, scene_idx in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(
                    f"Non-KlingAI scene {scene_idx} processing failed: {e}",
                    extra={"task_id": task_id}
                )
                raise
    
    return results

def process_scene_parallel(scene, scene_idx, use_global_narration, global_audio_prompt_url, global_subtitle_config, task_id):
    """Process a single scene for parallel execution."""
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance(f"scene_{scene_idx}_parallel")
    def _process_scene():
        result = process_scene_sequential(scene, scene_idx, use_global_narration, global_audio_prompt_url, task_id, 
                                     scene_context=None, video_context=None, global_subtitle_config=global_subtitle_config)
        # Return scene index along with result for proper ordering
        return result[0], result[1], scene_idx  # (scene_file, files_to_clean, scene_index)
    
    return _process_scene()

def process_scene_sequential(scene, scene_idx, use_global_narration, global_audio_prompt_url, task_id, 
                           scene_context: dict = None, video_context: dict = None, global_subtitle_config: dict = None):
    """Process a single scene sequentially."""
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance(f"scene_{scene_idx}_sequential")
    def _process_scene():
        # Per-scene narration
        narration_path = None
        narration_duration = None
        
        if not use_global_narration:
            if scene.get("narration"):
                try:
                    logger.info(f"Downloading narration asset: {scene.narration}", extra={"task_id": task_id})
                    narration_path = download_asset(scene.narration)
                    logger.info(f"Added narration from file: {narration_path}", extra={"task_id": task_id})
                    
                    # Get narration duration for duration calculation
                    try:
                        from moviepy.audio.io.AudioFileClip import AudioFileClip
                        narration_audio = AudioFileClip(narration_path)
                        narration_duration = narration_audio.duration
                        narration_audio.close()
                        logger.info(f"Narration duration: {narration_duration} seconds", extra={"task_id": task_id})
                    except Exception as e:
                        logger.warning(f"Could not determine narration duration: {e}", extra={"task_id": task_id})
                        
                except Exception as e:
                    logger.error(f"Failed to download narration asset: {e}", exc_info=True, extra={"task_id": task_id})
                    raise
            elif scene.get("narration_text"):
                try:
                    # Use scene audio_prompt_url if set, else use the passed audio_prompt_url as fallback
                    scene_audio_prompt_url = scene.get('audio_prompt_url')
                    final_audio_prompt_url = scene_audio_prompt_url or global_audio_prompt_url
                    logger.info(f"Generating narration from text. scene_audio_prompt_url={scene_audio_prompt_url}, fallback_audio_prompt_url={global_audio_prompt_url}, final_audio_prompt_url={final_audio_prompt_url}", extra={"task_id": task_id})
                    narration_path = generate_narration(text=scene["narration_text"], audio_prompt_url=final_audio_prompt_url)
                    logger.info(f"Added narration from text: {narration_path}", extra={"task_id": task_id})
                    
                    # Verify the file exists before trying to load it
                    if not os.path.exists(narration_path):
                        raise FileNotFoundError(f"Narration file was not created: {narration_path}")
                    
                    # Get narration duration for duration calculation
                    try:
                        from moviepy.audio.io.AudioFileClip import AudioFileClip
                        narration_audio = AudioFileClip(narration_path)
                        narration_duration = narration_audio.duration
                        narration_audio.close()
                        logger.info(f"Narration duration: {narration_duration} seconds", extra={"task_id": task_id})
                    except Exception as e:
                        logger.warning(f"Could not determine narration duration: {e}", extra={"task_id": task_id})
                    
                    # Retry logic for loading the audio file (keeping existing logic for compatibility)
                    max_retries = 3
                    retry_delay = 0.1  # 100ms
                    
                    for attempt in range(max_retries):
                        try:
                            from moviepy.audio.io.AudioFileClip import AudioFileClip
                            narration_audio = AudioFileClip(narration_path)
                            silence = AudioClip(lambda t: 0, duration=0.5, fps=44100)
                            # Don't modify the scene dictionary here - duration will be handled in render_scene
                            narration_audio.close()
                            break
                        except FileNotFoundError as e:
                            if attempt < max_retries - 1:
                                logger.warning(f"Attempt {attempt + 1}: Narration file not found, retrying in {retry_delay}s: {e}", extra={"task_id": task_id})
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                            else:
                                logger.error(f"Failed to load narration audio after {max_retries} attempts: {e}", exc_info=True, extra={"task_id": task_id})
                                raise
                        except Exception as e:
                            logger.error(f"Failed to load narration audio: {e}", exc_info=True, extra={"task_id": task_id})
                            raise
                except Exception as e:
                    logger.error(f"Failed to generate narration: {e}", exc_info=True, extra={"task_id": task_id})
                    raise
        
        # Ensure scene has required fields before creating SceneInput
        if "duration" not in scene or scene["duration"] is None:
            # Use narration duration if available, otherwise fall back to default
            if narration_duration is not None:
                # Convert float duration to integer by rounding up to ensure video covers entire audio
                scene["duration"] = int(narration_duration + 0.5)  # Round to nearest integer
                logger.info(f"Set scene duration to narration duration: {narration_duration}s -> {scene['duration']}s (rounded)", extra={"task_id": task_id})
            else:
                scene["duration"] = 10  # Fallback to 10 seconds if no narration
                logger.info(f"No narration duration available, set default duration: {scene['duration']} seconds", extra={"task_id": task_id})
        
        # Generate scene_id if not provided
        if not scene.get("scene_id"):
            scene["scene_id"] = generate_scene_id(scene, scene_idx, task_id)
        
        scene_file, files_to_clean = render_scene(SceneInput(**scene), use_global_narration=use_global_narration, 
                                                 task_id=task_id, scene_context=scene_context, video_context=video_context,
                                                 audio_prompt_url=global_audio_prompt_url, global_subtitle_config=global_subtitle_config)
        return scene_file, files_to_clean
    
    return _process_scene() 