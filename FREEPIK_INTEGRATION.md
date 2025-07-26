# Freepik API Integration

This document explains how to use the Freepik API integration for automatic image generation in ProtoVideo.

## Overview

The video generator now supports Freepik's AI Mystic API for image generation, in addition to OpenAI's DALL-E. This provides an alternative image generation service with different styles and capabilities.

## Setup

### 1. Get Freepik API Key

1. Sign up for a Freepik account at [freepik.com](https://freepik.com)
2. Navigate to your account settings
3. Generate an API key for the AI Mystic service
4. Set the environment variable:
   ```bash
   export FREEPIK_API_KEY="your_freepik_api_key_here"
   ```

### 2. Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `FREEPIK_API_KEY` | Your Freepik API key | Yes (for Freepik generation) |
| `OPENAI_API_KEY` | Your OpenAI API key | Yes (for OpenAI generation) |

## Usage

### API Request

When creating a video generation request, you can specify which image generation provider to use:

```json
{
  "output_filename": "my_video.mp4",
  "scenes": [
    {
      "type": "image",
      "promptImage": "A beautiful sunset over mountains",
      "image_provider": "freepik",
      "duration": 10
    },
    {
      "type": "image", 
      "promptImage": "A modern city skyline at night",
      "image_provider": "openai",
      "duration": 8
    }
  ]
}
```

### Provider Options

- **`"openai"`** (default): Uses OpenAI's DALL-E for image generation
- **`"freepik"`**: Uses Freepik's AI Mystic for image generation

### Aspect Ratios (Freepik)

Freepik supports different aspect ratios. The current implementation uses `"classic_4_3"` by default, but you can modify the code to support:

- `"classic_4_3"` - Traditional 4:3 aspect ratio
- `"square_1_1"` - Square 1:1 aspect ratio
- `"portrait_3_4"` - Portrait 3:4 aspect ratio
- `"landscape_16_9"` - Widescreen 16:9 aspect ratio

## Features

### Freepik API Features

- **Asynchronous Generation**: Images are generated asynchronously with status polling
- **Multiple Aspect Ratios**: Support for different image aspect ratios
- **High Quality**: Professional-grade image generation
- **Style Variety**: Different artistic styles and approaches compared to DALL-E

### Error Handling

The integration includes comprehensive error handling:

- **API Key Validation**: Checks for valid API keys before making requests
- **Timeout Protection**: Configurable timeouts to prevent hanging requests
- **Status Polling**: Monitors generation progress and handles failures
- **Fallback Support**: Can fall back to OpenAI if Freepik fails

## Testing

Run the test script to verify Freepik integration:

```bash
cd protovideo-worker
python tests/test_freepik_integration.py
```

## Code Examples

### Basic Usage

```python
from video_generator.image_utils import generate_image_from_prompt

# Generate with Freepik
image_path = generate_image_from_prompt(
    prompt="A beautiful sunset over mountains",
    api_key="your_freepik_api_key",
    out_path="output.png",
    provider="freepik"
)

# Generate with OpenAI (default)
image_path = generate_image_from_prompt(
    prompt="A modern city skyline",
    api_key="your_openai_api_key", 
    out_path="output.png",
    provider="openai"
)
```

### Direct Freepik API Usage

```python
from video_generator.freepik_api import FreepikAPI

freepik = FreepikAPI("your_api_key")

# Generate image URL
image_url = freepik.generate_image(
    prompt="A beautiful landscape",
    aspect_ratio="classic_4_3"
)

# Download the image
local_path = freepik.download_generated_image(image_url, "output.png")
```

## Configuration

### Timeout Settings

You can adjust timeout settings in the `FreepikAPI` class:

```python
# In freepik_api.py
def generate_image(self, prompt: str, aspect_ratio: str = "classic_4_3", 
                  max_wait_time: int = 60, poll_interval: int = 2) -> str:
```

- `max_wait_time`: Maximum time to wait for generation (default: 60 seconds)
- `poll_interval`: Time between status checks (default: 2 seconds)

### Logging

The integration uses structured logging with task IDs for easy debugging:

```python
logger.info(f"Generating image with Freepik API. Prompt: {prompt[:50]}...")
logger.info(f"Freepik generation task created: {task_id}")
logger.info(f"Freepik image generation completed: {image_url}")
```

## Troubleshooting

### Common Issues

1. **"FREEPIK_API_KEY environment variable not set"**
   - Ensure you've set the `FREEPIK_API_KEY` environment variable
   - Check that the API key is valid and has the necessary permissions

2. **"Freepik generation failed"**
   - Check your API key permissions
   - Verify the prompt doesn't violate Freepik's content policies
   - Check network connectivity

3. **"Freepik image generation timed out"**
   - Increase `max_wait_time` for complex prompts
   - Check Freepik service status
   - Try a simpler prompt

4. **"Failed to download Freepik image"**
   - Check network connectivity
   - Verify the image URL is accessible
   - Ensure sufficient disk space

### Debug Mode

Enable debug logging to see detailed API interactions:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Performance Considerations

- **Generation Time**: Freepik images typically take 10-30 seconds to generate
- **Polling**: The system polls every 2 seconds by default
- **Concurrent Requests**: Freepik may have rate limits - check their documentation
- **Image Quality**: Freepik images are optimized for professional use

## Cost Considerations

- **Freepik Credits**: Each image generation consumes Freepik credits
- **API Limits**: Check your Freepik account for rate limits and quotas
- **Fallback Strategy**: Consider using OpenAI as a fallback for cost optimization

## Security Notes

- **API Keys**: Never commit API keys to version control
- **Environment Variables**: Use secure environment variable management
- **Rate Limiting**: Implement appropriate rate limiting for production use
- **Content Policies**: Ensure generated content complies with Freepik's policies 