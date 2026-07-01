"""
Camera interfaces for Bird Tracker System

This module provides camera abstractions for:
- Low-resolution camera (Raspberry Pi camera module) for detection and tracking
- Nikon Z6 II controller for high-quality image capture via gphoto2

Classes:
- LowResCamera: Captures frames from Raspberry Pi CSI camera via picamera2
- NikonZ6II: Controls Nikon Z6 II over USB via gphoto2
"""

import time
import numpy as np
import logging
from pathlib import Path
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
        self.rotate_180 = config.get('rotate_180', False)
        
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

            if self.rotate_180:
                bgr_frame = np.ascontiguousarray(bgr_frame[::-1, ::-1])

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

    

class NikonZ6II:
    """
    Controls a Nikon Z6 II over USB using the gphoto2 Python bindings.

    Handles connection, camera settings, autofocus, capture, and image download.
    Supports use as a context manager.

    Args:
        config (dict): Optional configuration with keys:
            - save_dir (str): Local directory for downloaded images (default 'data/captures')
            - capture_target (str): 'Memory card' or 'Internal RAM' (default 'Internal RAM')
            - af_timeout (float): Seconds to wait after triggering AF (default 0.5)
            - enabled (bool): If False, all operations are no-ops (default True)

    Example:
        >>> with NikonZ6II({'save_dir': 'data/captures'}) as cam:
        ...     cam.set_iso(800)
        ...     path = cam.focus_and_capture()
    """

    # gphoto2 short config names for Nikon Z6 II (as returned by camera.list_config())
    _CFG = {
        'iso':              'iso',
        'aperture':         'f-number',
        'shutter_speed':    'shutterspeed',
        'exposure_program': 'expprogram',
        'image_format':     'imagequality',
        'image_size':       'imagesize',
        'capture_target':   'capturetarget',
        'autofocus':        'autofocusdrive',
        'battery':          'batterylevel',
    }

    def __init__(self, config: dict = None):
        config = config or {}
        self.enabled = config.get('enabled', True)
        self.save_dir = Path(config.get('save_dir', 'data/captures'))
        self.capture_target = config.get('capture_target', 'Internal RAM')
        self.af_timeout = config.get('af_timeout', 0.5)
        self._camera = None
        self._gp = None

        if self.enabled:
            try:
                import gphoto2 as gp
                self._gp = gp
            except ImportError:
                raise ImportError(
                    "python-gphoto2 not found. Install with: pip install gphoto2"
                )

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Open USB connection to the first detected camera.

        Returns:
            True on success, False on failure.
        """
        if not self.enabled:
            return False
        gp = self._gp
        try:
            self._camera = gp.Camera()
            self._camera.init()
            abilities = self._camera.get_abilities()
            logger.info(f"Connected to {abilities.model}")
            self.save_dir.mkdir(parents=True, exist_ok=True)
            self._set_capture_target(self.capture_target)
            return True
        except gp.GPhoto2Error as e:
            logger.error(f"Failed to connect to camera: {e}")
            self._camera = None
            return False

    def disconnect(self):
        """Release the USB connection."""
        if self._camera is not None:
            try:
                self._camera.exit()
                logger.info("Camera disconnected")
            except Exception as e:
                logger.warning(f"Error during camera disconnect: {e}")
            finally:
                self._camera = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def autofocus(self) -> bool:
        """Trigger a single autofocus cycle.

        Returns:
            True if AF was triggered successfully.
        """
        if not self._connected():
            return False
        try:
            widget = self._camera.get_single_config(self._CFG['autofocus'])
            widget.set_value(1)
            self._camera.set_single_config(self._CFG['autofocus'], widget)
            time.sleep(self.af_timeout)
            logger.debug("Autofocus triggered")
            return True
        except Exception as e:
            logger.error(f"Autofocus failed: {e}")
            return False

    def capture(self, filename: Optional[str] = None) -> Optional[Path]:
        """Capture an image and download it locally.

        Args:
            filename: Destination filename (without extension). Defaults to
                      a timestamp-based name.

        Returns:
            Path to the downloaded file, or None on failure.
        """
        if not self._connected():
            return None
        gp = self._gp
        try:
            camera_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
            logger.debug(f"Captured to camera path: {camera_path.folder}/{camera_path.name}")

            ext = Path(camera_path.name).suffix
            local_name = filename if filename else f"bird_{int(time.time())}{ext}"
            local_path = self.save_dir / local_name

            camera_file = self._camera.file_get(
                camera_path.folder, camera_path.name, gp.GP_FILE_TYPE_NORMAL
            )
            camera_file.save(str(local_path))
            logger.info(f"Image saved to {local_path}")

            # Clean up from camera RAM if that was the capture target
            if self.capture_target == 'Internal RAM':
                try:
                    self._camera.file_delete(camera_path.folder, camera_path.name)
                except Exception:
                    pass

            return local_path
        except gp.GPhoto2Error as e:
            logger.error(f"Capture failed: {e}")
            return None

    def focus_and_capture(self, filename: Optional[str] = None) -> Optional[Path]:
        """Trigger autofocus then capture an image.

        Returns:
            Path to the downloaded file, or None on failure.
        """
        if not self.enabled:
            logger.debug("NikonZ6II disabled, skipping capture")
            return None
        self.autofocus()
        return self.capture(filename)

    # ------------------------------------------------------------------
    # Camera settings
    # ------------------------------------------------------------------

    def get_config_value(self, key: str) -> Optional[str]:
        """Read a camera config value by its short key or gphoto2 name.

        Args:
            key: Short key from NikonZ6II._CFG (e.g. 'iso') or a raw gphoto2 name.

        Returns:
            String value, or None on failure.
        """
        if not self._connected():
            return None
        name = self._CFG.get(key, key)
        try:
            widget = self._camera.get_single_config(name)
            return str(widget.get_value())
        except Exception as e:
            logger.error(f"Failed to read config '{key}': {e}")
            return None

    def set_config_value(self, key: str, value: str) -> bool:
        """Write a camera config value by its short key or gphoto2 name.

        Args:
            key: Short key from NikonZ6II._CFG or a raw gphoto2 name.
            value: New value as a string.

        Returns:
            True on success.
        """
        if not self._connected():
            return False
        name = self._CFG.get(key, key)
        try:
            widget = self._camera.get_single_config(name)
            widget.set_value(value)
            self._camera.set_single_config(name, widget)
            logger.debug(f"Set {key} = {value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set config '{key}' to '{value}': {e}")
            return False

    def set_iso(self, iso: int) -> bool:
        """Set ISO sensitivity (e.g. 100, 400, 800, 3200)."""
        return self.set_config_value('iso', str(iso))

    def set_aperture(self, aperture: str) -> bool:
        """Set aperture (e.g. '2.8', '5.6', '8')."""
        return self.set_config_value('aperture', str(aperture))

    def set_shutter_speed(self, shutter: str) -> bool:
        """Set shutter speed (e.g. '1/500', '1/1000', '1/4000')."""
        return self.set_config_value('shutter_speed', shutter)

    def set_image_format(self, fmt: str) -> bool:
        """Set image format (e.g. 'JPEG Fine', 'NEF (Raw)')."""
        return self.set_config_value('image_format', fmt)

    def get_battery_level(self) -> Optional[str]:
        """Return battery level as reported by the camera."""
        return self.get_config_value('battery')

    def set_roi(self, x: int, y: int, w: int, h: int) -> bool:
        """No-op — Nikon Z6 II does not expose ROI-based AF over gphoto2."""
        logger.debug(f"set_roi({x}, {y}, {w}, {h}) is not supported on Nikon Z6 II via gphoto2")
        return False

    def release(self):
        """Alias for disconnect(), for compatibility with LowResCamera interface."""
        self.disconnect()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connected(self) -> bool:
        if self._camera is None:
            logger.warning("Camera not connected — call connect() first")
            return False
        return True

    def _set_capture_target(self, target: str):
        """Set where captures are stored ('Memory card' or 'Internal RAM')."""
        try:
            widget = self._camera.get_single_config(self._CFG['capture_target'])
            widget.set_value(target)
            self._camera.set_single_config(self._CFG['capture_target'], widget)
            logger.debug(f"Capture target set to '{target}'")
        except Exception as e:
            logger.warning(f"Could not set capture target: {e}")


# Backward-compatible alias used by infer.py and __init__.py
DslrController = NikonZ6II