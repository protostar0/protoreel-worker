"""
Core video generation logic for ProtoVideo.
Handles orchestration, scene rendering, and helpers.
"""
from typing import List, Optional, Dict, Any
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
from video_generator.audio_utils import generate_narration, generate_whisper_phrase_subtitles
from video_generator.cleanup_utils import cleanup_files, upload_to_r2
from video_generator.logging_utils import get_logger
from video_generator.config import Config
from pydantic import BaseModel
import time

logger = get_logger()

REEL_SIZE = Config.REEL_SIZE

class TextOverlay(BaseModel):
    content: str
    position: str = "center"
    fontsize: int = 36
    color: str = "white"

class SceneInput(BaseModel):
    type: str
    image: Optional[str] = None
    prompt_image: Optional[str] = None
    image_provider: Optional[str] = Config.DEFAULT_IMAGE_PROVIDER  # "openai", "freepik", or "gemini"
    video: Optional[str] = None
    narration: Optional[str] = None
    narration_text: Optional[str] = None
    audio_prompt_url: Optional[str] = None
    music: Optional[str] = None
    duration: int
    text: Optional[TextOverlay] = None
    subtitle: bool = False
    """
    image_provider:
        - "openai": Use OpenAI DALL-E
        - "freepik": Use Freepik AI Mystic
        - "gemini": Use Google Gemini
    """

def render_scene(scene: SceneInput, use_global_narration: bool = False, task_id: Optional[str] = None, 
                scene_context: dict = None, video_context: dict = None) -> (str, List[str]):
    """
    Render a single scene (image or video) with optional narration, music, and subtitles.
    Returns the path to the rendered scene video and a list of temp files to clean up.
    
    Args:
        scene: Scene input data
        use_global_narration: Whether to use global narration
        task_id: Task ID for logging
        scene_context: Additional context about the scene (scene_index, total_scenes, etc.)
        video_context: Context about the entire video (theme, narration_text, etc.)
    """
    logger.info(f"Rendering scene: {scene}", extra={"task_id": task_id})
    temp_files = []
    video_clip = None
    audio_clips = []
    # Handle image or video
    if scene.type == "image":
        image_path = None
        if scene.image:
            try:
                logger.info(f"Downloading image asset: {scene.image}", extra={"task_id": task_id})
                image_path = download_asset(scene.image)
                temp_files.append(image_path)
                logger.info(f"Added image from file: {image_path}", extra={"task_id": task_id})
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
            
            out_path = os.path.join(tempfile.gettempdir(), f"generated_{uuid.uuid4().hex}.png")
            try:
                logger.info(f"Generating image from prompt using {provider}: {scene.prompt_image}", extra={"task_id": task_id})
                image_path = generate_image_from_prompt(scene.prompt_image, api_key, out_path, provider=provider, scene_context=scene_context, video_context=video_context)
                temp_files.append(image_path)
                logger.info(f"Generated image from prompt: {image_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.error(f"Image generation failed: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        else:
            logger.error("Image URL/path or prompt_image required for image scene.", extra={"task_id": task_id})
            raise ValueError("Image URL/path or prompt_image required for image scene.")
        # --- Set duration from narration_text if present ---
        narration_path = None
        narration_audio = None
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
                    # Support per-scene audio_prompt_url
                    audio_prompt_url = getattr(scene, 'audio_prompt_url', None)
                    logger.info(f"Generating narration from text. audio_prompt_url={audio_prompt_url}", extra={"task_id": task_id})
                    narration_path = generate_narration(text=scene.narration_text, audio_prompt_url=audio_prompt_url)
                    temp_files.append(narration_path)
                    logger.info(f"Added narration from text: {narration_path}", extra={"task_id": task_id})
                    
                    # Verify the file exists before trying to load it
                    if not os.path.exists(narration_path):
                        raise FileNotFoundError(f"Narration file was not created: {narration_path}")
                    
                    # Retry logic for loading the audio file
                    max_retries = 3
                    retry_delay = 0.1  # 100ms
                    
                    for attempt in range(max_retries):
                        try:
                            narration_audio = AudioFileClip(narration_path)
                            silence = AudioClip(lambda t: 0, duration=0.5, fps=44100)
                            scene.duration = narration_audio.duration + 0.5
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
        duration = scene.duration
        try:
            logger.info(f"Creating ImageClip for {image_path}", extra={"task_id": task_id})
            video_clip = ImageClip(image_path).with_duration(duration)
            video_clip = video_clip.resized(height=REEL_SIZE[1])
            if video_clip.w > REEL_SIZE[0]:
                video_clip = video_clip.resized(width=REEL_SIZE[0])
            def zoom(t):
                return 1.0 + 0.5 * (t / duration)
            video_clip = video_clip.resized(zoom)
            video_clip = video_clip.with_background_color(size=REEL_SIZE, color=(0,0,0), pos='center')
            video_clip = video_clip.with_effects([MultiplyColor(0.5)])
        except Exception as e:
            logger.error(f"Failed to create or process ImageClip: {e}", exc_info=True, extra={"task_id": task_id})
            raise
        # Add narration audio
        if not use_global_narration:
            if narration_path:
                try:
                    logger.info(f"Adding narration audio to video clip.", extra={"task_id": task_id})
                    narration_clip = AudioFileClip(narration_path)
                    if narration_clip.duration < video_clip.duration:
                        silence = AudioClip(lambda t: 0, duration=video_clip.duration - narration_clip.duration)
                        narration_padded = CompositeAudioClip([
                            narration_clip,
                            silence.with_start(narration_clip.duration)
                        ])
                        narration_padded = narration_padded.with_duration(video_clip.duration)
                    else:
                        narration_padded = narration_clip.subclipped(0, video_clip.duration)
                    video_clip = video_clip.with_audio(narration_padded)
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
                subtitle_clips = generate_whisper_phrase_subtitles(
                    narration_path, video_clip, min_words=4, max_words=6, font_size=50
                )
                video_clip = CompositeVideoClip([video_clip] + subtitle_clips)
                logger.info("Subtitles added for scene narration.", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Subtitle generation failed for scene: {e}", exc_info=True, extra={"task_id": task_id})
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
    # TODO: Handle video scenes if needed
    raise NotImplementedError("Video scenes not implemented in refactor.")

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
            
            # Process scenes in parallel if multiple scenes
            if len(request["scenes"]) > 1:
                logger.info(f"Processing {len(request['scenes'])} scenes in parallel", extra={"task_id": task_id})
                scene_results = optimizer.parallel_process_scenes(
                    request["scenes"], 
                    process_scene_parallel, 
                    use_global_narration=use_global_narration,
                    global_audio_prompt_url=global_audio_prompt_url,
                    task_id=task_id
                )
                
                # Extract results
                for scene_file, files_to_clean in scene_results:
                    scene_files.append(scene_file)
                    temp_files.extend(files_to_clean)
            else:
                # Process single scene sequentially
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
                            "theme": request.get("theme"),
                            "output_filename": request.get("output_filename")
                        }
                        
                        scene_file, files_to_clean = process_scene_sequential(
                            scene, idx, use_global_narration, global_audio_prompt_url, task_id,
                            scene_context=scene_context, video_context=video_context
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
            
            # Concatenate video clips
            from moviepy import VideoFileClip, concatenate_videoclips
            try:
                logger.info(f"Loading scene video clips for concatenation.", extra={"task_id": task_id})
                clips = [VideoFileClip(f) for f in scene_files]
                logger.info(f"Concatenating {len(clips)} scene clips.", extra={"task_id": task_id})
                
                # Generate output filename
                output_filename = request['output_filename']
                if task_id:
                    output_filename = f"{task_id}_{output_filename}"
                output_path = os.path.join(Config.OUTPUT_DIR, output_filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                logger.info(f"Exporting final video to {output_path}", extra={"task_id": task_id})
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
                    final_clip = final_clip.subclip(0, max_duration)
                
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
                
                return {
                    "r2_url": r2_url,
                    "local_path": output_path,
                    "duration": final_clip.duration if final_clip else 0,
                    "performance_report": optimizer.get_performance_report()
                }
                
            except Exception as e:
                logger.error(f"Failed to concatenate video clips: {e}", exc_info=True, extra={"task_id": task_id})
                raise
                
        except Exception as e:
            logger.error(f"Video generation failed: {e}", exc_info=True, extra={"task_id": task_id})
            # Clean up on failure
            cleanup_files(temp_files + scene_files)
            raise
    
    return _generate_video_internal()

def process_scene_parallel(scene, scene_idx, use_global_narration, global_audio_prompt_url, task_id):
    """Process a single scene for parallel execution."""
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance(f"scene_{scene_idx}_parallel")
    def _process_scene():
        return process_scene_sequential(scene, scene_idx, use_global_narration, global_audio_prompt_url, task_id)
    
    return _process_scene()

def process_scene_sequential(scene, scene_idx, use_global_narration, global_audio_prompt_url, task_id, 
                           scene_context: dict = None, video_context: dict = None):
    """Process a single scene sequentially."""
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance(f"scene_{scene_idx}_sequential")
    def _process_scene():
        # Per-scene narration
        if not use_global_narration:
            if scene.get("narration"):
                try:
                    logger.info(f"Downloading narration asset: {scene.narration}", extra={"task_id": task_id})
                    narration_path = download_asset(scene.narration)
                    logger.info(f"Added narration from file: {narration_path}", extra={"task_id": task_id})
                except Exception as e:
                    logger.error(f"Failed to download narration asset: {e}", exc_info=True, extra={"task_id": task_id})
                    raise
            elif scene.get("narration_text"):
                try:
                    # Use scene audio_prompt_url if set, else use global
                    audio_prompt_url = scene.get("audio_prompt_url", global_audio_prompt_url)
                    logger.info(f"Generating narration from text. audio_prompt_url={audio_prompt_url}", extra={"task_id": task_id})
                    narration_path = generate_narration(scene["narration_text"], audio_prompt_url=audio_prompt_url)
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
                            # Only update duration, do not replace scene dict
                            if "type" not in scene:
                                logger.error(f"Scene missing required 'type' field after narration generation: {scene}", extra={"task_id": task_id})
                                raise ValueError("Scene missing required 'type' field after narration generation")
                            scene["duration"] = int(round(narration_audio.duration + 0.5))
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
        
        scene_file, files_to_clean = render_scene(SceneInput(**scene), use_global_narration=use_global_narration, 
                                                 task_id=task_id, scene_context=scene_context, video_context=video_context)
        return scene_file, files_to_clean
    
    return _process_scene() 