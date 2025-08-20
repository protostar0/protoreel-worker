from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import os
import PIL.Image

image = PIL.Image.open('/Users/abdelhakkherroubi/Work/library/protoreel-worker/tests/image.png')

client = genai.Client(api_key=os.environ["GEMENI_API_KEY"])

text_input = """prompt"""

response = client.models.generate_content(
    model="gemini-2.0-flash-preview-image-generation",
    contents=[text_input, image],
    config=types.GenerateContentConfig(
      response_modalities=['TEXT', 'IMAGE']
    )
)

for part in response.candidates[0].content.parts:
  if part.text is not None:
    print(part.text)
  elif part.inline_data is not None:
    image = Image.open(BytesIO((part.inline_data.data)))
    image.show()