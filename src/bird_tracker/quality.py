"""
Quality Assessment Module

Evaluates image quality for focus, lighting, and ROI size.

Class: QualityAssessor
- __init__(config): Set thresholds for focus, brightness, roi_fraction
- assess(frame, bbox): Return dict with quality metrics and pass/fail
"""

import numpy as np
import cv2

class QualityAssessor:
    def __init__(self, config: dict):
        self.focus_threshold = config.get('focus_threshold', 100.0)
        self.brightness_threshold = config.get('brightness_threshold', 0.3)
        self.roi_fraction = config.get('roi_fraction', 0.25)

    def assess(self, frame: np.ndarray, bbox: tuple) -> dict:
        # Compute focus (Laplacian variance)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        focus = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Compute brightness (mean intensity)
        brightness = np.mean(gray) / 255.0

        # Compute ROI size
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        roi_area = (x2 - x1) * (y2 - y1)
        total_area = h * w
        roi_frac = roi_area / total_area

        return {
            'focus': focus,
            'brightness': brightness,
            'roi_fraction': roi_frac,
            'focus_ok': focus > self.focus_threshold,
            'brightness_ok': brightness > self.brightness_threshold,
            'roi_ok': roi_frac > self.roi_fraction,
            'overall_ok': all([focus > self.focus_threshold, brightness > self.brightness_threshold, roi_frac > self.roi_fraction])
        }