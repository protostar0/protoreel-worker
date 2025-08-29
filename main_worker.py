from video_generator.logging_utils import get_logger
import os
import dotenv
import sys
import signal
import psutil
import threading
import time
import gc
import argparse
from contextlib import contextmanager

dotenv.load_dotenv()

logger = get_logger()

# Global variables for error handling
current_task_id = None
task_failed = False
failure_reason = None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Protoreel Worker - Video Generation Service')
    parser.add_argument('task_id', nargs='?', help='Task ID to process')
    parser.add_argument('--api-key', dest='api_key', help='API key for authentication')
    parser.add_argument('--task-id', dest='task_id_alt', help='Task ID (alternative to positional argument)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Handle task_id from either positional argument or --task-id flag
    if args.task_id_alt and not args.task_id:
        args.task_id = args.task_id_alt
    
    return args

def clear_cache():
    """Clear all cached files to prevent stale cache issues."""
    try:
        import shutil
        import os
        from video_generator.config import Config

        # Clear cache in temp directory
        cache_dir = os.path.join(Config.TEMP_DIR, "cache")
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                logger.info("[CACHE] Cleared temp cache directory")
            except Exception as e:
                logger.warning(f"[CACHE] Failed to clear temp cache directory: {e}")

        # Also clear any .pkl files in temp directory
        temp_dir = Config.TEMP_DIR
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                if file.endswith('.pkl'):
                    file_path = os.path.join(temp_dir, file)
                    try:
                        os.remove(file_path)
                        logger.info(f"[CACHE] Removed temp cache file: {file}")
                    except Exception as e:
                        logger.warning(f"[CACHE] Failed to remove temp cache file {file}: {e}")

        # Clear local cache directory (protovideo-worker/cache/)
        from video_generator.config import Config
        local_cache_dir = os.path.join(Config.TEMP_DIR, "cache")
        if os.path.exists(local_cache_dir):
            try:
                shutil.rmtree(local_cache_dir)
                logger.info("[CACHE] Cleared local cache directory")
            except Exception as e:
                logger.warning(f"[CACHE] Failed to clear local cache directory: {e}")

        # Also clear any .pkl files in temp directory
        temp_dir = Config.TEMP_DIR
        for file in os.listdir(temp_dir):
            if file.endswith('.pkl'):
                file_path = os.path.join(temp_dir, file)
                try:
                    os.remove(file_path)
                    logger.info(f"[CACHE] Removed local cache file: {file}")
                except Exception as e:
                    logger.warning(f"[CACHE] Failed to remove local cache file {file}: {e}")

        logger.info("[CACHE] Cache clearing completed")
    except Exception as e:
        logger.error(f"[CACHE] Failed to clear cache: {e}")

def clear_cache_on_completion():
    """Clear cache when task completes (success or failure)."""
    from video_generator.config import Config
    
    # Check if cache clearing is enabled
    if not Config.ENABLE_CACHE_CLEARING:
        logger.info("[CACHE] Cache clearing disabled via ENABLE_CACHE_CLEARING=false")
        return
    
    try:
        if Config.CACHE_CLEARING_ASYNC:
            # Run cache clearing in a separate thread to avoid blocking
            import threading
            cache_thread = threading.Thread(target=clear_cache, daemon=True)
            cache_thread.start()
            # Don't wait for completion to avoid blocking
            logger.info("[CACHE] Cache clearing started in background thread")
        else:
            # Run cache clearing synchronously
            clear_cache()
            logger.info("[CACHE] Cache clearing completed synchronously")
    except Exception as e:
        logger.error(f"[CACHE] Error during cache clearing: {e}")

def signal_handler(signum, frame):
    """Handle process termination signals."""
    global current_task_id, task_failed, failure_reason
    
    signal_name = signal.Signals(signum).name
    failure_reason = f"Process terminated by signal: {signal_name} (SIG{signum})"
    task_failed = True
    
    logger.error(f"[SIGNAL] Received {signal_name} signal. Marking task {current_task_id} as failed.")
    
    if current_task_id:
        try:
            from db import update_task_status
            update_task_status(current_task_id, 'failed', error=failure_reason)
            logger.info(f"[SIGNAL] Task {current_task_id} marked as failed due to signal {signal_name}")
        except Exception as e:
            logger.error(f"[SIGNAL] Failed to update task status: {e}")
    
    # Clear cache on signal termination
    try:
        clear_cache_on_completion()
    except Exception as e:
        logger.error(f"[SIGNAL] Failed to clear cache on signal termination: {e}")
    
    # Exit gracefully
    sys.exit(1)

def memory_monitor():
    """Monitor memory usage and proactively clear cache to prevent container termination."""
    global task_failed, failure_reason
    from video_generator.config import Config
    
    # Check if memory monitoring is enabled
    if not Config.ENABLE_MEMORY_MONITORING:
        logger.info("[MEMORY] Memory monitoring disabled via ENABLE_MEMORY_MONITORING=false")
        return
    
    process = psutil.Process()
    last_cleanup_time = 0
    cleanup_cooldown = Config.MEMORY_CLEANUP_COOLDOWN
    
    while not task_failed:
        try:
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            current_time = time.time()
            
            # Only perform cleanup if enough time has passed since last cleanup
            if current_time - last_cleanup_time < cleanup_cooldown:
                time.sleep(15)  # Check less frequently during cooldown
                continue
            
            if memory_mb > Config.MEMORY_WARNING_THRESHOLD_MB:  # Warning threshold
                logger.warning(f"[MEMORY] High memory usage: {memory_mb:.1f}MB")
                
                # Proactively clear cache to prevent container termination
                if Config.ENABLE_CACHE_CLEARING:
                    try:
                        clear_cache_on_completion()
                        # Force garbage collection
                        import gc
                        gc.collect()
                        last_cleanup_time = current_time
                        logger.info(f"[MEMORY] Proactively cleared cache and forced GC at {memory_mb:.1f}MB to prevent container termination")
                    except Exception as e:
                        logger.error(f"[MEMORY] Failed to clear cache proactively: {e}")
            
            elif memory_mb > Config.MEMORY_CRITICAL_THRESHOLD_MB:  # Critical threshold
                logger.error(f"[MEMORY] Critical memory usage: {memory_mb:.1f}MB - clearing cache aggressively")
                
                # Aggressive cache clearing
                if Config.ENABLE_CACHE_CLEARING:
                    try:
                        clear_cache_on_completion()
                        # Force garbage collection multiple times
                        import gc
                        gc.collect()
                        gc.collect()
                        last_cleanup_time = current_time
                        logger.info(f"[MEMORY] Aggressively cleared cache and forced multiple GC at {memory_mb:.1f}MB")
                    except Exception as e:
                        logger.error(f"[MEMORY] Failed to clear cache aggressively: {e}")
                
            elif memory_mb > Config.MEMORY_EMERGENCY_THRESHOLD_MB:  # Emergency threshold
                logger.error(f"[MEMORY] EMERGENCY memory usage: {memory_mb:.1f}MB - emergency cleanup")
                
                # Emergency cleanup
                if Config.ENABLE_CACHE_CLEARING:
                    try:
                        clear_cache_on_completion()
                        # Force garbage collection multiple times
                        import gc
                        gc.collect()
                        gc.collect()
                        gc.collect()
                        # Clear all caches
                        from video_generator.performance_optimizer import get_performance_optimizer
                        optimizer = get_performance_optimizer()
                        optimizer.clear_all_caches()
                        last_cleanup_time = current_time
                        logger.info(f"[MEMORY] Emergency cleanup completed at {memory_mb:.1f}MB")
                    except Exception as e:
                        logger.error(f"[MEMORY] Failed emergency cleanup: {e}")
            
            time.sleep(Config.MEMORY_MONITOR_INTERVAL)  # Use configurable interval
        except Exception as e:
            logger.error(f"[MEMORY] Memory monitoring error: {e}")
            break

@contextmanager
def error_recovery_context(task_id):
    """Context manager for comprehensive error handling."""
    global current_task_id, task_failed, failure_reason
    
    current_task_id = task_id
    task_failed = False
    failure_reason = None
    
    # Set up signal handlers
    original_handlers = {}
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGKILL]:
        try:
            original_handlers[sig] = signal.signal(sig, signal_handler)
        except (OSError, ValueError):
            pass  # Some signals might not be available
    
    # Start memory monitoring in background
    memory_thread = threading.Thread(target=memory_monitor, daemon=True)
    memory_thread.start()
    
    try:
        yield
    except Exception as e:
        import traceback
        failure_reason = f"Exception: {str(e)}\n{traceback.format_exc()}"
        task_failed = True
        logger.error(f"[ERROR] Task {task_id} failed: {failure_reason}")
        raise
    finally:
        # Clean up
        task_failed = True  # Stop memory monitoring
        current_task_id = None
        
        # Restore original signal handlers
        for sig, handler in original_handlers.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError):
                pass

def process_all_pending_tasks():
    import sys
    from db import get_task_by_id, update_task_status
    
    logger.info("[JOB MODE] Starting process_all_pending_tasks...")
    
    # Parse arguments manually for backward compatibility
    task_id = None
    api_key = None
    verbose = False
    debug = False
    config_file = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == "--api-key" and i + 1 < len(sys.argv):
            api_key = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--api-key="):
            api_key = arg.split("=", 1)[1]
            i += 1
        elif arg == "--task-id" and i + 1 < len(sys.argv):
            task_id = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--task-id="):
            task_id = arg.split("=", 1)[1]
            i += 1
        elif arg in ["--verbose", "-v"]:
            verbose = True
            i += 1
        elif arg == "--debug":
            debug = True
            i += 1
        elif arg == "--config" and i + 1 < len(sys.argv):
            config_file = sys.argv[i + 1]
            i += 2
        elif arg.startswith("--config="):
            config_file = arg.split("=", 1)[1]
            i += 1
        elif arg == "--help" or arg == "-h":
            print("[JOB MODE] Usage: python main_worker.py <task_id> or --task-id=<task_id>")
            print("[JOB MODE] Optional: --api-key <key> --verbose --debug --config <file>")
            sys.exit(0)
        elif not arg.startswith("-") and task_id is None:
            task_id = arg
            i += 1
        else:
            i += 1
    
    # Set environment variables for arguments
    if api_key:
        os.environ['API_KEY'] = api_key
        logger.info("[ARGS] API key set from command line argument")
    
    if verbose:
        os.environ['VERBOSE'] = 'true'
        logger.info("[ARGS] Verbose logging enabled")
    
    if debug:
        os.environ['DEBUG'] = 'true'
        logger.info("[ARGS] Debug mode enabled")
    
    if config_file:
        os.environ['CONFIG_FILE'] = config_file
        logger.info(f"[ARGS] Configuration file set to: {config_file}")
    
    if not task_id:
        logger.error("[JOB MODE] No task_id provided. Usage: python main_worker.py <task_id> or --task-id=<task_id>")
        logger.error("[JOB MODE] Optional: --api-key <key> --verbose --debug --config <file>")
        sys.exit(1)
    
    logger.info(f"[JOB MODE] Processing task_id: {task_id}")
    
    # Get task from database
    task = get_task_by_id(task_id)
    if not task:
        logger.error(f"[JOB MODE] Task not found: {task_id}")
        sys.exit(1)
    
    if getattr(task, 'status', None) == 'finished':
        logger.info(f"[JOB MODE] Task {task_id} already finished.")
        sys.exit(0)
    
    # Update task status to in progress
    try:
        update_task_status(task_id, 'inprogress')
        logger.info(f"[JOB MODE] Task {task_id} status updated to inprogress")
    except Exception as e:
        logger.error(f"[JOB MODE] Failed to update task status to inprogress: {e}")
        sys.exit(1)
    
    # Process task with comprehensive error handling
    with error_recovery_context(task_id):
        try:
            from video_generator.generator import generate_video_core
            import gc
            
            payload = task.request_payload
            if not payload:
                raise ValueError("Task payload is empty or None")
            
            logger.info(f"[JOB MODE] Generating video for task {task_id}...")
            logger.info(f"[JOB MODE] Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
            logger.info(f"[JOB MODE]  video payload {task_id}: {payload}")

            # Force garbage collection before starting
            gc.collect()
            
            result = generate_video_core(payload, task_id=task_id)
            
            if not result:
                raise ValueError("Video generation returned empty result")
            
            # Force garbage collection after video generation
            gc.collect()
            logger.info(f"[JOB MODE] Memory optimized after video generation")
            
            # Update task status to finished
            update_task_status(task_id, 'finished', result=result)
            logger.info(f"[JOB MODE] Task {task_id} finished successfully. Result: {result}")
            
            # Deduct credits for completed task
            try:
                from db import get_user_by_api_key, update_credits
                
                # Get the user's API key from the task
                user_api_key = task.user_api_key
                logger.info(f"[CREDITS] Deducting credits for user API key: {user_api_key[:8]}...")
                
                # Calculate credits to deduct based on completed scenes
                credits_to_deduct = 0
                if payload and 'scenes' in payload:
                    scenes = payload['scenes']
                    for scene in scenes:
                        scene_type = scene.get('type', 'unknown')
                        if scene_type == 'video':
                            if scene.get('prompt_video'):
                                credits_to_deduct += 5  # AI video generation
                                logger.info(f"[CREDITS] Scene {scene_type}: AI video generation (5 credits)")
                            elif scene.get('video_url'):
                                credits_to_deduct += 1  # Existing video
                                logger.info(f"[CREDITS] Scene {scene_type}: Existing video (1 credit)")
                            else:
                                credits_to_deduct += 1  # Default video scene
                                logger.info(f"[CREDITS] Scene {scene_type}: Default video (1 credit)")
                        else:
                            credits_to_deduct += 1  # Image scenes
                            logger.info(f"[CREDITS] Scene {scene_type}: Image scene (1 credit)")
                
                # Deduct credits from user account
                if credits_to_deduct > 0:
                    update_credits(user_api_key, -credits_to_deduct)
                    logger.info(f"[CREDITS] Successfully deducted {credits_to_deduct} credits from user account")
                    
                    # Get updated user info for logging
                    user_info = get_user_by_api_key(user_api_key)
                    if user_info:
                        remaining_credits = user_info.get('credits', 0)
                        logger.info(f"[CREDITS] User remaining credits: {remaining_credits}")
                else:
                    logger.warning(f"[CREDITS] No credits calculated for deduction")
                    
            except Exception as credit_error:
                logger.error(f"[CREDITS] Failed to deduct credits: {credit_error}")
                # Don't fail the task for credit deduction errors
                # The task completed successfully, credits can be handled separately
            
            # Clear cache on successful completion
            clear_cache_on_completion()
            
        except Exception as e:
            import traceback
            error_msg = f"Task processing failed: {str(e)}\n{traceback.format_exc()}"
            
            logger.error(f"[JOB MODE] Error processing task {task_id}: {error_msg}", exc_info=True)
            
            # Update task status to failed
            try:
                update_task_status(task_id, 'failed', error=error_msg)
                logger.info(f"[JOB MODE] Task {task_id} marked as failed")
                
                # Refund any credits that were reserved for this failed task
                try:
                    from db import get_user_by_api_key, update_credits
                    
                    # Get the user's API key from the task
                    user_api_key = task.user_api_key
                    logger.info(f"[CREDITS] Processing credit refund for failed task, user API key: {user_api_key[:8]}...")
                    
                    # Calculate credits to refund based on failed task scenes
                    credits_to_refund = 0
                    if payload and 'scenes' in payload:
                        scenes = payload['scenes']
                        for scene in scenes:
                            scene_type = scene.get('type', 'unknown')
                            if scene_type == 'video':
                                if scene.get('prompt_video'):
                                    credits_to_refund += 5  # AI video generation
                                    logger.info(f"[CREDITS] Failed scene {scene_type}: AI video generation (5 credits refund)")
                                elif scene.get('video_url'):
                                    credits_to_refund += 1  # Existing video
                                    logger.info(f"[CREDITS] Failed scene {scene_type}: Existing video (1 credit refund)")
                                else:
                                    credits_to_refund += 1  # Default video scene
                                    logger.info(f"[CREDITS] Failed scene {scene_type}: Default video (1 credit refund)")
                            else:
                                credits_to_refund += 1  # Image scenes
                                logger.info(f"[CREDITS] Failed scene {scene_type}: Image scene (1 credit refund)")
                    
                    # Refund credits to user account
                    if credits_to_refund > 0:
                        update_credits(user_api_key, credits_to_refund)
                        logger.info(f"[CREDITS] Successfully refunded {credits_to_refund} credits for failed task")
                        
                        # Get updated user info for logging
                        user_info = get_user_by_api_key(user_api_key)
                        if user_info:
                            remaining_credits = user_info.get('credits', 0)
                            logger.info(f"[CREDITS] User remaining credits after refund: {remaining_credits}")
                    else:
                        logger.warning(f"[CREDITS] No credits calculated for refund")
                        
                except Exception as credit_error:
                    logger.error(f"[CREDITS] Failed to refund credits for failed task: {credit_error}")
                    # Don't fail the error handling for credit refund errors
                    # The task is already marked as failed
                
            except Exception as update_error:
                logger.error(f"[JOB MODE] Failed to update task status to failed: {update_error}")
            
            # Clear cache on failure
            clear_cache_on_completion()
            
            # Re-raise the exception to trigger the context manager's error handling
            raise
    
    # Check if task failed due to external factors (signals, memory, etc.)
    if task_failed and failure_reason:
        logger.error(f"[JOB MODE] Task {task_id} failed due to external factor: {failure_reason}")
        try:
            update_task_status(task_id, 'failed', error=failure_reason)
            
            # Refund any credits that were reserved for this externally failed task
            try:
                from db import get_user_by_api_key, update_credits
                
                # Get the user's API key from the task
                user_api_key = task.user_api_key
                logger.info(f"[CREDITS] Processing credit refund for external failure, user API key: {user_api_key[:8]}...")
                
                # Calculate credits to refund based on failed task scenes
                credits_to_refund = 0
                if payload and 'scenes' in payload:
                    scenes = payload['scenes']
                    for scene in scenes:
                        scene_type = scene.get('type', 'unknown')
                        if scene_type == 'video':
                            if scene.get('prompt_video'):
                                credits_to_refund += 5  # AI video generation
                                logger.info(f"[CREDITS] External failure scene {scene_type}: AI video generation (5 credits refund)")
                            elif scene.get('video_url'):
                                credits_to_refund += 1  # Existing video
                                logger.info(f"[CREDITS] External failure scene {scene_type}: Existing video (1 credit refund)")
                            else:
                                credits_to_refund += 1  # Default video scene
                                logger.info(f"[CREDITS] External failure scene {scene_type}: Default video (1 credit refund)")
                        else:
                            credits_to_refund += 1  # Image scenes
                            logger.info(f"[CREDITS] External failure scene {scene_type}: Image scene (1 credit refund)")
                
                # Refund credits to user account
                if credits_to_refund > 0:
                    update_credits(user_api_key, credits_to_refund)
                    logger.info(f"[CREDITS] Successfully refunded {credits_to_refund} credits for external failure")
                    
                    # Get updated user info for logging
                    user_info = get_user_by_api_key(user_api_key)
                    if user_info:
                        remaining_credits = user_info.get('credits', 0)
                        logger.info(f"[CREDITS] User remaining credits after external failure refund: {remaining_credits}")
                else:
                    logger.warning(f"[CREDITS] No credits calculated for external failure refund")
                    
            except Exception as credit_error:
                logger.error(f"[CREDITS] Failed to refund credits for external failure: {credit_error}")
                # Don't fail the error handling for credit refund errors
                # The task is already marked as failed
            
        except Exception as e:
            logger.error(f"[JOB MODE] Failed to update task status after external failure: {e}")
        
        # Clear cache on external failure
        clear_cache_on_completion()
        
        sys.exit(2)
    
    logger.info(f"[JOB MODE] Task {task_id} completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Set API key if provided
    if args.api_key:
        os.environ['API_KEY'] = args.api_key
        logger.info("[ARGS] API key set from command line argument")
    
    # Set environment variables for other arguments
    if args.verbose:
        os.environ['VERBOSE'] = 'true'
        logger.info("[ARGS] Verbose logging enabled")
    
    if args.debug:
        os.environ['DEBUG'] = 'true'
        logger.info("[ARGS] Debug mode enabled")
    
    if args.config:
        os.environ['CONFIG_FILE'] = args.config
        logger.info(f"[ARGS] Configuration file set to: {args.config}")
    
    # Check if task_id is provided
    if not args.task_id:
        print("[ERROR] Usage: python main_worker.py <task_id> or python main_worker.py --task-id <task_id>")
        print("[ERROR] Optional: --api-key <key> --verbose --debug --config <file>")
        sys.exit(1)
    
    # Process the task
    process_all_pending_tasks() 