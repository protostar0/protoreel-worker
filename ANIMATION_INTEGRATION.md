# Animation Integration for ProtoReel Worker

## Overview

The ProtoReel Worker now supports configurable animations for image scenes, providing dynamic visual effects that enhance the viewing experience. The animation system is designed to be flexible, allowing users to choose from predefined presets or create custom animation combinations.

## 🎬 Animation Features

### Available Animation Modes

#### Zoom Effects
- **`zoom_in`**: Gradual zoom from 1.0x to 1.3x scale
- **`zoom_out`**: Gradual zoom from 1.2x to 1.0x scale  
- **`pulse`**: Gentle oscillation between 1.05x and 1.15x scale

#### Motion Effects
- **`drift_up`**: Smooth upward movement over the clip duration
- **`drift_down`**: Smooth downward movement over the clip duration
- **`oscillate`**: Up/down oscillation with configurable amplitude

### Animation Presets

Predefined combinations for common use cases:

- **`subtle`**: `["zoom_in", "drift_up"]` - Gentle, professional animation
- **`dynamic`**: `["zoom_out", "oscillate"]` - Energetic, engaging movement
- **`smooth`**: `["pulse"]` - Gentle, smooth pulsing animation
- **`gentle_drift`**: `["drift_down"]` - Calm, flowing drift motion
- **`energetic`**: `["pulse", "oscillate"]` - Vibrant, lively animation
- **`zoom_only`**: `["zoom_in"]` - Simple zoom effect only
- **`motion_only`**: `["oscillate"]` - Motion effect only

## 🚀 Usage

### 1. Random Animation (Default)

When no animation is specified, the system automatically selects a random combination:

```json
{
  "type": "image",
  "prompt_image": "A beautiful sunset over mountains",
  "narration_text": "Welcome to our amazing world",
  "duration": 8,
  "subtitle": true
  // No animation_mode = random animation
}
```

### 2. Using Animation Presets

Choose from predefined animation styles:

```json
{
  "type": "image",
  "prompt_image": "A professional business setup",
  "narration_text": "Professional excellence at its finest",
  "duration": 10,
  "subtitle": true,
  "animation_preset": "energetic"
}
```

### 3. Custom Animation Modes

Create your own animation combinations:

```json
{
  "type": "image",
  "prompt_image": "A dynamic city skyline",
  "narration_text": "The city never sleeps",
  "duration": 12,
  "subtitle": true,
  "animation_mode": ["zoom_in", "oscillate"],
  "animation_darken_factor": 0.3,
  "animation_drift_px": 80,
  "animation_osc_px": 50
}
```

### 4. Advanced Customization

Fine-tune animation parameters:

```json
{
  "type": "image",
  "prompt_image": "A peaceful forest scene",
  "narration_text": "Nature's tranquility",
  "duration": 8,
  "subtitle": true,
  "animation_mode": ["pulse", "drift_up"],
  "animation_darken_factor": 0.2,  // 20% darkening
  "animation_drift_px": 100,       // 100px drift distance
  "animation_osc_px": 30           // 30px oscillation amplitude
}
```

## ⚙️ Configuration Parameters

### Animation Mode
- **Type**: `string` or `array[string]`
- **Description**: Animation mode(s) to apply
- **Examples**: `"zoom_in"`, `["zoom_out", "oscillate"]`
- **Default**: Random animation if not specified

### Animation Preset
- **Type**: `string`
- **Description**: Predefined animation combination
- **Options**: `"subtle"`, `"dynamic"`, `"smooth"`, `"gentle_drift"`, `"energetic"`, `"zoom_only"`, `"motion_only"`
- **Note**: Overrides `animation_mode` if both are specified

### Animation Darken Factor
- **Type**: `float`
- **Range**: 0.0 to 1.0
- **Description**: Darkening effect intensity (0.0 = no darken, 0.5 = 50% darker)
- **Default**: 0.5
- **Note**: Darkening effect may not be available in all MoviePy versions and will be skipped gracefully if not supported

### Animation Drift Pixels
- **Type**: `integer`
- **Description**: Distance in pixels for drift motion effects
- **Default**: 60

### Animation Oscillation Pixels
- **Type**: `integer`
- **Description**: Amplitude in pixels for oscillation effects
- **Default**: 40

## 🎯 Complete Example

```json
{
  "output_filename": "animated_video.mp4",
  "scenes": [
    {
      "type": "image",
      "prompt_image": "A peaceful mountain landscape",
      "image_provider": "gemini",
      "narration_text": "Welcome to our journey",
      "duration": 8,
      "subtitle": true,
      "animation_preset": "subtle"
    },
    {
      "type": "image",
      "prompt_image": "A bustling city street",
      "image_provider": "gemini",
      "narration_text": "The energy of urban life",
      "duration": 10,
      "subtitle": true,
      "animation_mode": ["zoom_out", "oscillate"],
      "animation_darken_factor": 0.4,
      "animation_drift_px": 70,
      "animation_osc_px": 45
    },
    {
      "type": "image",
      "prompt_image": "A serene ocean sunset",
      "image_provider": "gemini",
      "narration_text": "Finding peace in nature",
      "duration": 8,
      "subtitle": true,
      "animation_preset": "smooth"
    }
  ]
}
```

## 🔧 Technical Implementation

### Animation System Architecture

1. **Animation Utilities** (`video_generator/animation_utils.py`)
   - Core animation functions
   - Mode validation and preset management
   - Random animation generation

2. **Scene Model Integration** (`video_generator/generator.py`)
   - Extended `SceneInput` model with animation fields
   - Animation parameter processing
   - Integration with existing video generation pipeline

3. **Rendering Pipeline**
   - Animation mode determination
   - Parameter validation and fallbacks
   - Animated clip creation

### Animation Curves

#### Zoom Functions
```python
def zoom_in(t):   # 1.00 -> 1.30
    return 1.0 + 0.30 * (t / duration)

def zoom_out(t):  # 1.20 -> 1.00
    return 1.20 - 0.20 * (t / duration)

def zoom_pulse(t):  # gentle 1.10 ± 0.05
    return 1.10 + 0.05 * np.sin(2 * np.pi * t / duration)
```

#### Motion Functions
```python
def pos_drift_up(t):
    return ('center', H / 2 - drift_px * (t / duration))

def pos_drift_down(t):
    return ('center', H / 2 + drift_px * (t / duration))

def pos_oscillate(t):
    return ('center', H / 2 + osc_px * np.sin(2 * np.pi * t / duration))
```

## 🧪 Testing

Run the animation integration test:

```bash
python test_animation_integration.py
```

This will test:
- Animation utilities import and functionality
- Scene model with animation fields
- Example payloads with different animation configurations

## 🎨 Best Practices

### Animation Selection

1. **Content Type**
   - **Professional/Business**: Use `subtle` or `zoom_only`
   - **Energetic/Dynamic**: Use `dynamic` or `energetic`
   - **Calm/Serene**: Use `smooth` or `motion_only`

2. **Duration Considerations**
   - **Short clips (5-8s)**: Use single effects or subtle combinations
   - **Medium clips (8-15s)**: Use moderate combinations
   - **Long clips (15s+)**: Use more complex combinations

3. **Content Matching**
   - **Zoom in**: Good for revealing details or building excitement
   - **Zoom out**: Good for showing context or calming effects
   - **Oscillation**: Good for dynamic, energetic content
   - **Drift**: Good for smooth, flowing narratives

### Performance Optimization

- Animation processing is optimized for Instagram Reels (9:16 aspect ratio)
- Effects are applied efficiently using MoviePy's built-in functions
- Memory usage is monitored and optimized during animation generation
- Darkening effects are gracefully skipped if not supported in the current MoviePy version

## 🔄 Backward Compatibility

The animation system is fully backward compatible:

- Existing payloads without animation fields will use random animations
- No changes required to existing video generation workflows
- Animation parameters are optional with sensible defaults

## 🚀 Future Enhancements

Planned features for future releases:

1. **Advanced Animation Modes**
   - Rotation effects
   - Color transitions
   - Particle effects

2. **Animation Templates**
   - User-defined animation presets
   - Animation style libraries
   - Brand-specific animation themes

3. **Performance Improvements**
   - GPU acceleration for animations
   - Caching for repeated animations
   - Optimized rendering pipelines

---

**Version**: 1.0.0  
**Status**: Production Ready ✅  
**Compatibility**: ProtoReel Worker v2.0+ 