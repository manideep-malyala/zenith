
from .base import BaseDetector


class DetectorRegistry:
    def __init__(self):
        self._detectors: list[BaseDetector] = []

    def register(self, detector: BaseDetector) -> None:
        if not any(d.detector_id == detector.detector_id for d in self._detectors):
            self._detectors.append(detector)

    def all(self) -> tuple[BaseDetector, ...]:
        # Return in deterministic order by detector_id
        return tuple(sorted(self._detectors, key=lambda d: d.detector_id))

    def get_detector(self, detector_id: str) -> BaseDetector | None:
        for d in self._detectors:
            if d.detector_id == detector_id:
                return d
        return None
