# Setup Guide for Bird-Tracker on Raspberry Pi 5

## Quick Setup (Recommended)

Run the automated setup script (handles all installation steps):

```bash
cd /home/jrswanbe/Documents/Bird-Tracker
./setup.sh
```

This script will:
1. Install system dependencies via apt
2. Create a Python virtual environment
3. Install Python packages
4. Verify the installation

## Manual Setup

If you prefer manual setup or the script doesn't work:

### 1. Install System Dependencies

```bash
sudo apt update
sudo apt install -y \
    python3-full \
    python3-pip \
    python3-venv \
    python3-numpy \
    python3-opencv \
    python3-yaml \
    python3-picamera2 \
    python3-pil \
    build-essential \
    python3-dev
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### 4. Install Development Tools

```bash
pip install pytest pytest-cov black flake8
```

### 5. Install PyTorch (CPU for Raspberry Pi)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

*Note: PyTorch installation may take 10-15 minutes on Raspberry Pi 5*

### 6. Verify Installation

```bash
python -c "from bird_tracker.camera import LowResCamera; print('✓ Installation successful')"
```

## Activating the Virtual Environment

After setup, you need to activate the virtual environment each time you use Bird-Tracker:

```bash
cd /home/jrswanbe/Documents/Bird-Tracker
source venv/bin/activate
```

Your prompt should change to show `(venv)` prefix.

## Why Virtual Environment?

- **Isolation**: Keeps project dependencies separate from system packages
- **PEP 668 Compliance**: Raspberry Pi OS requires this for user-installed packages
- **Clean**: Easy to remove or recreate if needed

## Troubleshooting

### "command not found: activate"

Make sure you're in the Bird-Tracker directory and use the full path:
```bash
source ./venv/bin/activate
```

### PyTorch installation too slow

You can skip PyTorch initially and only install it when ready to use the detection model:
```bash
# Install without PyTorch first
pip install pytest pytest-cov black flake8

# Then later:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### "No module named 'picamera2'"

Install the Raspberry Pi system package:
```bash
sudo apt install python3-picamera2
```

### Still getting PEP 668 error

If the script doesn't work, you can force installation (not recommended):
```bash
pip install --break-system-packages -r requirements.txt
```

## Next Steps

After setup:

1. **Test the camera**:
   ```bash
   python tests/test_lowres_camera.py --num-frames 10
   ```

2. **View live feed**:
   ```bash
   python examples/camera_example.py
   ```

3. **Run full system**:
   ```bash
   python scripts/run_inference.py
   ```

## System Requirements Met

✓ Python 3.9+
✓ Raspberry Pi 5
✓ 8GB+ RAM (for PyTorch)
✓ CSI camera module attached
✓ 32GB+ microSD card recommended
✓ 5V/3A+ power supply
