# Scene Transitions Integration for ProtoReel Worker

## Overview

The ProtoReel Worker now supports smooth transitions between video scenes, providing professional-looking video flow that enhances the viewing experience. The transition system is designed to be flexible, allowing users to choose from different transition types and durations.

## 🎬 Transition Features

### Available Transition Types

- **`crossfade`**: Smooth crossfade between scenes (default)
- **`fade`**: Simple fade in/out effect
- **`none`**: No transition (abrupt scene changes)

### Transition Presets

Predefined transition configurations for common use cases:

- **`smooth`**: Gentle crossfade with 1.5s duration
- **`quick`**: Fast crossfade with 0.5s duration
- **`dramatic`**: Long crossfade with 2.0s duration
- **`none`**: No transitions

## 🚀 Usage

### 1. Global Transition Configuration

Apply the same transition to all scenes in the video:

```json
{
  "output_filename": "my_video.mp4",
  "global_transition_config": {
    "transition_type": "crossfade",
    "transition_duration": 1.5
  },
  "scenes": [
    {
      "type": "image",
      "prompt_image": "A beautiful sunset",
      "narration_text": "Welcome to our journey",
      "duration": 8,
      "subtitle": true,
      "animation_mode": ["zoom_in", "drift_up"]
    },
    {
      "type": "image",
      "prompt_image": "A bustling city",
      "narration_text": "The energy of urban life",
      "duration": 10,
      "subtitle": true,
      "animation_mode": ["zoom_out", "oscillate"]
    }
  ]
}
```

### 2. Per-Scene Transition Configuration

Apply different transitions to individual scenes:

```json
{
  "output_filename": "my_video.mp4",
  "scenes": [
    {
      "type": "image",
      "prompt_image": "A peaceful forest",
      "narration_text": "Finding tranquility",
      "duration": 8,
      "subtitle": true,
      "animation_mode": ["pulse"],
      "transition_type": "crossfade",
      "transition_duration": 1.0
    },
    {
      "type": "image",
      "prompt_image": "A dramatic mountain",
      "narration_text": "Reaching new heights",
      "duration": 10,
      "subtitle": true,
      "animation_mode": ["zoom_in", "oscillate"],
      "transition_type": "fade",
      "transition_duration": 2.0
    }
  ]
}
```

### 3. No Transitions

Create videos with abrupt scene changes:

```json
{
  "output_filename": "my_video.mp4",
  "global_transition_config": {
    "transition_type": "none",
    "transition_duration": 0.0
  },
  "scenes": [
    // ... scenes without transitions
  ]
}
```

## ⚙️ Configuration Parameters

### Global Transition Configuration

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `transition_type` | `string` | Type of transition to apply | `"crossfade"` |
| `transition_duration` | `float` | Duration of transition in seconds | `1.0` |

### Per-Scene Transition Configuration

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `transition_type` | `string` | Transition type for this scene | `None` |
| `transition_duration` | `float` | Transition duration in seconds | `1.0` |

## 🎯 Complete Example

```json
{
  "output_filename": "transition_demo.mp4",
  "global_transition_config": {
    "transition_type": "crossfade",
    "transition_duration": 1.5
  },
  "scenes": [
    {
      "type": "image",
      "prompt_image": "A serene mountain landscape at sunrise",
      "narration_text": "Welcome to our journey through nature's wonders",
      "duration": 8,
      "subtitle": true,
      "animation_mode": ["zoom_in", "drift_up"],
      "animation_darken_factor": 0.3
    },
    {
      "type": "image",
      "prompt_image": "A vibrant city street with people and lights",
      "narration_text": "Experience the energy of urban life",
      "duration": 10,
      "subtitle": true,
      "animation_mode": ["zoom_out", "oscillate"],
      "animation_darken_factor": 0.4
    },
    {
      "type": "image",
      "prompt_image": "A peaceful beach with gentle waves",
      "narration_text": "Find tranquility by the ocean",
      "duration": 8,
      "subtitle": true,
      "animation_mode": ["pulse"],
      "animation_darken_factor": 0.2
    }
  ]
}
```

## 🔧 Technical Implementation

### Transition System Architecture

1. **Transition Utilities** (`video_generator/transition_utils.py`)
   - Core transition functions
   - Transition validation and preset management
   - Smooth concatenation with transitions

2. **Scene Model Integration** (`video_generator/generator.py`)
   - Extended `SceneInput` model with transition fields
   - Global transition configuration handling
   - Integration with existing video generation pipeline

3. **Concatenation Pipeline**
   - Transition type determination
   - Parameter validation and fallbacks
   - Smooth scene concatenation with transitions

### Transition Effects

#### Crossfade Transition
```python
# Smooth crossfade between scenes
clip = clip.with_effects([CrossFadeIn(transition_duration)])
```

#### Fade Transition
```python
# Simple fade in/out effect
clip = clip.with_effects([CrossFadeIn(transition_duration)])
```

## 🧪 Testing

Run the transition system test:

```bash
python test_transitions.py
```

This will test:
- Transition utilities import and functionality
- Scene model with transition fields
- Example payloads with different transition configurations

## 🎨 Best Practices

### Transition Selection

1. **Content Type**
   - **Professional/Business**: Use `crossfade` with 1.0-1.5s duration
   - **Energetic/Dynamic**: Use `crossfade` with 0.5-1.0s duration
   - **Calm/Serene**: Use `crossfade` with 1.5-2.0s duration

2. **Duration Considerations**
   - **Short clips (5-8s)**: Use shorter transitions (0.5-1.0s)
   - **Medium clips (8-15s)**: Use moderate transitions (1.0-1.5s)
   - **Long clips (15s+)**: Use longer transitions (1.5-2.0s)

3. **Content Matching**
   - **Crossfade**: Good for most content types
   - **Fade**: Good for dramatic or emotional content
   - **None**: Good for news or documentary style content

### Performance Optimization

- Transitions are applied efficiently using MoviePy's built-in effects
- Memory usage is optimized during transition processing
- Fallback mechanisms ensure video generation continues even if transitions fail

## 🔄 Backward Compatibility

The transition system is fully backward compatible:

- Existing payloads without transition fields will use default crossfade transitions
- No changes required to existing video generation workflows
- Transition parameters are optional with sensible defaults

## 🚀 Future Enhancements

Planned features for future releases:

1. **Advanced Transition Types**
   - Slide transitions (left, right, up, down)
   - Zoom transitions (zoom in/out between scenes)
   - Wipe transitions (various wipe patterns)

2. **Transition Templates**
   - User-defined transition presets
   - Brand-specific transition themes
   - Transition style libraries

3. **Performance Improvements**
   - GPU acceleration for transitions
   - Caching for repeated transitions
   - Optimized rendering pipelines

---

**Version**: 1.0.0  
**Status**: Production Ready ✅  
**Compatibility**: ProtoReel Worker v2.0+ 