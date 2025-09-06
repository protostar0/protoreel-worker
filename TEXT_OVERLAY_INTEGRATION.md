# Text Overlay Integration for ProtoReel Worker

## Overview

The ProtoReel Worker now supports rich text overlays for videos! Add titles, captions, callouts, and watermarks to your video scenes with customizable styling, positioning, and animations.

## 🎬 Text Overlay Features

### Text Types
- **Titles**: Large, prominent text for scene headers
- **Subtitles**: Medium text for descriptions
- **Captions**: Small text for additional information
- **Callouts**: Highlighted text to draw attention
- **Watermarks**: Subtle branding or attribution text

### Positioning Options
- **`top`**: Centered at the top
- **`top-left`**: Top left corner
- **`top-right`**: Top right corner
- **`center`**: Center of the video
- **`bottom`**: Centered at the bottom
- **`bottom-left`**: Bottom left corner
- **`bottom-right`**: Bottom right corner

### Animation Effects
- **`fade_in`**: Text fades in over 0.5 seconds
- **`fade_out`**: Text fades out over last 0.5 seconds
- **`fade_in_out`**: Text fades in and out
- **`none`**: No animation (default)

## 🚀 Usage

### 1. Basic Text Overlay

Add simple text to a scene:

```json
{
  "type": "image",
  "prompt_image": "A beautiful sunset",
  "duration": 8,
  "text": {
    "content": "Welcome to Our Journey",
    "position": "center",
    "fontsize": 48,
    "color": "white"
  }
}
```

### 2. Using Text Presets

Use predefined text styles:

```json
{
  "type": "image",
  "prompt_image": "A mountain landscape",
  "duration": 10,
  "text": {
    "content": "Mountain Adventure",
    "preset": "title"
  }
}
```

### 3. Custom Styling

Create custom text with full control:

```json
{
  "type": "image",
  "prompt_image": "A city street",
  "duration": 8,
  "text": {
    "content": "Urban Life",
    "position": "bottom",
    "fontsize": 36,
    "color": "yellow",
    "stroke_color": "black",
    "stroke_width": 3,
    "font": "Arial",
    "animation_type": "fade_in"
  }
}
```

### 4. Callout Text

Highlight important information:

```json
{
  "type": "image",
  "prompt_image": "A product showcase",
  "duration": 12,
  "text": {
    "content": "NEW FEATURE!",
    "preset": "callout",
    "animation_type": "fade_in_out"
  }
}
```

### 5. Watermark

Add subtle branding:

```json
{
  "type": "image",
  "prompt_image": "A professional scene",
  "duration": 10,
  "text": {
    "content": "© 2024 Your Brand",
    "preset": "watermark"
  }
}
```

## ⚙️ Configuration Parameters

### TextOverlay Model

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `content` | `string` | Text content to display | **Required** |
| `position` | `string` | Position of the text | `"center"` |
| `fontsize` | `int` | Font size in pixels | `36` |
| `color` | `string` | Text color | `"white"` |
| `stroke_color` | `string` | Stroke/outline color | `"black"` |
| `stroke_width` | `int` | Stroke width in pixels | `2` |
| `font` | `string` | Font family name | `"Arial"` |
| `animation_type` | `string` | Animation effect | `"none"` |
| `preset` | `string` | Predefined text style | `None` |

### Text Presets

| Preset | Font Size | Color | Stroke | Position | Use Case |
|--------|-----------|-------|--------|----------|----------|
| `title` | 72px | White | Black, 3px | Center | Main titles |
| `subtitle` | 48px | White | Black, 2px | Bottom | Descriptions |
| `caption` | 24px | White | Black, 1px | Bottom | Small text |
| `callout` | 36px | Yellow | Black, 2px | Center | Highlights |
| `watermark` | 18px | Semi-transparent | None | Bottom-right | Branding |

## 🎯 Complete Example

```json
{
  "output_filename": "text_overlay_demo.mp4",
  "scenes": [
    {
      "type": "image",
      "prompt_image": "A serene mountain landscape at sunrise",
      "duration": 8,
      "text": {
        "content": "Mountain Adventure",
        "preset": "title",
        "animation_type": "fade_in"
      }
    },
    {
      "type": "image",
      "prompt_image": "A bustling city street with people",
      "duration": 10,
      "text": {
        "content": "Urban Life",
        "position": "bottom",
        "fontsize": 36,
        "color": "yellow",
        "stroke_color": "black",
        "stroke_width": 2,
        "animation_type": "fade_in_out"
      }
    },
    {
      "type": "image",
      "prompt_image": "A peaceful beach with gentle waves",
      "duration": 8,
      "text": {
        "content": "Tranquility",
        "preset": "subtitle"
      }
    }
  ]
}
```

## 🔧 Technical Implementation

### Text Overlay System Architecture

1. **Text Overlay Utilities** (`video_generator/text_overlay_utils.py`)
   - Core text creation functions
   - Position calculation and validation
   - Animation effects and presets
   - Text styling and formatting

2. **Scene Model Integration** (`video_generator/generator.py`)
   - Extended `TextOverlay` model with rich options
   - Integration with existing scene rendering pipeline
   - Preset and custom configuration support

3. **Rendering Pipeline**
   - Text overlay creation and positioning
   - Composite video generation with text
   - Animation effect application
   - Error handling and fallbacks

### Text Rendering Process

```python
# 1. Create text clip with styling
text_clip = TextClip(
    text=content,
    fontsize=font_size,
    color=color,
    stroke_color=stroke_color,
    stroke_width=stroke_width,
    font=font
)

# 2. Position the text
positioned_clip = text_clip.with_position((x, y))

# 3. Apply animations
if animation_type == "fade_in":
    animated_clip = positioned_clip.with_effects([
        lambda clip: clip.with_opacity(lambda t: min(1.0, t / 0.5))
    ])

# 4. Composite with video
result_clip = CompositeVideoClip([video_clip, animated_clip])
```

## 🧪 Testing

Test text overlay functionality:

```bash
# Test with a simple payload
python -c "
import json
payload = {
    'output_filename': 'test_text.mp4',
    'scenes': [{
        'type': 'image',
        'prompt_image': 'A test image',
        'duration': 5,
        'text': {
            'content': 'Test Text',
            'preset': 'title'
        }
    }]
}
print(json.dumps(payload, indent=2))
"
```

## 🎨 Best Practices

### Text Selection

1. **Content Type**
   - **Titles**: Use for main scene headers (preset: "title")
   - **Subtitles**: Use for descriptions (preset: "subtitle")
   - **Captions**: Use for additional info (preset: "caption")
   - **Callouts**: Use for highlights (preset: "callout")
   - **Watermarks**: Use for branding (preset: "watermark")

2. **Positioning Guidelines**
   - **Center**: Good for main titles and callouts
   - **Top**: Good for scene headers
   - **Bottom**: Good for subtitles and captions
   - **Corners**: Good for watermarks and small text

3. **Color Considerations**
   - **White text**: Good contrast on most backgrounds
   - **Yellow text**: Good for highlights and callouts
   - **Stroke/outline**: Essential for readability
   - **Semi-transparent**: Good for watermarks

### Performance Optimization

- Text overlays are rendered efficiently using MoviePy
- Memory usage is optimized during text processing
- Fallback mechanisms ensure video generation continues even if text fails

## 🔄 Backward Compatibility

The text overlay system is fully backward compatible:

- Existing payloads without text overlays work unchanged
- No changes required to existing video generation workflows
- Text overlay parameters are optional with sensible defaults

## 🚀 Future Enhancements

Planned features for future releases:

1. **Advanced Text Effects**
   - Text shadows and glows
   - Gradient text colors
   - Text masks and clipping
   - 3D text effects

2. **Text Templates**
   - User-defined text styles
   - Brand-specific text themes
   - Text style libraries

3. **Interactive Text**
   - Clickable text overlays
   - Text-based navigation
   - Dynamic text updates

4. **Performance Improvements**
   - GPU acceleration for text rendering
   - Text caching and optimization
   - Batch text processing

---

**Version**: 1.0.0  
**Status**: Production Ready ✅  
**Compatibility**: ProtoReel Worker v2.0+ 