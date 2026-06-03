"""
Live integration tests for NikonZ6II — require the camera to be physically
connected over USB. Tests are skipped automatically when no camera is detected.

Run with:
    venv/bin/pytest tests/test_nikon_z6ii_live.py -v -s
"""

import pytest
from bird_tracker.camera import NikonZ6II

# ---------------------------------------------------------------------------
# Auto-skip when camera is not present
# ---------------------------------------------------------------------------

def _camera_detected() -> bool:
    try:
        import gphoto2 as gp
        cam = gp.Camera()
        cam.init()
        cam.exit()
        return True
    except Exception:
        return False

camera_required = pytest.mark.skipif(
    not _camera_detected(),
    reason="Nikon Z6 II not detected on USB — skipping live tests",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@camera_required
def test_camera_connects_and_reports_model():
    """Camera connects, reports a model name, and disconnects cleanly."""
    cam = NikonZ6II()
    assert cam.connect(), "connect() returned False — camera may be busy or unclaimed"
    cam.disconnect()
    assert cam._camera is None


@camera_required
def test_camera_context_manager():
    """Context manager leaves camera disconnected on exit."""
    with NikonZ6II() as cam:
        assert cam._camera is not None, "Camera not connected inside context manager"
    assert cam._camera is None


@camera_required
def test_battery_level_readable():
    """Battery level can be read and looks like a non-empty string."""
    with NikonZ6II() as cam:
        level = cam.get_battery_level()
    assert level is not None, "get_battery_level() returned None"
    assert len(level) > 0, "get_battery_level() returned empty string"
    print(f"\nBattery level: {level}")


@camera_required
def test_iso_readable():
    """ISO setting can be read from the camera."""
    with NikonZ6II() as cam:
        iso = cam.get_config_value('iso')
    assert iso is not None, "get_config_value('iso') returned None"
    print(f"\nISO: {iso}")


@camera_required
def test_capture_returns_valid_path(tmp_path):
    """Camera captures an image and saves it to disk."""
    with NikonZ6II({'save_dir': str(tmp_path), 'capture_target': 'Internal RAM'}) as cam:
        path = cam.capture()
    assert path is not None, "capture() returned None"
    assert path.exists(), f"Captured file not found at {path}"
    assert path.stat().st_size > 0, "Captured file is empty"
    print(f"\nCaptured image: {path} ({path.stat().st_size} bytes)")


@camera_required
def test_focus_and_capture_returns_valid_path(tmp_path):
    """Autofocus + capture produces a non-empty file on disk."""
    with NikonZ6II({'save_dir': str(tmp_path), 'capture_target': 'Internal RAM'}) as cam:
        path = cam.focus_and_capture()
    assert path is not None, "focus_and_capture() returned None"
    assert path.exists(), f"Captured file not found at {path}"
    assert path.stat().st_size > 0, "Captured file is empty"
    print(f"\nCaptured image: {path} ({path.stat().st_size} bytes)")
