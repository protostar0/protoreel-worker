#!/usr/bin/env python3
"""
E-commerce Video Ad Config Generator

Takes product information (name, image, price) and generates a complete video ad configuration
using OpenAI API. Creates a 30-second ad with 6 scenes optimized for short-form platforms.

Usage:
    python tests/generate_ecommerce_video_config.py --product-name "Wireless Headphones" --product-image "https://example.com/image.jpg" --price 99.99
    python tests/generate_ecommerce_video_config.py --product-name "Smart Watch" --price 199.99 --description "Premium fitness tracker"
"""

import os
import sys
import json
import argparse
import requests
import logging
import base64
import re
from typing import Optional, Dict, Any

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an autonomous AI e-commerce video ad strategist who creates complete short-form video ad concepts from a single product input.

You handle the entire process end-to-end:

- Write a persuasive, high-converting 30-second ad script

- Plan and outline cinematic scenes

- Generate detailed 2:3 image prompts

- Write Kling-ready video animation prompts

=====================

PHASE 0 – SCRIPT GENERATION

=====================

If the user provides only a product name, description, or image, you automatically:

1. Analyze the product type, tone, and audience cues

2. Infer the target demographic (age, gender, interests, lifestyle, income level)

3. Write a complete 30-second e-commerce ad script structured as:

Hook (0–5s): Emotional or problem-based opener

Product Intro (5–10s): What it is and why it matters

Features/Benefits (10–20s): Emotional key selling points

Proof/Use Case (20–25s): Demonstrate results or trust

Call-to-Action (25–30s): Urgent, emotionally resonant ending

The script must be conversational, visual, and optimized for TikTok/Reel voiceover.

After the script is generated, immediately continue to visual phases.

=====================

PHASE 1 – SHOT LIST PLANNING

=====================

Break the script into 6 visual scenes (5 seconds each, total 30s).

For each scene, define:

- Scene number

- Purpose (Hook, Product Intro, Benefit, Lifestyle, Proof, CTA)

- Emotional tone

- Suggested camera style

- Scene type (video or image)

SCENE TYPE GUIDELINES:

- Use "video" type for dynamic scenes with motion, action, or product in use

- Use "image" type for:
  * Static product showcases (especially for color variants)
  * When product images show different colors/variants - use image scenes to showcase each color
  * Detail shots or close-ups that don't need motion
  * Color comparison or variant displays (e.g., clothing in different colors)
  * Any scene where a static image better serves the purpose
- For image scenes showcasing color variants:
  * Use the `image_url` field to reference a specific product image from the provided product_images array
  * This allows OpenAI to use the actual product image as input/reference when generating the scene image
  * Example: If showcasing a black variant, use the black product image URL in `image_url`

- Scene 6 (CTA) MUST always be type "image"

- Mix scene types as needed - you can have both video and image scenes in the same ad

Example outline:

1. Hook – Capture attention emotionally (video or image)

2. Product Intro – Showcase what it is (video or image)

3. Feature Highlight / Color Variant – Show use in action OR showcase different colors (video or image)

4. Benefit – Emotional or lifestyle payoff (video or image)

5. Social Proof / Color Showcase – Reinforce trust OR show more color options (video or image)

6. CTA – Inspire final conversion (MUST be image)

If product images show different colors/variants (e.g., clothing in red, blue, green), consider using image scenes to showcase these color options clearly.

Then proceed automatically to image prompt generation.

=====================

PHASE 2 – IMAGE PROMPT GENERATION

=====================

Generate one vivid 2:3 vertical cinematic image prompt per scene.

CRITICAL: The prompt_image describes the FIRST FRAME of the video - it must be extremely detailed and match exactly what the video will start with.

Each image prompt must:

- Begin with: "Create an image of the product featured in the ad..."

- Describe the EXACT first frame of the video scene in extreme detail:
  * Exact product position, angle, and orientation
  * Precise lighting (direction, intensity, color temperature)
  * Background details (texture, color, depth of field)
  * Camera angle and perspective (close-up, medium shot, wide shot)
  * Product state (if it's a blender, is it closed? open? with ingredients?)
  * Any props or elements visible in the first frame
  * Color palette and mood
  * Composition and framing

- The image prompt should be so detailed that someone could recreate the exact first frame from your description

- Reflect the tone and action of the corresponding script scene

- Avoid vague language, brand names, or on-image text

SPECIAL RULE FOR SCENE 6 (CTA):

- Scene 6 MUST be type "image" (not video) and will be generated by OpenAI DALL-E.

- If price is provided in product information:
  - Visually include a limited offer moment with price discount:
    - Show an old price crossed out and a new discounted price clearly visible.
    - Add "Limited Offer" or "Limited Time" text elements.
    - Include urgency cues (countdown timer, flash sale badge, etc.).
  
- If price is NOT provided in product information:
  - Do NOT include any price information in the image.
  - Use creative, compelling call-to-action phrases such as:
    - "Limited Offer" / "Limited Time"
    - "Shop Now" / "Get Yours Now"
    - "Don't Miss Out" / "Act Now"
    - "Exclusive Deal" / "Special Offer"
    - "Grab It Now" / "Claim Yours"
    - Or other creative, urgency-driven CTA text
  - Add visual CTA elements (e.g., a hand reaching to tap the button, glowing light, urgency cues, flash sale badge).
  - Make it exciting and conversion-focused even without price.

- In both cases, focus composition on excitement, urgency, and conversion.
- The image should be a static conversion-focused scene (no video animation needed).

All 6 image prompts must be generated together under labeled sections:

Scene 1 – Hook:

[Prompt]

...

Scene 6 – CTA:

[Prompt]

Then proceed automatically to video prompt generation.

IMPORTANT: Scene 6 (CTA) does NOT need a video prompt since it will be a static image scene.

=====================

PHASE 3 – VIDEO PROMPT GENERATION (KLING)

=====================

Convert each image prompt into a cinematic video prompt.

CRITICAL CONSTRAINTS FOR VIDEO AI:

- The video AI is NOT good with complex actions or movements
- AVOID complex actions like: mixing, blending, cutting, chopping, pouring, shaking vigorously, rapid movements
- KEEP IT SIMPLE: Use smooth, gentle, slow movements only
- Good movements: slow camera pan, gentle zoom in/out, slow rotation, smooth fade, gentle tilt
- Bad movements: fast spinning, rapid mixing, chopping, pouring, shaking, complex multi-step actions
- The video should start from the exact first frame described in prompt_image
- Use simple, cinematic camera movements that showcase the product elegantly
- Focus on smooth transitions and gentle motion
- Think: product photography in motion, not action scenes

Each video prompt:

- Describes smooth, simple animation and motion for one scene

- Uses natural cinematic language

- Includes gentle motion, lighting, and emotional tone

- Avoids text or brand names

- Refers generically to the product ("the bottle," "the device," etc.)

- MUST start from the exact first frame described in prompt_image

- Keep movements simple and smooth - no complex actions

Output format:

For each VIDEO scene, provide a video animation prompt:

Scene 1 – Hook (if video):

[Video animation prompt]

...

Scene 5 – Social Proof (if video):

[Video animation prompt]

NOTE: 
- Image scenes (including Scene 6 CTA) do NOT need video prompts - they will be static image scenes generated by OpenAI DALL-E
- Only generate video prompts for scenes that are type "video"

=====================

CREATIVE STYLE

=====================

- Cinematic yet data-driven

- Emotional yet product-focused

- Confident, persuasive, and visually articulate

- Optimized for short-form ads (TikTok, Meta, YouTube Shorts)

=====================

RULES

=====================

- Input: product name, description, or script

- Default duration: 30 seconds (6 scenes × 5s)

- Automatically infer audience

- Output everything (script + visuals) in one structured message

- Never ask follow-up questions

- Maintain cinematic consistency and storytelling tone

=====================

FINAL OUTPUT FORMAT (JSON)

=====================

You MUST output ONLY valid JSON in this exact format:

{
  "output_filename": "product-name-30s.mp4",
  "scenes": [
    {
      "type": "video",
      "narration_text": "script of the scene",
      "prompt_image": "AI-generated image prompt for the scene",
      "prompt_video": "video animation prompt for the scene",
      "image_url": "https://example.com/product-image.jpg",
      "video_provider": "klingai",
      "video_aspect_ratio": "9:16",
      "video_duration": "5s",
      "video_model": "kling-v1"
    },
    {
      "type": "image",
      "narration_text": "CTA script for the scene",
      "prompt_image": "AI-generated image prompt for CTA scene with Buy Now action",
      "image_provider": "openai",
      "image_url": "https://example.com/product-image.jpg"
    }
  ],
  "post_description": "Engaging social media post description for the product"
}

IMPORTANT: 
- Scene types can be mixed: use "video" for dynamic scenes, "image" for static showcases (especially color variants)
- Scene 6 (CTA) MUST always be type "image" (not video)
- For image scenes:
  - narration_text: Script for the scene
  - prompt_image: Detailed image prompt for the complete scene
  - image_provider: "openai" (will be generated by OpenAI DALL-E)
  - image_url: (OPTIONAL) URL of an existing image to use as input/reference. If provided, OpenAI will use this image along with the prompt to generate a related image (e.g., for color variants, use a product image URL)
  - Do NOT include prompt_video, video_provider, or other video fields
- For video scenes:
  - narration_text: Script for the scene
  - prompt_image: EXACT first frame description (extremely detailed)
  - prompt_video: Video animation prompt for KlingAI (keep movements simple and smooth)
  - image_url: (OPTIONAL) URL of an existing image to use as input/reference when generating the first frame image. If provided, OpenAI will use this image along with prompt_image to generate a related image that matches the product (e.g., use a product image URL to ensure the generated image is product-accurate)
  - video_provider: "klingai"
  - video_aspect_ratio: "9:16"
  - video_duration: "5s"
  - video_model: "kling-v1"
- Each scene should have narration_text (5 seconds worth of script)
- If product images show different colors/variants, consider using image scenes to showcase each color clearly
- Product images are provided in the top-level product_images array and will be used as reference when generating images
- Do NOT include prompt_video_image in scenes - product images are handled via video_context
- Do NOT include "subtitle" field in scenes - it will be handled automatically
- Generate exactly 6 scenes (5 seconds each = 30 seconds total)
- Include a compelling post_description for social media
- Video prompts must avoid complex actions - use only smooth, gentle camera movements
- For Scene 6: If price is provided, include limited offer with price discount. If price is NOT provided, use creative CTA phrases like "Limited Offer", "Shop Now", "Don't Miss Out", "Exclusive Deal", etc. (no price information)."""


def generate_video_config(
    product_name: str,
    product_image: Optional[str] = None,
    product_images: Optional[list] = None,
    price: Optional[float] = None,
    description: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate e-commerce video ad configuration from product information.
    
    Args:
        product_name: Name of the product
        product_image: Optional URL to product image (single image, deprecated - use product_images)
        product_images: Optional list of product image URLs
        price: Optional product price
        description: Optional product description
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        
    Returns:
        Dictionary containing video configuration with scenes
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set or provided")
    
    # Handle images: prefer product_images array, fallback to product_image
    images = product_images or []
    if product_image and product_image not in images:
        images.insert(0, product_image)  # Add single image to front if provided
    
    # Use first image as primary for prompt_video_image
    primary_image = images[0] if images else None
    
    # Build user prompt with product information
    user_prompt_parts = [f"Product Name: {product_name}"]
    
    if description:
        user_prompt_parts.append(f"Product Description: {description}")
    
    # Track if price is provided for CTA scene handling
    has_price = False
    
    if price:
        has_price = True
        # Convert price to float if it's a string
        try:
            if isinstance(price, str):
                # Remove $ and other currency symbols, then convert to float
                price_clean = price.replace('$', '').replace(',', '').strip()
                price_float = float(price_clean)
            else:
                price_float = float(price)
            user_prompt_parts.append(f"Price: ${price_float:.2f}")
        except (ValueError, TypeError) as e:
            # If conversion fails, just use the price as-is
            logger.warning(f"Could not convert price to float: {price}. Using as-is: {e}")
            user_prompt_parts.append(f"Price: {price}")
    
    # Add instruction about CTA scene based on price availability
    if has_price:
        user_prompt_parts.append("\nIMPORTANT FOR SCENE 6 (CTA): Price is provided. Include limited offer with price discount (old price crossed out, new discounted price visible) in the CTA scene.")
    else:
        user_prompt_parts.append("\nIMPORTANT FOR SCENE 6 (CTA): Price is NOT provided. Do NOT include any price information. Use creative, compelling call-to-action phrases like 'Limited Offer', 'Shop Now', 'Don't Miss Out', 'Exclusive Deal', 'Grab It Now', or other urgency-driven CTA text. Make it exciting and conversion-focused.")
    
    # Prepare messages for OpenAI API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Build user message with text and images
    user_message_content = []
    user_message_content.append({"type": "text", "text": "\n".join(user_prompt_parts)})
    
    # Add images for visual analysis if provided
    if images:
        logger.info(f"Downloading and encoding {len(images)} product image(s) for visual analysis...")
        for idx, img_url in enumerate(images, 1):
            try:
                # Download image
                img_response = requests.get(img_url, timeout=30)
                img_response.raise_for_status()
                
                # Get content type
                content_type = img_response.headers.get('content-type', 'image/jpeg')
                if not content_type.startswith('image/'):
                    content_type = 'image/jpeg'  # Default fallback
                
                # Encode to base64
                img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                
                # Add image to message content
                user_message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{img_base64}",
                        "detail": "high"  # Use high detail for better analysis
                    }
                })
                
                logger.info(f"  ✓ Encoded image {idx}/{len(images)}: {img_url[:50]}...")
                
            except Exception as e:
                logger.warning(f"Failed to download/encode image {idx} ({img_url}): {e}. Continuing with text-only...")
                # Fallback: add URL as text if image download fails
                user_message_content.append({
                    "type": "text",
                    "text": f"\nProduct Image {idx} URL: {img_url}"
                })
        
        user_message_content.append({
            "type": "text",
            "text": "\n\nAnalyze the product images visually and use the insights to:\n"
                   "- Understand the product's visual features, colors, design, and style\n"
                   "- If images show different colors/variants (e.g., clothing in multiple colors), consider using image scenes to showcase each color variant clearly\n"
                   "- For image scenes showcasing specific color variants, use the `image_url` field to reference the corresponding product image from the provided images\n"
                   "- For video scenes, you can also use `image_url` to reference a product image - this ensures the generated first frame image is product-accurate and matches the actual product\n"
                   "- This allows OpenAI to use the actual product image as input/reference when generating the scene image, ensuring better accuracy\n"
                   "- Generate accurate image prompts that match the product's appearance\n"
                   "- Create video prompts that showcase the product authentically (for video scenes)\n"
                   "- The product images will be provided in the top-level 'product_images' array and used as reference when generating images from prompt_image.\n\n"
                   "Generate the complete video ad configuration in JSON format as specified. Mix scene types (video/image) as appropriate, especially for color showcases."
        })
    else:
        user_message_content.append({
            "type": "text",
            "text": "\n\nGenerate the complete video ad configuration in JSON format as specified."
        })
    
    messages.append({"role": "user", "content": user_message_content})
    
    logger.info(f"Generating video config for product: {product_name}")
    if price:
        logger.info(f"Price: ${price:.2f}")
    if images:
        logger.info(f"Product images provided: {len(images)} image(s)")
        if primary_image:
            logger.info(f"Primary image: {primary_image}")
    
    # Try GPT-5 first, fallback to GPT-4o if unavailable
    models_to_try = ["gpt-5", "gpt-4o"]
    last_error = None
    
    for model in models_to_try:
        try:
            logger.info(f"Attempting to generate video config with {model}...")
            
            # Build request payload - GPT-5 has different parameter requirements
            request_payload = {
                "model": model,
                "messages": messages
            }
            
            # GPT-5 has specific requirements:
            # - Uses max_completion_tokens instead of max_tokens
            # - Only supports default temperature (1), so we omit it
            # - May not support response_format the same way, so we omit it and extract JSON from response
            # - GPT-5 uses "reasoning tokens" for internal reasoning, so we need higher limit
            #   to ensure there are tokens left for the actual content output
            if model == "gpt-5":
                # Set a much higher limit to account for reasoning tokens (GPT-5 uses tokens for reasoning + output)
                # If reasoning uses 4000 tokens, we need at least 4000 more for actual content
                request_payload["max_completion_tokens"] = 8000
                # Don't set temperature for GPT-5 (defaults to 1)
                # Don't set response_format for GPT-5 - we'll extract JSON from the response
            else:
                request_payload["max_tokens"] = 4000
                request_payload["temperature"] = 0.7  # GPT-4o and others support custom temperature
                request_payload["response_format"] = {"type": "json_object"}  # GPT-4o supports this
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=request_payload,
                timeout=180  # Increased timeout for image processing
            )
            
            # Check for errors and log the response body
            if response.status_code != 200:
                error_data = {}
                try:
                    error_data = response.json()
                except (ValueError, json.JSONDecodeError):
                    error_data = {"error": response.text}
                
                error_message = error_data.get("error", {})
                if isinstance(error_message, dict):
                    error_msg = error_message.get("message", str(error_message))
                    error_code = error_message.get("code", "unknown")
                else:
                    error_msg = str(error_message)
                    error_code = "unknown"
                
                logger.warning(f"{model} API error ({response.status_code}): {error_msg} (code: {error_code})")
                
                # If this is not the last model, try the next one
                if model != models_to_try[-1]:
                    logger.info(f"Falling back to {models_to_try[models_to_try.index(model) + 1]}...")
                    last_error = f"{model}: {error_msg}"
                    continue
                else:
                    # This was the last model, raise the error
                    response.raise_for_status()
            
            # Success - parse the response
            data = response.json()
            
            # Log full response for debugging (truncated to avoid huge logs)
            logger.debug(f"Full API response keys: {list(data.keys())}")
            if 'choices' in data and len(data['choices']) > 0:
                logger.debug(f"First choice keys: {list(data['choices'][0].keys())}")
            
            if 'choices' not in data or len(data['choices']) == 0:
                logger.error(f"No choices in response. Response keys: {list(data.keys())}")
                logger.error(f"Full response (first 1000 chars): {str(data)[:1000]}")
                raise RuntimeError("No response from OpenAI API")
            
            choice = data['choices'][0]
            
            if 'message' not in choice:
                logger.error(f"No message in choice. Choice keys: {list(choice.keys())}")
                logger.error(f"Full choice: {choice}")
                raise RuntimeError("No message in API response")
            
            message = choice['message']
            
            # GPT-5 might return content differently - check both 'content' and other possible fields
            if 'content' in message:
                content = message['content']
            elif 'text' in message:
                content = message['text']
            else:
                logger.error(f"No content or text in message. Message keys: {list(message.keys())}")
                logger.error(f"Full message: {message}")
                raise RuntimeError(f"No content found in API response. Message keys: {list(message.keys())}")
            
            if not content or not content.strip():
                # Log the full response structure for GPT-5 to understand what's happening
                logger.error(f"Empty content in response from {model}.")
                logger.error(f"Message structure: {message}")
                logger.error(f"Choice structure: {choice}")
                logger.error(f"Full response data keys: {list(data.keys())}")
                logger.error(f"Full response (first 3000 chars): {str(data)[:3000]}")
                
                # For GPT-5, if content is empty, it might be a model limitation
                # Skip GPT-5 and try the next model
                if model == "gpt-5":
                    logger.warning("GPT-5 returned empty content. This appears to be a GPT-5 API limitation. Falling back to GPT-4o.")
                    last_error = "GPT-5 returned empty content - possible API limitation"
                    continue  # Try next model
                else:
                    raise RuntimeError("Empty content in OpenAI API response")
            
            content = content.strip()
            logger.info(f"Successfully received response from {model} API (content length: {len(content)} chars)")
            break  # Success, exit the loop
            
        except requests.exceptions.HTTPError as e:
            # If this is not the last model, try the next one
            if model != models_to_try[-1]:
                logger.warning(f"{model} failed: {e}. Trying next model...")
                last_error = str(e)
                continue
            else:
                # This was the last model, raise the error
                last_error = str(e)
                raise
        except Exception as e:
            # If this is not the last model, try the next one
            if model != models_to_try[-1]:
                logger.warning(f"{model} failed: {e}. Trying next model...")
                last_error = str(e)
                continue
            else:
                # This was the last model, raise the error
                last_error = str(e)
                raise
    
    # If we get here without breaking, all models failed
    if 'content' not in locals():
        raise RuntimeError(f"All models failed. Last error: {last_error}")
    
    # Parse JSON response
    try:
        # For GPT-5, content might be wrapped in markdown code blocks or have extra text
        # Extract JSON from the response (handle markdown code blocks)
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
            logger.info("Extracted JSON from markdown code block")
        else:
            # Try to find JSON object directly
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
                logger.info("Extracted JSON object from response")
        
        video_config = json.loads(content)
        logger.info(f"Successfully parsed JSON response with {len(video_config.get('scenes', []))} scenes")
        
        # Validate and enhance the configuration
        if 'scenes' not in video_config:
            raise ValueError("Response missing 'scenes' field")
        
        # Ensure all scenes have required fields and defaults
        for idx, scene in enumerate(video_config['scenes']):
            scene_idx = idx + 1
            is_cta_scene = (scene_idx == 6)
            
            # Remove subtitle field if present (will be handled automatically)
            if 'subtitle' in scene:
                del scene['subtitle']
            
            # Determine scene type (default to video if not specified, except CTA which is always image)
            scene_type = scene.get('type', 'video' if not is_cta_scene else 'image')
            
            # Scene 6 (CTA) is always an image scene generated by OpenAI
            if is_cta_scene:
                scene['type'] = 'image'
                scene.setdefault('image_provider', 'openai')
                scene.setdefault('duration', 5)  # 5 seconds
                
                # Remove video-related fields from CTA scene
                for video_field in ['prompt_video', 'video_prompt', 'video_provider', 'video_aspect_ratio', 'video_duration', 'video_model']:
                    if video_field in scene:
                        del scene[video_field]
                
                logger.info(f"Scene 6 (CTA) configured as image scene with OpenAI image generation")
            elif scene_type == 'image':
                # Image scene (for color showcases, static product displays, etc.)
                scene['type'] = 'image'
                scene.setdefault('image_provider', 'openai')
                scene.setdefault('duration', 5)  # 5 seconds
                
                # Remove video-related fields from image scenes
                for video_field in ['prompt_video', 'video_prompt', 'video_provider', 'video_aspect_ratio', 'video_duration', 'video_model']:
                    if video_field in scene:
                        del scene[video_field]
                
                logger.info(f"Scene {scene_idx} configured as image scene with OpenAI image generation")
            else:
                # Video scene (default for Scenes 1-5)
                scene['type'] = 'video'
                scene.setdefault('video_provider', 'klingai')
                scene.setdefault('video_aspect_ratio', '9:16')
                scene.setdefault('video_duration', '5s')
                scene.setdefault('video_model', 'kling-v1')
                scene.setdefault('duration', 5)  # 5 seconds per scene
            
            # Note: prompt_video_image is no longer used in scenes
            # Product images are now passed via video_context.product_images
            # and used as reference when generating images from prompt_image
            
            # Ensure narration_text exists
            if 'narration_text' not in scene:
                logger.warning(f"Scene {scene_idx} missing narration_text, using placeholder")
                scene['narration_text'] = "Product showcase scene" if not is_cta_scene else "Buy now! Limited offer!"
            
            # Map prompt_image if provided (for AI image generation fallback)
            if 'image_prompt' in scene and 'prompt_image' not in scene:
                scene['prompt_image'] = scene.pop('image_prompt')
            
            # Ensure prompt_video exists for video scenes (from video_prompt if provided)
            if not is_cta_scene:
                if 'video_prompt' in scene and 'prompt_video' not in scene:
                    scene['prompt_video'] = scene.pop('video_prompt')
        
        # Set default output filename if not provided
        if 'output_filename' not in video_config:
            safe_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '-').lower()
            video_config['output_filename'] = f"{safe_name}-30s.mp4"
        
        # Add post_description if not provided
        if 'post_description' not in video_config:
            video_config['post_description'] = f"Check out this amazing {product_name}! {'Limited time offer!' if price else ''}"
        
        # Add product_images to top-level payload for e-commerce workflow
        if images:
            video_config['product_images'] = images
            logger.info(f"Added {len(images)} product image(s) to payload")
        
        logger.info(f"Video config generated successfully: {len(video_config['scenes'])} scenes")
        return video_config
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response content: {content[:500]}")
        raise RuntimeError(f"Invalid JSON response from OpenAI: {e}")
    except Exception as e:
        logger.error(f"Failed to generate video config: {e}", exc_info=True)
        raise


def parse_product_json(json_input: str) -> Dict[str, Any]:
    """
    Parse product information from JSON string or file path.
    
    Args:
        json_input: JSON string or file path
        
    Returns:
        Dictionary with product information (name, price, description, images)
    """
    # Try to parse as JSON string first
    try:
        product_data = json.loads(json_input)
        return product_data
    except json.JSONDecodeError:
        # If not valid JSON, try as file path
        if os.path.exists(json_input):
            with open(json_input, 'r', encoding='utf-8') as f:
                product_data = json.load(f)
            return product_data
        else:
            raise ValueError(f"Invalid JSON string and file not found: {json_input}")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Generate e-commerce video ad configuration from product information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using JSON input (recommended)  python tests/generate_ecommerce_video_config.py --product-json '{"name": "Nutribullet Portable 475ml cordless Blender for Shakes & Smoothies, BPA Free, Leakproof Flip and sip, USB-C type, PB475W, Black", "price": 1050.00, "description": "Premium audio quality", "images": ["https://m.media-amazon.com/images/I/61e0VzSXAbL._AC_SL1500_.jpg","https://m.media-amazon.com/images/I/61JGqf-NjmL._AC_SL1500_.jpg","https://m.media-amazon.com/images/I/710McmM3YbL._AC_SL1500_.jpg"]}'
  # Using JSON input (recommended)  python tests/generate_ecommerce_video_config.py --product-json '{"name": "Blvck x Basquiat Crown Hoodie", "description": "Elevate your game with the Blvck x Jean-Michel Basquiat Crown Hoodie. This premium piece seamlessly brings together contemporary style and the iconic art of Basquiat. Crafted from 100% cotton, the hoodie is super soft to the touch and offered in two elegant shades: black and twilight cream. The front boasts a striking embroidered crown symbol, while the back features a monochromatic graphic for a subtle yet powerful statement. Indulge in both comfort and artistic expression with this must-have addition to your wardrobe.", "images": ["https://blvck.com/cdn/shop/files/Front_c112b621-08be-4f9c-9726-4fa326683518.jpg","https://blvck.com/cdn/shop/files/Front_e3353e9e-ab41-4a69-b311-ad60962406d1.jpg","https://blvck.com/cdn/shop/files/01_19fb1d50-1112-47e5-9591-ab832b04de48.jpg"]}'

  https://shop.eminem.com/cdn/shop/products/Kamikaze_Green_Hoodie_Male_Model_Front_1024x1024_f9d40831-2f58-4a08-a853-eb1f057ea1b8.jpg?v=1574892759&width=800
  # Using JSON file
  python generate_ecommerce_video_config.py --product-json product.json
  
  # Using individual arguments (legacy)
  python generate_ecommerce_video_config.py --product-name "Wireless Headphones" --price 99.99
  
  # With product image
  python generate_ecommerce_video_config.py --product-name "Smart Watch" --price 199.99 --product-image "https://example.com/watch.jpg"
  
  # With multiple images via JSON
  python generate_ecommerce_video_config.py --product-json '{"name": "Smart Watch", "price": 199.99, "images": ["https://example.com/watch1.jpg", "https://example.com/watch2.jpg"]}'
  
  # Save to file
  python generate_ecommerce_video_config.py --product-json product.json --output config.json

Product JSON Format:
  {
    "name": "Product Name",
    "price": 99.99,
    "description": "Product description (optional)",
    "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
  }

Environment Variables:
  - OPENAI_API_KEY: Your OpenAI API key (required)
        """
    )
    
    # Product input options (mutually exclusive)
    product_group = parser.add_mutually_exclusive_group(required=True)
    product_group.add_argument("--product-json", help="Product information as JSON string or file path")
    product_group.add_argument("--product-name", help="Product name (legacy, use --product-json instead)")
    
    # Legacy arguments (only used if --product-name is provided)
    parser.add_argument("--product-image", help="URL to product image (optional, legacy)")
    parser.add_argument("--price", type=float, help="Product price (optional, legacy)")
    parser.add_argument("--description", help="Product description (optional, legacy)")
    
    parser.add_argument("--api-key", help="OpenAI API key (defaults to OPENAI_API_KEY env var)")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: print to stdout)")
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if not args.api_key and not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable must be set or provided via --api-key")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        sys.exit(1)
    
    try:
        # Parse product information
        if args.product_json:
            # Parse from JSON
            product_data = parse_product_json(args.product_json)
            product_name = product_data.get('name') or product_data.get('product_name')
            if not product_name:
                raise ValueError("Product JSON must contain 'name' or 'product_name' field")
            
            price = product_data.get('price')
            description = product_data.get('description')
            images = product_data.get('images', [])
            
            # Validate images is a list
            if images and not isinstance(images, list):
                raise ValueError("'images' field must be an array")
            
            logger.info(f"Parsed product from JSON: {product_name}")
        else:
            # Legacy: use individual arguments
            product_name = args.product_name
            price = args.price
            description = args.description
            images = [args.product_image] if args.product_image else []
        
        # Generate video configuration
        logger.info("Starting video config generation...")
        video_config = generate_video_config(
            product_name=product_name,
            product_image=None,  # Deprecated, use product_images
            product_images=images,
            price=price,
            description=description,
            api_key=args.api_key
        )
        
        # Output result
        output_json = json.dumps(video_config, indent=2, ensure_ascii=False)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"✅ Video configuration saved to: {args.output}")
            print(f"   Generated {len(video_config.get('scenes', []))} scenes")
        else:
            print(output_json)
            
    except Exception as e:
        logger.error(f"Failed to generate video config: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

