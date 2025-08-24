import requests
import time
import os
from lumaai import LumaAI

client = LumaAI(
    auth_token=os.environ.get("LUMAAI_API_KEY"),
)
generation = client.generations.create(
  prompt="A glowing digital bitcoin slowly rotating in a futuristic server room with dramatic lighting and tech UI overlays, deep blue tones, cinematic camera movement.",
    model="ray-2",
resolution="720p",
    duration="5s",
    aspect_ratio = "9:16",

)
completed = False
while not completed:
  generation = client.generations.get(id=generation.id)
  if generation.state == "completed":
    completed = True
  elif generation.state == "failed":
    raise RuntimeError(f"Generation failed: {generation.failure_reason}")
  print("Dreaming")
  time.sleep(3)

video_url = generation.assets.video

# download the video
response = requests.get(video_url, stream=True)
with open(f'{generation.id}.mp4', 'wb') as file:
    file.write(response.content)
print(f"File downloaded as {generation.id}.mp4")