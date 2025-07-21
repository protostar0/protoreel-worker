from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from video_generator.generator import generate_video_core
from video_generator.logging_utils import get_logger
import requests
import os
import dotenv
dotenv.load_dotenv()

logger = get_logger()

app = FastAPI(title="ProtoVideo Worker Service")

def notify_backend_task_started(task_id):
    backend_url = os.environ.get("BACKEND_API_URL", "http://localhost:8080")
    worker_api_key = os.environ.get("WORKER_API_KEY", "kfoG9qjBBfsoo3GcpMIKjsojQBLCX5WYK_UHCOMatoY")
    payload = {"task_id": task_id}
    headers = {"Authorization": f"Bearer {worker_api_key}"}
    try:
        response = requests.post(f"{backend_url}/worker/task-started", json=payload, headers=headers)
        logger.info(f"Task started webhook response: {response.status_code}, {response.text}", extra={"task_id": task_id})
    except Exception as e:
        logger.error(f"Failed to notify backend of task started: {str(e)}", extra={"task_id": task_id})

def notify_backend_task_finished(task_id, video_url):
    backend_url = os.environ.get("BACKEND_API_URL", "http://localhost:8080")
    worker_api_key = os.environ.get("WORKER_API_KEY", "kfoG9qjBBfsoo3GcpMIKjsojQBLCX5WYK_UHCOMatoY")
    payload = {
        "task_id": task_id,
        "video_url": video_url
    }
    headers = {"Authorization": f"Bearer {worker_api_key}"}
    try:
        response = requests.post(f"{backend_url}/worker/task-finished", json=payload, headers=headers)
        logger.info(f"Task finished webhook response: {response.status_code}, {response.text}", extra={"task_id": task_id})
    except Exception as e:
        logger.error(f"Failed to notify backend of finished task: {str(e)}", extra={"task_id": task_id})

def notify_backend_task_failed(task_id, error):
    backend_url = os.environ.get("BACKEND_API_URL", "http://localhost:8080")
    worker_api_key = os.environ.get("WORKER_API_KEY", "kfoG9qjBBfsoo3GcpMIKjsojQBLCX5WYK_UHCOMatoY")
    payload = {"task_id": task_id, "error": error}
    headers = {"Authorization": f"Bearer {worker_api_key}"}
    try:
        response = requests.post(f"{backend_url}/worker/task-failed", json=payload, headers=headers)
        logger.info(f"Task failed webhook response: {response.status_code}, {response.text}", extra={"task_id": task_id})
    except Exception as e:
        logger.error(f"Failed to notify backend of task failed: {str(e)}", extra={"task_id": task_id})

@app.post("/process-task")
async def process_task(request: Request):
    payload = await request.json()
    task_id = payload["task_id"]
    request_dict = payload["request_dict"]
    try:
        notify_backend_task_started(task_id)
        # No direct DB update; rely on webhook
        result = generate_video_core(request_dict, task_id=task_id)
        video_url = result.get("r2_url")
        if video_url:
            notify_backend_task_finished(task_id, video_url)
        return {"status": "finished", "result": result}
    except Exception as e:
        notify_backend_task_failed(task_id, str(e))
        return {"status": "failed", "error": str(e)} 