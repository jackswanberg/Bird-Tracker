"""
Bird Detection Model Implementation

Supports two backends selected via config key 'backend':
  'cpu'   (default) — Ultralytics YOLO running on the Pi 5 CPU
  'hailo'           — HailoRT running on the Hailo AI Hat

Use create_detector(config) to get the right instance automatically.
"""

import contextlib
from pathlib import Path
from typing import List, NamedTuple

import numpy as np

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None

try:
    from hailo_platform import (
        HEF, VDevice, ConfigureParams, HailoStreamInterface,
        InputVStreamParams, OutputVStreamParams, FormatType, InferVStreams,
    )
    _hailo_available = True
except ImportError:  # pragma: no cover
    _hailo_available = False


class Detection(NamedTuple):
    bbox: tuple  # (x1, y1, x2, y2) in pixel coords
    confidence: float
    class_id: int


# ---------------------------------------------------------------------------
# CPU backend (Ultralytics YOLO)
# ---------------------------------------------------------------------------

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

    def release(self):
        pass


# ---------------------------------------------------------------------------
# Hailo AI Hat backend (HailoRT)
# ---------------------------------------------------------------------------

class HailoBirdDetector:
    """
    Bird detector that runs inference on the Hailo AI Hat.

    Expects a .hef model compiled with NMS post-processing (as shipped in the
    Hailo model zoo). The Hailo runtime keeps a persistent inference pipeline
    open for the lifetime of this object; call release() when done.

    NMS output format assumed: (1, num_classes, top_k, 5)
    where each detection row is [y1, x1, y2, x2, score] in normalised [0, 1]
    coords. A flat (N, 6) layout [x1, y1, x2, y2, score, class_id] is also
    handled as a fallback.
    """

    def __init__(self, hef_path: str, config: dict):
        if not _hailo_available:
            raise ImportError(
                "hailo_platform not found. Install the Hailo driver stack with: "
                "sudo apt install hailo-all"
            )

        import cv2 as _cv2
        self._cv2 = _cv2

        self.conf_threshold = float(config.get('confidence_threshold', 0.5))
        target_class_ids = config.get('target_class_ids')
        self.target_class_ids = (
            set(int(x) for x in target_class_ids) if target_class_ids else None
        )

        hef = HEF(hef_path)

        input_info = hef.get_input_vstream_infos()[0]
        self._input_name = input_info.name
        # HEF input shape is (H, W, C)
        self._input_h = input_info.shape[0]
        self._input_w = input_info.shape[1]

        output_infos = hef.get_output_vstream_infos()
        self._output_names = [info.name for info in output_infos]
        self._has_nms = any('nms' in n.lower() for n in self._output_names)

        # Keep all Hailo objects alive on self — local variables would be GC'd
        # after __init__ returns, invalidating the pipeline.
        self._target = VDevice()
        configure_params = ConfigureParams.create_from_hef(
            hef, interface=HailoStreamInterface.PCIe
        )
        self._ng = self._target.configure(hef, configure_params)[0]

        input_params = InputVStreamParams.make(self._ng, format_type=FormatType.UINT8)
        output_params = OutputVStreamParams.make(self._ng, format_type=FormatType.FLOAT32)

        self._stack = contextlib.ExitStack()
        self._pipeline = self._stack.enter_context(
            InferVStreams(self._ng, input_params, output_params)
        )
        self._stack.enter_context(self._ng.activate(self._ng.create_params()))

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """BGR frame → uint8 RGB resized to HEF input dims, with batch axis."""
        rgb = frame[..., ::-1]
        resized = self._cv2.resize(rgb, (self._input_w, self._input_h))
        return resized.astype(np.uint8)[np.newaxis]  # (1, H, W, 3)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        if frame is None:
            return []
        orig_h, orig_w = frame.shape[:2]
        raw = self._pipeline.infer({self._input_name: self._preprocess(frame)})
        return self._postprocess(raw, orig_w, orig_h)

    def _postprocess(self, raw: dict, orig_w: int, orig_h: int) -> List[Detection]:
        # Hailo NMS output: list[batch] → list[class_id] → ndarray(N, 5)
        # Each row: [y1, x1, y2, x2, score] in normalised [0, 1] coords.
        detections: List[Detection] = []
        for name in self._output_names:
            per_batch = raw[name]
            class_arrays = per_batch[0]  # drop batch dim
            for class_id, dets in enumerate(class_arrays):
                if self.target_class_ids and class_id not in self.target_class_ids:
                    continue
                for y1, x1, y2, x2, score in dets:
                    if score < self.conf_threshold:
                        continue
                    detections.append(Detection(
                        bbox=(x1 * orig_w, y1 * orig_h, x2 * orig_w, y2 * orig_h),
                        confidence=float(score),
                        class_id=class_id,
                    ))
        return detections

    def release(self):
        self._stack.close()

    def __del__(self):
        try:
            self._stack.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_detector(config: dict):
    """Return a BirdDetector or HailoBirdDetector based on config['backend']."""
    backend = config.get('backend', 'cpu').lower()
    if backend == 'hailo':
        hef_path = config.get('model_path', 'src/bird_tracker/models/yolov6n_h8l.hef')
        return HailoBirdDetector(hef_path, config)
    return BirdDetector(config.get('model_path', 'yolov8n.pt'), config)
