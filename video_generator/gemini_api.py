"""
Gemini API integration for image generation using google-genai.
"""
import os
import logging
from PIL import Image
from io import BytesIO
import google.genai as genai
from google.genai import types
from video_generator.config import Config

logger = logging.getLogger(__name__)

def generate_image_from_prompt_gemini(prompt: str, out_path: str, model: str = "gemini-2.0-flash-preview-image-generation") -> str:
    """
    Generate an image from a text prompt using Google Gemini and save to out_path.
    Returns the path to the generated image.
    """
    try:
        client = genai.Client(api_key=os.environ["GEMENI_API_KEY"])
        # Add aspect ratio specification to the prompt
        enhanced_prompt = f"{prompt} (9:16 aspect ratio, vertical orientation)"
        response = client.models.generate_content(
            model=model,
            contents=enhanced_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'],
            )
        )
        found_image = False
        for part in response.candidates[0].content.parts:
            if getattr(part, 'text', None) is not None:
                logger.info(f"Gemini text response: {part.text}")
            elif getattr(part, 'inline_data', None) is not None:
                image = Image.open(BytesIO(part.inline_data.data))
                # Resize to REEL_SIZE
                image = image.resize(Config.REEL_SIZE, Image.LANCZOS)
                image.save(out_path)
                logger.info(f"Gemini image saved to {out_path}")
                found_image = True
        if not found_image:
            raise RuntimeError("No image found in Gemini response.")
        return out_path
    except Exception as e:
        logger.error(f"Gemini image generation failed: {e}")
        raise RuntimeError(f"Gemini image generation failed: {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m video_generator.gemini_api 'your prompt here' [output_path]")
        sys.exit(1)
    prompt = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "generated_gemini_image.png"
    try:
        result_path = generate_image_from_prompt_gemini(prompt, out_path)
        print(f"Gemini image saved to {result_path}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 