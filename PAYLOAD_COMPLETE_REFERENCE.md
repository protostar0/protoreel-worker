# Complete Payload Reference Guide

## Overview

This document provides a comprehensive reference for all payload features supported by the ProtoReel Worker, including scene types, subtitle configurations, logo settings, image/video options, and advanced features.

## Table of Contents

1. [Basic Payload Structure](#basic-payload-structure)
2. [Scene Types](#scene-types)
3. [Subtitle Configuration](#subtitle-configuration)
4. [Logo Configuration](#logo-configuration)
5. [Image Generation & Sources](#image-generation--sources)
6. [Video Generation](#video-generation)
7. [Audio & Narration](#audio--narration)
8. [Advanced Features](#advanced-features)
9. [Complete Examples](#complete-examples)

---

## Basic Payload Structure

### Required Fields
```json
{
  "output_filename": "your_video.mp4",
  "scenes": [
    // Scene definitions here
  ]
}
```

### Optional Global Fields
```json
{
  "output_filename": "your_video.mp4",
  "global_subtitle_config": { /* Global subtitle settings */ },
  "logo": { /* Global logo settings */ },
  "narration_text": "Global narration for all scenes",
  "audio_prompt_url": "https://example.com/audio_prompt.mp3",
  "theme": "professional",
  "scenes": [ /* Scene definitions */ ]
}
```

---

## Scene Types

### 1. Image Scene
Generate or use an image with narration and optional subtitles.

```json
{
  "type": "image",
  "narration_text": "Your narration text here",
  "prompt_image": "A professional business setup with modern equipment",
  "image_provider": "openai",  // "openai", "freepik", "gemini"
  "duration": 10,
  "subtitle": true,
  "subtitle_config": { /* Subtitle settings */ },
  "logo": { /* Per-scene logo */ },
  "music": "https://example.com/music.mp3",
  "music_volume": 0.3
}
```

### 2. Video Scene
Use existing video or generate new video with AI.

```json
{
  "type": "video",
  "video_url": "https://example.com/video.mp4",  // Existing video
  "prompt_video": "A professional tutorial video",  // AI-generated video
  "video_resolution": "1080p",  // "720p", "1080p", "1440p"
  "video_aspect_ratio": "16:9",  // "9:16", "16:9", "1:1", "4:3", "3:4"
  "video_duration": "10s",  // "5s", "10s", "15s", "30s"
  "video_model": "ray-2",  // LumaAI model
  "narration_text": "Your narration text",
  "duration": 10,
  "subtitle": true,
  "logo": { /* Per-scene logo */ }
}
```

### 3. Image Edit Scene
Edit an existing image using AI prompts.

```json
{
  "type": "image",
  "image_url": "https://example.com/original.jpg",
  "prompt_edit_image": "Add a professional background and modern lighting",
  "image_provider": "gemini",  // Best for image editing
  "narration_text": "Your narration text",
  "duration": 8,
  "subtitle": true
}
```

---

## Subtitle Configuration

### Global Subtitle Config
Apply subtitle settings to all scenes by default.

```json
{
  "global_subtitle_config": {
    "font": "Bangers-Regular.ttf",
    "font_size": 120,
    "font_color": "yellow",
    "stroke_color": "black",
    "stroke_width": 3,
    "highlight_current_word": true,
    "word_highlight_color": "red",
    "line_count": 2,
    "position": "center",
    "padding": 50,
    "shadow_strength": 1.0,
    "shadow_blur": 0.1,
    "initial_prompt": "Professional tutorial video",
    "use_local_whisper": "auto"
  }
}
```

### Per-Scene Subtitle Config
Override global settings for specific scenes.

```json
{
  "type": "image",
  "narration_text": "Your text here",
  "subtitle": true,
  "subtitle_config": {
    "font_size": 150,  // Override global size
    "position": "bottom",  // Override global position
    "font_color": "white"  // Override global color
    // Other parameters use global defaults
  }
}
```

### Subtitle Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `font` | string | `"Bangers-Regular.ttf"` | Font file name |
| `font_size` | integer | `120` | Font size in pixels |
| `font_color` | string | `"yellow"` | Text color |
| `stroke_color` | string | `"black"` | Stroke/outline color |
| `stroke_width` | integer | `3` | Stroke width |
| `highlight_current_word` | boolean | `true` | Enable word highlighting |
| `word_highlight_color` | string | `"red"` | Highlight color |
| `line_count` | integer | `2` | Maximum text lines |
| `position` | string | `"center"` | Position: `"top"`, `"center"`, `"bottom"` |
| `padding` | integer | `50` | Edge padding |
| `shadow_strength` | float | `1.0` | Shadow strength (0.0-2.0) |
| `shadow_blur` | float | `0.1` | Shadow blur (0.0-1.0) |
| `initial_prompt` | string | `null` | Transcription prompt |
| `use_local_whisper` | string | `"auto"` | Whisper model: `"auto"`, `"yes"`, `"no"` |

---

## Logo Configuration

### Global Logo Config
Apply logo to all scenes and final video.

```json
{
  "logo": {
    "url": "https://example.com/logo.png",
    "position": "bottom-right",  // "top-left", "top-right", "bottom-left", "bottom-right", "center"
    "opacity": 0.7,  // 0.0 to 1.0
    "size": [150, 150],  // [width, height] in pixels
    "margin": 20,  // Distance from edges
    "show_in_all_scenes": true,  // Apply to every scene
    "cta_screen": true  // Show on final video
  }
}
```

### Per-Scene Logo Config
Override global logo for specific scenes.

```json
{
  "type": "image",
  "narration_text": "Your text here",
  "logo": {
    "url": "https://example.com/scene_logo.png",
    "position": "center",
    "opacity": 0.5,
    "size": [100, 100]
    // Will override global logo for this scene
  }
}
```

### Logo Parameters Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | string | **Required** | Logo image URL |
| `position` | string | `"bottom-right"` | Logo position on video |
| `opacity` | float | `1.0` | Logo transparency (0.0-1.0) |
| `size` | array | `null` | Logo dimensions [width, height] |
| `margin` | integer | `20` | Distance from video edges |
| `show_in_all_scenes` | boolean | `false` | Apply to every scene |
| `cta_screen` | boolean | `false` | Show on final concatenated video |

---

## Image Generation & Sources

### Image Providers

#### OpenAI DALL-E
```json
{
  "image_provider": "openai",
  "prompt_image": "A modern office with professional lighting and equipment"
}
```

#### Freepik AI Mystic
```json
{
  "image_provider": "freepik",
  "prompt_image": "Professional business presentation setup"
}
```

#### Google Gemini
```json
{
  "image_provider": "gemini",
  "prompt_image": "A creative workspace with modern technology"
}
```

### Image Editing
```json
{
  "image_url": "https://example.com/original.jpg",
  "prompt_edit_image": "Add professional background, improve lighting, make it more modern",
  "image_provider": "gemini"  // Best for editing
}
```

---

## Video Generation

### LumaAI Video Generation
```json
{
  "type": "video",
  "prompt_video": "A professional tutorial video showing step-by-step process",
  "video_resolution": "1080p",  // "720p", "1080p", "1440p"
  "video_aspect_ratio": "16:9",  // "9:16", "16:9", "1:1", "4:3", "3:4"
  "video_duration": "15s",  // "5s", "10s", "15s", "30s"
  "video_model": "ray-2"  // LumaAI model
}
```

### Video Parameters Reference

| Parameter | Type | Options | Description |
|-----------|------|---------|-------------|
| `video_resolution` | string | `"720p"`, `"1080p"`, `"1440p"` | Video quality |
| `video_aspect_ratio` | string | `"9:16"`, `"16:9"`, `"1:1"`, `"4:3"`, `"3:4"` | Video dimensions |
| `video_duration` | string | `"5s"`, `"10s"`, `"15s"`, `"30s"` | Video length |
| `video_model` | string | `"ray-2"` | LumaAI generation model |

---

## Audio & Narration

### Global Narration
Apply the same narration to all scenes.

```json
{
  "narration_text": "This is a comprehensive tutorial about advanced features",
  "audio_prompt_url": "https://example.com/voice_prompt.mp3"
}
```

### Per-Scene Narration
```json
{
  "type": "image",
  "narration_text": "Scene-specific narration text",
  "audio_prompt_url": "https://example.com/scene_voice.mp3"
}
```

### Background Music
```json
{
  "type": "image",
  "narration_text": "Your text here",
  "music": "https://example.com/background_music.mp3",
  "music_volume": 0.25  // 0.0 to 1.0
}
```

### Audio Parameters Reference

| Parameter | Type | Description |
|-----------|------|-------------|
| `narration_text` | string | Text to convert to speech |
| `audio_prompt_url` | string | Voice style reference audio |
| `music` | string | Background music URL |
| `music_volume` | float | Music volume (0.0-1.0) |

---

## Advanced Features

### Scene Context & Metadata
```json
{
  "type": "image",
  "narration_text": "Your text here",
  "duration": 10,
  "text": {
    "content": "Overlay text on video",
    "position": "top-center",
    "font_size": 48,
    "color": "white"
  }
}
```

### Performance Optimization
```json
{
  "scenes": [ /* Your scenes */ ],
  "performance": {
    "parallel_processing": true,
    "memory_optimization": true,
    "cache_enabled": true
  }
}
```

### Custom Text Overlays
```json
{
  "text": {
    "content": "Your overlay text",
    "position": "top-center",  // "top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right"
    "font_size": 48,
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 2
  }
}
```

---

## Complete Examples

### Example 1: Professional Tutorial Video
```json
{
  "output_filename": "professional_tutorial.mp4",
  "global_subtitle_config": {
    "font": "Arial-Bold.ttf",
    "font_size": 100,
    "font_color": "white",
    "stroke_color": "black",
    "stroke_width": 2,
    "position": "bottom",
    "highlight_current_word": true,
    "word_highlight_color": "yellow"
  },
  "logo": {
    "url": "https://example.com/company_logo.png",
    "position": "bottom-right",
    "opacity": 0.8,
    "size": [120, 120],
    "show_in_all_scenes": true,
    "cta_screen": true
  },
  "scenes": [
    {
      "type": "image",
      "narration_text": "Welcome to our comprehensive tutorial",
      "prompt_image": "Professional tutorial setup with modern equipment",
      "image_provider": "openai",
      "duration": 8,
      "subtitle": true
    },
    {
      "type": "image",
      "narration_text": "Let's start with the basics",
      "prompt_image": "Basic concepts visualization with clear diagrams",
      "image_provider": "gemini",
      "duration": 10,
      "subtitle": true,
      "subtitle_config": {
        "font_size": 120,
        "position": "center"
      }
    },
    {
      "type": "video",
      "prompt_video": "Step-by-step demonstration of the process",
      "video_resolution": "1080p",
      "video_aspect_ratio": "16:9",
      "video_duration": "15s",
      "narration_text": "Here's how to implement this step by step",
      "duration": 15,
      "subtitle": true
    }
  ]
}
```

### Example 2: Social Media Content
```json
{
  "output_filename": "social_media_post.mp4",
  "global_subtitle_config": {
    "font": "Bangers-Regular.ttf",
    "font_size": 150,
    "font_color": "orange",
    "stroke_color": "purple",
    "stroke_width": 4,
    "highlight_current_word": true,
    "word_highlight_color": "pink",
    "position": "center",
    "line_count": 1
  },
  "scenes": [
    {
      "type": "image",
      "narration_text": "Amazing new feature alert!",
      "prompt_image": "Exciting announcement with modern design",
      "image_provider": "freepik",
      "duration": 5,
      "subtitle": true,
      "music": "https://example.com/upbeat_music.mp3",
      "music_volume": 0.4
    },
    {
      "type": "image",
      "narration_text": "Check out these incredible benefits",
      "prompt_image": "Benefits list with attractive visuals",
      "image_provider": "openai",
      "duration": 6,
      "subtitle": true
    }
  ]
}
```

### Example 3: Educational Content
```json
{
  "output_filename": "educational_video.mp4",
  "global_subtitle_config": {
    "font": "Arial.ttf",
    "font_size": 80,
    "font_color": "white",
    "stroke_color": "black",
    "stroke_width": 1,
    "position": "bottom",
    "highlight_current_word": false,
    "line_count": 2
  },
  "scenes": [
    {
      "type": "image",
      "image_url": "https://example.com/existing_diagram.jpg",
      "prompt_edit_image": "Add clear labels and improve readability",
      "image_provider": "gemini",
      "narration_text": "This diagram shows the fundamental structure",
      "duration": 12,
      "subtitle": true
    },
    {
      "type": "image",
      "narration_text": "Now let's examine the key components",
      "prompt_image": "Detailed component breakdown with annotations",
      "image_provider": "openai",
      "duration": 15,
      "subtitle": true,
      "subtitle_config": {
        "font_size": 90,
        "position": "bottom"
      }
    }
  ]
}
```

---

## Best Practices

### 1. **Subtitle Configuration**
- Use **global subtitle config** for consistent styling across all scenes
- Override specific parameters per scene when needed
- Ensure high contrast between text and background
- Test font sizes for different viewing platforms

### 2. **Logo Placement**
- Use **bottom-right** for most content (least intrusive)
- Keep opacity between 0.5-0.8 for visibility
- Size logos appropriately (10-20% of video dimensions)
- Enable `cta_screen` for final branding

### 3. **Scene Duration**
- Keep scenes between 5-15 seconds for engagement
- Match duration to narration length
- Use consistent timing across similar content types

### 4. **Image Generation**
- Use **OpenAI** for realistic, professional images
- Use **Freepik** for creative, artistic content
- Use **Gemini** for image editing and modifications
- Provide detailed, specific prompts for better results

### 5. **Performance**
- Enable parallel processing for multiple scenes
- Use appropriate video resolutions for your needs
- Optimize memory usage for Docker environments

---

## Troubleshooting

### Common Issues

1. **Scenes in Wrong Order**
   - ✅ **Fixed**: Scene order is now preserved in parallel processing
   - Check logs for "Added scene X to final video" messages

2. **Subtitle Not Appearing**
   - Ensure `subtitle: true` is set
   - Check `narration_text` is provided
   - Verify subtitle config parameters

3. **Logo Not Visible**
   - Check logo URL accessibility
   - Verify opacity and size settings
   - Ensure `show_in_all_scenes` or per-scene config

4. **Image Generation Fails**
   - Verify API keys are set
   - Check prompt clarity and appropriateness
   - Ensure image provider is supported

### Debug Commands
```bash
# Check environment variables
env | grep -E "(OPENAI|FREEPIK|GEMINI)"

# Test subtitle integration
python -c "from video_generator.captacity_integration import test_captacity_integration; test_captacity_integration()"

# Test generator import
python -c "from video_generator.generator import generate_video_core; print('✅ Generator working')"
```

---

## API Reference

### SceneInput Model
```python
class SceneInput(BaseModel):
    type: str                                    # "image" or "video"
    image_url: Optional[str] = None             # Existing image URL
    prompt_image: Optional[str] = None          # AI image generation prompt
    prompt_edit_image: Optional[str] = None     # AI image editing prompt
    image_provider: Optional[str] = "openai"    # "openai", "freepik", "gemini"
    video_url: Optional[str] = None            # Existing video URL
    prompt_video: Optional[str] = None         # AI video generation prompt
    video_resolution: Optional[str] = "720p"   # Video quality
    video_aspect_ratio: Optional[str] = "9:16" # Video dimensions
    video_duration: Optional[str] = "5s"       # Video length
    video_model: Optional[str] = "ray-2"       # LumaAI model
    narration: Optional[str] = None            # Audio file URL
    narration_text: Optional[str] = None       # Text to convert to speech
    audio_prompt_url: Optional[str] = None     # Voice style reference
    music: Optional[str] = None                # Background music URL
    music_volume: Optional[float] = 0.25       # Music volume
    duration: int                              # Scene duration in seconds
    text: Optional[TextOverlay] = None         # Text overlay configuration
    subtitle: bool = False                     # Enable subtitles
    subtitle_config: Optional[Dict[str, Any]] = None  # Subtitle settings
    logo: Optional[LogoConfig] = None          # Per-scene logo
```

---

**Last Updated**: August 2025  
**Version**: 2.0.0  
**Status**: Production Ready ✅  
**Compatibility**: ProtoReel Worker v2.0+ with Full Feature Set 