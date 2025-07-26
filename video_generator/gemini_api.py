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

def generate_image_from_prompt_gemini(prompt: str, out_path: str, model: str = "gemini-2.0-flash-preview-image-generation", 
                                    scene_context: dict = None, video_context: dict = None) -> str:
    """
    Generate an image from a text prompt using Google Gemini and save to out_path.
    Enhanced with contextual information for better scene coherence.
    
    Args:
        prompt: Base text prompt for image generation
        out_path: Path to save the generated image
        model: Gemini model to use
        scene_context: Additional context about the scene (scene_index, total_scenes, etc.)
        video_context: Context about the entire video (theme, narration_text, etc.)
    """
    try:
        client = genai.Client(api_key=os.environ["GEMENI_API_KEY"])
        
        # Build enhanced prompt with context
        enhanced_prompt = build_enhanced_prompt(prompt, scene_context, video_context)
        
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

def build_enhanced_prompt(base_prompt: str, scene_context: dict = None, video_context: dict = None) -> str:
    """
    Build an enhanced prompt with contextual information for better scene coherence.
    
    Args:
        base_prompt: The original image prompt
        scene_context: Scene-specific context (scene_index, total_scenes, duration, etc.)
        video_context: Video-wide context (theme, narration_text, etc.)
    
    Returns:
        Enhanced prompt string
    """
    enhanced_parts = []
    
    # Add Instagram Reels context
    enhanced_parts.append("Create a stunning Instagram Reel image with:")
    enhanced_parts.append("- 9:16 vertical aspect ratio for mobile viewing")
    enhanced_parts.append("- High contrast and vibrant colors for social media")
    enhanced_parts.append("- Professional composition with clear focal points")
    enhanced_parts.append("- Modern, engaging visual style")
    
    # Add video context if available
    if video_context:
        if video_context.get('narration_text'):
            enhanced_parts.append(f"- Visual theme related to: {video_context['narration_text'][:100]}...")
        if video_context.get('theme'):
            enhanced_parts.append(f"- Overall video theme: {video_context['theme']}")
    
    # Add scene context if available
    if scene_context:
        scene_index = scene_context.get('scene_index', 0)
        total_scenes = scene_context.get('total_scenes', 1)
        duration = scene_context.get('duration', 10)
        
        enhanced_parts.append(f"- This is scene {scene_index + 1} of {total_scenes}")
        enhanced_parts.append(f"- Scene duration: {duration} seconds")
        
        # Add scene progression context
        if total_scenes > 1:
            if scene_index == 0:
                enhanced_parts.append("- Opening scene: Set the tone and introduce the topic")
            elif scene_index == total_scenes - 1:
                enhanced_parts.append("- Closing scene: Provide conclusion or call-to-action")
            else:
                enhanced_parts.append("- Middle scene: Build on previous context and maintain flow")
    
    # Add the base prompt
    enhanced_parts.append(f"- Main visual content: {base_prompt}")
    
    # Add Instagram Reels optimization
    enhanced_parts.append("- Optimized for Instagram Reels with:")
    enhanced_parts.append("  * Eye-catching composition")
    enhanced_parts.append("  * Strong visual hierarchy")
    enhanced_parts.append("  * Mobile-friendly details")
    enhanced_parts.append("  * Social media appeal")
    
    # Add technical specifications
    enhanced_parts.append("- Technical requirements:")
    enhanced_parts.append("  * 9:16 aspect ratio")
    enhanced_parts.append("  * High resolution for crisp display")
    enhanced_parts.append("  * Professional lighting and composition")
    
    return " ".join(enhanced_parts)

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