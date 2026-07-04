"""
Live detection test — runs a continuous video loop, draws bounding boxes, and
prints pixel locations of every detection to the console.

Run with:
    venv/bin/pytest tests/test_bird_detection_live.py::test_detector_initialises -v
    venv/bin/pytest tests/test_bird_detection_live.py::test_live_video -v -s

Press 'q' in the OpenCV window to stop the live video test.
"""

import cv2
import pytest

from bird_tracker.models.detector import draw_detections, print_detections


def test_detector_initialises(detector):
    """Detector loads without error — fast, no camera needed."""
    assert detector is not None


def test_live_video(detector, config):
    """
    Live video loop — captures frames continuously, runs detection on each,
    draws bounding boxes and prints pixel locations to the console.

    Press 'q' in the OpenCV window to stop.
    """
    from bird_tracker.camera import LowResCamera

    cam = LowResCamera(config['low_res_camera'])

    frame_idx   = 0
    print_every = 15

    print("\nLive detection running — press 'q' to quit")
    try:
        while True:
            frame = cam.capture_frame()
            h, w  = frame.shape[:2]

            detections = detector.detect(frame)
            frame_idx += 1

            if frame_idx % print_every == 0 or detections:
                print_detections(frame_idx, detections, w, h)
                print(detections)

            display = draw_detections(frame.copy(), detections)
            cv2.putText(display, f"frame:{frame_idx} det:{len(detections)}",
                        (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            cv2.imshow('Live Detection', display)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()

    assert frame_idx > 0
