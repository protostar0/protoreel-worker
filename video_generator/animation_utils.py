"""
Animation utilities for ProtoReel Worker.
Provides configurable animation modes for image clips with zoom, motion, and effects.
"""
import numpy as np
import random
from typing import Union, Tuple, List, Optional
from moviepy import ImageClip
from video_generator.logging_utils import get_logger

logger = get_logger()

# Available animation modes
ZOOM_MODES = ["zoom_in", "zoom_out", "pulse"]
MOTION_MODES = ["drift_up", "drift_down", "oscillate"]
ALL_MODES = ZOOM_MODES + MOTION_MODES

def get_random_animation_mode() -> Tuple[str, Optional[str]]:
    """
    Get a random animation mode combination.
    Returns a tuple of (zoom_mode, motion_mode) where one can be None.
    """
    zoom_mode = random.choice(ZOOM_MODES + [None])
    motion_mode = random.choice(MOTION_MODES + [None])
    
    # Ensure we don't have both as None
    if zoom_mode is None and motion_mode is None:
        zoom_mode = random.choice(ZOOM_MODES)
    
    return zoom_mode, motion_mode

def create_animated_image_clip(
    image_path: str,
    duration: float,
    reel_size: Tuple[int, int],
    mode: Union[str, Tuple[str, ...], List[str]] = None,
    background_color: Tuple[int, int, int] = (0, 0, 0),
    darken_factor: float = 0.5,
    drift_px: int = 60,
    osc_px: int = 40,
    task_id: Optional[str] = None
) -> ImageClip:
    """
    Build a stylized MoviePy ImageClip with selectable animation modes.
    
    Args:
        image_path: Path to the image file
        duration: Duration of the clip in seconds
        reel_size: Target size as (width, height)
        mode: Animation mode(s). Can be:
            - None: Use random animation
            - str: Single mode (e.g., "zoom_in")
            - tuple/list: Multiple modes (e.g., ("zoom_out", "oscillate"))
        background_color: Background color for the clip
        darken_factor: Darkening factor (0.0 = no darken, 0.5 = 50% darker)
        drift_px: Pixels for drift up/down motion
        osc_px: Amplitude for oscillation
        task_id: Task ID for logging
        
    Returns:
        Animated ImageClip
        
    Modes:
        Zoom: "zoom_in", "zoom_out", "pulse"
        Motion: "drift_up", "drift_down", "oscillate"
        
    Examples:
        mode="zoom_in"
        mode=("zoom_out", "oscillate")
        mode=("pulse", "drift_up")
        mode=None  # Random animation
    """
    # Normalize mode input
    if mode is None:
        # Use random animation
        zoom_mode, motion_mode = get_random_animation_mode()
        modes = set()
        if zoom_mode:
            modes.add(zoom_mode)
        if motion_mode:
            modes.add(motion_mode)
    elif isinstance(mode, str):
        modes = {mode}
    else:
        modes = set(mode or ())

    logger.info(f"Creating animated ImageClip for {image_path} with modes={modes}",
                extra={"task_id": task_id} if task_id else None)

    W, H = reel_size

    # Base image -> video
    clip = ImageClip(image_path).with_duration(duration)

    # Safe fit by height, then clamp width if needed
    clip = clip.resized(height=H)
    if clip.w > W:
        clip = clip.resized(width=W)

    # Define zoom curves
    def zoom_in(t):   # 1.00 -> 1.30
        return 1.0 + 0.30 * (t / duration)

    def zoom_out(t):  # 1.20 -> 1.00
        return 1.20 - 0.20 * (t / duration)

    def zoom_pulse(t):  # gentle 1.10 ± 0.05
        return 1.10 + 0.05 * np.sin(2 * np.pi * t / duration)

    zoom_fn = None
    if "zoom_in" in modes:
        zoom_fn = zoom_in
    elif "zoom_out" in modes:
        zoom_fn = zoom_out
    elif "pulse" in modes:
        zoom_fn = zoom_pulse

    if zoom_fn:
        clip = clip.resized(zoom_fn)

    # Define motion curves (position)
    def pos_center(_t):
        return ('center', H / 2)

    def pos_drift_up(t):
        # Move up by drift_px over the clip, but limit to prevent going out of frame
        max_drift = min(drift_px, H * 0.15)  # Limit to 15% of frame height
        return ('center', H / 2 - max_drift * (t / duration))

    def pos_drift_down(t):
        # Move down by drift_px over the clip, but limit to prevent going out of frame
        max_drift = min(drift_px, H * 0.15)  # Limit to 15% of frame height
        return ('center', H / 2 + max_drift * (t / duration))

    def pos_oscillate(t):
        # Up/down oscillation ±osc_px
        return ('center', H / 2 + osc_px * np.sin(2 * np.pi * t / duration))

    pos_fn = pos_center
    if "drift_up" in modes:
        pos_fn = pos_drift_up
    elif "drift_down" in modes:
        pos_fn = pos_drift_down
    elif "oscillate" in modes:
        pos_fn = pos_oscillate

    clip = clip.with_position(pos_fn)

    # Background canvas + optional darken
    clip = clip.with_background_color(size=reel_size, color=background_color, pos='center')

    # Apply darkening effect if supported
    try:
        # Try different import paths for multiply_color effect
        try:
            from moviepy.video.fx.all import multiply_color as MultiplyColor
        except ImportError:
            try:
                from moviepy.video.fx import multiply_color as MultiplyColor
            except ImportError:
                # If multiply_color is not available, we'll skip the darkening effect
                MultiplyColor = None
        
        if darken_factor is not None and 0.0 < darken_factor < 1.0 and MultiplyColor is not None:
            clip = clip.with_effects([MultiplyColor(darken_factor)])
            logger.info(f"Applied darkening effect with factor {darken_factor}", 
                       extra={"task_id": task_id} if task_id else None)
        elif darken_factor is not None and 0.0 < darken_factor < 1.0:
            # Alternative darkening approach using color adjustment
            logger.info(f"Darkening effect not available, using alternative approach", 
                       extra={"task_id": task_id} if task_id else None)
            # We'll skip darkening for now since multiply_color is not available
            pass
    except Exception as e:
        # Fallback: skip darken if effect isn't available
        logger.warning(f"Darkening effect not available: {e}", 
                      extra={"task_id": task_id} if task_id else None)

    return clip

def validate_animation_mode(mode: Union[str, Tuple[str, ...], List[str]]) -> bool:
    """
    Validate that the animation mode(s) are supported.
    
    Args:
        mode: Animation mode(s) to validate
        
    Returns:
        True if valid, False otherwise
    """
    if mode is None:
        return True
    
    if isinstance(mode, str):
        modes = {mode}
    else:
        modes = set(mode)
    
    for m in modes:
        if m not in ALL_MODES:
            logger.error(f"Invalid animation mode: {m}. Valid modes: {ALL_MODES}")
            return False
    
    return True

def get_animation_preset(preset_name: str) -> Union[str, Tuple[str, ...]]:
    """
    Get predefined animation presets.
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Animation mode(s) for the preset
        
    Available presets:
        - "subtle": Gentle zoom with slight motion
        - "dynamic": Strong zoom with oscillation
        - "smooth": Smooth drift motion
        - "energetic": Pulse with oscillation
    """
    presets = {
        "subtle": ("zoom_in", "drift_up"),
        "dynamic": ("zoom_out", "oscillate"),
        "smooth": ("pulse",),  # Changed to gentle pulse for smooth animation
        "gentle_drift": ("drift_down",),  # New preset for gentle drift motion
        "energetic": ("pulse", "oscillate"),
        "zoom_only": ("zoom_in",),
        "motion_only": ("oscillate",),
    }
    
    return presets.get(preset_name, None) 