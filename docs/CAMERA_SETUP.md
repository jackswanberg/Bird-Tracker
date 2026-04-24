# Raspberry Pi Camera Setup Guide

## Prerequisites

### Hardware
- Raspberry Pi 5
- Raspberry Pi Camera Module (CSI/camera port)
- 5V Power supply (minimum 3A recommended)
- microSD card (minimum 32GB recommended)

### Software
- Raspberry Pi OS (Bullseye or later)
- Python 3.9+
- libcamera (built-in on modern Raspberry Pi OS)

## Installation Steps

### 1. Enable Camera Interface

On Raspberry Pi 5, the camera is managed by libcamera. Ensure it's enabled:

```bash
# On Raspberry Pi OS with desktop:
# Settings -> Raspberry Pi Configuration -> Interfaces -> Camera -> Enable

# Or via command line:
raspi-config
# Navigate to: Interfacing Options -> Camera -> Enable
```

### 2. Install picamera2

picamera2 is the Python interface for libcamera and is the recommended way to use cameras on Pi 5:

```bash
sudo apt update
sudo apt install -y python3-picamera2
```

### 3. Test Camera with libcamera Tools

Before using in Python, test the camera is working:

```bash
# List available cameras
libcamera-hello --list-cameras

# Preview camera (5-second preview)
libcamera-hello

# Capture a test image
libcamera-jpeg -o test.jpg
```

### 4. Install Bird-Tracker Dependencies

```bash
cd /home/jrswanbe/Documents/Bird-Tracker

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install opencv-python pyyaml

# If using PyTorch for detection models:
pip install torch torchvision
```

## Configuration

Edit `configs/config.yaml` to set camera parameters:

```yaml
low_res_camera:
  camera_index: 0          # 0 for main CSI port
  resolution: [640, 480]   # Adjust for your needs
  fps: 30                  # Frame rate
  auto_white_balance: true
  auto_exposure: true
```

### Camera Resolution Recommendations
- **Detection & Tracking**: 640x480 or 320x240 (lower for faster inference)
- **Higher resolution**: 1920x1080 or 1280x720 (if detection model supports)
- **Lower resolution**: 320x240 (for lightweight models on Pi 5)

## Testing

### 1. Test Camera Initialization

```bash
cd /home/jrswanbe/Documents/Bird-Tracker
python tests/test_lowres_camera.py --num-frames 10
```

Expected output:
```
INFO - Testing camera initialization...
INFO - Initialized camera 0
INFO - ✓ Camera initialized successfully
INFO - Testing frame capture (10 frames)...
INFO - ✓ All tests passed!
```

### 2. Test with Display

If you have display access (HDMI or SSH X11):

```bash
python tests/test_lowres_camera.py --num-frames 10 --display
```

### 3. Run Simple Example

```bash
python examples/camera_example.py
```

Press 'q' to exit. Should show:
- Live camera feed
- Frame count and FPS
- Frame shape and format

## Troubleshooting

### "ModuleNotFoundError: No module named 'picamera2'"

Solution: Install picamera2:
```bash
sudo apt install -y python3-picamera2
```

### "Failed to initialize camera"

- Check camera is physically connected to CSI port
- Enable camera in raspi-config
- Check no other process is using the camera

```bash
# Kill any existing processes
pkill -f libcamera
pkill -f picamera
```

### "No cameras detected" from libcamera

```bash
# Verify camera is detected
vcgencmd get_camera
# Should show: supported=1 detected=1

# Check device permissions
ls -la /dev/video*
```

### Frames are very dark or overexposed

Adjust auto_exposure and check lighting conditions:

```yaml
low_res_camera:
  auto_exposure: true
  auto_white_balance: true
```

Or disable auto-exposure and set manual exposure/gains (advanced).

## Performance Tips

1. **Resolution vs Speed**: Lower resolution = faster inference
   - Start with 640x480, reduce if inference is too slow

2. **Frame Rate**: Set to actual expected rate
   - Don't set fps=60 if you only need 30 fps

3. **Auto White Balance**: Can be slower, disable if not needed
   ```yaml
   auto_white_balance: false
   ```

## Next Steps

1. Train or load a bird detection model
2. Configure DSLR control in config.yaml
3. Run the full inference pipeline with `scripts/run_inference.py`

## References

- [libcamera Documentation](https://libcamera.org/)
- [picamera2 Documentation](https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf)
- [Raspberry Pi Camera Module Guide](https://www.raspberrypi.com/documentation/accessories/camera.html)
