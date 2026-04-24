"""
Real-Time Inference Pipeline

Orchestrates the bird detection, tracking, quality assessment, and DSLR capture.

Main class: InferencePipeline
- __init__(config): Initialize components
- run(): Main loop: capture frame, detect, track, assess quality, capture if ready
"""

import time
import cv2
from .camera import LowResCamera, DslrController
from .models.detector import BirdDetector
from .trackers import Tracker
from .quality import QualityAssessor

class InferencePipeline:
    def __init__(self, config: dict):
        self.low_res_cam = LowResCamera(config['low_res_camera'])
        self.dslr = DslrController(config['dslr'])
        self.detector = BirdDetector(config['model_path'], config)
        self.tracker = Tracker(config['tracker'])
        self.quality = QualityAssessor(config['quality'])
        self.capture_cooldown = config.get('capture_cooldown', 5.0)  # seconds
        self.last_capture_time = 0

    def select_best_target(self, tracks):
        # Heuristic: choose track with largest bbox, or highest confidence
        if not tracks:
            return None
        return max(tracks, key=lambda t: (t.bbox[2]-t.bbox[0]) * (t.bbox[3]-t.bbox[1]))

    def run(self):
        while True:
            frame = self.low_res_cam.capture_frame()
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)

            target = self.select_best_target(tracks)
            if target:
                quality = self.quality.assess(frame, target.bbox)
                if quality['overall_ok'] and time.time() - self.last_capture_time > self.capture_cooldown:
                    self.dslr.focus_and_capture()
                    self.last_capture_time = time.time()
                    print("Captured image!")

            # Optional: display frame
            cv2.imshow('Bird Tracker', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.low_res_cam.release()