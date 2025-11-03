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
    payload = {
        "output_filename": "generated_video.mp4",
        "scenes": [
            {
                "narration_text": "Did you know Solana's SOL token dropped nearly 20 right after the U.S. spot ETF launched? This dramatic selloff has left many investors puzzled. Let's find out why.",
                "subtitle": True,
                "type": "video",
                "video_url": "https://videos.pexels.com/video-files/6133983/6133983-uhd_2160_4096_25fps.mp4"
            },
            {
                "narration_text": "Despite strong inflows from the ETF, which typically signals positive sentiment, SOL experienced a sharp decline landing between 175 and 180. This highlights the unpredictable nature of crypto markets.",
                "subtitle": True,
                "type": "video",
                "video_url": "https://videos.pexels.com/video-files/6436549/6436549-uhd_2160_3840_24fps.mp4"
            },
            {
                "narration_text": "SOL is currently testing critical support levels at 180. Analysts warn that if this level fails, we could see a further drop to 150 or even lower. Holding above 180 is crucial for stabilization.",
                "subtitle": True,
                "type": "video",
                "video_url": "https://videos.pexels.com/video-files/6134189/6134189-uhd_2160_4096_25fps.mp4"
            },
            {
                "narration_text": "Rising trading volumes indicate active selling pressure, suggesting traders are reacting swiftly to market changes. This shift in sentiment emphasizes caution among investors at this time.",
                "subtitle": True,
                "type": "image",
                "prompt_image": "Create an Instagram Reels-style image that features a bustling trading floor filled with diverse traders of various ethnicities, intensely focused on their screens displaying fluctuating stock charts and graphs. The environment is dynamic, with bright LED screens illuminating the space, casting vibrant blues, greens, and reds that reflect the active trading atmosphere. Traders are seen with furrowed brows, some pointing at their screens while others are speaking into headsets, showcasing their swift reactions to market changes. The mood is tense yet energetic, emphasizing a sense of urgency and caution among investors. The camera perspective is slightly elevated, capturing the chaos below with a depth of field that highlights both the traders and the screens, creating an engaging and immersive experience. The lighting is bright, with a mix of natural light streaming through large windows and the artificial glow from the screens, enhancing the modern, vibrant feel of the scene. The composition should be vertical 9:16, optimized for social media engagement."
            },
            {
                "narration_text": "While the short-term outlook appears bearish, some analysts believe this could be a 'buy the dip' opportunity for those willing to take on risk, viewing Solana as a long-term investment.",
                "subtitle": True,
                "type": "image",
                "prompt_image": "Create an Instagram Reels-style image that features a dynamic trading room filled with diverse young professionals engaged in animated discussions about cryptocurrency. The environment is sleek and modern, illuminated by bright LED screens displaying fluctuating Solana charts and bullish market trends. The mood is a blend of optimism and tension, with some analysts cheerfully pointing at a screen showing the phrase \"Buy the Dip!\" while others look contemplative, analyzing graphs. The composition is slightly tilted to give a sense of action, with a close-up of a hand gesturing towards a bullish trend line on a digital tablet. The background is filled with vibrant colors—greens for growth, reds for caution—creating a striking contrast. The camera perspective is from a low angle, making the analysts appear empowered and engaged, emphasizing the high-stakes atmosphere of investment. The vertical 9:16 format is designed to capture attention on social media platforms, ensuring an engaging and visually stimulating experience."
            },
            {
                "narration_text": "Like if this helped you understand Solana's recent moves, and follow for more crypto insights and updates. Stay informed and make smart investment choices!",
                "subtitle": True,
                "type": "image",
                "prompt_image": "Create an Instagram Reels-style image that features a dynamic split-screen layout. On the left side, depict a modern workspace with a sleek laptop showcasing a colorful graph of Solana's price movements. The screen should display bright green and blue upward trends with animated elements like arrows and icons representing growth. A confident young adult, casually dressed, leans over the laptop, pointing at the graph with an enthusiastic smile, embodying the spirit of making smart investment choices. \n\nOn the right side, illustrate a vibrant digital landscape with abstract cryptocurrency symbols swirling around, including the Solana logo, dollar signs, and coins, all glowing in a bright neon palette. The background should have a gradient of deep blue to purple, creating a tech-savvy and futuristic atmosphere. \n\nUse warm, natural lighting to illuminate the workspace while the digital landscape is enhanced with glowing effects, creating a contrast that draws the eye. The overall mood should be energetic and inspiring, encouraging viewers to stay informed about crypto. The composition should invite"
            }
        ],
        "post_description": "Solana's SOL token is on a wild ride! 🚀 Are you in or out? Discover what's happening with the ETF launch and where the price might go. Like and follow for more crypto insights! #Solana #CryptoNews #InvestSmart"
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
    response = requests.post(WORKER_URL, json=payload, timeout=60)
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