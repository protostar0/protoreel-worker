import os
import uuid
import requests
import time
import tempfile
from unittest.mock import patch, MagicMock
from video_generator.audio_utils import generate_narration
import subprocess
from db import create_task, get_task_by_id, update_task_status, SessionLocal, Task

def delete_task(task_id):
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            db.delete(task)
            db.commit()
    finally:
        db.close()

def test_worker_job_mode():
    # 1. Create a task in the DB
    task_id = str(uuid.uuid4())
    user_api_key = "78c33510dbea4817910ec221c48191c1"
    payload = {
  "output_filename": "comprehensive_text_overlay_demo.mp4",
  "scenes": [
    # Scene 1: Title preset with top position
    {
      "type": "image",
      "prompt_image": "A majestic mountain landscape at sunrise",
      "duration": 6,
      "text": {
        "content": "MOUNTAIN ADVENTURE",
        "preset": "title",
        "position": "top"
      }
    },
    
    # Scene 2: Custom configuration with center position
    {
      "type": "image", 
      "prompt_image": "A bustling city street with neon lights",
      "duration": 6,
      "text": {
        "content": "Urban Life",
        "position": "center",
        "fontsize": 80,
        "color": "yellow",
        "stroke_color": "black",
        "stroke_width": 3
      }
    },
    
    # Scene 3: Subtitle preset with bottom position
    {
      "type": "image",
      "prompt_image": "A peaceful beach with crystal clear water",
      "duration": 6,
      "text": {
        "content": "Tranquility Awaits",
        "preset": "subtitle",
        "position": "bottom"
      }
    },
    
    # Scene 4: Caption preset with bottom-left position
    {
      "type": "image",
      "prompt_image": "A modern office building with glass facade",
      "duration": 6,
      "text": {
        "content": "Professional Excellence",
        "preset": "caption",
        "position": "bottom-left"
      }
    },
    
    # Scene 5: Callout preset with center position
    {
      "type": "image",
      "prompt_image": "A vibrant marketplace with colorful stalls",
      "duration": 6,
      "text": {
        "content": "SPECIAL OFFER!",
        "preset": "callout",
        "position": "center"
      }
    },
    
    # Scene 6: Watermark preset with bottom-right position
    {
      "type": "image",
      "prompt_image": "A serene forest path with dappled sunlight",
      "duration": 6,
      "text": {
        "content": "© 2024 ProtoReel",
        "preset": "watermark",
        "position": "bottom-right"
      }
    },
    
    # Scene 7: Top-left position with custom styling
    {
      "type": "image",
      "prompt_image": "A futuristic city skyline at night",
      "duration": 6,
      "text": {
        "content": "Future City",
        "position": "top-left",
        "fontsize": 60,
        "color": "cyan",
        "stroke_color": "darkblue",
        "stroke_width": 2
      }
    },
    
    # Scene 8: Top-right position with custom styling
    {
      "type": "image",
      "prompt_image": "A cozy coffee shop interior",
      "duration": 6,
      "text": {
        "content": "Coffee Time",
        "position": "top-right",
        "fontsize": 50,
        "color": "brown",
        "stroke_color": "white",
        "stroke_width": 1
      }
    },
    
    # Scene 9: Custom configuration with fade_in animation
    {
      "type": "image",
      "prompt_image": "A starry night sky with aurora borealis",
      "duration": 6,
      "text": {
        "content": "Magical Night",
        "position": "center",
        "fontsize": 70,
        "color": "purple",
        "stroke_color": "white",
        "stroke_width": 2,
        "animation_type": "fade_in"
      }
    },
    
    # Scene 10: Custom configuration with fade_out animation
    {
      "type": "image",
      "prompt_image": "A sunset over calm ocean waters",
      "duration": 6,
      "text": {
        "content": "Peaceful Sunset",
        "position": "center",
        "fontsize": 65,
        "color": "orange",
        "stroke_color": "darkred",
        "stroke_width": 2,
        "animation_type": "fade_out"
      }
    },
    
    # Scene 11: Custom configuration with fade_in_out animation
    {
      "type": "image",
      "prompt_image": "A field of blooming sunflowers",
      "duration": 6,
      "text": {
        "content": "Nature's Beauty",
        "position": "center",
        "fontsize": 75,
        "color": "gold",
        "stroke_color": "darkgreen",
        "stroke_width": 3,
        "animation_type": "fade_in_out"
      }
    },
    
    # Scene 12: Large font size test
    {
      "type": "image",
      "prompt_image": "A dramatic stormy sky with lightning",
      "duration": 6,
      "text": {
        "content": "POWER",
        "position": "center",
        "fontsize": 120,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 4
      }
    },
    
    # Scene 13: Small font size test
    {
      "type": "image",
      "prompt_image": "A delicate flower garden",
      "duration": 6,
      "text": {
        "content": "Delicate Details",
        "position": "bottom",
        "fontsize": 20,
        "color": "pink",
        "stroke_color": "white",
        "stroke_width": 1
      }
    },
    
    # Scene 14: Multiple colors and stroke combinations
    {
      "type": "image",
      "prompt_image": "A rainbow over rolling hills",
      "duration": 6,
      "text": {
        "content": "Colorful World",
        "position": "center",
        "fontsize": 55,
        "color": "red",
        "stroke_color": "yellow",
        "stroke_width": 3
      }
    },
    
    # Scene 15: No stroke test
    {
      "type": "image",
      "prompt_image": "A minimalist white room with soft lighting",
      "duration": 6,
      "text": {
        "content": "Minimalist Design",
        "position": "center",
        "fontsize": 45,
        "color": "black",
        "stroke_color": "none",
        "stroke_width": 0
      }
    }
  ]
}
    create_task(task_id, user_api_key, payload)
    print(f"PYTHONPATH=. python main_worker.py --task-id {task_id}  --api-key {user_api_key}")

    # 2. Run the worker as a subprocess (simulate Cloud Run Job)
    # result = subprocess.run(
    #     ["python", "main_worker.py", task_id],
    #     env={**os.environ, "JOB_MODE": "1"},
    #     capture_output=True,
    #     text=True
    # )
    # print("Worker stdout:", result.stdout)
    # print("Worker stderr:", result.stderr)
    # assert result.returncode == 0, f"Worker failed with exit code {result.returncode}"

    # # 3. Check the DB for task status/result
    # task = get_task_by_id(task_id)
    # assert task.status == "finished"
    # assert task.result is not None
    # r2_url = task.result.get("r2_url")
    # print("R2 URL:", r2_url)
    # assert r2_url and r2_url.startswith("http")

    # # 4. Cleanup: delete the test task from the DB
    # delete_task(task_id)
    # print("Test task deleted from DB.")

def test_worker_process_task():
    WORKER_URL = os.environ.get("WORKER_URL") or "http://localhost:8080/process-task"
    # Simulate a task_id and a minimal valid request_dict
    WORKER_URL = "http://localhost:8080/process-task"
    # task_id = str(uuid.uuid4())
    task_id= "7003c133-9b50-40f8-90a9-c3be2be60848"
    payload = {
    "task_id": "7003c133-9b50-40f8-90a9-c3be2be60848",
    "request_dict": {
        "output_filename": "test_worker_video2.mp4",
        "scenes": [
            {
                "type": "image",
                "narration_text": "In a monumental announcement, President Donald Trump has revealed a massive trade deal with Japan, calling it the 'largest deal in history with Japan.' This landmark agreement promises to reshape global economic partnerships.",
                "prompt_image": "A photo-realistic image of President holding a press conference with the flags of the United States and Japan in the background, emphasizing a momentous announcement.",
                "image_provider": "gemini",
                "subtitle": True,
                "animation_preset": "energetic",
                "animation_darken_factor": 0.3,
                "animation_drift_px": 65,
                "animation_osc_px": 40
            },
            # {
            #     "type": "image",
            #     "narration_text": "The deal includes a staggering $550 billion investment from Japan into the United States. This infusion of funds is expected to boost various sectors and create numerous jobs, potentially strengthening ties between the two nations.",
            #     "prompt_image": "A photo-realistic image of a bustling New York City skyline with symbolic dollar signs and yen symbols overlayed, representing financial investment.",
            #     "image_provider": "gemini",
            #     "subtitle": True
            # },
            # {
            #     "type": "image",
            #     "narration_text": "Both countries will implement a 15% tariff on each other's goods, including crucial sectors such as vehicles and agricultural products. While this aims to level the playing field, experts warn to carefully evaluate its long-term benefits.",
            #     "prompt_image": "A photo-realistic image of shipping containers at a busy port with agricultural products and cars visible, representing international trade and tariffs.",
            #     "image_provider": "gemini",
            #     "subtitle": True
            # },
            # {
            #     "type": "image",
            #     "narration_text": "As full details of the agreement are still unfolding, stay tuned for updates. Follow the hashtags #USJapanDeal and #TrumpTradeDeal for the latest news. Experts continue to analyze the potential impacts on global business dynamics.",
            #     "prompt_image": "A photo-realistic image of a group of analysts in an office with a world map and international news screens visible, symbolizing ongoing discussions and evaluations.",
            #     "image_provider": "gemini",
            #     "subtitle": True
            # }
        ]
    }
}
    response = requests.post(WORKER_URL, json=payload)
    assert response.status_code == 200, f"Worker returned status {response.status_code}: {response.text}"
    data = response.json()
    assert data["status"] == "accepted", f"Worker did not accept: {data}"
    print("Worker accepted the task for background processing.")

# Optionally, add polling for task completion here if needed.

def test_generate_narration_with_audio_prompt_url():
    # Prepare a fake audio prompt file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        tmp.write(b"fake wav data")
        audio_prompt_path = tmp.name
    audio_prompt_url = f"file://{audio_prompt_path}"

    # Patch requests.get to simulate download
    def fake_requests_get(url, stream=True, timeout=60):
        class FakeResponse:
            def raise_for_status(self):
                pass
            def iter_content(self, chunk_size=8192):
                with open(audio_prompt_path, 'rb') as f:
                    yield f.read()
        return FakeResponse()

    # Patch ChatterboxTTS and ta.save
    with patch("video_generator.audio_utils.requests.get", side_effect=fake_requests_get), \
         patch("video_generator.audio_utils.ChatterboxTTS.from_pretrained") as mock_tts, \
         patch("video_generator.audio_utils.ta.save") as mock_save:
        mock_model = MagicMock()
        mock_model.generate.return_value = b"fake wav"
        mock_model.sr = 16000
        mock_tts.return_value = mock_model
        # Should not raise
        out_path = generate_narration("test text", audio_prompt_url=audio_prompt_url)
        assert out_path.endswith(".mp3")
        mock_model.generate.assert_called_once()
        # Check that audio_prompt_path was passed
        called_kwargs = mock_model.generate.call_args[1]
        assert "audio_prompt_path" in called_kwargs
        assert os.path.exists(out_path)
    # Cleanup
    os.remove(audio_prompt_path)
    if os.path.exists(out_path):
        os.remove(out_path)

if __name__ == "__main__":
    test_worker_job_mode()
    # test_generate_narration_with_audioprompt_url()