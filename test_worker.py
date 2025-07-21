import os
import uuid
import requests
import time

def test_worker_process_task():
    WORKER_URL = os.environ.get("WORKER_URL") or "http://localhost:8000/process-task"
    # Simulate a task_id and a minimal valid request_dict
    # task_id = str(uuid.uuid4())
    task_id= "7003c133-9b50-40f8-90a9-c3be2be60848"
    payload = {
        "task_id": task_id,
        "request_dict": {
            "output_filename": "test_worker_video.mp4",
            "scenes": [
                {
                    "type": "image",
                    "image": "https://images.pexels.com/photos/30572214/pexels-photo-30572214.jpeg",
                    "duration": 5,
                    "narration_text": "This is a test narration for the worker.",
                    "subtitle": True
                }
            ]
        }
    }
    response = requests.post(WORKER_URL, json=payload)
    assert response.status_code == 200, f"Worker returned status {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "accepted", f"Worker did not accept: {data}"
    print("Worker accepted the task for background processing.")

# Optionally, add polling for task completion here if needed.
    
test_worker_process_task()