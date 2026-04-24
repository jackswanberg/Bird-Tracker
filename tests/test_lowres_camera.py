#!/usr/bin/env python3
"""
Test script for LowResCamera on Raspberry Pi 5

Validates that:
1. Camera can be initialized
2. Frames can be captured
3. Frame format is correct (BGR, proper shape)
4. Camera can be released cleanly

Usage:
    python tests/test_lowres_camera.py [--num-frames 10] [--display]
"""

import sys
import argparse
import logging
import numpy as np

# Add src to path
sys.path.insert(0, '/home/jrswanbe/Documents/Bird-Tracker')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_camera_init():
    """Test camera initialization."""
    logger.info("Testing camera initialization...")
    from src.bird_tracker.camera import LowResCamera
    
    config = {
        'camera_index': 0,
        'resolution': (640, 480),
        'fps': 30
    }
    
    try:
        camera = LowResCamera(config)
        logger.info("✓ Camera initialized successfully")
        return camera
    except Exception as e:
        logger.error(f"✗ Camera initialization failed: {e}")
        raise


def test_frame_capture(camera, num_frames=5):
    """Test frame capture and format."""
    logger.info(f"Testing frame capture ({num_frames} frames)...")
    
    for i in range(num_frames):
        try:
            frame = camera.capture_frame()
            
            # Validate frame format
            assert isinstance(frame, np.ndarray), "Frame is not numpy array"
            assert frame.ndim == 3, f"Frame should be 3D, got {frame.ndim}D"
            assert frame.shape[2] == 3, f"Frame should have 3 channels, got {frame.shape[2]}"
            assert frame.dtype == np.uint8, f"Frame should be uint8, got {frame.dtype}"
            
            logger.info(f"  Frame {i+1}/{num_frames}: {frame.shape} {frame.dtype} ✓")
        
        except Exception as e:
            logger.error(f"✗ Frame capture failed on frame {i+1}: {e}")
            raise
    
    logger.info("✓ All frames captured successfully")


def test_camera_release(camera):
    """Test camera release."""
    logger.info("Testing camera release...")
    try:
        camera.release()
        logger.info("✓ Camera released successfully")
    except Exception as e:
        logger.error(f"✗ Camera release failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description='Test LowResCamera on Raspberry Pi')
    parser.add_argument('--num-frames', type=int, default=10,
                        help='Number of frames to capture (default 10)')
    parser.add_argument('--display', action='store_true',
                        help='Display captured frames (requires display available)')
    args = parser.parse_args()
    
    try:
        # Initialize
        camera = test_camera_init()
        
        # Capture
        test_frame_capture(camera, args.num_frames)
        
        # Display (optional)
        if args.display:
            logger.info("Displaying frames (press 'q' to quit)...")
            import cv2
            for i in range(5):  # Show a few frames
                frame = camera.capture_frame()
                cv2.imshow('LowResCamera Test', frame)
                key = cv2.waitKey(1)
                if key & 0xFF == ord('q'):
                    break
            cv2.destroyAllWindows()
        
        # Release
        test_camera_release(camera)
        
        logger.info("\n✓ All tests passed!")
        return 0
    
    except Exception as e:
        logger.error(f"\n✗ Tests failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
