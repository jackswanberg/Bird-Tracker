"""
Pan-tilt gimbal control for bird targeting.

PanTiltController  — drives ST3215 serial bus servos via a servo controller
                     board connected over UART/USB. Uses the Feetech SCServo SDK.
Targeter           — converts a detection bbox to gimbal move commands using a
                     proportional controller and the Pi camera's FOV.

Hardware assumed:
  - Feetech ST3215 (STS series) servos for pan and tilt
  - Servo controller board with its own power supply, connected to the Pi via
    USB or UART (e.g. /dev/ttyUSB0)
  - SDK: pip install scservo_sdk

ST3215 position range: 0–4095 ticks = 0–360°  (≈ 0.088° per tick)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ST3215 register addresses (STS series)
_ADDR_GOAL_POSITION    = 42   # 2 bytes, write
_ADDR_PRESENT_POSITION = 56   # 2 bytes, read
_TICKS_PER_DEG         = 4096 / 360.0
_DEG_PER_TICK          = 360.0 / 4096


def _deg_to_ticks(deg: float) -> int:
    return int(round(deg * _TICKS_PER_DEG))


def _ticks_to_deg(ticks: int) -> float:
    return ticks * _DEG_PER_TICK


class PanTiltController:
    """
    Drives a two-axis ST3215 servo pan-tilt head via a serial controller board.

    Args:
        config (dict):
            port          (str):   Serial port, e.g. '/dev/ttyUSB0'
            baud_rate     (int):   Baud rate — ST3215 default is 1000000
            pan_servo_id  (int):   Servo bus ID for pan  (default 1)
            tilt_servo_id (int):   Servo bus ID for tilt (default 2)
            pan_min       (float): Min pan  angle degrees (default   0)
            pan_max       (float): Max pan  angle degrees (default 180)
            tilt_min      (float): Min tilt angle degrees (default  45)
            tilt_max      (float): Max tilt angle degrees (default 135)
            center_pan    (float): Neutral pan  angle     (default  90)
            center_tilt   (float): Neutral tilt angle     (default  90)
    """

    def __init__(self, config: dict):
        self.port          = config.get('port', '/dev/ttyUSB0')
        self.baud          = int(config.get('baud_rate', 1_000_000))
        self.pan_id        = int(config.get('pan_servo_id',  1))
        self.tilt_id       = int(config.get('tilt_servo_id', 2))
        self.pan_min       = float(config.get('pan_min',    0))
        self.pan_max       = float(config.get('pan_max',  180))
        self.tilt_min      = float(config.get('tilt_min',  45))
        self.tilt_max      = float(config.get('tilt_max', 135))
        self.center_pan    = float(config.get('center_pan',  90))
        self.center_tilt   = float(config.get('center_tilt', 90))

        self._pan  = self.center_pan
        self._tilt = self.center_tilt
        self._port_handler   = None
        self._packet_handler = None

        try:
            from scservo_sdk import PortHandler, PacketHandler
            port_handler   = PortHandler(self.port)
            packet_handler = PacketHandler(0)  # STS/SMS protocol version

            if port_handler.openPort():
                port_handler.setBaudRate(self.baud)
                self._port_handler   = port_handler
                self._packet_handler = packet_handler
                self._write_position(self.pan_id,  self.center_pan,  self.pan_min,  self.pan_max)
                self._write_position(self.tilt_id, self.center_tilt, self.tilt_min, self.tilt_max)
                logger.info(f"PanTiltController ready — pan id={self.pan_id} "
                            f"tilt id={self.tilt_id} on {self.port}")
            else:
                logger.warning(f"Could not open serial port {self.port} — gimbal disabled")
        except ImportError:
            logger.warning("scservo_sdk not installed — gimbal disabled. "
                           "Install with: pip install scservo_sdk")

    @property
    def connected(self) -> bool:
        return self._port_handler is not None

    def move_to(self, pan: float, tilt: float):
        """Move to absolute pan/tilt angles (degrees)."""
        self._pan  = max(self.pan_min,  min(self.pan_max,  pan))
        self._tilt = max(self.tilt_min, min(self.tilt_max, tilt))
        self._write_position(self.pan_id,  self._pan,  self.pan_min,  self.pan_max)
        self._write_position(self.tilt_id, self._tilt, self.tilt_min, self.tilt_max)

    def move_by(self, dpan: float, dtilt: float):
        """Move by a relative angle delta (degrees)."""
        self.move_to(self._pan + dpan, self._tilt + dtilt)

    def center(self):
        """Return the gimbal to its neutral home position."""
        self.move_to(self.center_pan, self.center_tilt)

    def read_position(self) -> Optional[tuple]:
        """
        Read current servo positions.

        Returns:
            (pan_deg, tilt_deg) or None if not connected.
        """
        if not self.connected:
            return None
        pan_ticks,  _, _ = self._packet_handler.read2ByteTxRx(
            self._port_handler, self.pan_id,  _ADDR_PRESENT_POSITION)
        tilt_ticks, _, _ = self._packet_handler.read2ByteTxRx(
            self._port_handler, self.tilt_id, _ADDR_PRESENT_POSITION)
        return _ticks_to_deg(pan_ticks), _ticks_to_deg(tilt_ticks)

    def release(self):
        """Close the serial port."""
        if self._port_handler:
            self._port_handler.closePort()
            self._port_handler   = None
            self._packet_handler = None

    def _write_position(self, servo_id: int, angle: float,
                        angle_min: float, angle_max: float):
        if not self.connected:
            return
        angle  = max(angle_min, min(angle_max, angle))
        ticks  = _deg_to_ticks(angle)
        result, error = self._packet_handler.write2ByteTxRx(
            self._port_handler, servo_id, _ADDR_GOAL_POSITION, ticks)
        if result != 0:  # COMM_SUCCESS == 0
            logger.warning(f"Servo {servo_id} write failed: result={result} error={error}")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.release()


class Targeter:
    """
    Converts a detection bounding box to gimbal move commands.

    Computes the pixel offset of the bbox centre from the frame centre,
    converts it to degrees using the Pi camera's field of view, and drives
    the gimbal with a proportional controller.

    Args:
        controller (PanTiltController): Gimbal to drive.
        config (dict):
            camera_hfov (float): Pi camera horizontal FOV in degrees (default 66)
            camera_vfov (float): Pi camera vertical FOV in degrees   (default 41)
            kp          (float): Proportional gain 0–1               (default 0.3)
            deadzone_px (int):   Pixel radius around centre to ignore (default 20)
    """

    def __init__(self, controller: PanTiltController, config: dict):
        self.controller  = controller
        self.hfov        = float(config.get('camera_hfov', 66.0))
        self.vfov        = float(config.get('camera_vfov', 41.0))
        self.kp          = float(config.get('kp', 0.3))
        self.deadzone_px = int(config.get('deadzone_px', 20))

    def update(self, bbox: tuple, frame_w: int, frame_h: int):
        """
        Drive the gimbal toward the centre of bbox.

        Args:
            bbox:    (x1, y1, x2, y2) pixel coordinates.
            frame_w: Frame width in pixels.
            frame_h: Frame height in pixels.
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        dx = cx - frame_w / 2   # positive = bird is right of centre
        dy = cy - frame_h / 2   # positive = bird is below centre

        if abs(dx) < self.deadzone_px and abs(dy) < self.deadzone_px:
            return

        deg_per_px_h = self.hfov / frame_w
        deg_per_px_v = self.vfov / frame_h

        dpan  = dx * deg_per_px_h * self.kp
        dtilt = dy * deg_per_px_v * self.kp

        self.controller.move_by(dpan, dtilt)

    def center(self):
        self.controller.center()
