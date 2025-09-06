# ProtoReel Worker

## 🎬 New Features: Animations & Transitions

The ProtoReel Worker now supports configurable animations and smooth scene transitions! Create professional videos with:

### Animations
- **6 Animation Modes**: zoom_in, zoom_out, pulse, drift_up, drift_down, oscillate
- **7 Animation Presets**: subtle, dynamic, smooth, gentle_drift, energetic, zoom_only, motion_only
- **Random Animations**: Automatic random animation selection when no mode is specified
- **Custom Parameters**: Fine-tune darkening, drift distance, and oscillation amplitude

### Scene Transitions
- **3 Transition Types**: crossfade, fade, none
- **4 Transition Presets**: smooth, quick, dramatic, none
- **Global & Per-Scene**: Apply transitions globally or customize per scene
- **Smooth Flow**: Professional video flow between scenes

### Text Overlays
- **5 Text Types**: title, subtitle, caption, callout, watermark
- **7 Positions**: top, center, bottom, and corner positions
- **4 Animations**: fade_in, fade_out, fade_in_out, none
- **Rich Styling**: Custom fonts, colors, strokes, and presets

### Quick Examples

#### Animations
```json
{
  "type": "image",
  "prompt_image": "A beautiful sunset",
  "animation_preset": "energetic"  // Use predefined animation
}
```

```json
{
  "type": "image", 
  "prompt_image": "A professional setup",
  "animation_mode": ["zoom_in", "oscillate"],  // Custom combination
  "animation_darken_factor": 0.3
}
```

#### Transitions
```json
{
  "output_filename": "my_video.mp4",
  "global_transition_config": {
    "transition_type": "crossfade",
    "transition_duration": 1.5
  },
  "scenes": [
    // Your scenes here
  ]
}
```

#### Text Overlays
```json
{
  "type": "image",
  "prompt_image": "A beautiful scene",
  "duration": 8,
  "text": {
    "content": "Welcome to Our Journey",
    "preset": "title",
    "animation_type": "fade_in"
  }
}
```

See [ANIMATION_INTEGRATION.md](ANIMATION_INTEGRATION.md), [TRANSITION_INTEGRATION.md](TRANSITION_INTEGRATION.md), and [TEXT_OVERLAY_INTEGRATION.md](TEXT_OVERLAY_INTEGRATION.md) for complete documentation.

## Environment Variables Configuration

### Memory Monitoring Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MEMORY_MONITORING` | `true` | Enable/disable memory monitoring |
| `MEMORY_MONITOR_INTERVAL` | `20` | Check memory every N seconds |
| `MEMORY_WARNING_THRESHOLD_MB` | `2500` | Warning at 2.5GB memory usage |
| `MEMORY_CRITICAL_THRESHOLD_MB` | `3500` | Critical at 3.5GB memory usage |
| `MEMORY_EMERGENCY_THRESHOLD_MB` | `5000` | Emergency at 5GB memory usage |
| `MEMORY_CLEANUP_COOLDOWN` | `30` | Cooldown between cleanups (seconds) |

### Cache Clearing Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_CACHE_CLEARING` | `true` | Enable/disable cache clearing |
| `CACHE_CLEARING_ASYNC` | `true` | Run cache clearing in background |
| `CACHE_CLEARING_INTERVAL` | `5` | Clear cache every N tasks |
| `CACHE_MAX_SIZE_MB` | `500` | Maximum cache size in MB |
| `CACHE_TTL_HOURS` | `1` | Cache time-to-live in hours |

### Memory Optimization Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_MEMORY_OPTIMIZATION` | `true` | Enable/disable memory optimization |
| `MEMORY_CLEANUP_INTERVAL` | `1` | Optimize memory every N scenes |
| `MAX_MEMORY_USAGE_MB` | `3500` | Maximum memory usage limit |
| `FORCE_GC_AFTER_SCENE` | `true` | Force garbage collection after scenes |

## Example Configurations

### High Performance (Minimal Monitoring)
```bash
ENABLE_MEMORY_MONITORING=false
ENABLE_CACHE_CLEARING=false
ENABLE_MEMORY_OPTIMIZATION=false
```

### Balanced (Default)
```bash
ENABLE_MEMORY_MONITORING=true
MEMORY_MONITOR_INTERVAL=20
MEMORY_WARNING_THRESHOLD_MB=2500
MEMORY_CRITICAL_THRESHOLD_MB=3500
ENABLE_CACHE_CLEARING=true
CACHE_CLEARING_ASYNC=true
```

### Aggressive Memory Management
```bash
ENABLE_MEMORY_MONITORING=true
MEMORY_MONITOR_INTERVAL=10
MEMORY_WARNING_THRESHOLD_MB=2000
MEMORY_CRITICAL_THRESHOLD_MB=3000
MEMORY_EMERGENCY_THRESHOLD_MB=4000
ENABLE_CACHE_CLEARING=true
CACHE_CLEARING_ASYNC=false
ENABLE_MEMORY_OPTIMIZATION=true
MEMORY_CLEANUP_INTERVAL=1
```

### Conservative (High Memory Containers)
```bash
ENABLE_MEMORY_MONITORING=true
MEMORY_MONITOR_INTERVAL=30
MEMORY_WARNING_THRESHOLD_MB=6000
MEMORY_CRITICAL_THRESHOLD_MB=7000
MEMORY_EMERGENCY_THRESHOLD_MB=8000
ENABLE_CACHE_CLEARING=true
CACHE_CLEARING_ASYNC=true
```

## Usage Examples

### Disable Memory Monitoring
```bash
export ENABLE_MEMORY_MONITORING=false
```

### Adjust Memory Thresholds
```bash
export MEMORY_WARNING_THRESHOLD_MB=3000
export MEMORY_CRITICAL_THRESHOLD_MB=5000
export MEMORY_EMERGENCY_THRESHOLD_MB=7000
```

### Disable Cache Clearing
```bash
export ENABLE_CACHE_CLEARING=false
```

### Synchronous Cache Clearing
```bash
export CACHE_CLEARING_ASYNC=false
```

### More Frequent Memory Checks
```bash
export MEMORY_MONITOR_INTERVAL=10
```

### Less Frequent Memory Checks
```bash
export MEMORY_MONITOR_INTERVAL=60
``` 
