import requests
import os
import time
import logging
import base64

logger = logging.getLogger(__name__)

# Try to import OpenAI - handle both old and new API versions
try:
    from openai import OpenAI
    OPENAI_NEW_API = True
    openai_old = None  # Old API not needed
except ImportError:
    try:
        import openai as openai_old
        OPENAI_NEW_API = False
        OpenAI = None  # New API not available
    except ImportError:
        raise ImportError("OpenAI library not installed. Install with: pip install openai>=1.0.0")

def analyze_product_images_with_vision(product_images: list, original_prompt: str, api_key: str) -> str:
    """
    Use GPT-4 Vision to analyze product images and extract visual details to enhance the prompt.
    
    Args:
        product_images: List of product image URLs
        original_prompt: Original image generation prompt
        api_key: OpenAI API key
        
    Returns:
        Enhanced prompt with product visual details
    """
    if not product_images or len(product_images) == 0:
        return original_prompt
    
    try:
        logger.info(f"Analyzing {len(product_images)} product image(s) with GPT-4 Vision to extract visual details...")
        
        # Build messages for GPT-4 Vision
        messages = [
            {
                "role": "system",
                "content": "You are a visual analysis expert specializing in product image generation. Your task is to analyze product images and create a highly detailed, specific description that will be used to generate an image that accurately matches the actual product. Focus on exact colors, precise design elements, materials, textures, shapes, patterns, brand-specific features, logos, text, and any distinctive visual characteristics. Be extremely specific and accurate."
            },
            {
                "role": "user",
                "content": []
            }
        ]
        
        # Add text instruction with emphasis on accuracy and structured output
        messages[1]["content"].append({
            "type": "text",
            "text": f"""You are analyzing product images to create a DALL-E prompt that will generate an image matching this EXACT product.

ORIGINAL PROMPT: '{original_prompt}'

CRITICAL INSTRUCTIONS:
Analyze these product images pixel by pixel and create a STRUCTURED, HIGHLY DETAILED description that DALL-E can use to recreate this product EXACTLY.

EXTRACT AND DESCRIBE IN THIS EXACT FORMAT:

1. PRIMARY COLOR:
   - Exact color name (e.g., "deep charcoal black", "navy blue", "off-white cream")
   - Hex code if visible or can be determined
   - Color distribution (where each color appears)

2. DESIGN & PATTERNS:
   - Exact pattern type (solid, stripes, logo placement, etc.)
   - Logo details: exact text, font style, size, position, color
   - Any graphics, illustrations, or decorative elements
   - Text content: exact words, numbers, font style, size, color, position

3. MATERIALS & TEXTURE:
   - Fabric/material type (cotton, polyester, denim, leather, etc.)
   - Texture description (smooth, ribbed, brushed, matte, glossy, etc.)
   - Finish quality (premium, distressed, vintage, etc.)

4. CONSTRUCTION DETAILS:
   - Stitching: color, style, visibility
   - Seams: type, placement
   - Hardware: zippers, buttons, snaps (color, material, style)
   - Labels/tags: exact text, position, style

5. SHAPE & FIT:
   - Silhouette type (oversized, fitted, relaxed, etc.)
   - Proportions and dimensions
   - Cut style (regular, slim, wide, etc.)

6. BRAND ELEMENTS:
   - Brand name: exact spelling, font, size, position
   - Logo: exact design, colors, size, position
   - Any brand-specific design elements

7. STYLING & AESTHETIC:
   - Overall style (casual, formal, streetwear, luxury, etc.)
   - Mood/vibe
   - Target aesthetic

OUTPUT FORMAT:
Provide your analysis in a clear, structured format that can be directly used in a DALL-E prompt. Be EXTREMELY SPECIFIC about:
- Colors (use exact color names, not generic terms)
- Text content (exact words, numbers, spelling)
- Logo details (exact design, placement, size)
- Material appearance (exact texture, finish)
- All visible design elements

IMPORTANT: Your description will be used to generate an image. Be so specific that someone could recreate this product exactly from your description alone."""
        })
        
        # Download and encode product images
        encoded_images = 0
        for idx, img_url in enumerate(product_images[:3]):  # Limit to 3 images for API efficiency
            try:
                img_response = requests.get(img_url, timeout=30)
                img_response.raise_for_status()
                
                content_type = img_response.headers.get('content-type', 'image/jpeg')
                if not content_type.startswith('image/'):
                    content_type = 'image/jpeg'
                
                img_base64 = base64.b64encode(img_response.content).decode('utf-8')
                
                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{img_base64}",
                        "detail": "high"
                    }
                })
                
                encoded_images += 1
                logger.info(f"  ✓ Encoded product image {idx + 1}/{min(len(product_images), 3)}")
                
            except Exception as e:
                logger.warning(f"Failed to download/encode product image {idx + 1}: {e}. Skipping...")
                continue
        
        # If no images were successfully encoded, return original prompt
        if encoded_images == 0:
            logger.warning("No product images could be encoded for analysis. Using original prompt.")
            return original_prompt
        
        # Call GPT-4 Vision API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 1000,  # Increased to allow more detailed analysis
                "temperature": 0.1  # Lower temperature for more accurate, consistent analysis
            },
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        if 'choices' not in data or len(data['choices']) == 0:
            logger.warning("No response from GPT-4 Vision, using original prompt")
            return original_prompt
        
        visual_analysis = data['choices'][0]['message']['content'].strip()
        logger.info(f"GPT-4 Vision analysis: {visual_analysis[:300]}...")
        
        # Create a highly structured prompt for DALL-E
        # DALL-E works best with clear, specific, structured descriptions
        enhanced_prompt = f"""Create a product image that matches this exact product specification:

{visual_analysis}

PRODUCT SPECIFICATION DETAILS:
{original_prompt}

CRITICAL REQUIREMENTS FOR ACCURACY:
1. Use the EXACT colors specified in the analysis above
2. Include ALL text, logos, and brand elements exactly as described
3. Match the material texture and finish precisely
4. Replicate all design patterns, stitching, and construction details
5. Maintain the exact proportions and silhouette described
6. Include all visible hardware, labels, and decorative elements

STYLE REQUIREMENTS:
- Professional product photography style
- Clean, well-lit background
- Product centered and clearly visible
- High quality, detailed rendering
- Accurate color representation
- Precise text and logo reproduction

Generate an image that is a pixel-perfect match to the product described in the specification above."""
        
        logger.info(f"Enhanced prompt length: {len(enhanced_prompt)} characters")
        return enhanced_prompt
        
    except Exception as e:
        logger.warning(f"Failed to analyze product images with GPT-4 Vision: {e}. Using original prompt.")
        return original_prompt


def _generate_image_with_product_reference(prompt, api_key, out_path, product_images, retries=3, delay=5):
    """
    Generate an image using GPT-5 with image generation tool, using product images as direct reference.
    This provides better product accuracy than prompt enhancement alone.
    
    Args:
        prompt: Text prompt for image generation
        api_key: OpenAI API key
        out_path: Path to save the generated image
        product_images: List of product image URLs to use as reference
        retries: Number of retry attempts
        delay: Delay between retries
        
    Returns:
        Path to the generated image file
    """
    last_exception = None
    for attempt in range(retries):
        try:
            if OPENAI_NEW_API:
                client = OpenAI(api_key=api_key)
                
                # Download and encode product images (use first image for now, can be extended)
                product_image_url = product_images[0] if product_images else None
                if not product_image_url:
                    raise ValueError("No product image provided")
                
                logger.info(f"Downloading product image for reference: {product_image_url}")
                img_response = requests.get(product_image_url, timeout=30)
                img_response.raise_for_status()
                
                # Save temporarily to encode
                temp_img_path = os.path.join(os.path.dirname(out_path) or '.', f"temp_product_{os.path.basename(out_path)}")
                with open(temp_img_path, 'wb') as f:
                    f.write(img_response.content)
                
                try:
                    # Encode image to base64
                    def b64_encode(path):
                        return base64.b64encode(open(path, "rb").read()).decode("utf-8")
                    
                    img_b64 = b64_encode(temp_img_path)
                    
                    # Enhance prompt for e-commerce lifestyle images
                    enhanced_prompt = (
                        f"{prompt} "
                        "Create a photorealistic lifestyle image featuring the exact same product "
                        "from the reference photo. Preserve brand colors, label text, and product design. "
                        "35mm depth of field, soft shadows, professional product photography style."
                    )
                    
                    logger.info(f"Generating image with GPT-5 using product reference: {enhanced_prompt[:100]}...")
                    
                    # Use GPT-5 with image generation tool
                    # Note: This requires organization verification in OpenAI
                    try:
                        resp = client.responses.create(
                            model="gpt-5",  # Mainline model calling the tool
                            input=[{
                                "role": "user",
                                "content": [
                                    {"type": "input_text", "text": enhanced_prompt},
                                    {"type": "input_image", "image_url": f"data:image/png;base64,{img_b64}"},
                                ],
                            }],
                            tools=[{"type": "image_generation"}],  # Uses gpt-image-1 under the hood
                        )
                    except Exception as api_error:
                        error_str = str(api_error)
                        # Check for organization verification error
                        if "organization must be verified" in error_str.lower() or "403" in error_str:
                            raise RuntimeError(
                                "GPT-5 requires organization verification. "
                                "Please verify your organization at: https://platform.openai.com/settings/organization/general"
                            ) from api_error
                        raise
                    
                    # Extract the base64 image from response
                    img_calls = [o for o in resp.output if o.type == "image_generation_call"]
                    if not img_calls or not img_calls[0].result:
                        raise RuntimeError("No image generated in GPT-5 response")
                    
                    img_b64_result = img_calls[0].result
                    
                    # Decode and save the image
                    img_data = base64.b64decode(img_b64_result)
                    
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
                    
                    with open(out_path, 'wb') as f:
                        f.write(img_data)
                    
                    logger.info(f"Successfully generated and saved image to: {out_path}")
                    return out_path
                    
                finally:
                    # Clean up temporary product image
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
            else:
                raise RuntimeError("GPT-5 image generation requires OpenAI API v1.0+. Please upgrade to openai>=1.0.0")
                
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise RuntimeError(f"GPT-5 image generation failed after {retries} attempts: {e}") from e
    
    raise RuntimeError(f"GPT-5 image generation failed: {last_exception}")


def generate_image_from_prompt(prompt, api_key, out_path="generated_image.png", retries=3, delay=5, product_images=None):
    """
    Generate an image from a text prompt using OpenAI's API and save it to out_path.
    If product_images are provided, uses GPT-5 with image generation tool for direct product reference.
    Otherwise, uses GPT-4 Vision to analyze and enhance the prompt, then DALL-E 3.
    Retries on failure.
    
    Args:
        prompt: Text prompt for image generation
        api_key: OpenAI API key
        out_path: Path to save the generated image
        retries: Number of retry attempts
        delay: Delay between retries
        product_images: Optional list of product image URLs to use as reference
        
    Returns:
        Path to the generated image file
        
    Raises:
        RuntimeError: If image generation fails after all retries
        ValueError: If api_key is not provided
    """
    if not api_key:
        raise ValueError("OpenAI API key is required")
    
    # If product images are provided, try GPT-5 with image generation tool first
    # If GPT-5 is not available (e.g., organization not verified), fall back to DALL-E
    if product_images and len(product_images) > 0:
        try:
            if OPENAI_NEW_API:
                logger.info("Attempting GPT-5 with image generation tool for product image reference (e-commerce workflow)")
                # Use minimal retries (1) to fail fast if GPT-5 is not available
                return _generate_image_with_product_reference(prompt, api_key, out_path, product_images, retries=1, delay=2)
        except Exception as e:
            error_msg = str(e)
            # Check if it's an organization verification error
            if "organization must be verified" in error_msg.lower() or ("gpt-5" in error_msg.lower() and "403" in error_msg):
                logger.warning("GPT-5 not available (organization verification required). Falling back to DALL-E with enhanced prompt.")
            else:
                logger.warning(f"GPT-5 image generation failed, falling back to DALL-E with enhanced prompt: {e}")
            
            # Fall back to the enhanced prompt approach
            try:
                enhanced_prompt = analyze_product_images_with_vision(product_images, prompt, api_key)
                logger.info("Using enhanced prompt based on product image analysis")
            except Exception as e2:
                logger.warning(f"Failed to analyze product images, using original prompt: {e2}")
                enhanced_prompt = prompt
    else:
        enhanced_prompt = prompt
    
    # Handle both old and new OpenAI API
    last_exception = None
    for attempt in range(retries):
        try:
            if OPENAI_NEW_API:
                # New OpenAI API (v1.0+)
                client = OpenAI(api_key=api_key)
                # Use quality="hd" for better detail and accuracy
                # Use style="vivid" for more accurate color and detail reproduction
                response = client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    n=1,
                    size="1024x1792",  # 9:16 aspect ratio for Reels (portrait)
                    quality="hd",  # Higher quality for better product accuracy
                    style="vivid"  # More accurate colors and details
                )
                # Access the image URL from the response
                # The response.data might be a list-like object that needs proper handling
                try:
                    if hasattr(response, 'data'):
                        data = response.data
                        # Convert to list if it's iterable but not a list
                        if not isinstance(data, list):
                            if hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):
                                data = list(data)
                            else:
                                # If it's a single object, wrap it in a list
                                data = [data] if data else []
                        
                        if len(data) > 0:
                            # Access the first item's url attribute
                            first_item = data[0]
                            if hasattr(first_item, 'url'):
                                image_url = first_item.url
                            else:
                                raise RuntimeError(f"Response data item has no 'url' attribute. Type: {type(first_item)}")
                        else:
                            raise RuntimeError("No image data in OpenAI response")
                    else:
                        raise RuntimeError(f"Response object has no 'data' attribute. Type: {type(response)}")
                except (TypeError, AttributeError, IndexError) as e:
                    # Log the actual response structure for debugging
                    logger.error(f"Failed to access image URL from response. Response type: {type(response)}, "
                               f"Has 'data': {hasattr(response, 'data')}, Error: {e}")
                    raise RuntimeError(f"Failed to extract image URL from OpenAI response: {e}") from e
            else:
                # Old OpenAI API (< v1.0)
                if openai_old is None:
                    raise RuntimeError("OpenAI library version not supported. Please upgrade to openai>=1.0.0")
                openai_old.api_key = api_key
                response = openai_old.Image.create(
                    prompt=enhanced_prompt,
                    n=1,
                    size="1024x1792"  # 9:16 aspect ratio for Reels (portrait)
            )
            image_url = response['data'][0]['url']
            
            # Download the generated image
            img_data = requests.get(image_url, timeout=30).content
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
            
            # Save the image
            with open(out_path, 'wb') as handler:
                handler.write(img_data)
            
            logger.info(f"Successfully generated and saved image to: {out_path}")
            return out_path
            
        except Exception as e:
            last_exception = e
            logger.warning(f"Attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise RuntimeError(f"OpenAI image generation failed after {retries} attempts: {e}")
    
    # This should never be reached, but just in case
    raise RuntimeError(f"OpenAI image generation failed: {last_exception}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.error("Usage: python -m video_generator.generate_image 'your prompt here' [output_path]")
        exit(1)
    prompt = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else "generated_image.png"
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("Set OPENAI_API_KEY env variable.")
        exit(1)
    out_path = generate_image_from_prompt(prompt, api_key, out_path)
    logger.info(f"Image saved to {out_path}") 