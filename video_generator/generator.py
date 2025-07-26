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

logger = get_logger()

TEMP_DIR = Config.TEMP_DIR
REEL_SIZE = Config.REEL_SIZE

class TextOverlay(BaseModel):
    content: str
    position: str = "center"
    fontsize: int = 36
    color: str = "white"

class SceneInput(BaseModel):
    type: str
    image: Optional[str] = None
    promptImage: Optional[str] = None
    image_provider: Optional[str] = "openai"  # "openai", "freepik", or "gemini"
    video: Optional[str] = None
    narration: Optional[str] = None
    narration_text: Optional[str] = None
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

def render_scene(scene: SceneInput, use_global_narration: bool = False, task_id: Optional[str] = None) -> (str, List[str]):
    """
    Render a single scene (image or video) with optional narration, music, and subtitles.
    Returns the path to the rendered scene video and a list of temp files to clean up.
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
        elif scene.promptImage:
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
                logger.info(f"Generating image from prompt using {provider}: {scene.promptImage}", extra={"task_id": task_id})
                image_path = generate_image_from_prompt(scene.promptImage, api_key, out_path, provider=provider)
                temp_files.append(image_path)
                logger.info(f"Generated image from prompt: {image_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.error(f"Image generation failed: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        else:
            logger.error("Image URL/path or promptImage required for image scene.", extra={"task_id": task_id})
            raise ValueError("Image URL/path or promptImage required for image scene.")
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
                    try:
                        narration_audio = AudioFileClip(narration_path)
                        silence = AudioClip(lambda t: 0, duration=0.5, fps=44100)
                        scene.duration = narration_audio.duration + 0.5
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
        scene_output = os.path.join(TEMP_DIR, f"scene_{uuid.uuid4().hex}.mp4")
        try:
            logger.info(f"Exporting scene to {scene_output}", extra={"task_id": task_id})
            video_clip.write_videofile(
                scene_output,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=f"{scene_output}.temp_audio.m4a",
                remove_temp=True,
                logger=None
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
    request = copy.deepcopy(request_dict)
    temp_files = []
    scene_files = []
    use_global_narration = bool(request.get("narration_text"))
    narration_path = None
    narration_duration = None
    global_audio_prompt_url = request.get("audio_prompt_url")  # NEW: get global audio_prompt_url
    clips = []
    final_clip = None
    output_path = None
    try:
        if use_global_narration:
            try:
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
            except Exception as e:
                logger.error(f"Failed to generate global narration: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        for idx, scene in enumerate(request["scenes"]):
            try:
                logger.info(f"Processing scene {idx+1}/{len(request['scenes'])}", extra={"task_id": task_id})
                # Per-scene narration
                if not use_global_narration:
                    if scene.get("narration"):
                        try:
                            logger.info(f"Downloading narration asset: {scene.narration}", extra={"task_id": task_id})
                            narration_path = download_asset(scene.narration)
                            temp_files.append(narration_path)
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
                            temp_files.append(narration_path)
                            logger.info(f"Added narration from text: {narration_path}", extra={"task_id": task_id})
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
                            except Exception as e:
                                logger.error(f"Failed to load narration audio: {e}", exc_info=True, extra={"task_id": task_id})
                                raise
                        except Exception as e:
                            logger.error(f"Failed to generate narration: {e}", exc_info=True, extra={"task_id": task_id})
                            raise
                scene_file, files_to_clean = render_scene(SceneInput(**scene), use_global_narration=use_global_narration, task_id=task_id)
                scene_files.append(scene_file)
                temp_files.extend(files_to_clean)
                gc.collect()
            except Exception as e:
                logger.error(f"Failed to process scene {idx+1}: {e}", exc_info=True, extra={"task_id": task_id})
                raise
        from moviepy import VideoFileClip, concatenate_videoclips
        try:
            logger.info(f"Loading scene video clips for concatenation.", extra={"task_id": task_id})
            clips = [VideoFileClip(f) for f in scene_files]
            logger.info(f"Concatenating {len(clips)} scene clips.", extra={"task_id": task_id})
            # --- Update: include task_id in output file name ---
            output_filename = request['output_filename']
            if task_id:
                output_filename = f"{task_id}_{output_filename}"
            output_path = os.path.join(Config.OUTPUT_DIR, output_filename)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Exporting final video to {output_path}", extra={"task_id": task_id})
            final_clip = concatenate_videoclips(clips, method="compose")
            # --- Enforce Instagram Reels duration limits ---
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
            # --- Export at 30 fps ---
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                audio_fps=48000,
                temp_audiofile=f"{output_path}.temp_audio.m4a",
                remove_temp=True,
                threads=4,
                preset="slow",
                ffmpeg_params=[
                    "-profile:v", "high",
                    "-level", "4.0",
                    "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart",
                    "-b:v", "2000k",
                    "-maxrate", "2500k",
                    "-bufsize", "5000k",
                    "-r", "30",  # force frame rate again
                    "-ac", "2",  # enforce stereo
                    "-ar", "48000"  # audio resample (again, to avoid backend mismatch)
                ],
                logger=None
            )
            # --- Check file size ---
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            if file_size_mb > 100:
                logger.warning(f"Exported video file size is {file_size_mb:.2f} MB, which may exceed Instagram's limits.", extra={"task_id": task_id})
            for c in clips:
                c.close()
                del c
            if final_clip:
                final_clip.close()
                del final_clip
            gc.collect()
        except Exception as e:
            logger.error(f"Failed to concatenate or export final video: {e}", exc_info=True, extra={"task_id": task_id})
            raise
        # --- Cloud upload logic ---
        bucket_name = os.environ.get('R2_BUCKET_NAME')
        if not bucket_name:
            logger.error("R2_BUCKET_NAME not set, cannot upload.", extra={"task_id": task_id})
            raise RuntimeError("Cloud upload failed: R2_BUCKET_NAME not set.")
        try:
            logger.info(f"Uploading final video to R2 bucket {bucket_name}.", extra={"task_id": task_id})
            r2_url = upload_to_r2(output_path, bucket_name, os.path.basename(output_path))
            if r2_url:
                logger.info(f"Upload successful: {r2_url}", extra={"task_id": task_id})
                return {"r2_url": r2_url}
            else:
                logger.error("Upload to R2 failed: No URL returned.", extra={"task_id": task_id})
                raise RuntimeError("Cloud upload failed: No URL returned.")
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}", exc_info=True, extra={"task_id": task_id})
            raise
    finally:
        logger.info(f"Cleaning up {len(temp_files)} temp files at end of job.", extra={"task_id": task_id})
        cleanup_files(temp_files)
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
                logger.info(f"Deleted output video: {output_path}", extra={"task_id": task_id})
            except Exception as e:
                logger.warning(f"Failed to delete output video {output_path}: {e}", extra={"task_id": task_id})
        gc.collect() 