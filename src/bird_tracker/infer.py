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
from .models.detector import create_detector
from .trackers import Tracker
from .quality import QualityAssessor

class InferencePipeline:
    def __init__(self, config: dict):
        self.low_res_cam = LowResCamera(config['low_res_camera'])
        self.dslr = DslrController(config['dslr'])
        self.detector = create_detector(config)
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
        frame_idx = 0
        while True:
            frame = self.low_res_cam.capture_frame()
            detections = self.detector.detect(frame)
            tracks = self.tracker.update(detections)
            frame_idx += 1

            # Draw all detections
            for det in detections:
                x1, y1, x2, y2 = (int(v) for v in det.bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{det.confidence:.2f}", (x1, y1 - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            # Draw confirmed tracks
            for track in tracks:
                x1, y1, x2, y2 = (int(v) for v in track.bbox)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                cv2.putText(frame, f"id:{track.id}", (x1, y2 + 14),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)

            # Status overlay
            cv2.putText(frame, f"det:{len(detections)} trk:{len(tracks)}",
                        (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            # Console output every 30 frames
            if frame_idx % 30 == 0:
                print(f"frame {frame_idx:5d} | detections: {len(detections):2d} | tracks: {len(tracks):2d}")

            target = self.select_best_target(tracks)
            if target:
                quality = self.quality.assess(frame, target.bbox)
                if quality['overall_ok'] and time.time() - self.last_capture_time > self.capture_cooldown:
                    self.dslr.focus_and_capture()
                    self.last_capture_time = time.time()
                    print("Captured image!")

            cv2.imshow('Bird Tracker', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.low_res_cam.release()