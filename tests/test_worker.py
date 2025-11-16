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
#     payload = {
#   "output_filename": "blvck-basquiat-crown-hoodie-30s.mp4",
#   "scenes": [
#     {
#       "type": "video",
#       "narration_text": "Not just a hoodie—wear the crown. Art you can feel, every day.",
#       "prompt_image": "Create an image of the product featured in the ad from an ultra-close, macro perspective of the embroidered crown emblem on the chest of the black cotton hoodie. The frame is vertical 2:3. The camera is 10 cm from the fabric, angled slightly downward (15°) so the stitches catch highlights. The crown embroidery appears crisp and textured in off‑white thread against a matte, deep‑black knit. Lighting: a single narrow softbox at 45° front-right with 5000K neutral light; a faint rim fill from rear-left to reveal thread relief; high contrast; shallow depth of field so the emblem is sharp while surrounding fabric softly falls out of focus. Background is a charcoal-to-black seamless gradient with no text or logos. Composition: the crown sits slightly above center, occupying the middle third, with visible fabric grain and subtle shadows in the lower portion.",
#       "prompt_video": "Start from the exact macro close-up frame described. Execute a slow, cinematic 8% push-in toward the embroidered crown while a gentle light sweep glides from right to left across the stitches to reveal texture. Keep the background static, depth of field shallow, and motion silky smooth—no sudden changes.",
#       "video_provider": "klingai",
#       "video_aspect_ratio": "9:16",
#       "video_duration": "5s",
#       "video_model": "kling-v1",
#       "duration": 5
#     },
#     {
#       "type": "video",
#       "narration_text": "Meet the Blvck x Basquiat Crown Hoodie—100% cotton, super soft, built to stand out.",
#       "prompt_image": "Create an image of the product featured in the ad as a full front view of the black hoodie suspended on an invisible hanger in a minimalist studio. Vertical 2:3 framing. The hood is slightly raised, front pocket openings visible, and the embroidered crown on the chest centered. Camera: medium shot at chest height with a 50mm lens equivalent, straight-on perspective. Lighting: large diffused key light from front-left (5600K), soft fill from right, and a subtle top hair light to define the hood. Background: smooth neutral gray seamless paper with a faint gradient from darker top to lighter bottom. The garment edges are clean and the cotton texture is lightly defined; no on-image text.",
#       "prompt_video": "Begin exactly on the centered studio product frame. Perform a slow pedestal-up motion (about 6% vertical rise) combined with a gentle 5° clockwise yaw, revealing the hoodie’s form and hood shape. Keep lighting constant and movement smooth, like premium product cinematography.",
#       "video_provider": "klingai",
#       "video_aspect_ratio": "9:16",
#       "video_duration": "5s",
#       "video_model": "kling-v1",
#       "duration": 5
#     },
#     {
#       "type": "image",
#       "narration_text": "Choose your vibe: deep black or twilight cream. Embroidered crown up front—minimal yet bold.",
#       "prompt_image": "Create an image of the product featured in the ad showing the twilight cream color variant in a clean, front-facing studio shot. Vertical 2:3 framing. The hoodie is centered, hood gently lifted, and the dark embroidered crown emblem sits perfectly centered on the chest. Camera: straight-on medium shot with a 55mm lens look. Lighting: soft, even illumination from a large frontal softbox (5400K) with subtle edge lights to separate sleeves from the background. Background: warm light-gray seamless with smooth falloff; reflective surfaces are avoided for a matte, premium feel. Fabric texture on the cream cotton is visible around the pocket openings and cuff ribbing. No text or branding on the image.",
#       "image_provider": "openai",
#       "duration": 5
#     },
#     {
#       "type": "video",
#       "narration_text": "From studio to street, it drapes clean and keeps you cozy—premium weight without the bulk.",
#       "prompt_image": "Create an image of the product featured in the ad being worn by a model standing still in an urban night setting. Vertical 2:3 framing. The model faces camera, hood up, hands relaxed by sides, wearing the black hoodie; the embroidered crown is centered and clearly visible. Background: defocused city lights with teal and amber bokeh, subtle reflections on a slightly wet pavement. Lighting: soft key at 4000K from front-left, a cool rim light from rear-right to outline the hood, and gentle fill to maintain detail in the black fabric. Camera: eye-level medium shot, slight downward angle (5°) for presence, shallow depth of field so the model and hoodie are crisp while the city remains blurred. No text in frame.",
#       "prompt_video": "Start on the static, centered portrait with the model wearing the hoodie. Perform a slow, steady 10% dolly-in while adding a subtle 3° tilt up to emphasize the chest emblem and hood shape. Maintain shallow depth of field and gentle bokeh drift; the subject remains motionless for a calm, premium mood.",
#       "video_provider": "klingai",
#       "video_aspect_ratio": "9:16",
#       "video_duration": "5s",
#       "video_model": "kling-v1",
#       "duration": 5
#     },
#     {
#       "type": "image",
#       "narration_text": "Details win: a subtle monochrome back graphic, clean lines, street-approved comfort.",
#       "prompt_image": "Create an image of the product featured in the ad from a back view to highlight the subtle monochrome graphic. Vertical 2:3 framing. The black hoodie is displayed on an invisible form at a 3/4 back angle, slightly turned to the left so shoulder structure and hood volume are visible. The tonal graphic sits high on the back, visible but understated. Lighting: raking key light from right at 35° to bring out the print’s low-contrast texture; soft fill from left; 5200K neutral color. Background: deep gray seamless with a gentle vignette. Camera: medium shot, straight-on with a slight elevated viewpoint (5°) to keep the back panel flat and readable. No text or logos in frame.",
#       "image_provider": "openai",
#       "duration": 5
#     },
#     {
#       "type": "image",
#       "narration_text": "This drop won’t last. Limited time—tap Shop Now and claim your crown.",
#       "prompt_image": "Create an image of the product featured in the ad as a conversion-focused CTA layout. Vertical 2:3 framing. Two hoodies are arranged front-facing: black on the left, twilight cream on the right, both evenly lit and centered slightly above mid-frame. Background: a sleek charcoal-to-stone gradient with a subtle spotlight bloom behind the products. Lighting: balanced softboxes (5600K) with gentle edge lights to separate each colorway. Add bold, clean CTA design elements: a glowing badge near the top reading “Limited Time”, and a prominent rounded button at the bottom center reading “Shop Now”. Include a subtle countdown icon next to the badge for urgency. Keep typography modern, minimal, and high-contrast; ensure the garments remain the focal point.",
#       "image_provider": "openai",
#       "duration": 5
#     }
#   ],
#   "post_description": "Art meets street. The Blvck x Basquiat Crown Hoodie delivers premium 100% cotton comfort with an iconic embroidered crown and a subtle monochrome back graphic. Available in deep black and twilight cream. Limited time—tap to claim your crown. #Streetwear #Basquiat #Blvck #HoodieDrop #MinimalAesthetic #MonochromeStyle #UnisexStyle",
#   "product_images": [
#     "https://blvck.com/cdn/shop/files/Front_c112b621-08be-4f9c-9726-4fa326683518.jpg",
#     "https://blvck.com/cdn/shop/files/Front_e3353e9e-ab41-4a69-b311-ad60962406d1.jpg",
#     "https://blvck.com/cdn/shop/files/01_19fb1d50-1112-47e5-9591-ab832b04de48.jpg"
#   ]
# }

    payload = {
    "output_filename": "blvck-basquiat-crown-hoodie-30s.mp4",
    "scenes": [
      {
        "type": "video",
        "video_url": "https://pub-497ff0d12ef74e099d02fb1d996b7d89.r2.dev/videos/1df6d1f2-9122-417b-872a-bd36e7c7dcaf/1df6d1f2-9122-417b-872a-bd36e7c7dcaf_blvck-basquiat-crown-hoodie-30s.mp4",
        "music": "https://userupload.protoreel.com/musics/groovy-vibe-427121.mp3",
        "music_volume": 0.3,
        "duration": 30
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