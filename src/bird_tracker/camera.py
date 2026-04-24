"""
Camera interfaces for Bird Tracker System

This module provides camera abstractions for:
- Low-resolution camera (Raspberry Pi camera module) for detection and tracking
- DSLR controller for high-quality image capture

Classes:
- LowResCamera: Captures frames from Raspberry Pi CSI camera via picamera2
- DslrController: Controls external DSLR camera for capture commands
"""

import numpy as np
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class LowResCamera:
    """
    Captures frames from Raspberry Pi camera module attached to CSI port.
    
    Uses picamera2 (libcamera Python bindings) for Raspberry Pi 5 compatibility.
    
    Args:
        config (dict): Configuration dictionary with keys:
            - camera_index (int): Camera index (default 0 for main CSI port)
            - resolution (tuple): (width, height) for capture (default (640, 480))
            - fps (int): Target frame rate (default 30)
            - auto_white_balance (bool): Enable AWB (default True)
            - auto_exposure (bool): Enable auto exposure (default True)
    
    Attributes:
        picam2: picamera2.Picamera2 instance
        width: Frame width in pixels
        height: Frame height in pixels
        fps: Target frame rate
    
    Example:
        >>> config = {'resolution': (640, 480), 'fps': 30}
        >>> camera = LowResCamera(config)
        >>> frame = camera.capture_frame()  # numpy array, BGR format
        >>> camera.release()
    """
    
    def __init__(self, config: dict):
        """Initialize Raspberry Pi camera with given configuration."""
        try:
            from picamera2 import Picamera2
        except ImportError:
            raise ImportError(
                "picamera2 not found. Install with: "
                "sudo apt update && sudo apt install -y python3-picamera2"
            )
        
        self.camera_index = config.get('camera_index', 0)
        self.width, self.height = config.get('resolution', (640, 480))
        self.fps = config.get('fps', 30)
        self.auto_white_balance = config.get('auto_white_balance', True)
        self.auto_exposure = config.get('auto_exposure', True)
        
        try:
            self.picam2 = Picamera2(self.camera_index)
            logger.info(f"Initialized camera {self.camera_index}")
        except Exception as e:
            logger.error(f"Failed to initialize camera {self.camera_index}: {e}")
            raise
        
        # Configure capture resolution and frame rate
        try:
            config_dict = self.picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (self.width, self.height)},
                controls={"FrameRate": self.fps}
            )
            self.picam2.configure(config_dict)
            self.picam2.start()
            logger.info(f"Camera started: {self.width}x{self.height} @ {self.fps} fps")
        except Exception as e:
            logger.error(f"Failed to configure/start camera: {e}")
            self.picam2.close()
            raise
    
    def capture_frame(self) -> np.ndarray:
        """
        Capture and return a single frame from the camera.
        
        Returns:
            np.ndarray: Frame in BGR format (compatible with OpenCV), 
                       shape (height, width, 3), dtype uint8
        
        Raises:
            RuntimeError: If frame capture fails
        """
        try:
            request = self.picam2.capture_request()
            array = request.make_array("main")
            request.release()
            
            # Convert RGB to BGR for OpenCV compatibility
            rgb_frame = np.asarray(array)
            bgr_frame = rgb_frame[..., ::-1].copy()  # Reverse channels and ensure contiguous
            
            return bgr_frame
        
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            raise RuntimeError(f"Frame capture failed: {e}")
    
    def release(self):
        """Stop camera and clean up resources."""
        try:
            self.picam2.stop()
            self.picam2.close()
            logger.info("Camera released")
        except Exception as e:
            logger.warning(f"Error during camera release: {e}")

    

class DslrController:
    """
    Interface for DSLR control.
    
    Supports controlling an external DSLR camera via USB/tethering for 
    high-quality image capture when quality conditions are met.
    
    Args:
        config (dict): Configuration dictionary with keys:
            - device_path (str): Path to camera device or IP for tethering
            - backend (str): Control backend ('gphoto2', 'libgphoto2', etc.)
            - focus_mode (str): Focus mode ('auto', 'continuous', 'manual')
            - capture_format (str): Output format ('jpg', 'raw', etc.)
            - enabled (bool): Whether DSLR control is enabled (default False)
    
    Methods:
        focus_and_capture(): Trigger autofocus and capture image
        set_roi(x, y, w, h): Set region of interest (if supported)
        release(): Clean up and close connection
    """
    
    def __init__(self, config: dict):
        """Initialize DSLR controller with given configuration."""
        self.device_path = config.get('device_path', None)
        self.backend = config.get('backend', 'gphoto2')
        self.focus_mode = config.get('focus_mode', 'auto')
        self.capture_format = config.get('capture_format', 'jpg')
        self.enabled = config.get('enabled', False)
        
        if self.enabled and not self.device_path:
            logger.warning("DSLR controller enabled but no device path specified")
        
        if self.enabled:
            logger.info(f"DSLR controller initialized (backend: {self.backend})")
    
    def focus_and_capture(self) -> bool:
        """
        Trigger autofocus and capture image on connected DSLR.
        
        Returns:
            bool: True if capture was successful, False otherwise
        """
        if not self.enabled:
            logger.debug("DSLR capture disabled")
            return False
        
        try:
            # Placeholder for DSLR control logic
            # Implementation would use gphoto2 or similar
            logger.info("DSLR capture triggered")
            return True
        except Exception as e:
            logger.error(f"DSLR capture failed: {e}")
            return False
    
    def set_roi(self, x: int, y: int, w: int, h: int) -> bool:
        """
        Set region of interest for DSLR autofocus.
        
        Args:
            x, y: Top-left corner of ROI in pixels
            w, h: Width and height of ROI
        
        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False
        
        try:
            logger.debug(f"Set DSLR ROI: ({x}, {y}, {w}, {h})")
            return True
        except Exception as e:
            logger.error(f"Failed to set DSLR ROI: {e}")
            return False
    
    def release(self):
        """Clean up DSLR connection."""
        logger.info("DSLR controller released")