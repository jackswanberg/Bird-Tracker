"""Tests for NikonZ6II gphoto2 camera controller."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

import sys
import types

# ---------------------------------------------------------------------------
# Provide a minimal gphoto2 stub so tests run without the library installed
# ---------------------------------------------------------------------------

_gp_stub = types.ModuleType("gphoto2")
_gp_stub.GP_CAPTURE_IMAGE = 0
_gp_stub.GP_FILE_TYPE_NORMAL = 1


class _GPhoto2Error(Exception):
    pass


_gp_stub.GPhoto2Error = _GPhoto2Error
sys.modules.setdefault("gphoto2", _gp_stub)

from bird_tracker.camera import NikonZ6II, DslrController  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_gp(monkeypatch):
    """Patch gphoto2 inside the camera module with a fully mocked version."""
    gp = MagicMock()
    gp.GPhoto2Error = _GPhoto2Error
    gp.GP_CAPTURE_IMAGE = 0
    gp.GP_FILE_TYPE_NORMAL = 1

    abilities = MagicMock()
    abilities.model = "Nikon Z6 II"

    camera_mock = MagicMock()
    camera_mock.get_abilities.return_value = abilities

    gp.Camera.return_value = camera_mock

    import bird_tracker.camera as cam_module
    monkeypatch.setattr(cam_module, "gphoto2", gp, raising=False)
    monkeypatch.setattr("bird_tracker.camera.NikonZ6II._gp", gp, raising=False)

    return gp, camera_mock


@pytest.fixture()
def connected_cam(tmp_path, mock_gp):
    """Return a NikonZ6II instance that is already connected."""
    gp, camera_mock = mock_gp
    cam = NikonZ6II({'save_dir': str(tmp_path), 'capture_target': 'Internal RAM'})
    cam._gp = gp
    cam._camera = camera_mock
    return cam, camera_mock, tmp_path


# ---------------------------------------------------------------------------
# Construction & connection
# ---------------------------------------------------------------------------

def test_disabled_camera_does_not_import_gphoto2():
    cam = NikonZ6II({'enabled': False})
    assert cam._gp is None
    assert not cam.connect()


def test_connect_logs_model(tmp_path, mock_gp):
    gp, camera_mock = mock_gp
    cam = NikonZ6II({'save_dir': str(tmp_path)})
    cam._gp = gp
    assert cam.connect()
    camera_mock.init.assert_called_once()


def test_connect_returns_false_on_gphoto2_error(tmp_path, mock_gp):
    gp, camera_mock = mock_gp
    camera_mock.init.side_effect = _GPhoto2Error("no camera")
    cam = NikonZ6II({'save_dir': str(tmp_path)})
    cam._gp = gp
    assert not cam.connect()
    assert cam._camera is None


def test_context_manager_connects_and_disconnects(tmp_path, mock_gp):
    gp, camera_mock = mock_gp
    cam = NikonZ6II({'save_dir': str(tmp_path)})
    cam._gp = gp
    with cam:
        assert cam._camera is not None
    camera_mock.exit.assert_called_once()
    assert cam._camera is None


def test_disconnect_clears_camera_reference(connected_cam):
    cam, camera_mock, _ = connected_cam
    cam.disconnect()
    camera_mock.exit.assert_called_once()
    assert cam._camera is None


# ---------------------------------------------------------------------------
# Autofocus
# ---------------------------------------------------------------------------

def test_autofocus_sets_widget_value(connected_cam, monkeypatch):
    cam, camera_mock, _ = connected_cam
    monkeypatch.setattr(time, "sleep", lambda _: None)

    af_widget = MagicMock()
    camera_mock.get_single_config.return_value = af_widget

    assert cam.autofocus()
    af_widget.set_value.assert_called_once_with(1)
    camera_mock.set_single_config.assert_called_once_with(NikonZ6II._CFG['autofocus'], af_widget)


def test_autofocus_returns_false_when_not_connected():
    cam = NikonZ6II({'enabled': True})
    cam._gp = MagicMock()
    cam._gp.GPhoto2Error = _GPhoto2Error
    assert not cam.autofocus()


def test_autofocus_returns_false_on_error(connected_cam, monkeypatch):
    cam, camera_mock, _ = connected_cam
    monkeypatch.setattr(time, "sleep", lambda _: None)
    camera_mock.get_single_config.side_effect = _GPhoto2Error("config error")
    assert not cam.autofocus()


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def test_capture_saves_file_and_returns_path(connected_cam, monkeypatch):
    cam, camera_mock, tmp_path = connected_cam
    monkeypatch.setattr(time, "time", lambda: 1234567890.0)

    camera_path = MagicMock()
    camera_path.folder = "/store_00010001/DCIM/100NCD7M"
    camera_path.name = "DSC_0001.JPG"
    camera_mock.capture.return_value = camera_path

    camera_file = MagicMock()
    camera_mock.file_get.return_value = camera_file

    result = cam.capture()

    camera_mock.capture.assert_called_once()
    camera_file.save.assert_called_once()
    assert result is not None
    assert result.suffix == ".JPG"


def test_capture_deletes_from_ram_after_download(connected_cam, monkeypatch):
    cam, camera_mock, tmp_path = connected_cam
    monkeypatch.setattr(time, "time", lambda: 1.0)

    camera_path = MagicMock()
    camera_path.folder = "/DCIM"
    camera_path.name = "DSC_0001.JPG"
    camera_mock.capture.return_value = camera_path
    camera_mock.file_get.return_value = MagicMock()

    cam.capture()
    camera_mock.file_delete.assert_called_once_with("/DCIM", "DSC_0001.JPG")


def test_capture_returns_none_on_gphoto2_error(connected_cam):
    cam, camera_mock, _ = connected_cam
    cam._gp.GPhoto2Error = _GPhoto2Error
    camera_mock.capture.side_effect = _GPhoto2Error("capture failed")
    assert cam.capture() is None


def test_capture_returns_none_when_not_connected():
    cam = NikonZ6II()
    cam._gp = MagicMock()
    cam._gp.GPhoto2Error = _GPhoto2Error
    assert cam.capture() is None


# ---------------------------------------------------------------------------
# focus_and_capture
# ---------------------------------------------------------------------------

def test_focus_and_capture_calls_autofocus_then_capture(connected_cam, monkeypatch):
    cam, camera_mock, tmp_path = connected_cam
    monkeypatch.setattr(time, "sleep", lambda _: None)
    monkeypatch.setattr(time, "time", lambda: 1.0)

    camera_path = MagicMock()
    camera_path.folder = "/DCIM"
    camera_path.name = "DSC_0001.JPG"
    camera_mock.capture.return_value = camera_path
    camera_mock.file_get.return_value = MagicMock()

    config_mock = MagicMock()
    camera_mock.get_config.return_value = config_mock

    result = cam.focus_and_capture()
    assert result is not None


def test_focus_and_capture_returns_none_when_disabled():
    cam = NikonZ6II({'enabled': False})
    assert cam.focus_and_capture() is None


# ---------------------------------------------------------------------------
# Config get/set
# ---------------------------------------------------------------------------

def test_get_config_value_returns_string(connected_cam):
    cam, camera_mock, _ = connected_cam
    widget = MagicMock()
    widget.get_value.return_value = "800"
    camera_mock.get_single_config.return_value = widget

    assert cam.get_config_value('iso') == "800"
    camera_mock.get_single_config.assert_called_once_with(NikonZ6II._CFG['iso'])


def test_set_config_value_calls_set_config(connected_cam):
    cam, camera_mock, _ = connected_cam
    widget = MagicMock()
    camera_mock.get_single_config.return_value = widget

    assert cam.set_config_value('iso', '1600')
    widget.set_value.assert_called_once_with('1600')
    camera_mock.set_single_config.assert_called_with(NikonZ6II._CFG['iso'], widget)


def test_set_iso(connected_cam):
    cam, camera_mock, _ = connected_cam
    camera_mock.get_single_config.return_value = MagicMock()
    cam.set_iso(3200)
    camera_mock.get_single_config.assert_called_with(NikonZ6II._CFG['iso'])


def test_set_aperture(connected_cam):
    cam, camera_mock, _ = connected_cam
    camera_mock.get_single_config.return_value = MagicMock()
    cam.set_aperture('5.6')
    camera_mock.get_single_config.assert_called_with(NikonZ6II._CFG['aperture'])


def test_set_shutter_speed(connected_cam):
    cam, camera_mock, _ = connected_cam
    camera_mock.get_single_config.return_value = MagicMock()
    cam.set_shutter_speed('1/1000')
    camera_mock.get_single_config.assert_called_with(NikonZ6II._CFG['shutter_speed'])


def test_get_battery_level(connected_cam):
    cam, camera_mock, _ = connected_cam
    widget = MagicMock()
    widget.get_value.return_value = "75%"
    camera_mock.get_single_config.return_value = widget

    assert cam.get_battery_level() == "75%"


# ---------------------------------------------------------------------------
# set_roi (unsupported on Z6 II, should be a no-op)
# ---------------------------------------------------------------------------

def test_set_roi_returns_false(connected_cam):
    cam, _, _ = connected_cam
    assert not cam.set_roi(0, 0, 100, 100)


# ---------------------------------------------------------------------------
# Backward-compat alias
# ---------------------------------------------------------------------------

def test_dslr_controller_is_alias_for_nikon_z6ii():
    assert DslrController is NikonZ6II
