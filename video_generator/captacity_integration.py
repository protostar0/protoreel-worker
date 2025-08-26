#!/usr/bin/env python3
"""
Captacity integration for ProtoReel worker.
Replaces the current Whisper-based subtitle generation with Captacity.
"""

import os
import tempfile
import logging
from typing import List, Optional
from pathlib import Path
from video_generator.logging_utils import get_logger

logger = get_logger()

def generate_captacity_subtitles(
    video_path: str, 
    audio_path: str,
    output_path: str,
    font: str = "Bangers-Regular.ttf",
    font_size: int = 100,
    font_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 4,
    position: str = "bottom",
    task_id: Optional[str] = None,
    word_highlight_color: str = "red",
    line_count: int = 2,
    highlight_current_word: bool = True,
    padding: int = 50,

) -> str:
    """
    Generate subtitles using Captacity for a video with audio.
    
    Args:
        video_path: Path to the input video file
        audio_path: Path to the audio file for transcription
        output_path: Path where the video with subtitles will be saved
        font_size: Font size for subtitles
        font_color: Color of the subtitle text
        stroke_color: Color of the text stroke/outline
        stroke_width: Width of the text stroke
        position: Position of subtitles ("bottom", "center", "top")
        padding: Padding from the edge of the video
        task_id: Task ID for logging
        
    Returns:
        Path to the output video file with subtitles
        
    Raises:
        RuntimeError: If subtitle generation fails
    """
    try:
        logger.info(f"Generating subtitles using Captacity for video: {video_path}", extra={"task_id": task_id})
        
        # Import Captacity functions
        from captacity import add_captions
        
        # Create temporary output path if none provided
        if not output_path:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"captacity_output_{os.path.basename(video_path)}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Generate subtitles using Captacity
        logger.info(f"Starting Captacity subtitle generation...", extra={"task_id": task_id})
        
        # Call Captacity's add_captions function
        add_captions(
            video_file=video_path,
            output_file=output_path,
            font=font,
            word_highlight_color=word_highlight_color,
            line_count=line_count,
            font_size=font_size,
            font_color=font_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            position=position,
            print_info=True,
            highlight_current_word=highlight_current_word,
            padding=padding
        )
        
        # Verify the output file was created
        if not os.path.exists(output_path):
            raise RuntimeError(f"Captacity output file not found: {output_path}")
        
        file_size = os.path.getsize(output_path)
        logger.info(f"Subtitles generated successfully: {output_path} ({file_size} bytes)", extra={"task_id": task_id})
        
        return output_path
        
    except ImportError as e:
        logger.error(f"Failed to import Captacity: {e}", extra={"task_id": task_id})
        raise RuntimeError(f"Captacity not available: {e}")
    except Exception as e:
        logger.error(f"Captacity subtitle generation failed: {e}", extra={"task_id": task_id})
        raise RuntimeError(f"Subtitle generation failed: {e}")


def generate_captacity_subtitles_for_scene(
    video_clip,
    audio_path: str,
    font: str = "Bangers-Regular.ttf",
    font_size: int = 100,
    font_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 4,
    highlight_current_word: bool = True,
    word_highlight_color: str = "red",
    line_count: int = 2,
    position: str = "bottom",
    padding: int = 50,
    task_id: Optional[str] = None
) -> str:
    """
    Generate subtitles for a scene using Captacity.
    
    Args:
        video_clip: MoviePy video clip object
        audio_path: Path to the audio file for transcription
        font: Font file name to use for subtitles
        font_size: Font size for subtitles
        font_color: Color of the subtitle text
        stroke_color: Color of the text stroke/outline
        stroke_width: Width of the text stroke
        highlight_current_word: Whether to highlight the current word
        word_highlight_color: Color for word highlighting
        line_count: Maximum number of lines for subtitles
        position: Position of subtitles ("bottom", "center", "top")
        padding: Padding from the edge of the video
        task_id: Task ID for logging
        
    Returns:
        Path to the video file with subtitles
    """
    try:
        logger.info(f"Generating Captacity subtitles for scene", extra={"task_id": task_id})
        
        # Save the video clip to a temporary file
        temp_video_path = os.path.join(tempfile.gettempdir(), f"temp_scene_{task_id or 'unknown'}.mp4")
        
        logger.info(f"Saving temporary video for subtitle processing: {temp_video_path}", extra={"task_id": task_id})
        
        # Write video to temporary file
        video_clip.write_videofile(
            temp_video_path,
            fps=video_clip.fps or 24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=f"{temp_video_path}.temp_audio.m4a",
            remove_temp=True,
            logger=None
        )
        
        # Generate output path
        output_path = os.path.join(tempfile.gettempdir(), f"scene_with_subtitles_{task_id or 'unknown'}.mp4")
        
        # Generate subtitles using Captacity
        result_path = generate_captacity_subtitles(
            video_path=temp_video_path,
            audio_path=audio_path,
            output_path=output_path,
            font=font,
            font_size=font_size,
            font_color=font_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            highlight_current_word=highlight_current_word,
            word_highlight_color=word_highlight_color,
            line_count=line_count,
            position=position,
            padding=padding,
            task_id=task_id
        )
        
        # Clean up temporary video file
        try:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
                logger.info(f"Cleaned up temporary video file: {temp_video_path}", extra={"task_id": task_id})
        except Exception as e:
            logger.warning(f"Failed to clean up temporary video file: {e}", extra={"task_id": task_id})
        
        return result_path
        
    except Exception as e:
        logger.error(f"Failed to generate Captacity subtitles for scene: {e}", extra={"task_id": task_id})
        raise


def create_captacity_subtitle_clips(
    video_clip,
    audio_path: str,
    font: str = "Bangers-Regular.ttf",
    font_size: int = 100,
    font_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 4,
    position: str = "bottom",
    word_highlight_color: str = "red",
    line_count: int = 2,
    task_id: Optional[str] = None
) -> List:
    """
    Create subtitle clips using Captacity that can be composited with the video.
    This function maintains compatibility with the existing subtitle system.
    
    Args:
        video_clip: MoviePy video clip object
        audio_path: Path to the audio file for transcription
        font_size: Font size for subtitles
        font_color: Color of the subtitle text
        stroke_color: Color of the text stroke/outline
        stroke_width: Width of the text stroke
        position: Position of subtitles ("bottom", "center", "top")
        padding: Padding from the edge of the video
        task_id: Task ID for logging
        
    Returns:
        List of subtitle clips that can be composited with the video
    """
    try:
        logger.info(f"Creating Captacity subtitle clips for scene", extra={"task_id": task_id})
        
        # For now, we'll use the direct video generation approach
        # This maintains the same interface as the old system
        subtitle_video_path = generate_captacity_subtitles_for_scene(
            video_clip=video_clip,
            audio_path=audio_path,
            font=font,
            font_size=font_size,
            font_color=font_color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            position=position,
            task_id=task_id,
            word_highlight_color=word_highlight_color,
            line_count=line_count,
        )
        
        # Load the video with subtitles as a clip
        from moviepy import VideoFileClip
        subtitle_clip = VideoFileClip(subtitle_video_path)
        
        # Return as a list to maintain compatibility
        return [subtitle_clip]
        
    except Exception as e:
        logger.error(f"Failed to create Captacity subtitle clips: {e}", extra={"task_id": task_id})
        raise


def test_captacity_integration() -> bool:
    """
    Test if Captacity integration is working properly.
    
    Returns:
        True if integration works, False otherwise
    """
    try:
        # Try to import Captacity
        from captacity import add_captions
        logger.info("✅ Captacity integration test successful")
        return True
    except ImportError as e:
        logger.error(f"❌ Captacity integration test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Captacity integration test failed: {e}")
        return False


# Convenience function for backward compatibility
def generate_captacity_subtitles_compatible(
    audio_path: str, 
    video_clip, 
    font: str = "Bangers-Regular.ttf",
    font_size: int = 130,
    font_color: str = "white",
    stroke_color: str = "black",
    stroke_width: int = 4,
    highlight_current_word: bool = True,
    word_highlight_color: str = "red",
    line_count: int = 2,
    position: str = "center",
    padding: int = 50
) -> List:
    """
    Compatible function that mimics the old generate_whisper_phrase_subtitles interface.
    
    Args:
        audio_path: Path to the audio file
        video_clip: MoviePy video clip object
        font: Font file name to use for subtitles
        font_size: Font size for subtitles
        font_color: Color of the subtitle text
        stroke_color: Color of the text stroke/outline
        stroke_width: Width of the text stroke
        highlight_current_word: Whether to highlight the current word
        word_highlight_color: Color for word highlighting
        line_count: Maximum number of lines for subtitles
        position: Position of subtitles ("bottom", "center", "top")
        padding: Padding from the edge of the video
        
    Returns:
        List containing a single video clip with subtitles
    """
    try:
        # Generate subtitles using Captacity
        subtitle_video_path = generate_captacity_subtitles_for_scene(
            video_clip=video_clip,
            audio_path=audio_path,
            font=font,
            font_color=font_color,
            font_size=font_size,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            highlight_current_word=highlight_current_word,
            word_highlight_color=word_highlight_color,
            line_count=line_count,
            position=position,
            padding=padding,
            task_id=None
        )
        
        # Load the result as a clip
        from moviepy import VideoFileClip
        subtitle_clip = VideoFileClip(subtitle_video_path)
        
        return [subtitle_clip]
        
    except Exception as e:
        logger.error(f"Captacity subtitle generation failed: {e}")
        # Return empty list to maintain compatibility
        return [] 