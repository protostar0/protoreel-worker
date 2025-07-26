"""
Configuration for ProtoVideo.
Centralizes all environment-based and default settings.
"""
import os
from pathlib import Path

class Config:
    # OpenAI API
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    # Cloudflare R2
    R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL", "")
    R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
    # Temp and output directories
    TEMP_DIR = os.getenv('TMPDIR', '/tmp')
    OUTPUT_DIR = os.environ.get("OUTPUT_DIR", str(Path(TEMP_DIR) / "generated_videos"))
    # Video settings optimized for Instagram Reels
    REEL_SIZE = (1080, 1920)  # 9:16 aspect ratio for Reels
    FPS = int(os.environ.get("FPS", "30"))  # 30fps for smooth Reels
    VIDEO_WIDTH = int(os.environ.get("VIDEO_WIDTH", "1080"))  # 1080p width
    VIDEO_HEIGHT = int(os.environ.get("VIDEO_HEIGHT", "1920"))  # 9:16 aspect ratio for Reels
    VIDEO_QUALITY = os.environ.get("VIDEO_QUALITY", "high")  # high, medium, low
    
    # Image generation settings
    DEFAULT_IMAGE_PROVIDER = os.environ.get("DEFAULT_IMAGE_PROVIDER", "gemini")
    
    # API Key for your service
    API_KEY = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
    
    # FFmpeg settings optimized for Reels
    FFMPEG_PRESET = os.environ.get("FFMPEG_PRESET", "fast")  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow, placebo
    FFMPEG_BITRATE = os.environ.get("FFMPEG_BITRATE", "5000k")  # 5Mbps for high quality Reels
    FFMPEG_CRF = int(os.environ.get("FFMPEG_CRF", "23"))  # 18-28 range, lower = better quality
    FFMPEG_THREADS = int(os.environ.get("FFMPEG_THREADS", os.cpu_count() or 4))
    
    # Hardware acceleration (if available)
    FFMPEG_HWACCEL = os.environ.get("FFMPEG_HWACCEL", "auto")  # auto, none, h264_nvenc, h264_qsv, etc.
    
    # Memory optimization
    MAX_MEMORY_MB = int(os.environ.get("MAX_MEMORY_MB", "2048"))  # 2GB memory limit
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
    
    # Parallel processing settings
    MAX_WORKERS = int(os.environ.get("MAX_WORKERS", min(4, os.cpu_count() or 2)))
    SCENE_PARALLEL_LIMIT = int(os.environ.get("SCENE_PARALLEL_LIMIT", 4))  # Max scenes to process in parallel
    
    # Video optimization settings
    VIDEO_OPTIMIZATION_ENABLED = os.environ.get("VIDEO_OPTIMIZATION_ENABLED", "true").lower() == "true"
    USE_HARDWARE_ACCELERATION = os.environ.get("USE_HARDWARE_ACCELERATION", "true").lower() == "true"
    AUTO_DETECT_HARDWARE = os.environ.get("AUTO_DETECT_HARDWARE", "true").lower() == "true"
    
    # Scene rendering optimization (faster for individual scenes)
    SCENE_RENDERING_THREADS = int(os.environ.get("SCENE_RENDERING_THREADS", os.cpu_count() or 4))
    SCENE_RENDERING_PRESET = os.environ.get("SCENE_RENDERING_PRESET", "ultrafast")  # ultrafast for scenes
    
    # Final video optimization (better quality for final output)
    FINAL_VIDEO_THREADS = int(os.environ.get("FINAL_VIDEO_THREADS", os.cpu_count() or 4))
    FINAL_VIDEO_PRESET = os.environ.get("FINAL_VIDEO_PRESET", "fast")  # fast for good quality/speed balance 
    
    # Performance optimization settings
    ENABLE_AGGRESSIVE_OPTIMIZATION = os.environ.get("ENABLE_AGGRESSIVE_OPTIMIZATION", "true").lower() == "true"
    ENABLE_MEMORY_OPTIMIZATION = os.environ.get("ENABLE_MEMORY_OPTIMIZATION", "true").lower() == "true"
    ENABLE_CPU_OPTIMIZATION = os.environ.get("ENABLE_CPU_OPTIMIZATION", "true").lower() == "true"
    ENABLE_MODULE_PRELOADING = os.environ.get("ENABLE_MODULE_PRELOADING", "true").lower() == "true"
    
    # Memory management settings (permissive - don't fail tasks)
    MEMORY_CLEANUP_INTERVAL = int(os.environ.get("MEMORY_CLEANUP_INTERVAL", "1"))  # Cleanup every N scenes
    MAX_MEMORY_USAGE_MB = int(os.environ.get("MAX_MEMORY_USAGE_MB", "10000"))  # 10GB limit (very permissive)
    FORCE_GC_AFTER_SCENE = os.environ.get("FORCE_GC_AFTER_SCENE", "true").lower() == "true"
    
    # CPU optimization settings
    CPU_PRIORITY = os.environ.get("CPU_PRIORITY", "high")  # high, normal, low
    CPU_AFFINITY_ENABLED = os.environ.get("CPU_AFFINITY_ENABLED", "true").lower() == "true"
    
    # Cache optimization settings
    CACHE_CLEANUP_INTERVAL = int(os.environ.get("CACHE_CLEANUP_INTERVAL", "5"))  # Cleanup every N tasks
    CACHE_MAX_SIZE_MB = int(os.environ.get("CACHE_MAX_SIZE_MB", "500"))  # 500MB cache limit
    CACHE_TTL_HOURS = int(os.environ.get("CACHE_TTL_HOURS", "1"))  # 1 hour cache TTL 