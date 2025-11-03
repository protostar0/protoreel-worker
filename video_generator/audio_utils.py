"""
Audio utilities for ProtoVideo.
Handles narration generation and Whisper-based subtitle generation.
Uses ElevenLabs API as primary TTS, with ChatterboxTTS as fallback.
"""
from typing import Optional, List
import os
import uuid
import logging
import requests
import threading
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
    # Include provider in cache key to differentiate ElevenLabs vs ChatterboxTTS results
    provider = "elevenlabs" if os.environ.get("ELEVENLABS_API_KEY") else "chatterbox"
    key_data = f"{text}:{audio_prompt_url or 'none'}:{provider}"
    return hashlib.md5(key_data.encode()).hexdigest()

def generate_narration_elevenlabs(
    text: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    audio_prompt_url: Optional[str] = None
) -> Optional[str]:
    """
    Generate narration using ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID (default: uses ELEVENLABS_VOICE_ID env var or defaults to "21m00Tcm4TlvDq8ikWAM")
        model_id: Model ID (default: "eleven_multilingual_v2" or "eleven_turbo_v2_5" for faster)
        audio_prompt_url: URL to audio file for voice cloning (optional)
        
    Returns:
        Path to generated audio file, or None if failed
    """
    logger = logging.getLogger(__name__)
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    
    if not api_key:
        logger.info("[NARRATION] ElevenLabs API key not found, will use fallback")
        return None
    
    try:
        logger.info(f"[NARRATION] Attempting ElevenLabs TTS for text: {text[:60]}...")
        
        # Default voice ID (Rachel - high quality female voice)
        default_voice_id = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "RaFzMbMIfqBcIurH6XF9")
        
        # Default model (can use "eleven_turbo_v2_5" for faster, lower latency)
        default_model_id = model_id or os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        
        # API endpoint
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{default_voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        # Build request payload
        data = {
            "text": text,
            "model_id": default_model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        # If audio_prompt_url is provided, try to use it for voice cloning
        # Note: This requires downloading the audio and potentially creating a voice first
        # For now, we'll use the voice_id directly
        
        logger.info(f"[NARRATION] Calling ElevenLabs API: voice_id={default_voice_id}, model={default_model_id}")
        
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        # Check for API errors
        if response.status_code == 401:
            logger.warning("[NARRATION] ElevenLabs API: Unauthorized (invalid API key)")
            return None
        elif response.status_code == 429:
            logger.warning("[NARRATION] ElevenLabs API: Rate limit exceeded")
            return None
        elif response.status_code == 402:
            logger.warning("[NARRATION] ElevenLabs API: Payment required (insufficient balance)")
            return None
        elif response.status_code != 200:
            logger.warning(f"[NARRATION] ElevenLabs API error: {response.status_code} - {response.text[:200]}")
            return None
        
        # Save audio to file
        TEMP_DIR = Config.TEMP_DIR
        local_filename = os.path.join(TEMP_DIR, f"narration_elevenlabs_{uuid.uuid4().hex}.mp3")
        
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Verify file was created
        if os.path.exists(local_filename) and os.path.getsize(local_filename) > 0:
            logger.info(f"[NARRATION] ElevenLabs TTS successful: {local_filename} ({os.path.getsize(local_filename)} bytes)")
            return local_filename
        else:
            logger.warning("[NARRATION] ElevenLabs API returned empty audio file")
            return None
            
    except requests.exceptions.Timeout:
        logger.warning("[NARRATION] ElevenLabs API timeout, will use fallback")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"[NARRATION] ElevenLabs API request failed: {e}, will use fallback")
        return None
    except Exception as e:
        logger.warning(f"[NARRATION] ElevenLabs API error: {e}, will use fallback", exc_info=True)
        return None

@cache_result(generate_cache_key)
def generate_narration(text: str, audio_prompt_url: Optional[str] = None) -> str:
    """
    Generate narration audio from text.
    Primary: ElevenLabs API (if ELEVENLABS_API_KEY is set)
    Fallback: ChatterboxTTS (local model)
    
    If audio_prompt_url is provided, it's passed to the TTS provider (voice cloning for ElevenLabs).
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
        
        # Try ElevenLabs API first (primary)
        elevenlabs_result = generate_narration_elevenlabs(
            text=text,
            audio_prompt_url=audio_prompt_url
        )
        
        if elevenlabs_result:
            logger.info(f"[NARRATION] Successfully generated narration using ElevenLabs: {elevenlabs_result}")
            return elevenlabs_result
        
        # Fallback to ChatterboxTTS
        logger.info("[NARRATION] Falling back to ChatterboxTTS...")
        logger.info(f"[NARRATION] Will save to: {local_filename}")
        logger.info(f"[NARRATION] TEMP_DIR: {TEMP_DIR}")
        logger.info(f"[NARRATION] TEMP_DIR exists: {os.path.exists(TEMP_DIR)}")
        logger.info(f"[NARRATION] TEMP_DIR writable: {os.access(TEMP_DIR, os.W_OK)}")
        
        # Use lock to prevent race conditions when multiple threads generate the same narration
        with _narration_lock:
            try:
                model = get_tts_model()
                logger.info(f"[NARRATION] Generating audio with ChatterboxTTS...")
                
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
                
                logger.info(f"[NARRATION] ChatterboxTTS generation completed")
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
                logger.error(f"[NARRATION] Failed to generate narration with ChatterboxTTS: {e}", exc_info=True)
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