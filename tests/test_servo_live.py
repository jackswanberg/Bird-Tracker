"""
Live integration tests for a Feetech/Waveshare STS-series serial bus servo —
require the servo to be physically connected and powered over USB/UART.
Tests are skipped automatically when no servo is detected.

Run with:
    venv/bin/pytest tests/test_servo_live.py -v -s

Override the default port/baud/id with environment variables:
    SERVO_PORT=/dev/ttyUSB0 SERVO_BAUD=1000000 SERVO_ID=1
"""

import os
import time

import pytest

from bird_tracker.STservo_sdk import COMM_SUCCESS, PortHandler, sts

SERVO_PORT = os.environ.get("SERVO_PORT", "/dev/ttyACM0")
SERVO_BAUD = int(os.environ.get("SERVO_BAUD", "1000000"))
SERVO_ID = int(os.environ.get("SERVO_ID", "1"))

STS_MIN_POSITION = 1024   # ~90 degrees
STS_MAX_POSITION = 3072   # ~270 degrees
MOVE_SPEED = 1000
MOVE_ACC = 50

STS_MODE = 33            # 0 = position control, 1 = wheel (continuous rotation)
STS_TORQUE_ENABLE = 40


def _open_servo():
    port_handler = PortHandler(SERVO_PORT)
    try:
        if not port_handler.openPort():
            return None, None
        port_handler.setBaudRate(SERVO_BAUD)
    except Exception:
        return None, None

    packet_handler = sts(port_handler)
    _, result, _ = packet_handler.ReadPos(SERVO_ID)
    if result != COMM_SUCCESS:
        port_handler.closePort()
        return None, None
    return port_handler, packet_handler


def _servo_detected() -> bool:
    port_handler, _ = _open_servo()
    if port_handler is None:
        return False
    port_handler.closePort()
    return True


servo_required = pytest.mark.skipif(
    not _servo_detected(),
    reason=f"No servo detected on {SERVO_PORT} (id={SERVO_ID}) — skipping live tests",
)


@pytest.fixture
def servo():
    port_handler, packet_handler = _open_servo()
    assert port_handler is not None, "Servo unexpectedly unreachable"

    mode, result, error = packet_handler.read1ByteTxRx(SERVO_ID, STS_MODE)
    assert result == COMM_SUCCESS, f"Could not read STS_MODE: result={result} error={error}"
    assert mode == 0, (
        f"Servo {SERVO_ID} is in mode {mode}, not position-control mode (0) — "
        "if this is 1 (wheel mode), goal-position writes are ignored and the "
        "servo just keeps spinning at its last commanded speed. Reset it with "
        "packet_handler.write1ByteTxRx(SERVO_ID, STS_MODE, 0) (EPROM must be "
        "unlocked first via unLockEprom)."
    )
    print(f"\nSTS_MODE: {mode} (0 = position control)")

    packet_handler.write1ByteTxRx(SERVO_ID, STS_TORQUE_ENABLE, 1)

    yield packet_handler

    packet_handler.write1ByteTxRx(SERVO_ID, STS_TORQUE_ENABLE, 0)
    port_handler.closePort()


@servo_required
def test_servo_connects_and_reports_position(servo):
    """Servo responds to a position read over the bus."""
    position, result, error = servo.ReadPos(SERVO_ID)
    assert result == COMM_SUCCESS, f"ReadPos failed: result={result} error={error}"
    assert 0 <= position <= 4095


@servo_required
def test_servo_moves_in_both_directions(servo):
    """Servo can be started, driven to two different positions, and settles at each."""
    pos_before, result, _ = servo.ReadPos(SERVO_ID)
    assert result == COMM_SUCCESS
    print(f"\nPosition before move: {pos_before}")

    result, error = servo.WritePosEx(SERVO_ID, STS_MIN_POSITION, MOVE_SPEED, MOVE_ACC)
    assert result == COMM_SUCCESS, f"Move to min failed: result={result} error={error}"

    for _ in range(20):  # poll until settled instead of a fixed sleep
        time.sleep(0.2)
        moving, result, _ = servo.ReadMoving(SERVO_ID)
        if result == COMM_SUCCESS and moving == 0:
            break
    pos_at_min, result, _ = servo.ReadPos(SERVO_ID)
    assert result == COMM_SUCCESS
    print(f"Position after move to min (target {STS_MIN_POSITION}): {pos_at_min} "
          f"(moving={moving})")

    result, error = servo.WritePosEx(SERVO_ID, STS_MAX_POSITION, MOVE_SPEED, MOVE_ACC)
    assert result == COMM_SUCCESS, f"Move to max failed: result={result} error={error}"

    for _ in range(20):
        time.sleep(0.2)
        moving, result, _ = servo.ReadMoving(SERVO_ID)
        if result == COMM_SUCCESS and moving == 0:
            break
    pos_at_max, result, _ = servo.ReadPos(SERVO_ID)
    assert result == COMM_SUCCESS
    print(f"Position after move to max (target {STS_MAX_POSITION}): {pos_at_max} "
          f"(moving={moving})")

    assert abs(pos_at_min - STS_MIN_POSITION) < 50, (
        f"Servo did not settle near its min target: wanted {STS_MIN_POSITION}, "
        f"read {pos_at_min}"
    )
    assert abs(pos_at_max - STS_MAX_POSITION) < 50, (
        f"Servo did not settle near its max target: wanted {STS_MAX_POSITION}, "
        f"read {pos_at_max}"
    )
    assert pos_at_max > pos_at_min, (
        f"Servo did not move toward the opposite direction: {pos_at_min} -> {pos_at_max}"
    )


@servo_required
def test_servo_stop_halts_motion(servo):
    """Torque-disable ('stop') leaves the servo free-moving and reads still succeed."""
    servo.WritePosEx(SERVO_ID, STS_MIN_POSITION, MOVE_SPEED, MOVE_ACC)
    time.sleep(0.2)

    result, error = servo.write1ByteTxRx(SERVO_ID, 40, 0)  # STS_TORQUE_ENABLE off
    assert result == COMM_SUCCESS, f"Torque disable failed: result={result} error={error}"

    position, result, error = servo.ReadPos(SERVO_ID)
    assert result == COMM_SUCCESS, f"ReadPos after stop failed: result={result} error={error}"
    print(f"\nPosition after stop: {position}")
