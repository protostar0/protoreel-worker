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
    payload ={
  "output_filename": "kamikaze-green-hoodie-30s.mp4",
  "scenes": [
    {
      "type": "video",
      "narration_text": "Flimsy hoodies? Nah—meet the heavy hitter you’ll wear nonstop.",
      "prompt_image": "Create an image of the product featured in the ad as an ultra-detailed macro first frame: a deep olive green heavyweight hoodie laid flat on a seamless charcoal matte surface, oriented slightly diagonal with the hood at the top-left and the chest centered in frame. The camera is a tight close-up (macro, 100mm) on the chest area and upper hood seam, showing the dense knit texture and soft, brushed surface. A subtle tonal graphic across the chest is visible but not emphasized. Lighting: a single soft key from top-left at 45°, 5600K, creating gentle raking highlights that reveal fabric grain; low-intensity fill from bottom-right; edges fall into rich shadows. Background stays out of focus with shallow depth of field (f/2.8). Color palette: olive green, charcoal, soft highlights. No props, no text overlays. Vertical 2:3 composition with the chest graphic sitting on the upper third line and the hood edge just touching the top frame.",
      "prompt_video": "Starting from the macro close-up of the chest and hood seam exactly as framed, perform a slow 5-second dolly-out of 5–8% to reveal a touch more of the hoodie shape while keeping the chest area dominant. Add a faint, soft light sweep from left to right across the fabric over the duration to emphasize texture. Maintain shallow depth of field and cinematic contrast. No fast movements, no text.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    },
    {
      "type": "video",
      "narration_text": "This is the Kamikaze Green Hoodie—clean lines, rich olive tone, built for the grind.",
      "prompt_image": "Create an image of the product featured in the ad as a full product showcase first frame: the olive green hoodie front-facing on an invisible hanger/mannequin, hood up, centered against a smooth dark gray seamless backdrop. The garment fills 70% of frame vertically, sleeves naturally relaxed. Kangaroo pocket clearly visible; minimal chest graphic appears subdued in black. Lighting: balanced studio setup—soft key from front-right (5600K), subtle rim lights from both sides to define silhouette, and a gentle top light for dimension. A faint shadow falls directly beneath the hem to ground the piece. Camera: medium shot at eye level, 50mm, straight-on perspective. Composition: perfectly centered, ample headroom, clean background, no props or text.",
      "prompt_video": "From this exact centered front view, apply a gentle 3% parallax rotation to the left while slowly dollying in by 5% to add depth. Keep the hoodie perfectly crisp and the background smooth. Subtle specular highlights glide along the shoulders to accentuate form. No rapid motion, no additional elements.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    },
    {
      "type": "video",
      "narration_text": "Heavyweight fabric, plush fleece interior, ribbed cuffs, and a deep kangaroo pocket.",
      "prompt_image": "Create an image of the product featured in the ad as a detail-first frame: close-up of the left sleeve cuff of the olive hoodie, slightly rolled to reveal the soft, fuzzy fleece interior. The small red hexagonal patch near the cuff edge is in sharp focus. Camera at 45° angle from top-right, 85mm lens, tight crop so the cuff dominates the lower-right quadrant while the torso fabric softly fills the background. Lighting: warm neutral key (5200K) from right, gentle fill from left, subtle falloff creating dimensional shadows within the fleece. Background remains the same charcoal seamless, softly blurred. No added text or props.",
      "prompt_video": "Starting from this tight cuff detail, execute a slow pan to the right of 6% while gently tilting down by 2% to trace along the cuff and reveal more of the plush interior and the red patch. Maintain soft, even motion and constant focus on the fabric texture. No fast actions.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    },
    {
      "type": "video",
      "narration_text": "Throw it on—instant comfort, premium feel, low‑key street vibe all day.",
      "prompt_image": "Create an image of the product featured in the ad worn by a model: a medium three‑quarter shot of a model wearing the olive green hoodie, hands resting inside the kangaroo pocket, hood relaxed, head slightly tilted down. The model stands slightly off-center to the right against a dark, moody studio gradient (black to deep charcoal). Camera at chest height, 70mm, slight angle from left to add depth. Lighting: dramatic key from left with soft falloff, subtle rim light from back-right creating a clean edge on the shoulder and hood, emphasizing the hoodie’s structure and drape. Fabric wrinkles look natural, chest graphic subdued. No brand text overlays or additional props.",
      "prompt_video": "Begin exactly on this composed medium shot. Perform a slow dolly-in of 6% toward the chest area while executing a gentle 2% vertical tilt up to bring attention to the hood and shoulders. Keep the model mostly still; let a soft light ripple roll across the fabric for mood. No abrupt changes.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    },
    {
      "type": "video",
      "narration_text": "Close-up quality: sturdy stitching, durable print, and that clean sleeve detail.",
      "prompt_image": "Create an image of the product featured in the ad as a proof-of-quality frame: an extreme close-up on the hoodie’s kangaroo pocket seam and lower torso, showing tight, even double stitching and the dense knit fabric. The camera is angled slightly upward from the lower-left at 60mm macro, with the seam running diagonally from bottom-left to center. Lighting: cool neutral (5600K) cross-light—one soft source from left to catch the seam ridge, a subtle kicker from right to separate the pocket edge; falloff to gentle shadows. Background remains the same charcoal seamless, heavily blurred. No props, no overlays.",
      "prompt_video": "From this exact seam macro, add a slow 5-second tilt up of 5% to glide from the pocket seam toward the mid-chest area while maintaining crisp focus on stitching. Introduce a faint moving highlight passing along the seam to emphasize craftsmanship. Keep motion smooth and minimal.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    },
    {
      "type": "video",
      "narration_text": "Limited drop—was $60, now $45. Tap Shop Now before your size’s gone.",
      "prompt_image": "Create an image of the product featured in the ad for a conversion-focused CTA: the olive green hoodie centered on a low matte-black pedestal, front-facing, against a deep charcoal-to-black gradient. Camera: medium-wide, straight-on, 50mm, with the hoodie filling the upper two-thirds of frame. Lighting: crisp key from front, soft rims from both sides, a subtle glow halo behind the hoodie for emphasis. On the lower third, display pricing UI: OLD PRICE $60.00 in small white text with a bold red strike-through; NEW PRICE $45.00 larger and bright white, slightly glowing. At bottom-center, a pill-shaped button reading Shop Now glows soft neon green with a faint pulsating light. A right hand enters from the right edge just barely visible in the first frame, fingertips aligned to tap the button. Clean composition, vertical 2:3. No brand names.",
      "prompt_video": "Starting on this exact CTA frame, gently dolly in by 6% over 5 seconds while the right hand slowly moves in a few centimeters to hover over and lightly tap the glowing button at the 4-second mark. Add a soft pulse to the NEW PRICE glow when the hand nears. Keep motion smooth and minimal; maintain focus on the hoodie and pricing.",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1",
      "duration": 5
    }
  ],
  "post_description": "Meet your new daily heavy hitter. The Kamikaze Green Hoodie delivers heavyweight comfort, a clean olive look, and premium details you can feel. Limited drop—was $60, now $45. Tap to cop before your size sells out. #streetwear #hoodie #dailyfit #mensstyle #unisex #olivegreen #cozyseason",
  "product_images": [
    "https://shop.eminem.com/cdn/shop/products/oodiefront_1024x1024_efa5f221-995c-4ed8-910f-a2edf13716d3.png?v=1574892759&width=800",
    "https://shop.eminem.com/cdn/shop/products/Kamikaze_Green_Hoodie_Male_Model_Front_1024x1024_f9d40831-2f58-4a08-a853-eb1f057ea1b8.jpg",
    "https://shop.eminem.com/cdn/shop/products/Kamikaze_Green_Hoodie_Male_Model_Detail_1024x1024_b1ee8346-a923-48eb-a08d-00355ed45b8b.jpg"
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