import os
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

def fake_upload_to_r2(local_file_path, bucket_name, object_key):
    # Return a fake R2 URL
    return f"https://fake-r2-url.com/{object_key}"

client = TestClient(app)

def test_generate_task_r2_url(monkeypatch):
    # Patch upload_to_r2 to avoid real upload
    monkeypatch.setattr("video_generator.cleanup_utils.upload_to_r2", fake_upload_to_r2)
    # Prepare a minimal video request
    video_request = {
        "output_filename": f"test_{uuid.uuid4().hex}.mp4",
        "scenes": [
            {
                "type": "image",
                "image": "https://via.placeholder.com/512",
                "duration": 2
            }
        ]
    }
    # Set up a test API key (assume test user exists with credits)
    api_key = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
    headers = {"x-api-key": api_key}
    # Start a generation task
    response = client.post("/generate-task", json=video_request, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]
    # Poll for task completion
    for _ in range(30):
        status_resp = client.get(f"/task-status/{task_id}", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        if status_data["status"] == "finished":
            # Should only have r2_url, not download_url
            assert "r2_url" in status_data
            assert status_data["r2_url"].startswith("https://fake-r2-url.com/")
            assert "download_url" not in status_data
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Task failed: {status_data.get('error')}")
        else:
            import time; time.sleep(1)
    else:
        pytest.fail("Task did not finish in time")

def test_generate_task_real_r2():
    r2_base = os.environ.get("R2_PUBLIC_BASE_URL")
    if not r2_base:
        pytest.skip("R2_PUBLIC_BASE_URL not set; skipping real R2 upload test.")
    video_request = {
        "output_filename": f"testreal_{uuid.uuid4().hex}.mp4",
        "scenes": [
            {
                "type": "image",
                "image": "https://via.placeholder.com/512",
                "duration": 2
            }
        ]
    }
    api_key = os.environ.get("PROTOVIDEO_API_KEY", "N8S6R_TydmHr58LoUzYZf9v2gRkcfWZemz1zWZ5WMkE")
    headers = {"x-api-key": api_key}
    response = client.post("/generate-task", json=video_request, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    task_id = data["task_id"]
    for _ in range(60):
        status_resp = client.get(f"/task-status/{task_id}", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        if status_data["status"] == "finished":
            assert "r2_url" in status_data
            assert status_data["r2_url"].startswith(r2_base.rstrip("/"))
            assert "download_url" not in status_data
            break
        elif status_data["status"] == "failed":
            pytest.fail(f"Task failed: {status_data.get('error')}")
        else:
            import time; time.sleep(2)
    else:
        pytest.fail("Task did not finish in time") 