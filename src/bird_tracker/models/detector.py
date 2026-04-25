"""
Bird Detection Model Implementation

This module provides a wrapper for bird detection models.
Supports loading pre-trained models (e.g., YOLO, SSD) and running inference.

Class: BirdDetector
- __init__(model_path, config): Load model from path, set confidence threshold
- detect(frame): Run detection on frame, return list of Detection objects
- Detection: NamedTuple with bbox, confidence, class_id
"""

from pathlib import Path
from typing import List, NamedTuple

import numpy as np

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None

class Detection(NamedTuple):
    bbox: tuple  # (x1, y1, x2, y2)
    confidence: float
    class_id: int


class BirdDetector:
    def __init__(self, model_path: str, config: dict):
        if YOLO is None:
            raise ImportError(
                "Ultralytics is required for BirdDetector. Install it with: "
                "pip install ultralytics"
            )

        self.conf_threshold = float(config.get('confidence_threshold', 0.5))
        self.img_size = int(config.get('imgsz', 640))
        target_class_ids = config.get('target_class_ids')
        self.target_class_ids = [int(x) for x in target_class_ids] if target_class_ids else None

        self.model_path = self._resolve_model_path(model_path)
        self.model = YOLO(self.model_path)

    def _resolve_model_path(self, model_path: str) -> str:
        if not model_path:
            return 'yolov8n.pt'

        path = Path(model_path)
        if path.is_dir():
            candidates = list(path.rglob('best.*'))
            if candidates:
                return str(candidates[0])
        
        # If the specified file doesn't exist, fall back to default YOLO model
        if not path.exists():
            print(f"Model path '{model_path}' not found. Using default yolov8n.pt")
            return 'yolov8n.pt'
        
        return str(path)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if frame is None:
            return []

        results = self.model(
            frame[..., ::-1],
            imgsz=self.img_size,
            conf=self.conf_threshold,
            classes=self.target_class_ids,
        )

        detections: List[Detection] = []
        for result in results:
            for box in result.boxes:
                coords = box.xyxy[0].cpu().numpy().tolist()
                confidence = float(box.conf.cpu().numpy())
                class_id = int(box.cls.cpu().numpy())
                if confidence < self.conf_threshold:
                    continue
                detections.append(Detection(bbox=tuple(coords), confidence=confidence, class_id=class_id))

        return detections