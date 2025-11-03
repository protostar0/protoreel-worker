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
{
  "output_filename": "generated_video.mp4",
  "scenes": [
    {
      "narration_text": "Have you heard about Bitcoin's recent silent IPO? This major shift in ownership is making waves in the crypto world as early holders transfer large amounts of BTC to new investors.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a dynamic, visually striking scene of a bustling cryptocurrency trading floor. In the foreground, a diverse group of young professionals, including a woman with bright blue hair and a man with glasses, are excitedly discussing and analyzing charts displayed on large screens showing Bitcoin prices and trading volumes. The environment is filled with high-tech screens and digital displays, showcasing vibrant graphs and Bitcoin symbols. The background is a sleek, modern office space with a city skyline visible through large glass windows, casting a warm golden light that suggests a late afternoon. The mood is energetic and optimistic, with a sense of anticipation in the air as early Bitcoin holders engage with new investors. The camera perspective is slightly tilted for a dynamic feel, capturing the hustle and bustle of the trading atmosphere, with Bitcoin coins subtly placed on desks and glowing neon accents around the room. The overall color palette is vibrant, with blues, greens, and golds, making the image eye-catching and perfect for social media."
    },
    {
      "narration_text": "In October 2025, approximately 62,000 BTC, valued at around 7 billion dollars, moved from long-term holders to institutional and retail buyers. This orderly exit is designed to avoid destabilizing prices.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a bustling, modern financial district in October 2025, showcasing a dramatic city skyline under a vibrant sunset. The foreground shows a diverse group of people, including institutional investors in sharp suits and retail buyers in casual attire, gathered around digital screens displaying animated Bitcoin charts and transaction graphics. The atmosphere is dynamic and energetic, with a blend of excitement and anticipation. Bright neon lights from surrounding buildings reflect off glass facades, creating a lively urban glow. The camera perspective is slightly elevated, capturing both the engaged crowd and the soaring skyscrapers in the background, emphasizing the scale of the financial movement. The overall mood is optimistic and forward-looking, with an emphasis on the transition of Bitcoin ownership, highlighted by visually striking graphics of Bitcoin coins transitioning from one wallet to another. The composition is vertical (9:16) to fit social media formats, ensuring the image is eye-catching and engaging for viewers."
    },
    {
      "narration_text": "Long-term holders still control 74 of Bitcoin's supply, but only 16.7 is actively traded. Large institutional investors now account for a staggering 86 of all trading volume.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a dynamic, modern digital landscape representing the world of Bitcoin trading. The foreground showcases a large, futuristic digital display with vibrant graphs and statistics, highlighting \\\"74% Long-term Holders\\\" and \\\"16.7% Actively Traded\\\" in bold, eye-catching text. Surrounding the display, a diverse group of people of various ethnicities and ages are engaged in animated discussions, with expressions of excitement and curiosity, symbolizing the active trading community. In the background, a sleek city skyline glows under a twilight sky, with neon lights reflecting the mood of innovation and finance. The lighting is dramatic, with bright, colorful accents illuminating the faces of the traders, creating a sense of urgency and engagement. A large, translucent Bitcoin symbol hovers above the scene, pulsating with energy, while a digital ticker tape at the bottom displays \\\"86% Institutional Trading Volume,\\\" emphasizing the dominance of institutional investors. The camera perspective is slightly tilted upwards, creating a dynamic and engaging composition perfect for social media."
    },
    {
      "narration_text": "Companies like BlackRock and corporate treasuries are accumulating Bitcoin, indicating a significant shift towards its adoption as a macroeconomic hedge. This is changing the landscape of cryptocurrency investing.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a bustling corporate office environment, with a large digital screen displaying a rising Bitcoin graph in the background. In the foreground, a diverse group of corporate professionals—two men in sharp suits and a woman in a stylish blazer—are gathered around a sleek glass table, examining Bitcoin charts on their laptops and tablets. The mood is energetic and optimistic, with warm, inviting lighting casting a glow on their focused expressions. The office is modern and stylish, featuring contemporary furniture and large windows that let in natural light. The camera perspective is slightly angled from above, capturing the dynamic interaction among the team as they discuss strategies, with Bitcoin symbols subtly integrated into the decor. The composition is vibrant and engaging, perfect for social media, with an emphasis on the transformative impact of Bitcoin in the financial world."
    },
    {
      "narration_text": "As Bitcoin transitions from concentrated ownership to a broader base, it becomes more stable and less volatile. This gradual distribution phases mirrors traditional equity market behavior during IPO unlock periods.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a vibrant, dynamic scene depicting a diverse group of people gathered in a modern urban setting, symbolizing the transition of Bitcoin from concentrated ownership to a broader base. In the foreground, a young woman of Asian descent is enthusiastically showing her smartphone screen displaying a graph of Bitcoin's price stabilizing, surrounded by a diverse group of friends, including a Black man and a Hispanic woman, who are engaged in conversation, all smiling and excited. The background showcases a bustling cityscape with tall buildings and digital billboards displaying Bitcoin symbols and stock market trends, reflecting the fusion of technology and finance. The lighting is bright and energetic, with the golden hues of sunset casting a warm glow over the scene, enhancing the mood of optimism and growth. The composition is framed from a slightly low angle to emphasize the height of the buildings and the energy of the group, creating a sense of upward movement and progress. The image is designed in a vertical 9:16 aspect ratio, optimized for social media platforms."
    },
    {
      "narration_text": "Like this video if you found this information helpful. Follow for more insights into the evolving world of cryptocurrency and stay updated on the latest trends in Bitcoin.",
      "subtitle": true,
      "type": "image",
      "prompt_image": "Create an Instagram Reels-style image that features a young, diverse group of three people enthusiastically discussing cryptocurrency trends in a modern, stylish living room. The scene is filled with colorful decor, including neon lights and digital screens displaying Bitcoin graphs and charts in the background. The mood is energetic and optimistic, with warm, inviting lighting that creates a cozy yet vibrant atmosphere. One person is pointing excitedly at a tablet showing a cryptocurrency app, while another is nodding in agreement, holding a smartphone with the \\\"Like\\\" icon prominently visible. The third person is leaning back on a plush couch, showing a thumbs-up gesture, all set at a dynamic angle to emphasize engagement. The composition is lively, inviting viewers to join the conversation, with a blurred foreground of plants and decorative items for added depth. The image is optimized for social media, capturing the essence of modern digital interaction in a vertical 9:16 format."
    }
  ],
  "post_description": "Explore the recent shift in Bitcoin ownership with our breakdown of the silent IPO dynamics. Learn how institutional adoption is shaping the future of cryptocurrency! Like for more insights! #Bitcoin #Crypto #Investing #BitcoinIPO"
}
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