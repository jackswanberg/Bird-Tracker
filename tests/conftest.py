"""Shared pytest fixtures and helpers for Bird Tracker tests."""

import sys
import yaml
import pytest

sys.path.insert(0, 'src')


@pytest.fixture
def config():
    """Load configs/config.yaml as a dict."""
    with open('configs/config.yaml') as f:
        return yaml.safe_load(f)


@pytest.fixture
def detector(config):
    """Yield a ready detector, releasing it after the test."""
    from bird_tracker.models.detector import create_detector
    det = create_detector(config)
    yield det
    det.release()
