# Bird-Tracker

A real-time computer vision system for bird identification and tracking using a two-stage camera setup:
- **Low-resolution camera** (Raspberry Pi CSI module) for detection and tracking
- **DSLR/mirrorless camera** for high-quality capture when conditions are met

## Features

- Real-time bird detection and tracking from Raspberry Pi camera
- Quality assessment (focus, lighting, ROI size)
- Automated DSLR capture when quality thresholds are met
- Configurable thresholds and camera parameters
- Optimized for Raspberry Pi 5 with picamera2

## Quick Start

### Prerequisites
- Raspberry Pi 5 with camera module attached to CSI port
- Python 3.9+
- 5V/3A+ power supply

### Automated Setup (Recommended)

```bash
cd /home/jrswanbe/Documents/Bird-Tracker
./setup.sh
```

This installs all dependencies automatically.

### Manual Setup

1. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3-full python3-venv python3-numpy python3-opencv python3-yaml python3-picamera2
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install the package and dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -e .
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```
   Optional: install extra features for Pi camera and detection models:
   ```bash
   pip install -e .[pi_camera,detection]
   ```

For detailed setup instructions, see [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md)

## Architecture

### Core Modules
- **`src/bird_tracker/camera.py`**: Camera interfaces (LowResCamera for Pi, DslrController for external camera)
- **`src/bird_tracker/models/detector.py`**: Bird detection model wrapper
- **`src/bird_tracker/trackers.py`**: Multi-object tracking
- **`src/bird_tracker/quality.py`**: Image quality assessment
- **`src/bird_tracker/infer.py`**: Main inference pipeline

### Data Flow
```
Raspberry Pi Camera
        ↓
  LowResCamera.capture_frame()
        ↓
  BirdDetector.detect()
        ↓
  Tracker.update()
        ↓
  QualityAssessor.assess()
        ↓
  If quality OK → DslrController.focus_and_capture()
        ↓
  High-quality DSLR image
```

## Configuration

Edit `configs/config.yaml` to customize:

```yaml
# Camera settings
low_res_camera:
  camera_index: 0          # CSI camera index
  resolution: [640, 480]   # Resolution (width, height)
  fps: 30                  # Frame rate
  auto_white_balance: true
  auto_exposure: true

# Quality thresholds
quality:
  focus_threshold: 100.0        # Laplacian variance (sharpness)
  brightness_threshold: 0.3     # Min brightness (0-1)
  roi_fraction: 0.25            # Min bird size (25% of image)

# DSLR control (optional)
dslr:
  enabled: false                # Enable when DSLR connected
  device_path: null             # USB device path
  backend: gphoto2
```

## Usage

### Run Full Inference Pipeline
```bash
python scripts/run_inference.py
```

### Train or fine-tune a bird model
```bash
pip install -e .[detection]
python -m bird_tracker.train --config configs/train.yaml
```
> **Note**: NumPy is pinned to 1.24.x to maintain binary compatibility with Raspberry Pi system packages (`picamera2`, `simplejpeg`). Newer NumPy 2.x versions will cause dtype size incompatibilities.

### Test Individual Components
```bash
# Test camera
python tests/test_lowres_camera.py

# View live camera feed
python examples/camera_example.py
```

## Troubleshooting

**Camera not detected?**
- Check physical connection to CSI port
- Enable camera in `raspi-config`
- Verify with: `libcamera-hello`

**Slow inference?**
- Reduce resolution in config
- Use lightweight detection model
- Lower frame rate if not needed

See [docs/CAMERA_SETUP.md](docs/CAMERA_SETUP.md) for detailed troubleshooting.

## Next Steps

1. Train or download a bird detection model
2. Integrate detection model in `src/bird_tracker/models/detector.py`
3. Configure DSLR if available
4. Fine-tune quality thresholds based on environment
5. Deploy on Raspberry Pi 5
