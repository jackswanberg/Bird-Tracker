"""
Real-Time Inference Pipeline

Orchestrates bird detection, tracking, gimbal targeting, quality assessment,
and DSLR capture.

Main class: InferencePipeline
- __init__(config): Initialize components
- run(): Main loop — detect, track, aim gimbal, capture when ready
"""

import time
import cv2
from .camera import LowResCamera, DslrController
from .models.detector import create_detector
from .trackers import Tracker
from .quality import QualityAssessor
from .gimbal import PanTiltController, Targeter


class InferencePipeline:
    def __init__(self, config: dict):
        self.low_res_cam = LowResCamera(config['low_res_camera'])
        self.dslr        = DslrController(config['dslr'])
        self.detector    = create_detector(config)
        self.tracker     = Tracker(config['tracker'])
        self.quality     = QualityAssessor(config['quality'])
        self.capture_cooldown  = config.get('capture_cooldown', 5.0)
        self.last_capture_time = 0

        gimbal_cfg = config.get('gimbal', {})
        self.gimbal   = PanTiltController(gimbal_cfg) if gimbal_cfg else None
        self.targeter = Targeter(self.gimbal, gimbal_cfg) if self.gimbal else None

    def select_best_target(self, tracks):
        """Choose the track with the largest bounding-box area."""
        if not tracks:
            return None
        return max(tracks, key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]))

    def run(self):
        frame_idx = 0
        try:
            while True:
                frame = self.low_res_cam.capture_frame()
                h, w  = frame.shape[:2]

                detections = self.detector.detect(frame)
                tracks     = self.tracker.update(detections)
                frame_idx += 1

                # Draw detections (green)
                for det in detections:
                    x1, y1, x2, y2 = (int(v) for v in det.bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"{det.confidence:.2f}", (x1, y1 - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                # Draw confirmed tracks (blue)
                for track in tracks:
                    x1, y1, x2, y2 = (int(v) for v in track.bbox)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 100, 0), 2)
                    cv2.putText(frame, f"id:{track.track_id}", (x1, y2 + 14),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 100, 0), 1)

                target = self.select_best_target(tracks)

                if target:
                    # Aim gimbal at the target every frame
                    if self.targeter:
                        self.targeter.update(target.bbox, w, h)

                    # Trigger DSLR when quality passes and cooldown elapsed
                    quality = self.quality.assess(frame, target.bbox)
                    if (quality['overall_ok']
                            and time.time() - self.last_capture_time > self.capture_cooldown):
                        self.dslr.focus_and_capture()
                        self.last_capture_time = time.time()
                        print("Captured image!")
                else:
                    # No target — nothing to do with gimbal
                    pass

                # Status overlay
                gimbal_str = ""
                if self.gimbal and self.gimbal.connected:
                    gimbal_str = f" pan:{self.gimbal._pan:.0f} tilt:{self.gimbal._tilt:.0f}"
                cv2.putText(frame,
                            f"det:{len(detections)} trk:{len(tracks)}{gimbal_str}",
                            (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

                if frame_idx % 30 == 0:
                    print(f"frame {frame_idx:5d} | det: {len(detections):2d} "
                          f"| trk: {len(tracks):2d}{gimbal_str}")

                cv2.imshow('Bird Tracker', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        finally:
            self.low_res_cam.release()
            if self.gimbal:
                self.gimbal.center()
                self.gimbal.release()
