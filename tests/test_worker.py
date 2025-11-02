import os
import uuid
import requests
import time
import json
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
    payload = json.loads("""

{"output_filename": "generated_video.mp4", "scenes": [{"narration_text": "On November 2, 2025, Binance founder Changpeng Zhao, also known as CZ, made headlines by purchasing over 2 million ASTER tokens. This bold move unleashed a wave of excitement in the crypto market.", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/25935019/11922005_2160_3840_24fps.mp4", "duration": 10}, {"narration_text": "The immediate impact was astonishing, with ASTER's price skyrocketing by nearly 20 to 35 percent. It jumped from 0.91 to above 1.20 in just one hour, a clear indicator of investor enthusiasm.", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/19002759/19002759-hd_1080_1920_24fps.mp4", "duration": 10}, {"narration_text": "CZ's purchase, using his personal funds, was seen as a strong endorsement for ASTER, a token focused on decentralized trading. His statement, 'I am not a trader. I buy and hold,' resonated with investors.", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/6282371/6282371-hd_1080_1920_30fps.mp4", "duration": 10}, {"narration_text": "Despite its soaring price, investors are advised to exercise caution due to ASTER's high token supply and competition in the market. Understanding the risks is essential in this volatile environment.", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/7413780/7413780-hd_1080_1920_24fps.mp4", "duration": 10}, {"narration_text": "With over half of ASTER's supply aimed at community incentives, the token's future is intertwined with CZ's influence in the crypto space. His recent pardon by President Trump adds another layer of intrigue.", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/34504641/14619504_2160_3840_30fps.mp4", "duration": 10}, {"narration_text": "If you found this update valuable, like if this helped you or follow for more insights on crypto trends and market movements. Stay informed and engaged with your investments!", "subtitle": true, "type": "video", "video_url": "https://videos.pexels.com/video-files/7579572/7579572-uhd_2160_4096_25fps.mp4", "duration": 10}], "post_description": "CZ's bold move on ASTER has shaken the crypto market! 🚀 Learn how his purchase influenced the token's price and what it means for investors. Like if this helped you! #CryptoNews #ASTERTokens #CZ"}
""")
    
    
    
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
  "output_filename": "trading_meme_video.mp4",
  "scenes": [
    {
      "type": "image",
      "narration_text": "Most beginner traders fall for this trap within their first month…",
      "prompt_image": "A wide-angle, high-contrast image of a stressed-out young trader looking at multiple monitors showing red candlestick charts, with text overlay: 'Don't Be This Guy 🧨'",
      "subtitle": False
    },
    {
      "type": "image",
      "narration_text": "Chasing green candles without strategy? It’s the quickest way to blow your account.",
      "prompt_image": "Top-down photo of a desk with crumpled notes, empty coffee cups, and a stock chart open on a tablet with price crashing. Dim lighting and chaotic vibes.",
      "subtitle": True
    },
    {
      "type": "image",
      "narration_text": "Here’s the strategy pros use — risk 1%, win 3x. No more gambling.",
      "prompt_image": "Clean, minimal scene showing a planner notebook open to a 'Risk Management Plan' with neat graphs and a hand pointing to a win-rate formula.",
      "subtitle": True
    },
    {
      "type": "image",
      "narration_text": "Consistency is the game. One good trade a day beats 10 reckless ones.",
      "prompt_image": "Ultra-sharp macro shot of a person sipping tea while watching a trading monitor calmly, with a zen garden in the background.",
      "subtitle": True
    },
    {
      "type": "image",
      "narration_text": "Ready to grow your trading with smarter content?",
      "prompt_image": "A closing shot of a stylized 'Follow for More' animation on a phone screen with a trading setup in the background, and bright neon callout: 'JOIN THE MOVEMENT 🚀'",
      "subtitle": False
    }
  ]
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