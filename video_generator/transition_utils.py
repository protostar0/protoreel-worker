"""
Transition utilities for ProtoReel Worker.
Provides smooth transitions between video scenes.
"""
import numpy as np
from typing import List, Optional, Tuple
from moviepy import VideoFileClip, concatenate_videoclips
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from video_generator.logging_utils import get_logger

logger = get_logger()

# Available transition types
TRANSITION_TYPES = ["crossfade", "fade", "none"]

def apply_transition_to_clip(clip: VideoFileClip, transition_type: str = "crossfade", 
                           transition_duration: float = 1.0) -> VideoFileClip:
    """
    Apply a transition effect to a video clip.
    
    Args:
        clip: Video clip to apply transition to
        transition_type: Type of transition ("crossfade", "fade", "none")
        transition_duration: Duration of the transition in seconds
        
    Returns:
        Video clip with transition applied
    """
    if transition_type == "none" or transition_duration <= 0:
        return clip
    
    try:
        if transition_type == "crossfade":
            # Apply crossfade effect
            clip = clip.with_effects([CrossFadeIn(transition_duration)])
            logger.info(f"Applied crossfade transition with duration {transition_duration}s")
        elif transition_type == "fade":
            # Apply simple fade effect
            clip = clip.with_effects([CrossFadeIn(transition_duration)])
            logger.info(f"Applied fade transition with duration {transition_duration}s")
        else:
            logger.warning(f"Unknown transition type: {transition_type}, using no transition")
            return clip
            
    except Exception as e:
        logger.warning(f"Failed to apply transition {transition_type}: {e}, using no transition")
        return clip
    
    return clip

def concatenate_with_transitions(clips: List[VideoFileClip], 
                               transition_type: str = "crossfade",
                               transition_duration: float = 1.0,
                               task_id: Optional[str] = None) -> VideoFileClip:
    """
    Concatenate video clips with smooth transitions between them.
    
    Args:
        clips: List of video clips to concatenate
        transition_type: Type of transition to use between clips
        transition_duration: Duration of each transition in seconds
        task_id: Task ID for logging
        
    Returns:
        Concatenated video clip with transitions
    """
    if not clips:
        raise ValueError("No clips provided for concatenation")
    
    if len(clips) == 1:
        logger.info("Single clip, no transitions needed", extra={"task_id": task_id})
        return clips[0]
    
    logger.info(f"Concatenating {len(clips)} clips with {transition_type} transitions", 
               extra={"task_id": task_id})
    
    try:
        if transition_type == "none" or transition_duration <= 0:
            # No transitions, use simple concatenation
            final_clip = concatenate_videoclips(clips, method="compose")
            logger.info("Concatenated clips without transitions", extra={"task_id": task_id})
            return final_clip
        
        # Apply transitions to clips
        transitioned_clips = []
        for i, clip in enumerate(clips):
            if i == 0:
                # First clip gets fade-in effect
                transitioned_clip = apply_transition_to_clip(clip, "fade", transition_duration)
            elif i == len(clips) - 1:
                # Last clip gets fade-out effect
                transitioned_clip = apply_transition_to_clip(clip, "fade", transition_duration)
            else:
                # Middle clips get crossfade effects
                transitioned_clip = apply_transition_to_clip(clip, "crossfade", transition_duration)
            
            transitioned_clips.append(transitioned_clip)
        
        # Concatenate with transitions
        final_clip = concatenate_videoclips(transitioned_clips, method="compose")
        logger.info(f"Successfully concatenated {len(clips)} clips with {transition_type} transitions", 
                   extra={"task_id": task_id})
        
        return final_clip
        
    except Exception as e:
        logger.error(f"Failed to concatenate with transitions: {e}", extra={"task_id": task_id})
        # Fallback to simple concatenation
        logger.info("Falling back to simple concatenation", extra={"task_id": task_id})
        return concatenate_videoclips(clips, method="compose")

def validate_transition_type(transition_type: str) -> bool:
    """
    Validate that the transition type is supported.
    
    Args:
        transition_type: Transition type to validate
        
    Returns:
        True if valid, False otherwise
    """
    if transition_type not in TRANSITION_TYPES:
        logger.error(f"Invalid transition type: {transition_type}. Valid types: {TRANSITION_TYPES}")
        return False
    return True

def get_transition_preset(preset_name: str) -> Tuple[str, float]:
    """
    Get predefined transition presets.
    
    Args:
        preset_name: Name of the preset
        
    Returns:
        Tuple of (transition_type, transition_duration)
        
    Available presets:
        - "smooth": Gentle crossfade with 1.5s duration
        - "quick": Fast crossfade with 0.5s duration
        - "dramatic": Long crossfade with 2.0s duration
        - "none": No transitions
    """
    presets = {
        "smooth": ("crossfade", 1.5),
        "quick": ("crossfade", 0.5),
        "dramatic": ("crossfade", 2.0),
        "none": ("none", 0.0),
    }
    
    return presets.get(preset_name, ("crossfade", 1.0)) 