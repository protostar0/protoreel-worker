import os
import uuid
import requests
import time
import tempfile
from unittest.mock import patch, MagicMock
from video_generator.audio_utils import generate_narration

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
                "promptImage": "A photo-realistic image of President holding a press conference with the flags of the United States and Japan in the background, emphasizing a momentous announcement.",
                "subtitle": True
            },
            {
                "type": "image",
                "narration_text": "The deal includes a staggering $550 billion investment from Japan into the United States. This infusion of funds is expected to boost various sectors and create numerous jobs, potentially strengthening ties between the two nations.",
                "promptImage": "A photo-realistic image of a bustling New York City skyline with symbolic dollar signs and yen symbols overlayed, representing financial investment.",
                "subtitle": True
            },
            {
                "type": "image",
                "narration_text": "Both countries will implement a 15% tariff on each other's goods, including crucial sectors such as vehicles and agricultural products. While this aims to level the playing field, experts warn to carefully evaluate its long-term benefits.",
                "promptImage": "A photo-realistic image of shipping containers at a busy port with agricultural products and cars visible, representing international trade and tariffs.",
                "subtitle": True
            },
            {
                "type": "image",
                "narration_text": "As full details of the agreement are still unfolding, stay tuned for updates. Follow the hashtags #USJapanDeal and #TrumpTradeDeal for the latest news. Experts continue to analyze the potential impacts on global business dynamics.",
                "promptImage": "A photo-realistic image of a group of analysts in an office with a world map and international news screens visible, symbolizing ongoing discussions and evaluations.",
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

test_worker_process_task()