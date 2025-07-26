"""
Audio utilities for ProtoVideo.
Handles narration generation and Whisper-based subtitle generation.
"""
from typing import Optional, List
import os
import uuid
import logging
import requests
import threading
import time
from video_generator.config import Config
from chatterbox.tts import ChatterboxTTS
import torchaudio as ta
import whisper
from moviepy import TextClip
from video_generator.performance_optimizer import cache_result

# File lock for narration generation to prevent race conditions
_narration_lock = threading.Lock()

def download_audio_prompt(url: str, temp_dir: str) -> str:
    local_path = os.path.join(temp_dir, f"audio_prompt_{uuid.uuid4().hex}.wav")
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return local_path
    except Exception as e:
        raise RuntimeError(f"[400] Failed to download audio prompt: {e}")

# Global TTS model cache
_tts_model = None
_tts_model_lock = threading.Lock()

def get_tts_model():
    """Get or create the TTS model with caching."""
    global _tts_model
    logger = logging.getLogger(__name__)
    
    if _tts_model is None:
        with _tts_model_lock:
            if _tts_model is None:
                logger.info("[NARRATION] Loading TTS model...")
                device = os.environ.get("TTS_DEVICE", "cpu")
                _tts_model = ChatterboxTTS.from_pretrained(device=device)
                logger.info(f"[NARRATION] Model loaded on device: {device}")
    
    return _tts_model

def generate_cache_key(text: str, audio_prompt_url: Optional[str] = None) -> str:
    """Generate a cache key for narration."""
    import hashlib
    key_data = f"{text}:{audio_prompt_url or 'none'}"
    return hashlib.md5(key_data.encode()).hexdigest()

@cache_result(generate_cache_key)
def generate_narration(text: str, audio_prompt_url: Optional[str] = None) -> str:
    """
    Generate narration audio from text using ChatterboxTTS with caching.
    If audio_prompt_url is provided, use it as the audio_prompt_path.
    Returns the path to the generated audio file.
    """
    from video_generator.performance_optimizer import monitor_performance
    
    @monitor_performance("narration_generation")
    def _generate_narration_internal():
        logger = logging.getLogger(__name__)
        logger.info(f"[NARRATION] Generating narration for text: {text[:60]}...")
        TEMP_DIR = Config.TEMP_DIR
        local_filename = os.path.join(TEMP_DIR, f"narration_{uuid.uuid4().hex}.mp3")
        audio_prompt_path = None
        
        logger.info(f"[NARRATION] Will save to: {local_filename}")
        logger.info(f"[NARRATION] TEMP_DIR: {TEMP_DIR}")
        logger.info(f"[NARRATION] TEMP_DIR exists: {os.path.exists(TEMP_DIR)}")
        logger.info(f"[NARRATION] TEMP_DIR writable: {os.access(TEMP_DIR, os.W_OK)}")
        
        # Use lock to prevent race conditions when multiple threads generate the same narration
        with _narration_lock:
            try:
                model = get_tts_model()
                logger.info(f"[NARRATION] Generating audio...")
                
                if audio_prompt_url:
                    logger.info(f"[NARRATION] Downloading audio prompt from {audio_prompt_url}")
                    audio_prompt_path = download_audio_prompt(audio_prompt_url, TEMP_DIR)
                    logger.info(f"[NARRATION] Audio prompt downloaded to {audio_prompt_path}")
                    wav = model.generate(
                        text,
                        exaggeration=0.5,
                        cfg_weight=0.5,
                        audio_prompt_path=audio_prompt_path
                    )
                else:
                    wav = model.generate(
                        text,
                        exaggeration=0.5,
                        cfg_weight=0.5
                    )
                
                logger.info(f"[NARRATION] TTS model generation completed")
                logger.info(f"[NARRATION] Audio tensor type: {type(wav)}")
                logger.info(f"[NARRATION] Audio tensor shape: {wav.shape if hasattr(wav, 'shape') else 'No shape'}")
                logger.info(f"[NARRATION] Audio tensor dtype: {wav.dtype if hasattr(wav, 'dtype') else 'No dtype'}")
                logger.info(f"[NARRATION] Audio tensor min/max: {wav.min().item() if hasattr(wav, 'min') else 'N/A'}/{wav.max().item() if hasattr(wav, 'max') else 'N/A'}")
                
                if wav is None or (hasattr(wav, 'shape') and wav.shape[0] == 0):
                    raise RuntimeError("TTS model generated empty audio")
                
                logger.info(f"[NARRATION] Audio generated. Saving to file: {local_filename}")
                logger.info(f"[NARRATION] Sample rate: {model.sr}")
                
                try:
                    ta.save(local_filename, wav, model.sr)
                    logger.info(f"[NARRATION] torchaudio.save completed")
                except Exception as save_error:
                    logger.error(f"[NARRATION] torchaudio.save failed: {save_error}")
                    raise RuntimeError(f"Failed to save audio file: {save_error}")
                
                # Verify the file was created successfully
                logger.info(f"[NARRATION] Checking if file exists: {local_filename}")
                logger.info(f"[NARRATION] File exists: {os.path.exists(local_filename)}")
                if os.path.exists(local_filename):
                    logger.info(f"[NARRATION] File size: {os.path.getsize(local_filename)} bytes")
                else:
                    logger.error(f"[NARRATION] File was not created by torchaudio.save")
                    # List files in temp directory to see what's there
                    temp_files = os.listdir(TEMP_DIR)
                    logger.info(f"[NARRATION] Files in temp directory: {temp_files[:10]}")  # Show first 10 files
                
                if not os.path.exists(local_filename):
                    raise RuntimeError(f"Failed to create narration file: {local_filename}")
                
                # Verify the file is readable
                try:
                    logger.info(f"[NARRATION] Testing file readability...")
                    with open(local_filename, 'rb') as f:
                        data = f.read(1024)  # Read a small chunk to verify file is accessible
                        logger.info(f"[NARRATION] Read {len(data)} bytes from file")
                    logger.info(f"[NARRATION] Narration saved and verified at {local_filename}")
                except Exception as e:
                    logger.error(f"[NARRATION] File readability test failed: {e}")
                    raise RuntimeError(f"Created narration file is not readable: {local_filename}, error: {e}")
                
                logger.info(f"[NARRATION] Successfully returning file path: {local_filename}")
                return local_filename
                
            except Exception as e:
                logger.error(f"[NARRATION] Failed to generate narration: {e}", exc_info=True)
                # Clean up the file if it was created but we're raising an error
                if os.path.exists(local_filename):
                    try:
                        os.remove(local_filename)
                        logger.info(f"[NARRATION] Cleaned up failed narration file: {local_filename}")
                    except Exception as cleanup_error:
                        logger.warning(f"[NARRATION] Failed to clean up failed narration file: {local_filename}: {cleanup_error}")
                raise RuntimeError(f"[500] Failed to generate narration: {e}")
            finally:
                if audio_prompt_path and os.path.exists(audio_prompt_path):
                    try:
                        os.remove(audio_prompt_path)
                        logger.info(f"[NARRATION] Deleted temp audio prompt: {audio_prompt_path}")
                    except Exception as e:
                        logger.warning(f"[NARRATION] Failed to delete temp audio prompt: {audio_prompt_path}: {e}")
    
    return _generate_narration_internal()

def generate_whisper_phrase_subtitles(audio_path: str, video_clip, min_words: int = 4, max_words: int = 6, font_size: int = 50) -> List:
    """
    Generate animated phrase subtitles using Whisper for a given audio file and video clip.
    Returns a list of subtitle TextClip objects.
    """
    import traceback
    import re
    logger = logging.getLogger(__name__)
    logger.info(f"[DEBUG] Entered generate_whisper_phrase_subtitles with audio_path={audio_path}, video_clip={video_clip}, min_words={min_words}, max_words={max_words}, font_size={font_size}")
    model = whisper.load_model("base")
    try:
        result = model.transcribe(audio_path, word_timestamps=True, verbose=False)
    except Exception as e:
        logger.error(f"[DEBUG] Exception during whisper transcribe: {e}\n{traceback.format_exc()}")
        raise
    all_words = []
    for segment in result['segments']:
        all_words.extend(segment.get('words', []))
    # Smart line breaking
    lines = []
    current = []
    for w in all_words:
        current.append(w)
        # If word ends with sentence-ending punctuation or comma, or max_words reached
        if (re.match(r'.*[.!?]$', w['word']) or
            (len(current) >= max_words) or
            (re.match(r'.*,$', w['word']) and len(current) >= min_words)):
            lines.append(current)
            current = []
    if current:
        lines.append(current)
    # Merge short lines
    merged = []
    for line in lines:
        if merged and len(line) < min_words:
            merged[-1].extend(line)
        else:
            merged.append(line)
    subtitle_clips = []
    for line in merged:
        try:
            line_text = ' '.join([w['word'].strip() for w in line])
            start = line[0]['start']
            end = line[-1]['end']
            base_clip = (
                TextClip(
                    text = line_text.upper()+"\n_",
                    font="./video_generator/font/Montserrat-Black.ttf",
                    font_size=font_size,
                    color="white",
                    stroke_color="black",
                    stroke_width=4,
                    method="caption",
                    text_align="center",
                    size=(video_clip.w - 120, None)
                )
                .with_position(("center", int(video_clip.h * 0.6)))
                .with_start(start)
                .with_duration(end - start)
            )
            subtitle_clips.append(base_clip)
        except Exception as e:
            logger.error(f"[DEBUG] Exception during subtitle clip creation: {e}\n{traceback.format_exc()}")
            raise
    return subtitle_clips 