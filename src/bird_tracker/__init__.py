"""Bird Tracker Package

A real-time bird identification and tracking system for Raspberry Pi 5
with DSLR camera control for high-quality image capture.
"""

from .camera import LowResCamera, NikonZ6II, DslrController
from .models.detector import BirdDetector, Detection
from .trackers import Tracker, Track
from .quality import QualityAssessor
from .infer import InferencePipeline

__version__ = "0.1.0"
__all__ = [
    'LowResCamera',
    'NikonZ6II',
    'DslrController',
    'BirdDetector',
    'Detection',
    'Tracker',
    'Track',
    'QualityAssessor',
    'InferencePipeline',
]
