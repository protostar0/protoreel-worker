"""
Captacity-based text overlay utilities for ProtoReel Worker.
Uses the robust text rendering from Captacity for high-quality text overlays.
"""

import os
import tempfile
from typing import Optional, Tuple, List
from moviepy import CompositeVideoClip
from video_generator.logging_utils import get_logger

logger = get_logger()

# Import Captacity text utilities
try:
    from captacity.text_drawer import create_text_ex, str_to_charlist
    CAPTACITY_AVAILABLE = True
except ImportError:
    CAPTACITY_AVAILABLE = False
    logger.warning("Captacity text drawer not available, falling back to basic text overlay")

# Available text positions
TEXT_POSITIONS = ["top", "top-left", "top-right", "center", "bottom", "bottom-left", "bottom-right"]

def create_captacity_text_overlay(
    text: str,
    video_size: Tuple[int, int],
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,
    duration: float = 5.0,
    padding: int = 20,
    opacity: float = 1.0,
    task_id: Optional[str] = None
):
    """
    Create a text overlay using Captacity's advanced text rendering.
    
    Args:
        text: Text content to display
        video_size: Size of the video (width, height)
        position: Position of the text
        font_size: Font size in pixels
        color: Text color
        stroke_color: Stroke/outline color
        stroke_width: Stroke width
        font: Font file path (optional)
        duration: Duration of the text overlay
        padding: Padding from edges
        opacity: Text opacity (0.0 to 1.0)
        task_id: Task ID for logging
        
    Returns:
        TextClip object positioned correctly
    """
    try:
        video_width, video_height = video_size
        
        if not CAPTACITY_AVAILABLE:
            logger.warning("Captacity not available, using fallback text overlay", 
                          extra={"task_id": task_id} if task_id else None)
            return create_fallback_text_overlay(text, video_size, position, font_size, color, 
                                              stroke_color, stroke_width, font, duration, opacity, task_id)
        
        # Use Captacity's text rendering
        logger.info(f"Creating Captacity text overlay: '{text}'", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Determine font path with proper error handling
        try:
            font_path = get_font_path(font)
        except FileNotFoundError:
            logger.warning("No valid fonts found, using fallback text overlay", 
                          extra={"task_id": task_id} if task_id else None)
            return create_fallback_text_overlay(text, video_size, position, font_size, color, 
                                              stroke_color, stroke_width, font, duration, opacity, task_id)
        
        # Create text using Captacity
        # Ensure we have a valid font path
        if not font_path:
            # Use a default font that we know exists
            font_path = "./captacity/assets/fonts/Bangers-Regular.ttf"
            if not os.path.exists(font_path):
                # Fallback to basic text overlay if no fonts available
                logger.warning("No valid fonts found, using fallback text overlay", 
                              extra={"task_id": task_id} if task_id else None)
                return create_fallback_text_overlay(text, video_size, position, font_size, color, 
                                                  stroke_color, stroke_width, font, duration, opacity, task_id)
        
        text_clip = create_text_ex(
            text=text,
            font_size=font_size,
            color=color,
            font=font_path,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            position="center",  # Captacity handles positioning internally
            opacity=opacity
        )
        
        # Set duration
        text_clip = text_clip.with_duration(duration)
        
        # Calculate position with padding
        text_width, text_height = text_clip.size
        
        if position == "top":
            x, y = (video_width - text_width) // 2, padding
        elif position == "top-left":
            x, y = padding, padding
        elif position == "top-right":
            x, y = video_width - text_width - padding, padding
        elif position == "center":
            x, y = (video_width - text_width) // 2, (video_height - text_height) // 2
        elif position == "bottom":
            x, y = (video_width - text_width) // 2, video_height - text_height - padding
        elif position == "bottom-left":
            x, y = padding, video_height - text_height - padding
        elif position == "bottom-right":
            x, y = video_width - text_width - padding, video_height - text_height - padding
        else:
            # Default to center
            x, y = (video_width - text_width) // 2, (video_height - text_height) // 2
            logger.warning(f"Invalid text position '{position}', defaulting to center", 
                          extra={"task_id": task_id} if task_id else None)
        
        # Position the text clip
        positioned_clip = text_clip.with_position((x, y))
        
        logger.info(f"Created Captacity text overlay: '{text}' at position {position}", 
                   extra={"task_id": task_id} if task_id else None)
        
        return positioned_clip
        
    except Exception as e:
        logger.error(f"Failed to create Captacity text overlay: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        # Fallback to basic text overlay
        return create_fallback_text_overlay(text, video_size, position, font_size, color, 
                                          stroke_color, stroke_width, font, duration, opacity, task_id)

def create_fallback_text_overlay(
    text: str,
    video_size: Tuple[int, int],
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,
    duration: float = 5.0,
    opacity: float = 1.0,
    task_id: Optional[str] = None
):
    """
    Fallback text overlay using basic MoviePy TextClip.
    """
    try:
        from moviepy import TextClip
        
        video_width, video_height = video_size
        
        logger.info(f"Creating fallback text overlay: '{text}'", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Create basic text clip
        text_clip = TextClip(
            text=text,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method="caption",
            size=(video_width - 40, None)
        ).with_duration(duration)
        
        # Apply opacity if not 1.0
        if opacity < 1.0:
            text_clip = text_clip.with_opacity(opacity)
        
        # Calculate position
        text_width, text_height = text_clip.size
        
        if position == "top":
            x, y = (video_width - text_width) // 2, 20
        elif position == "top-left":
            x, y = 20, 20
        elif position == "top-right":
            x, y = video_width - text_width - 20, 20
        elif position == "center":
            x, y = (video_width - text_width) // 2, (video_height - text_height) // 2
        elif position == "bottom":
            x, y = (video_width - text_width) // 2, video_height - text_height - 20
        elif position == "bottom-left":
            x, y = 20, video_height - text_height - 20
        elif position == "bottom-right":
            x, y = video_width - text_width - 20, video_height - text_height - 20
        else:
            x, y = (video_width - text_width) // 2, (video_height - text_height) // 2
        
        # Position the text clip
        positioned_clip = text_clip.with_position((x, y))
        
        return positioned_clip
        
    except Exception as e:
        logger.error(f"Failed to create fallback text overlay: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        raise

def get_font_path(font: str = None) -> str:
    """
    Get the font path, with fallbacks to available fonts.
    Always returns a valid font path or raises an exception.
    """
    if font and os.path.exists(font):
        return font
    
    # Try to find available fonts
    font_candidates = [
        # "./video_generator/font/Montserrat-Black.ttf",
        "./captacity/assets/fonts/Bangers-Regular.ttf",
        "./captacity/assets/fonts/Knewave-Regular.ttf",
        "./captacity/assets/fonts/PoetsenOne-Regular.ttf"
    ]
    
    for font_path in font_candidates:
        if os.path.exists(font_path):
            return font_path
    
    # If no fonts found, raise an exception
    raise FileNotFoundError("No valid fonts found in the system")

def add_captacity_text_overlay_to_clip(
    video_clip,
    text: str,
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,
    padding: int = 20,
    opacity: float = 1.0,
    task_id: Optional[str] = None
):
    """
    Add a Captacity-based text overlay to a video clip.
    
    Args:
        video_clip: MoviePy video clip to add text to
        text: Text content to display
        position: Position of the text
        font_size: Font size in pixels
        color: Text color
        stroke_color: Stroke/outline color
        stroke_width: Stroke width
        font: Font file path (optional)
        padding: Padding from edges
        opacity: Text opacity (0.0 to 1.0)
        task_id: Task ID for logging
        
    Returns:
        Video clip with text overlay
    """
    try:
        # Create text overlay
        text_clip = create_captacity_text_overlay(
            text=text,
            video_size=video_clip.size,
            position=position,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            font=font,
            duration=video_clip.duration,
            padding=padding,
            opacity=opacity,
            task_id=task_id
        )
        
        # Composite text over video
        result_clip = CompositeVideoClip([video_clip, text_clip])
        
        logger.info(f"Added Captacity text overlay to video clip: '{text}'", 
                   extra={"task_id": task_id} if task_id else None)
        
        return result_clip
        
    except Exception as e:
        logger.error(f"Failed to add Captacity text overlay to clip: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        raise

def validate_text_position(position: str) -> bool:
    """
    Validate that the text position is supported.
    """
    if position not in TEXT_POSITIONS:
        logger.error(f"Invalid text position: {position}. Valid positions: {TEXT_POSITIONS}")
        return False
    return True

def get_text_preset(preset_name: str) -> dict:
    """
    Get predefined text overlay presets optimized for Captacity.
    """
    presets = {
        "title": {
            "font_size": 100,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 3,
            "position": "center",
            "padding": 50
        },
        "subtitle": {
            "font_size": 48,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 2,
            "position": "bottom",
            "padding": 30
        },
        "caption": {
            "font_size": 24,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 1,
            "position": "bottom",
            "padding": 20
        },
        "callout": {
            "font_size": 36,
            "color": "yellow",
            "stroke_color": "black",
            "stroke_width": 2,
            "position": "center",
            "padding": 40
        },
        "watermark": {
            "font_size": 18,
            "color": "white",
            "stroke_color": "none",
            "stroke_width": 0,
            "position": "bottom-right",
            "padding": 15,
            "opacity": 0.3
        }
    }
    
    return presets.get(preset_name, presets["subtitle"]) 