## Configuration Methods

### 1. **Per-Scene Configuration**
Set subtitle parameters for individual scenes:

```json
{
  "scenes": [
    {
      "type": "image",
      "narration_text": "Your text here",
      "subtitle": true,
      "subtitle_config": {
        "font": "Bangers-Regular.ttf",
        "font_size": 130,
        "font_color": "yellow",
        "position": "center"
      }
    }
  ]
}
```

### 2. **Global Configuration**
Set default subtitle parameters for all scenes:

```json
{
  "global_subtitle_config": {
    "font": "Bangers-Regular.ttf",
    "font_size": 120,
    "font_color": "yellow",
    "position": "center"
  },
  "scenes": [
    {
      "type": "image",
      "narration_text": "Your text here",
      "subtitle": true
    }
  ]
}
```

### 3. **Mixed Configuration with Fallback**
Combine global defaults with scene-specific overrides:

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
    "padding": 50
  },
  "scenes": [
    {
      "type": "image",
      "narration_text": "Scene 1 - Uses global config",
      "subtitle": true
      // No subtitle_config - automatically uses global_subtitle_config
    },
    {
      "type": "image",
      "narration_text": "Scene 2 - Overrides some global settings",
      "subtitle": true,
      "subtitle_config": {
        "font_size": 150,  // Override global size
        "position": "bottom",  // Override global position
        "font_color": "white"  // Override global color
        // Other parameters (font, stroke_color, etc.) use global defaults
      }
    }
  ]
}
```

### 4. **Automatic Fallback System**
The subtitle system automatically handles configuration fallback:

1. **Scene has `subtitle_config`**: Uses scene-specific settings
2. **Scene has no `subtitle_config` but `global_subtitle_config` exists**: Uses global settings
3. **Neither exists**: Uses hardcoded defaults

This means you can:
- Set global defaults once and apply to all scenes
- Override specific parameters per scene when needed
- Mix and match configurations freely
- Ensure consistent subtitle styling across your video 