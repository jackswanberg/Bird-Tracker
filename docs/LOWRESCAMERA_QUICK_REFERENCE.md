# LowResCamera Quick Reference

## Initialization

```python
from src.bird_tracker.camera import LowResCamera
import yaml

# From config file
with open('configs/config.yaml') as f:
    config = yaml.safe_load(f)
camera = LowResCamera(config['low_res_camera'])

# Or with direct config dict
config = {
    'camera_index': 0,
    'resolution': (640, 480),
    'fps': 30,
    'auto_white_balance': True,
    'auto_exposure': True
}
camera = LowResCamera(config)
```

## Capturing Frames

```python
# Single frame
frame = camera.capture_frame()  # Returns numpy array (H, W, 3), BGR, uint8

# In a loop
while True:
    frame = camera.capture_frame()
    # Process frame...
    if should_exit:
        break

# With display (OpenCV)
import cv2
frame = camera.capture_frame()
cv2.imshow('Camera', frame)
cv2.waitKey(1)
```

## Frame Properties

- **Shape**: (height, width, 3) = (480, 640, 3) by default
- **Format**: BGR (OpenCV compatible)
- **Data type**: uint8 (0-255 range)
- **Pixel order**: B, G, R channels

## Cleanup

```python
# Always release when done
camera.release()

# With error handling
try:
    camera = LowResCamera(config)
    frame = camera.capture_frame()
finally:
    camera.release()
```

## Common Configurations

### Lightweight (Fastest)
```yaml
low_res_camera:
  resolution: [320, 240]
  fps: 15
  auto_white_balance: false
  auto_exposure: false
```

### Balanced
```yaml
low_res_camera:
  resolution: [640, 480]
  fps: 30
  auto_white_balance: true
  auto_exposure: true
```

### High Quality
```yaml
low_res_camera:
  resolution: [1280, 720]
  fps: 30
  auto_white_balance: true
  auto_exposure: true
```

## Troubleshooting

### Camera not found
```bash
# Check if camera is detected
libcamera-hello

# Enable in raspi-config
raspi-config
# Navigate to: Interfacing Options -> Camera -> Enable
```

### ImportError: No module named 'picamera2'
```bash
sudo apt install -y python3-picamera2
```

### Frame capture fails
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Try again to see detailed error
try:
    frame = camera.capture_frame()
except Exception as e:
    print(f"Error: {e}")
```

## Integration with Bird Tracker Pipeline

```python
from src.bird_tracker.camera import LowResCamera
from src.bird_tracker.models.detector import BirdDetector
from src.bird_tracker.trackers import Tracker
import yaml

# Load config
with open('configs/config.yaml') as f:
    config = yaml.safe_load(f)

# Initialize components
camera = LowResCamera(config['low_res_camera'])
detector = BirdDetector(config['model_path'], config)
tracker = Tracker(config['tracker'])

# Main loop
while True:
    frame = camera.capture_frame()
    detections = detector.detect(frame)
    tracks = tracker.update(detections)
    # Process tracks...

camera.release()
```

## Performance Notes

| Resolution | FPS | Data Rate | Latency |
|------------|-----|-----------|---------|
| 320x240    | 30  | 0.9 MB/s  | 33ms    |
| 640x480    | 30  | 3.6 MB/s  | 33ms    |
| 1280x720   | 30  | 8.1 MB/s  | 33ms    |

## Testing

```bash
# Run test suite
python tests/test_lowres_camera.py --num-frames 10

# Show captured frames
python tests/test_lowres_camera.py --num-frames 10 --display

# Run example
python examples/camera_example.py
```

## API Reference

### LowResCamera

**`__init__(config: dict)`**
- Initialize camera with configuration

**`capture_frame() -> np.ndarray`**
- Returns next frame as BGR numpy array
- Raises RuntimeError on capture failure

**`release()`**
- Stop camera and clean up resources
- Safe to call multiple times

### DslrController

**`__init__(config: dict)`**
- Initialize DSLR controller

**`focus_and_capture() -> bool`**
- Trigger autofocus and capture
- Returns True if successful

**`set_roi(x: int, y: int, w: int, h: int) -> bool`**
- Set region of interest for autofocus
- Returns True if successful

**`release()`**
- Clean up DSLR connection
