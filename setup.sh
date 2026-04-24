#!/bin/bash
# Setup script for Bird-Tracker on Raspberry Pi 5

set -e

echo "Bird-Tracker Setup for Raspberry Pi 5"
echo "======================================"

# 1. Install system dependencies
echo -e "\n[1/4] Installing system dependencies..."
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

# 2. Create virtual environment
echo -e "\n[2/4] Creating Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
    echo "✓ Virtual environment created (with system packages access)"
else
    echo "✓ Virtual environment already exists"
fi

# 3. Activate and upgrade pip
echo -e "\n[3/4] Upgrading pip and installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip setuptools wheel

# Install core dependencies
pip install \
    pytest>=7.0.0 \
    pytest-cov>=3.0.0 \
    black>=22.0.0 \
    flake8>=4.0.0

# Install PyTorch (CPU-only for Pi 5)
echo "Installing PyTorch (this may take several minutes)..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Verify installation
echo -e "\n[4/4] Verifying installation..."
python -c "import sys; sys.path.insert(0, 'src'); from bird_tracker.camera import LowResCamera; print('✓ Bird-Tracker packages imported successfully')"

echo -e "\n✓ Setup complete!"
echo ""
echo "To activate the virtual environment in future sessions:"
echo "  source venv/bin/activate"
echo ""
echo "To test the camera:"
echo "  python tests/test_lowres_camera.py"
echo ""
echo "To view live camera feed:"
echo "  python examples/camera_example.py"
