"""
Performance optimization utilities for ProtoVideo.
Implements caching, parallel processing, and resource management.
"""
import os
import time
import threading
import hashlib
import json
import pickle
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import logging
from pathlib import Path
import gc
import psutil

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Performance optimization manager for video generation."""
    
    def __init__(self, cache_dir: str = None, max_workers: int = 4):
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), "cache")
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.cache_stats = {"hits": 0, "misses": 0}
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize performance monitoring
        self.start_time = None
        self.performance_metrics = {}
    
    def start_performance_monitoring(self, task_id: str):
        """Start monitoring performance for a task."""
        self.start_time = time.time()
        self.performance_metrics = {
            "task_id": task_id,
            "start_time": self.start_time,
            "steps": {},
            "memory_usage": []
        }
        logger.info(f"[PERF] Started performance monitoring for task {task_id}")
    
    def record_step(self, step_name: str, duration: float = None):
        """Record a performance step."""
        if duration is None:
            duration = time.time() - self.start_time
        
        self.performance_metrics["steps"][step_name] = {
            "duration": duration,
            "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024
        }
        logger.info(f"[PERF] Step '{step_name}' completed in {duration:.2f}s")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get a performance report."""
        total_time = time.time() - self.start_time if self.start_time else 0
        
        # Safely get total memory from steps
        steps = self.performance_metrics.get("steps", {})
        total_memory = 0
        if steps:
            total_memory = max([step.get("memory_mb", 0) for step in steps.values()], default=0)
        
        return {
            "total_time": total_time,
            "total_memory_mb": total_memory,
            "cache_stats": self.cache_stats,
            "steps": steps
        }
    
    def generate_cache_key(self, data: Any) -> str:
        """Generate a cache key from data."""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_cache_path(self, cache_key: str, extension: str = ".pkl") -> str:
        """Get the cache file path for a key."""
        return os.path.join(self.cache_dir, f"{cache_key}{extension}")
    
    def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get a cached result."""
        cache_path = self.get_cache_path(cache_key)
        
        logger.info(f"[CACHE] Looking for cache key: {cache_key}")
        logger.info(f"[CACHE] Cache path: {cache_path}")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    result = pickle.load(f)
                
                logger.info(f"[CACHE] Loaded cached result: {type(result)}")
                if isinstance(result, str):
                    logger.info(f"[CACHE] Cached result is file path: {result}")
                    logger.info(f"[CACHE] File exists: {os.path.exists(result)}")
                    if os.path.exists(result):
                        logger.info(f"[CACHE] File size: {os.path.getsize(result)} bytes")
                
                # If the cached result is a file path, verify the file exists
                if isinstance(result, str) and os.path.isfile(result):
                    if not os.path.exists(result):
                        logger.warning(f"[CACHE] Cached file path {result} no longer exists, treating as cache miss")
                        self.cache_stats["misses"] += 1
                        return None
                    logger.info(f"[CACHE] Verified cached file exists: {result}")
                
                self.cache_stats["hits"] += 1
                logger.info(f"[CACHE] Hit for key {cache_key}")
                return result
            except Exception as e:
                logger.warning(f"[CACHE] Failed to load cache for key {cache_key}: {e}")
        
        self.cache_stats["misses"] += 1
        logger.info(f"[CACHE] Miss for key {cache_key}")
        return None
    
    def cache_result(self, cache_key: str, result: Any):
        """Cache a result."""
        cache_path = self.get_cache_path(cache_key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            logger.info(f"[CACHE] Cached result for key {cache_key}")
        except Exception as e:
            logger.warning(f"[CACHE] Failed to cache result for key {cache_key}: {e}")
    
    def parallel_process_scenes(self, scenes: List[Dict], process_func, **kwargs) -> List[Any]:
        """Process scenes in parallel."""
        logger.info(f"[PERF] Processing {len(scenes)} scenes in parallel with {self.max_workers} workers")
        
        futures = []
        for i, scene in enumerate(scenes):
            future = self.executor.submit(process_func, scene, i, **kwargs)
            futures.append(future)
        
        results = []
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"[PERF] Scene processing failed: {e}")
                raise
        
        return results
    
    def clear_all_caches(self):
        """Clear all caches including local cache directory."""
        try:
            import os
            import shutil
            
            # Clear local cache directory
            local_cache_dir = os.path.join(os.getcwd(), "cache")
            if os.path.exists(local_cache_dir):
                try:
                    shutil.rmtree(local_cache_dir)
                    logger.info("[CACHE] Cleared local cache directory")
                except Exception as e:
                    logger.warning(f"[CACHE] Failed to clear local cache directory: {e}")
            
            # Clear any .pkl files in current directory
            current_dir = os.getcwd()
            for file in os.listdir(current_dir):
                if file.endswith('.pkl'):
                    file_path = os.path.join(current_dir, file)
                    try:
                        os.remove(file_path)
                        logger.info(f"[CACHE] Removed local cache file: {file}")
                    except Exception as e:
                        logger.warning(f"[CACHE] Failed to remove local cache file {file}: {e}")
            
            # Clear temp cache directory
            from video_generator.config import Config
            temp_cache_dir = os.path.join(Config.TEMP_DIR, "cache")
            if os.path.exists(temp_cache_dir):
                try:
                    shutil.rmtree(temp_cache_dir)
                    logger.info("[CACHE] Cleared temp cache directory")
                except Exception as e:
                    logger.warning(f"[CACHE] Failed to clear temp cache directory: {e}")
            
            logger.info("[CACHE] All caches cleared successfully")
            
        except Exception as e:
            logger.error(f"[CACHE] Failed to clear caches: {e}")

    def optimize_memory(self):
        """Conservative memory optimization to avoid breaking TTS models - permissive mode."""
        try:
            # Force garbage collection
            gc.collect()
            
            # Only clear matplotlib cache if used (safe)
            try:
                import matplotlib.pyplot as plt
                plt.close('all')
            except:
                pass
            
            # Don't clear numpy or other modules that might break TTS
            # Don't clear import cache for heavy modules
            # Don't clear MoviePy internal caches
            
            # Force memory cleanup
            import psutil
            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Clear unused memory
            gc.collect()
            
            memory_after = process.memory_info().rss / 1024 / 1024
            freed_memory = memory_before - memory_after
            
            # Only log if significant memory was freed
            if freed_memory > 50:  # Only log if more than 50MB was freed
                logger.info(f"[MEMORY] Conservative memory optimization. Freed: {freed_memory:.1f}MB")
            
        except Exception as e:
            logger.warning(f"[MEMORY] Memory optimization failed: {e}")
    
    def optimize_cpu_usage(self):
        """Optimize CPU usage for better performance."""
        try:
            import os
            import psutil
            
            # Set process priority (if supported)
            try:
                process = psutil.Process()
                process.nice(psutil.HIGH_PRIORITY_CLASS)
            except:
                pass
            
            # Set CPU affinity to use all cores efficiently
            try:
                cpu_count = os.cpu_count()
                if cpu_count:
                    process.cpu_affinity(list(range(cpu_count)))
                logger.info(f"[CPU] Optimized CPU usage for {cpu_count} cores")
            except:
                pass
            
        except Exception as e:
            logger.warning(f"[CPU] CPU optimization failed: {e}")
    
    def preload_common_modules(self):
        """Preload commonly used modules to reduce import time."""
        try:
            # Preload PIL (safe to preload)
            from PIL import Image, ImageDraw, ImageFont
            
            # Don't preload numpy to avoid reloading issues with TTS
            # import numpy as np
            
            # Only preload MoviePy if it's available and not already loaded
            try:
                import moviepy
                # Don't preload specific MoviePy modules as they may not exist
                logger.info("[PRELOAD] Preloaded PIL modules")
            except ImportError:
                logger.info("[PRELOAD] MoviePy not available for preloading")
            
        except Exception as e:
            logger.warning(f"[PRELOAD] Module preloading failed: {e}")
    
    def optimize_for_reels(self):
        """Optimize settings specifically for Instagram Reels."""
        try:
            from video_generator.config import Config
            
            # Set optimal settings for Reels
            os.environ['FFMPEG_PRESET'] = Config.SCENE_RENDERING_PRESET
            os.environ['FFMPEG_THREADS'] = str(Config.SCENE_RENDERING_THREADS)
            
            # Optimize for mobile viewing
            os.environ['VIDEO_QUALITY'] = 'high'
            os.environ['AUDIO_QUALITY'] = 'high'
            
            logger.info("[REELS] Optimized settings for Instagram Reels")
            
        except Exception as e:
            logger.warning(f"[REELS] Reels optimization failed: {e}")
    
    def batch_optimize(self):
        """Run all optimizations in batch."""
        # Clear all caches first
        self.clear_all_caches()
        # Only run memory optimization, skip aggressive module unloading
        self.optimize_memory()
        self.optimize_cpu_usage()
        # Skip preloading to avoid interference with narration generation
        # self.preload_common_modules()
        self.optimize_for_reels()
        logger.info("[BATCH] Completed performance optimizations with cache clearing")
    
    def cleanup_cache(self, max_age_hours: int = 24):
        """Clean up old cache files."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        cleaned_count = 0
        for cache_file in Path(self.cache_dir).glob("*"):
            if cache_file.is_file():
                file_age = current_time - cache_file.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        cache_file.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"[CACHE] Failed to delete old cache file {cache_file}: {e}")
        
        logger.info(f"[CACHE] Cleaned up {cleaned_count} old cache files")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)

# Global performance optimizer instance
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer

# Caching decorators
def cache_result(cache_key_func=None):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            optimizer = get_performance_optimizer()
            
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = optimizer.generate_cache_key((func.__name__, args, kwargs))
            
            logger.info(f"[CACHE] Function {func.__name__} called with cache key: {cache_key}")
            
            # Try to get cached result
            cached_result = optimizer.get_cached_result(cache_key)
            if cached_result is not None:
                logger.info(f"[CACHE] Returning cached result for {func.__name__}")
                return cached_result
            
            logger.info(f"[CACHE] Cache miss for {func.__name__}, executing function...")
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            logger.info(f"[CACHE] Function {func.__name__} completed, caching result: {type(result)}")
            optimizer.cache_result(cache_key, result)
            
            return result
        return wrapper
    return decorator

def parallel_execute(func, items: List[Any], max_workers: int = 4) -> List[Any]:
    """Execute a function on multiple items in parallel."""
    optimizer = get_performance_optimizer()
    return optimizer.parallel_process_scenes(items, lambda item, i: func(item), max_workers=max_workers)

# Performance monitoring decorator
def monitor_performance(step_name: str = None):
    """Decorator to monitor function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            optimizer = get_performance_optimizer()
            step = step_name or func.__name__
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                optimizer.record_step(step, time.time() - start_time)
                return result
            except Exception as e:
                optimizer.record_step(f"{step}_error", time.time() - start_time)
                raise
        return wrapper
    return decorator 