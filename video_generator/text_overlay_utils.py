"""
Text overlay utilities for ProtoReel Worker.
Provides rich text overlay capabilities for videos.
"""
import os
import tempfile
from typing import Optional, Tuple, List
from moviepy import TextClip, CompositeVideoClip
from video_generator.logging_utils import get_logger

logger = get_logger()

# Available text positions
TEXT_POSITIONS = ["top", "top-left", "top-right", "center", "bottom", "bottom-left", "bottom-right"]

def create_text_overlay(
    text: str,
    video_size: Tuple[int, int],
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,  # Use None for default font
    duration: float = 5.0,
    task_id: Optional[str] = None
) -> TextClip:
    """
    Create a text overlay clip for a video.
    
    Args:
        text: Text content to display
        video_size: Size of the video (width, height)
        position: Position of the text ("top", "center", "bottom", etc.)
        font_size: Font size in pixels
        color: Text color
        stroke_color: Stroke/outline color
        stroke_width: Stroke width
        font: Font family name
        duration: Duration of the text overlay
        task_id: Task ID for logging
        
    Returns:
        TextClip object positioned correctly
    """
    try:
        video_width, video_height = video_size
        
        # Create text clip with proper font handling
        try:
            # Try to use the specified font, fallback to default if not available
            font_path = font if os.path.exists(font) else None
            
            text_clip = TextClip(
                text=text,
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                font=font_path,
                method="caption",
                size=(video_width - 40, None)  # Leave 20px margin on each side
            ).with_duration(duration)
        except Exception as e:
            # Fallback to basic TextClip without font specification
            logger.warning(f"Failed to create TextClip with font '{font}': {e}, using default font", 
                          extra={"task_id": task_id} if task_id else None)
            text_clip = TextClip(
                text=text,
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                method="caption",
                size=(video_width - 40, None)
            ).with_duration(duration)
        
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
            # Default to center
            x, y = (video_width - text_width) // 2, (video_height - text_height) // 2
            logger.warning(f"Invalid text position '{position}', defaulting to center", 
                          extra={"task_id": task_id} if task_id else None)
        
        # Position the text clip
        positioned_clip = text_clip.with_position((x, y))
        
        logger.info(f"Created text overlay: '{text}' at position {position}", 
                   extra={"task_id": task_id} if task_id else None)
        
        return positioned_clip
        
    except Exception as e:
        logger.error(f"Failed to create text overlay: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        raise

def add_text_overlay_to_clip(
    video_clip,
    text: str,
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,  # Use None for default font
    task_id: Optional[str] = None
):
    """
    Add a text overlay to a video clip.
    
    Args:
        video_clip: MoviePy video clip to add text to
        text: Text content to display
        position: Position of the text
        font_size: Font size in pixels
        color: Text color
        stroke_color: Stroke/outline color
        stroke_width: Stroke width
        font: Font family name
        task_id: Task ID for logging
        
    Returns:
        Video clip with text overlay
    """
    try:
        # Create text overlay
        text_clip = create_text_overlay(
            text=text,
            video_size=video_clip.size,
            position=position,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            font=font,
            duration=video_clip.duration,
            task_id=task_id
        )
        
        # Composite text over video
        result_clip = CompositeVideoClip([video_clip, text_clip])
        
        logger.info(f"Added text overlay to video clip: '{text}'", 
                   extra={"task_id": task_id} if task_id else None)
        
        return result_clip
        
    except Exception as e:
        logger.error(f"Failed to add text overlay to clip: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        raise

def create_animated_text_overlay(
    text: str,
    video_size: Tuple[int, int],
    position: str = "center",
    font_size: int = 36,
    color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 2,
    font: str = None,  # Use None for default font
    duration: float = 5.0,
    animation_type: str = "fade_in",
    task_id: Optional[str] = None
) -> TextClip:
    """
    Create an animated text overlay with fade-in/fade-out effects.
    
    Args:
        text: Text content to display
        video_size: Size of the video (width, height)
        position: Position of the text
        font_size: Font size in pixels
        color: Text color
        stroke_color: Stroke/outline color
        stroke_width: Stroke width
        font: Font family name
        duration: Duration of the text overlay
        animation_type: Type of animation ("fade_in", "fade_out", "fade_in_out", "none")
        task_id: Task ID for logging
        
    Returns:
        Animated TextClip object
    """
    try:
        # Create base text clip
        text_clip = create_text_overlay(
            text=text,
            video_size=video_size,
            position=position,
            font_size=font_size,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            font=font,
            duration=duration,
            task_id=task_id
        )
        
        # Apply animation effects
        if animation_type == "fade_in":
            # Fade in over first 0.5 seconds
            text_clip = text_clip.with_effects([
                lambda clip: clip.with_opacity(lambda t: min(1.0, t / 0.5) if t < 0.5 else 1.0)
            ])
        elif animation_type == "fade_out":
            # Fade out over last 0.5 seconds
            text_clip = text_clip.with_effects([
                lambda clip: clip.with_opacity(lambda t: 1.0 if t < duration - 0.5 else max(0.0, (duration - t) / 0.5))
            ])
        elif animation_type == "fade_in_out":
            # Fade in over first 0.5s, fade out over last 0.5s
            text_clip = text_clip.with_effects([
                lambda clip: clip.with_opacity(lambda t: min(1.0, t / 0.5) if t < 0.5 else (1.0 if t < duration - 0.5 else max(0.0, (duration - t) / 0.5)))
            ])
        elif animation_type == "none":
            # No animation
            pass
        else:
            logger.warning(f"Unknown animation type '{animation_type}', using no animation", 
                          extra={"task_id": task_id} if task_id else None)
        
        logger.info(f"Created animated text overlay: '{text}' with {animation_type} animation", 
                   extra={"task_id": task_id} if task_id else None)
        
        return text_clip
        
    except Exception as e:
        logger.error(f"Failed to create animated text overlay: {e}", 
                    extra={"task_id": task_id} if task_id else None)
        raise

def validate_text_position(position: str) -> bool:
    """
    Validate that the text position is supported.
    
    Args:
        position: Text position to validate
        
    Returns:
        True if valid, False otherwise
    """
    if position not in TEXT_POSITIONS:
        logger.error(f"Invalid text position: {position}. Valid positions: {TEXT_POSITIONS}")
        return False
    return True

def get_text_preset(preset_name: str) -> dict:
    """
    Get predefined text overlay presets.
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Dictionary with text overlay configuration
        
    Available presets:
        - "title": Large title text
        - "subtitle": Medium subtitle text
        - "caption": Small caption text
        - "callout": Highlighted callout text
        - "watermark": Subtle watermark text
    """
    presets = {
        "title": {
            "font_size": 100,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 3,
            "position": "center"
        },
        "subtitle": {
            "font_size": 48,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 2,
            "position": "bottom"
        },
        "caption": {
            "font_size": 24,
            "color": "white",
            "stroke_color": "black",
            "stroke_width": 1,
            "position": "bottom"
        },
        "callout": {
            "font_size": 36,
            "color": "yellow",
            "stroke_color": "black",
            "stroke_width": 2,
            "position": "center"
        },
        "watermark": {
            "font_size": 18,
            "color": "rgba(255,255,255,0.3)",
            "stroke_color": "none",
            "stroke_width": 0,
            "position": "bottom-right"
        }
    }
    
    return presets.get(preset_name, presets["subtitle"]) 