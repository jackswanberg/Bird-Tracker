"""
Training pipeline for the bird detection model.

This module uses Ultralytics YOLO to train on a YOLO-formatted dataset.
The training config should specify a data YAML file, model type, and save location.
"""

import argparse
import shutil
from pathlib import Path

import yaml

try:
    from ultralytics import YOLO
except ImportError:  # pragma: no cover
    YOLO = None


def train_model(config: dict):
    if YOLO is None:
        raise ImportError(
            "Ultralytics is required to train the bird detector. "
            "Install it with: pip install ultralytics"
        )

    data_yaml = config.get('train_data')
    if not data_yaml:
        raise ValueError('Missing `train_data` in training config')

    data_path = Path(data_yaml)
    if not data_path.exists():
        raise FileNotFoundError(f"Training data YAML not found: {data_path}")

    pretrained = config.get('pretrained', 'yolov8n.pt')
    epochs = int(config.get('epochs', 50))
    batch_size = int(config.get('batch_size', 16))
    imgsz = int(config.get('imgsz', 640))
    device = config.get('device', 'cpu')
    save_dir = Path(config.get('save_dir', 'checkpoints'))
    run_name = config.get('run_name', 'bird_detector')
    export_path = Path(config.get('export_path', save_dir / 'bird_detector.pth'))

    print(f"Training model: {pretrained}")
    print(f"Dataset: {data_path}")
    print(f"Epochs: {epochs}, batch: {batch_size}, imgsz: {imgsz}, device: {device}")
    print(f"Saving weights to: {save_dir / run_name}")

    model = YOLO(pretrained)
    model.train(
        data=str(data_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device=device,
        project=str(save_dir),
        name=run_name,
        exist_ok=True,
    )

    best_weights = save_dir / run_name / 'weights' / 'best.pt'
    if best_weights.exists():
        export_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(best_weights, export_path)
        print(f"Copied best model to {export_path}")
    else:
        print(f"Warning: trained model weights not found at {best_weights}")


def load_config(path: str) -> dict:
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='Train the bird detection model')
    parser.add_argument(
        '--config',
        default='configs/train.yaml',
        help='Path to training config YAML file',
    )
    args = parser.parse_args()

    config = load_config(args.config)
    train_model(config)


if __name__ == '__main__':
    main()
