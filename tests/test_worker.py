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
    user_api_key = "test_api_key"
    payload = {
      "output_filename":"crypto_optimism.mp4",
        "scenes": [
    {
      "type": "video",
      "video_url":"https://storage.cdn-luma.com/dream_machine/06d5cd11-4f6c-46c0-87b2-8ca9ad0de90c/4a00db94-84ca-4b6c-bf1b-c1c7a6e3226b_resultaf9af1a7bc3134be.mp4",
    #   "prompt_video": "A vibrant table full of colorful fruits and vegetables under natural sunlight, cinematic close-up of fresh produce, high resolution, 16:9 aspect ratio",
      "narration_text": "Did you know your plate’s colors can reveal how healthy your meal is?",
        "subtitle": True,

    },
    # {
    #   "type": "video",
    #   "video_url":"https://storage.cdn-luma.com/dream_machine/4c5819c5-9040-4dfa-b7d1-4f16ab0a9b3c/8411958c-ca15-4acd-81a9-aa3c4bb1463c_result970d62fd71ed3325.mp4",
    # #   "prompt_video": "A person slicing fresh avocado on wholegrain toast in a bright modern kitchen, clean aesthetic, close-up food photography style, shallow depth of field",
    #   "narration_text": "Green foods like avocados and spinach boost your heart health and energy.",
    #     "subtitle": True,
    # },
    # {
    #   "type": "video",
    #   "video_url":"https://storage.cdn-luma.com/dream_machine/a1a4ea1d-fcf9-4865-948c-c4a23f05b976/1ba1d390-b0b3-4119-a316-336ddebe506c_result480d6c9187b63fa4.mp4",
    # #   "prompt_video": "Smoothie bowl with strawberries, blueberries, seeds arranged in a beautiful pattern, top-down cinematic shot with natural lighting",
    #   "narration_text": "Fuel your day with real food—because health starts with what you eat.",
    #     "subtitle": True,
    # }
  ],
      "logo":{
         "url":"https://pub-b3d68bfabb5742dabcd0275d1b282f2a.r2.dev/f83ba57b-4730-4e67-b549-eac4ac857cda.png",
         "position":"bottom-right",
         "opacity":0.2,
            "show_in_all_scenes":True,
         "cta_screen":True
      },
   }
    create_task(task_id, user_api_key, payload)
    print("PYTHONPATH=. python main_worker.py ", task_id)

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
                "subtitle": True
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