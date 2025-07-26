from video_generator.logging_utils import get_logger
import os
import dotenv
import sys
import signal
import psutil
import threading
import time
import gc
from contextlib import contextmanager

dotenv.load_dotenv()

logger = get_logger()

# Global variables for error handling
current_task_id = None
task_failed = False
failure_reason = None

def clear_cache():
    """Clear all cached files to prevent stale cache issues."""
    try:
        import shutil
        import os
        from video_generator.config import Config
        
        # Clear cache in temp directory
        cache_dir = os.path.join(Config.TEMP_DIR, "cache")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            logger.info("[CACHE] Cleared temp cache directory")
        
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
        local_cache_dir = os.path.join(os.getcwd(), "cache")
        if os.path.exists(local_cache_dir):
            try:
                shutil.rmtree(local_cache_dir)
                logger.info("[CACHE] Cleared local cache directory")
            except Exception as e:
                logger.warning(f"[CACHE] Failed to clear local cache directory: {e}")
        
        # Also clear any .pkl files in current directory
        current_dir = os.getcwd()
        for file in os.listdir(current_dir):
            if file.endswith('.pkl'):
                file_path = os.path.join(current_dir, file)
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
    try:
        clear_cache()
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
    """Monitor memory usage and log warnings only - don't fail tasks."""
    global task_failed, failure_reason
    process = psutil.Process()
    while not task_failed:
        try:
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            if memory_mb > 3000:  # Warning at 3GB
                logger.warning(f"[MEMORY] High memory usage: {memory_mb:.1f}MB")
            
            if memory_mb > 6000:  # Critical warning at 6GB (but don't fail)
                logger.error(f"[MEMORY] Critical memory usage: {memory_mb:.1f}MB - continuing task")
                
                # Clear cache on critical memory usage but don't fail
                try:
                    clear_cache_on_completion()
                    logger.info(f"[MEMORY] Cleared cache due to high memory usage")
                except Exception as e:
                    logger.error(f"[MEMORY] Failed to clear cache on critical memory: {e}")
                
                # Continue processing - don't set task_failed = True
                
            time.sleep(15)  # Check every 15 seconds
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
    
    # Accept task_id as positional argument or --task-id=... flag
    task_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("--task-id="):
            task_id = arg.split("=", 1)[1]
            break
        elif not arg.startswith("-") and task_id is None:
            task_id = arg
    
    if not task_id:
        logger.error("[JOB MODE] No task_id provided. Usage: python main_worker.py <task_id> or --task-id=<task_id>")
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
            
            payload = task.request_payload
            if not payload:
                raise ValueError("Task payload is empty or None")
            
            logger.info(f"[JOB MODE] Generating video for task {task_id}...")
            logger.info(f"[JOB MODE] Payload keys: {list(payload.keys()) if isinstance(payload, dict) else 'Not a dict'}")
            
            # Force garbage collection before starting
            gc.collect()
            
            result = generate_video_core(payload, task_id=task_id)
            
            if not result:
                raise ValueError("Video generation returned empty result")
            
            # Update task status to finished
            update_task_status(task_id, 'finished', result=result)
            logger.info(f"[JOB MODE] Task {task_id} finished successfully. Result: {result}")
            
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
        except Exception as e:
            logger.error(f"[JOB MODE] Failed to update task status after external failure: {e}")
        
        # Clear cache on external failure
        clear_cache_on_completion()
        
        sys.exit(2)
    
    logger.info(f"[JOB MODE] Task {task_id} completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("[ERROR] Usage: python main_worker.py <task_id>")
        sys.exit(1)
    process_all_pending_tasks() 