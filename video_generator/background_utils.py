"""
Video background utilities for ProtoReel Worker.
Provides functions to create blurred backgrounds from video content.
"""
import os
import tempfile
import numpy as np
from typing import Tuple, Optional
from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageFilter
from video_generator.logging_utils import get_logger

logger = get_logger()

def create_blurred_background_from_video(
    video_clip: VideoFileClip,
    target_size: Tuple[int, int],
    blur_radius: int = 20,
    opacity: float = 0.3,
    task_id: Optional[str] = None
) -> ImageClip:
    """
    Create a blurred background from a video clip.
    
    Args:
        video_clip: Source video clip
        target_size: Target size as (width, height)
        blur_radius: Blur radius for the background (higher = more blur)
        opacity: Opacity of the background (0.0 to 1.0)
        task_id: Task ID for logging
        
    Returns:
        ImageClip with blurred background
    """
    try:
        logger.info(f"Creating blurred background from video (blur_radius={blur_radius}, opacity={opacity})", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Get a frame from the middle of the video
        mid_time = video_clip.duration / 2
        frame = video_clip.get_frame(mid_time)
        
        # Convert numpy array to PIL Image
        pil_image = Image.fromarray(frame.astype('uint8'))
        
        # Resize to target size
        pil_image = pil_image.resize(target_size, Image.Resampling.LANCZOS)
        
        # Apply blur effect
        blurred_image = pil_image.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
        # Apply opacity if needed
        if opacity < 1.0:
            # Convert to RGBA if not already
            if blurred_image.mode != 'RGBA':
                blurred_image = blurred_image.convert('RGBA')
            
            # Apply opacity
            alpha = blurred_image.split()[3]
            alpha = alpha.point(lambda x: int(x * opacity))
            blurred_image.putalpha(alpha)
        
        # Save to temporary file
        temp_path = os.path.join(tempfile.gettempdir(), f"blurred_bg_{os.getpid()}_{id(video_clip)}.png")
        blurred_image.save(temp_path)
        
        # Create ImageClip from the blurred background
        background_clip = ImageClip(temp_path).with_duration(video_clip.duration)
        
        logger.info(f"Blurred background created: {temp_path}", 
                   extra={"task_id": task_id} if task_id else None)
        
        return background_clip
        
    except Exception as e:
        logger.error(f"Failed to create blurred background: {e}", exc_info=True, 
                    extra={"task_id": task_id} if task_id else None)
        raise

def composite_video_with_blurred_background(
    video_clip: VideoFileClip,
    target_size: Tuple[int, int],
    blur_radius: int = 20,
    background_opacity: float = 0.3,
    task_id: Optional[str] = None
) -> VideoFileClip:
    """
    Composite a video clip with a blurred background when the video is smaller than target size.
    First tries to fill the entire frame, then uses blurred background if needed.
    
    Args:
        video_clip: Source video clip
        target_size: Target size as (width, height)
        blur_radius: Blur radius for the background
        background_opacity: Opacity of the background
        task_id: Task ID for logging
        
    Returns:
        CompositeVideoClip with blurred background
    """
    try:
        logger.info(f"Processing video: original size {video_clip.w}x{video_clip.h}, target size {target_size[0]}x{target_size[1]}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Validate input dimensions
        if video_clip.w <= 0 or video_clip.h <= 0:
            logger.error(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}")
        
        if target_size[0] <= 0 or target_size[1] <= 0:
            logger.error(f"Invalid target dimensions: {target_size[0]}x{target_size[1]}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid target dimensions: {target_size[0]}x{target_size[1]}")
        
        # First, try to resize video to fill the entire target size
        # Calculate scale factors for both width and height
        scale_w = target_size[0] / video_clip.w
        scale_h = target_size[1] / video_clip.h
        
        # Use the larger scale to fill the entire frame (may crop some content)
        fill_scale = max(scale_w, scale_h)
        
        # Resize video to fill the entire target size
        fill_w = int(video_clip.w * fill_scale)
        fill_h = int(video_clip.h * fill_scale)
        
        # Validate fill dimensions
        if fill_w <= 0 or fill_h <= 0:
            logger.error(f"Invalid fill dimensions: {fill_w}x{fill_h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid fill dimensions: {fill_w}x{fill_h}")
        
        logger.info(f"Filling frame: scaling by {fill_scale:.2f} to {fill_w}x{fill_h}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Resize video to fill the frame
        resized_video = video_clip.resized((fill_w, fill_h))
        
        # Validate resized video dimensions
        if resized_video.w <= 0 or resized_video.h <= 0:
            logger.error(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}")
        
        # Center the video (this will crop excess if video is larger than target)
        x = (target_size[0] - fill_w) // 2
        y = (target_size[1] - fill_h) // 2
        resized_video = resized_video.with_position((x, y))
        
        # Check if video now fills the entire target size
        fills_completely = (fill_w >= target_size[0] and fill_h >= target_size[1])
        
        if fills_completely:
            logger.info("Video fills entire frame completely, no background needed", 
                       extra={"task_id": task_id} if task_id else None)
            
            # Calculate crop coordinates to center the video in target size
            # The resized video is larger than target, so we need to crop from center
            crop_x1 = max(0, (fill_w - target_size[0]) // 2)
            crop_y1 = max(0, (fill_h - target_size[1]) // 2)
            crop_x2 = crop_x1 + target_size[0]
            crop_y2 = crop_y1 + target_size[1]
            
            # Validate crop dimensions
            crop_width = crop_x2 - crop_x1
            crop_height = crop_y2 - crop_y1
            
            if crop_width <= 0 or crop_height <= 0:
                logger.error(f"Invalid crop dimensions: {crop_width}x{crop_height}", 
                           extra={"task_id": task_id} if task_id else None)
                raise ValueError(f"Invalid crop dimensions: {crop_width}x{crop_height}")
            
            logger.info(f"Cropping video to: x1={crop_x1}, y1={crop_y1}, x2={crop_x2}, y2={crop_y2} ({crop_width}x{crop_height})", 
                       extra={"task_id": task_id} if task_id else None)
            
            # Crop to exact target size
            try:
                result_clip = resized_video.cropped(x1=crop_x1, y1=crop_y1, x2=crop_x2, y2=crop_y2)
                
                # Validate the cropped clip dimensions
                if result_clip.w <= 0 or result_clip.h <= 0:
                    logger.error(f"Cropped clip has invalid dimensions: {result_clip.w}x{result_clip.h}", 
                               extra={"task_id": task_id} if task_id else None)
                    raise ValueError(f"Cropped clip has invalid dimensions: {result_clip.w}x{result_clip.h}")
                
                # Ensure the clip has proper size
                if result_clip.w != target_size[0] or result_clip.h != target_size[1]:
                    logger.warning(f"Cropped clip size mismatch: {result_clip.w}x{result_clip.h} != {target_size[0]}x{target_size[1]}", 
                                 extra={"task_id": task_id} if task_id else None)
                    # Force resize to exact target size
                    result_clip = result_clip.resized(target_size)
                
                return result_clip
            except Exception as crop_error:
                logger.warning(f"Cropping failed: {crop_error}, falling back to resize", 
                             extra={"task_id": task_id} if task_id else None)
                # Fallback: just resize to target size
                return video_clip.resized(target_size)
        
        # If video doesn't fill completely, use blurred background
        logger.info(f"Video doesn't fill completely ({fill_w}x{fill_h} < {target_size[0]}x{target_size[1]}), adding blurred background", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Create blurred background
        background_clip = create_blurred_background_from_video(
            video_clip, target_size, blur_radius, background_opacity, task_id
        )
        
        # Validate background clip dimensions
        if background_clip.w <= 0 or background_clip.h <= 0:
            logger.error(f"Background clip has invalid dimensions: {background_clip.w}x{background_clip.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Background clip has invalid dimensions: {background_clip.w}x{background_clip.h}")
        
        # Composite background and video
        try:
            composite_clip = CompositeVideoClip([background_clip, resized_video])
            
            # Validate composite clip dimensions
            if composite_clip.w <= 0 or composite_clip.h <= 0:
                logger.error(f"Composite clip has invalid dimensions: {composite_clip.w}x{composite_clip.h}", 
                           extra={"task_id": task_id} if task_id else None)
                raise ValueError(f"Composite clip has invalid dimensions: {composite_clip.w}x{composite_clip.h}")
            
            # Ensure composite clip has proper size
            if composite_clip.w != target_size[0] or composite_clip.h != target_size[1]:
                logger.warning(f"Composite clip size mismatch: {composite_clip.w}x{composite_clip.h} != {target_size[0]}x{target_size[1]}", 
                             extra={"task_id": task_id} if task_id else None)
                # Force resize to exact target size
                composite_clip = composite_clip.resized(target_size)
            
            logger.info(f"Video composited with blurred background: {fill_w}x{fill_h} at position ({x}, {y})", 
                       extra={"task_id": task_id} if task_id else None)
            
            return composite_clip
            
        except Exception as composite_error:
            logger.warning(f"CompositeVideoClip failed: {composite_error}, falling back to simple resize", 
                         extra={"task_id": task_id} if task_id else None)
            # Fallback: just resize to target size
            return video_clip.resized(target_size)
        
    except Exception as e:
        logger.error(f"Failed to composite video with blurred background: {e}", exc_info=True, 
                    extra={"task_id": task_id} if task_id else None)
        raise

def composite_video_with_blurred_background_safe(
    video_clip: VideoFileClip,
    target_size: Tuple[int, int],
    blur_radius: int = 20,
    background_opacity: float = 0.3,
    max_zoom_factor: float = 2.5,  # Maximum zoom factor before using blurred background
    task_id: Optional[str] = None
) -> VideoFileClip:
    """
    Safe version of video compositing that avoids mask issues.
    Uses a more conservative approach to prevent broadcasting errors.
    
    Args:
        video_clip: Source video clip
        target_size: Target size as (width, height)
        blur_radius: Blur radius for the background
        background_opacity: Opacity of the background
        task_id: Task ID for logging
        
    Returns:
        VideoFileClip with proper dimensions
    """
    try:
        logger.info(f"Safe processing video: original size {video_clip.w}x{video_clip.h}, target size {target_size[0]}x{target_size[1]}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Validate input dimensions
        if video_clip.w <= 0 or video_clip.h <= 0:
            logger.error(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid video dimensions: {video_clip.w}x{video_clip.h}")
        
        if target_size[0] <= 0 or target_size[1] <= 0:
            logger.error(f"Invalid target dimensions: {target_size[0]}x{target_size[1]}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid target dimensions: {target_size[0]}x{target_size[1]}")
        
        # Simple approach: just resize to fill the target size
        # Calculate scale factors
        scale_w = target_size[0] / video_clip.w
        scale_h = target_size[1] / video_clip.h
        
        # Use the larger scale to fill the entire frame
        fill_scale = max(scale_w, scale_h)
        
        # Check if zoom factor is too high - use blurred background instead
        if fill_scale > max_zoom_factor:
            logger.info(f"Zoom factor {fill_scale:.2f} exceeds maximum {max_zoom_factor}, using blurred background instead", 
                       extra={"task_id": task_id} if task_id else None)
            
            # Use blurred background approach for very small videos
            return _create_blurred_background_video(
                video_clip, target_size, blur_radius, background_opacity, task_id
            )
        
        # Resize video to fill the entire target size
        fill_w = int(video_clip.w * fill_scale)
        fill_h = int(video_clip.h * fill_scale)
        
        # Validate fill dimensions
        if fill_w <= 0 or fill_h <= 0:
            logger.error(f"Invalid fill dimensions: {fill_w}x{fill_h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Invalid fill dimensions: {fill_w}x{fill_h}")
        
        logger.info(f"Safe filling frame: scaling by {fill_scale:.2f} to {fill_w}x{fill_h}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Resize video to fill the frame
        resized_video = video_clip.resized((fill_w, fill_h))
        
        # Validate resized video dimensions
        if resized_video.w <= 0 or resized_video.h <= 0:
            logger.error(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}")
        
        # Check if video fills the entire target size
        fills_completely = (fill_w >= target_size[0] and fill_h >= target_size[1])
        
        if fills_completely:
            logger.info("Video fills entire frame completely, cropping to target size", 
                       extra={"task_id": task_id} if task_id else None)
            
            # Calculate crop coordinates to center the video in target size
            crop_x1 = max(0, (fill_w - target_size[0]) // 2)
            crop_y1 = max(0, (fill_h - target_size[1]) // 2)
            crop_x2 = crop_x1 + target_size[0]
            crop_y2 = crop_y1 + target_size[1]
            
            # Validate crop dimensions
            crop_width = crop_x2 - crop_x1
            crop_height = crop_y2 - crop_y1
            
            if crop_width <= 0 or crop_height <= 0:
                logger.error(f"Invalid crop dimensions: {crop_width}x{crop_height}", 
                           extra={"task_id": task_id} if task_id else None)
                raise ValueError(f"Invalid crop dimensions: {crop_width}x{crop_height}")
            
            logger.info(f"Safe cropping video to: x1={crop_x1}, y1={crop_y1}, x2={crop_x2}, y2={crop_y2} ({crop_width}x{crop_height})", 
                       extra={"task_id": task_id} if task_id else None)
            
            # Crop to exact target size
            try:
                result_clip = resized_video.cropped(x1=crop_x1, y1=crop_y1, x2=crop_x2, y2=crop_y2)
                
                # Validate the cropped clip dimensions
                if result_clip.w <= 0 or result_clip.h <= 0:
                    logger.error(f"Cropped clip has invalid dimensions: {result_clip.w}x{result_clip.h}", 
                               extra={"task_id": task_id} if task_id else None)
                    raise ValueError(f"Cropped clip has invalid dimensions: {result_clip.w}x{result_clip.h}")
                
                # Ensure the clip has proper size
                if result_clip.w != target_size[0] or result_clip.h != target_size[1]:
                    logger.warning(f"Cropped clip size mismatch: {result_clip.w}x{result_clip.h} != {target_size[0]}x{target_size[1]}", 
                                 extra={"task_id": task_id} if task_id else None)
                    # Force resize to exact target size
                    result_clip = result_clip.resized(target_size)
                
                return result_clip
            except Exception as crop_error:
                logger.warning(f"Safe cropping failed: {crop_error}, falling back to resize", 
                             extra={"task_id": task_id} if task_id else None)
                # Fallback: just resize to target size
                return video_clip.resized(target_size)
        else:
            logger.info("Video doesn't fill completely, using simple resize", 
                       extra={"task_id": task_id} if task_id else None)
            # Just resize to target size
            return video_clip.resized(target_size)
        
    except Exception as e:
        logger.error(f"Safe video processing failed: {e}", exc_info=True, 
                    extra={"task_id": task_id} if task_id else None)
        raise

def _create_blurred_background_video(
    video_clip: VideoFileClip,
    target_size: Tuple[int, int],
    blur_radius: int = 20,
    background_opacity: float = 0.3,
    task_id: Optional[str] = None
) -> VideoFileClip:
    """
    Create a video with blurred background for very small videos.
    This avoids excessive zooming by using a blurred background.
    
    Args:
        video_clip: Source video clip
        target_size: Target size as (width, height)
        blur_radius: Blur radius for the background
        background_opacity: Opacity of the background
        task_id: Task ID for logging
        
    Returns:
        VideoFileClip with blurred background
    """
    try:
        logger.info(f"Creating blurred background video for small source: {video_clip.w}x{video_clip.h}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Create blurred background
        background_clip = create_blurred_background_from_video(
            video_clip, target_size, blur_radius, background_opacity, task_id
        )
        
        # Resize video to reasonable size (not too small, not too big)
        # Use a moderate scale that maintains quality
        moderate_scale = min(target_size[0] / video_clip.w, target_size[1] / video_clip.h) * 0.7  # 70% of available space
        
        moderate_w = int(video_clip.w * moderate_scale)
        moderate_h = int(video_clip.h * moderate_scale)
        
        # Ensure minimum size
        moderate_w = max(moderate_w, 200)
        moderate_h = max(moderate_h, 200)
        
        logger.info(f"Resizing video to moderate size: {moderate_w}x{moderate_h}", 
                   extra={"task_id": task_id} if task_id else None)
        
        # Resize video to moderate size
        resized_video = video_clip.resized((moderate_w, moderate_h))
        
        # Center the video
        x = (target_size[0] - moderate_w) // 2
        y = (target_size[1] - moderate_h) // 2
        resized_video = resized_video.with_position((x, y))
        
        # Validate dimensions
        if resized_video.w <= 0 or resized_video.h <= 0:
            logger.error(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}", 
                       extra={"task_id": task_id} if task_id else None)
            raise ValueError(f"Resized video has invalid dimensions: {resized_video.w}x{resized_video.h}")
        
        # Composite background and video
        try:
            composite_clip = CompositeVideoClip([background_clip, resized_video])
            
            # Validate composite clip dimensions
            if composite_clip.w <= 0 or composite_clip.h <= 0:
                logger.error(f"Composite clip has invalid dimensions: {composite_clip.w}x{composite_clip.h}", 
                           extra={"task_id": task_id} if task_id else None)
                raise ValueError(f"Composite clip has invalid dimensions: {composite_clip.w}x{composite_clip.h}")
            
            # Ensure composite clip has proper size
            if composite_clip.w != target_size[0] or composite_clip.h != target_size[1]:
                logger.warning(f"Composite clip size mismatch: {composite_clip.w}x{composite_clip.h} != {target_size[0]}x{target_size[1]}", 
                             extra={"task_id": task_id} if task_id else None)
                # Force resize to exact target size
                composite_clip = composite_clip.resized(target_size)
            
            logger.info(f"Blurred background video created: {moderate_w}x{moderate_h} at position ({x}, {y})", 
                       extra={"task_id": task_id} if task_id else None)
            
            return composite_clip
            
        except Exception as composite_error:
            logger.warning(f"CompositeVideoClip failed: {composite_error}, falling back to simple resize", 
                         extra={"task_id": task_id} if task_id else None)
            # Fallback: just resize to target size
            return video_clip.resized(target_size)
        
    except Exception as e:
        logger.error(f"Failed to create blurred background video: {e}", exc_info=True, 
                    extra={"task_id": task_id} if task_id else None)
        raise

def cleanup_blurred_background_files():
    """Clean up temporary blurred background files."""
    try:
        import glob
        temp_dir = tempfile.gettempdir()
        pattern = os.path.join(temp_dir, "blurred_bg_*.png")
        files = glob.glob(pattern)
        
        for file_path in files:
            try:
                os.remove(file_path)
            except OSError:
                pass  # File might already be deleted
                
        if files:
            logger.info(f"Cleaned up {len(files)} blurred background files")
            
    except Exception as e:
        logger.warning(f"Failed to cleanup blurred background files: {e}")
