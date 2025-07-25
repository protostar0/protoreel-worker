from video_generator.logging_utils import get_logger
import os
import dotenv
import sys
dotenv.load_dotenv()

logger = get_logger()

# Remove FastAPI and uvicorn imports and app definition
# Remove notify_backend_task_started, notify_backend_task_finished, notify_backend_task_failed
# Only keep process_all_pending_tasks and job mode logic

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
    task = get_task_by_id(task_id)
    if not task:
        logger.error(f"[JOB MODE] Task not found: {task_id}")
        sys.exit(1)
    if getattr(task, 'status', None) == 'finished':
        logger.info(f"[JOB MODE] Task {task_id} already finished.")
        sys.exit(1)
    try:
        from video_generator.generator import generate_video_core
        payload = task.request_payload
        logger.info(f"[JOB MODE] Generating video for task {task_id}...")
        result = generate_video_core(payload, task_id=task_id)
        update_task_status(task_id, 'finished', result=result)
        logger.info(f"[JOB MODE] Task {task_id} finished. Result: {result}")
        sys.exit(0)
    except Exception as e:
        import traceback
        logger.error(f"[JOB MODE] Error processing task {task_id}: {e}\n{traceback.format_exc()}", exc_info=True)
        update_task_status(task_id, 'failed', error=f"{e}\n{traceback.format_exc()}")
        sys.exit(2)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("[ERROR] Usage: python main_worker.py <task_id>")
        sys.exit(1)
    process_all_pending_tasks() 