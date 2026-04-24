"""
Tracking Module for Bird Tracking

Implements multi-object tracking to maintain bird identities across frames.
Uses a simple tracker like SORT or Kalman filter-based tracking.

Class: Tracker
- __init__(config): Initialize with max_age, min_hits, etc.
- update(detections): Update tracks with new detections, return active tracks
- Track: NamedTuple with track_id, bbox, velocity, age
"""

from typing import List, NamedTuple
from .models.detector import Detection

class Track(NamedTuple):
    track_id: int
    bbox: tuple
    velocity: tuple  # (vx, vy)
    age: int

class Tracker:
    def __init__(self, config: dict):
        self.max_age = config.get('max_age', 30)
        self.min_hits = config.get('min_hits', 3)
        self.tracks = []  # List of Track objects

    def update(self, detections: List[Detection]) -> List[Track]:
        # Update tracks with detections
        # Implement association (e.g., Hungarian algorithm or IoU)
        # Return active tracks
        return self.tracks  # Placeholder