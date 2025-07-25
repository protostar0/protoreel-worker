"""
Audio utilities for ProtoVideo.
Handles narration generation and Whisper-based subtitle generation.
"""
from typing import Optional, List
import os
import uuid
import logging
import requests

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

def generate_narration(text: str, audio_prompt_url: Optional[str] = None) -> str:
    """
    Generate narration audio from text using ChatterboxTTS.
    If audio_prompt_url is provided, use it as the audio_prompt_path.
    Returns the path to the generated audio file.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"[NARRATION] Generating narration for text: {text[:60]}...")
    TEMP_DIR = Config.TEMP_DIR
    local_filename = os.path.join(TEMP_DIR, f"narration_{uuid.uuid4().hex}.mp3")
    audio_prompt_path = None
    try:
        logger.info("[NARRATION] Loading TTS model...")
        device = os.environ.get("TTS_DEVICE", "cpu")
        model = ChatterboxTTS.from_pretrained(device=device)
        logger.info(f"[NARRATION] Model loaded on device: {device}. Generating audio...")
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
        logger.info("[NARRATION] Audio generated. Saving to file...")
        ta.save(local_filename, wav, model.sr)
        logger.info(f"[NARRATION] Narration saved at {local_filename}")
        return local_filename
    except Exception as e:
        logger.error(f"[NARRATION] Failed to generate narration: {e}", exc_info=True)
        raise RuntimeError(f"[500] Failed to generate narration: {e}")
    finally:
        if audio_prompt_path and os.path.exists(audio_prompt_path):
            try:
                os.remove(audio_prompt_path)
                logger.info(f"[NARRATION] Deleted temp audio prompt: {audio_prompt_path}")
            except Exception as e:
                logger.warning(f"[NARRATION] Failed to delete temp audio prompt: {audio_prompt_path}: {e}")

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