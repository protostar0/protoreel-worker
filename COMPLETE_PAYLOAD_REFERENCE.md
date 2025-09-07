# 🎬 Complete ProtoReel Worker Payload Reference

## 📋 Basic Payload Structure

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

## 🏷️ Scene Tracking & Identification

### **Scene ID System**
Each scene can have a unique `scene_id` for better tracking and debugging throughout the video generation process.

#### **Manual Scene ID**
```json
{
  "scene_id": "intro_scene",
  "type": "image",
  "narration_text": "Welcome to our tutorial"
}
```

#### **Automatic Scene ID Generation**
If `scene_id` is not provided, the system automatically generates one based on:
- **Scene type** (image/video)
- **Scene index** (1-based position)
- **Content identifier** (from prompt, URL, or narration)

**Examples of auto-generated scene IDs:**
- `image_1_professional_business_setup` (from prompt_image)
- `video_2_step_by_step_demo` (from prompt_video)
- `image_3_welcome_to_our` (from narration_text)
- `video_1_example_video` (from video_url filename)

#### **Scene ID Benefits**
- **Better Logging**: All logs include scene_id for easier tracking
- **Debugging**: Easier to identify which scene caused issues
- **Monitoring**: Track performance per scene
- **Order Preservation**: Maintains scene order in parallel processing

---

## 🎭 Scene Types

### 1. **Image Scene** - Generate or use images
```json
{
  "scene_id": "image_1_intro",  // Optional: Unique identifier for scene tracking
  "type": "image",
  "narration_text": "Your narration text here",
  "prompt_image": "A professional business setup with modern equipment",
  "image_provider": "openai",  // "openai", "freepik", "gemini"
  "image_url": "https://example.com/existing.jpg",  // Use existing image
  "prompt_edit_image": "Add professional background",  // AI edit existing image
  "duration": 10,
  "subtitle": true,
  "subtitle_config": { /* Subtitle settings */ },
  "logo": { /* Per-scene logo */ },
  "music": "https://example.com/music.mp3",
  "music_volume": 0.3,
  "animation_mode": "zoom_in",  // Animation for image
  "animation_preset": "subtle",  // Predefined animation
  "text": { /* Text overlay */ }
}
```

### 2. **Video Scene** - Use existing or generate videos
```json
{
  "scene_id": "video_2_demo",  // Optional: Unique identifier for scene tracking
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

---

## 🖼️ Image Generation & Sources

### **Image Providers**
- **`"openai"`** - OpenAI DALL-E (realistic, professional images)
- **`"freepik"`** - Freepik AI Mystic (creative, artistic content)
- **`"gemini"`** - Google Gemini (best for image editing)

### **Image Features**
- **AI Generation**: `prompt_image` - Generate new images from text
- **Image Editing**: `prompt_edit_image` - Modify existing images with AI
- **Existing Images**: `image_url` - Use pre-existing images

---

## 🎥 Video Generation

### **LumaAI Video Generation**
- **Resolution**: `"720p"`, `"1080p"`, `"1440p"`
- **Aspect Ratios**: `"9:16"`, `"16:9"`, `"1:1"`, `"4:3"`, `"3:4"`
- **Duration**: `"5s"`, `"10s"`, `"15s"`, `"30s"`
- **Model**: `"ray-2"` (default LumaAI model)

---

## 🎵 Audio & Narration

### **Narration Options**
- **Global Narration**: `narration_text` - Same narration for all scenes
- **Per-Scene Narration**: Individual `narration_text` per scene
- **Voice Style**: `audio_prompt_url` - Reference audio for voice cloning
- **Existing Audio**: `narration` - Use pre-recorded audio files

### **Background Music**
- **Music URL**: `music` - Background music file
- **Volume Control**: `music_volume` (0.0 to 1.0)

---

## 📝 Subtitle Configuration

### **Global Subtitle Config**
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
    "position": "center",  // "top", "center", "bottom"
    "padding": 50,
    "shadow_strength": 1.0,
    "shadow_blur": 0.1,
    "initial_prompt": "Professional tutorial video",
    "use_local_whisper": "auto"  // "auto", "yes", "no"
  }
}
```

### **Subtitle Features**
- **Word Highlighting**: Current word highlighting with custom colors
- **Multiple Lines**: Support for 1-2 lines of text
- **Custom Fonts**: Support for custom font files
- **Positioning**: Top, center, or bottom placement
- **Styling**: Custom colors, strokes, shadows

---

## 🏷️ Logo Configuration

### **Global Logo Config**
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

### **Logo Features**
- **Per-Scene Override**: Individual logo settings per scene
- **Auto-Scaling**: Automatic size adjustment if not specified
- **Opacity Control**: Transparency adjustment
- **Positioning**: 5 different position options

---

## ✨ Animation Configuration

### **Animation Modes**
- **Zoom**: `"zoom_in"`, `"zoom_out"`, `"pulse"`
- **Motion**: `"drift_up"`, `"drift_down"`, `"oscillate"`
- **Combinations**: Multiple modes can be combined

### **Animation Presets**
- **`"subtle"`** - Gentle zoom with slight motion
- **`"dynamic"`** - Strong zoom with oscillation
- **`"smooth"`** - Smooth drift motion
- **`"energetic"`** - Pulse with oscillation
- **`"zoom_only"`** - Pure zoom effects
- **`"motion_only"`** - Pure motion effects

### **Animation Parameters**
```json
{
  "animation_mode": "zoom_in",
  "animation_preset": "subtle",
  "animation_darken_factor": 0.5,  // 0.0 to 1.0
  "animation_drift_px": 60,  // Pixels for drift motion
  "animation_osc_px": 40  // Amplitude for oscillation
}
```

---

## 📄 Text Overlays

### **Text Overlay Configuration**
```json
{
  "text": {
    "content": "Your overlay text",
    "position": "top-center",  // "top-left", "top-center", "top-right", "center", "bottom-left", "bottom-center", "bottom-right"
    "fontsize": 48,
    "color": "white",
    "stroke_color": "black",
    "stroke_width": 2,
    "font": "Arial.ttf",  // Custom font
    "padding": 20,
    "animation_type": "fade_in",  // "fade_in", "fade_out", "fade_in_out", "none"
    "preset": "title"  // "title", "subtitle", "caption", "callout", "watermark"
  }
}
```

---

## 🔄 Transition Configuration

### **Scene Transitions**
```json
{
  "transition_type": "fade",  // Transition type
  "transition_duration": 1.0  // Duration in seconds
}
```

---

## ⚡ Advanced Features

### **Performance Optimization**
- **Parallel Processing**: Multiple scenes processed simultaneously
- **Memory Optimization**: Automatic memory management
- **Cache System**: Cached results for faster processing
- **Hardware Acceleration**: GPU acceleration when available

### **Video Processing**
- **Smart Resizing**: Automatic video sizing with blurred backgrounds
- **Zoom Limiting**: Prevents excessive zooming (max 2.5x)
- **Background Blur**: Blurred backgrounds for small videos
- **Quality Optimization**: Multiple quality presets

---

## 🎯 Complete Example

```json
{
  "output_filename": "professional_tutorial.mp4",
  "global_subtitle_config": {
    "font": "Bangers-Regular.ttf",
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
      "subtitle": true,
      "animation_mode": "zoom_in",
      "animation_preset": "subtle"
    },
    {
      "type": "video",
      "prompt_video": "Step-by-step demonstration of the process",
      "video_resolution": "1080p",
      "video_aspect_ratio": "16:9",
      "video_duration": "15s",
      "narration_text": "Here's how to implement this step by step",
      "duration": 15,
      "subtitle": true,
      "music": "https://example.com/background.mp3",
      "music_volume": 0.3
    }
  ]
}
```

---

## 🔧 Environment Variables Required

- **`OPENAI_API_KEY`** - For DALL-E image generation
- **`FREEPIK_API_KEY`** - For Freepik AI Mystic
- **`GEMINI_API_KEY`** - For Google Gemini
- **`LUMAAI_API_KEY`** - For video generation
- **`R2_ENDPOINT_URL`** - Cloudflare R2 storage
- **`R2_ACCESS_KEY_ID`** - R2 credentials
- **`R2_SECRET_ACCESS_KEY`** - R2 credentials
- **`R2_BUCKET_NAME`** - R2 bucket name

---

## 🎨 Supported Formats

- **Video Output**: MP4 (H.264, optimized for social media)
- **Image Input**: JPG, PNG, WebP
- **Audio Input**: MP3, WAV, M4A
- **Font Files**: TTF, OTF
- **Aspect Ratios**: 9:16 (Reels), 16:9 (YouTube), 1:1 (Instagram), 4:3, 3:4

---

## 📊 SceneInput Model Reference

```python
class SceneInput(BaseModel):
    scene_id: Optional[str] = None                    # Unique identifier for scene tracking
    type: str                                        # "image" or "video"
    image_url: Optional[str] = None                  # Existing image URL
    prompt_image: Optional[str] = None               # AI image generation prompt
    prompt_edit_image: Optional[str] = None          # AI image editing prompt
    image_provider: Optional[str] = "openai"         # "openai", "freepik", "gemini"
    video_url: Optional[str] = None                  # Existing video URL
    prompt_video: Optional[str] = None               # AI video generation prompt
    video_resolution: Optional[str] = "720p"         # Video quality
    video_aspect_ratio: Optional[str] = "9:16"      # Video dimensions
    video_duration: Optional[str] = "5s"            # Video length
    video_model: Optional[str] = "ray-2"            # LumaAI model
    narration: Optional[str] = None                  # Audio file URL
    narration_text: Optional[str] = None             # Text to convert to speech
    audio_prompt_url: Optional[str] = None           # Voice style reference
    music: Optional[str] = None                      # Background music URL
    music_volume: Optional[float] = 0.25            # Music volume
    duration: int                                    # Scene duration in seconds
    text: Optional[TextOverlay] = None               # Text overlay configuration
    subtitle: bool = False                          # Enable subtitles
    subtitle_config: Optional[Dict[str, Any]] = None # Subtitle settings
    logo: Optional[LogoConfig] = None                # Per-scene logo
    animation_mode: Optional[Union[str, List[str]]] = None  # Animation mode(s)
    animation_preset: Optional[str] = None            # Predefined animation preset
    animation_darken_factor: Optional[float] = 0.5  # Darkening factor
    animation_drift_px: Optional[int] = 60           # Pixels for drift motion
    animation_osc_px: Optional[int] = 40             # Amplitude for oscillation
    transition_type: Optional[str] = None            # Transition type
    transition_duration: Optional[float] = 1.0      # Transition duration
```

---

## 🎯 Best Practices

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

## 🔍 Troubleshooting

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

**Last Updated**: January 2025  
**Version**: 2.0.0  
**Status**: Production Ready ✅  
**Compatibility**: ProtoReel Worker v2.0+ with Full Feature Set

This comprehensive payload system supports everything from simple image slideshows to complex multi-scene videos with AI-generated content, professional subtitles, logos, animations, and advanced audio processing! 🚀
