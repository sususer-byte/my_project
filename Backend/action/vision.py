import logging
import os
import time
import uuid
from typing import Any, Dict

logger = logging.getLogger("furgal.action.vision")


class VisionProcessor:
    def __init__(self, camera_index: int = 0, capture_dir: str = "storage/captures", simulate: bool = False):
        self.camera_index = camera_index
        self.capture_dir = capture_dir
        self.simulate = simulate
        self._opencv_available = False
        self._cv2 = None
        self._ensure_capture_dir()
        self._init_opencv()

    def _ensure_capture_dir(self):
        if not os.path.exists(self.capture_dir):
            os.makedirs(self.capture_dir, exist_ok=True)

    def _init_opencv(self):
        try:
            import cv2
            self._cv2 = cv2
            self._opencv_available = True
        except ImportError:
            self._opencv_available = False
            if not self.simulate:
                logger.warning("OpenCV not installed; forcing vision simulation mode")
                self.simulate = True

    def _ensure_simulation(self, reason: str):
        if not self.simulate:
            logger.warning("%s — switching vision to simulation mode", reason)
            self.simulate = True

    def _simulated_capture(self, task: str, output_path: str) -> Dict[str, Any]:
        return {
            "success": True,
            "mode": "simulated",
            "task": task,
            "path": output_path,
            "description": f"Simulated vision capture for task: {task}",
        }

    def capture_frame(self, task: str = "observe") -> Dict[str, Any]:
        timestamp = int(time.time() * 1000)
        filename = f"capture_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        output_path = os.path.join(self.capture_dir, filename)

        if self.simulate or not self._opencv_available:
            if not self._opencv_available:
                self._ensure_simulation("OpenCV unavailable at capture time")
            return self._simulated_capture(task, output_path)

        try:
            cap = self._cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                self._ensure_simulation(f"Unable to open camera index {self.camera_index}")
                return self._simulated_capture(task, output_path)
            ret, frame = cap.read()
            cap.release()
            if not ret or frame is None:
                self._ensure_simulation("Failed to read frame from camera")
                return self._simulated_capture(task, output_path)
            self._cv2.imwrite(output_path, frame)
            return {
                "success": True,
                "mode": "camera",
                "task": task,
                "path": output_path,
                "shape": {"height": int(frame.shape[0]), "width": int(frame.shape[1])},
            }
        except Exception as exc:
            logger.error("capture_frame failed: %s", exc)
            self._ensure_simulation(f"capture_frame error: {exc}")
            return self._simulated_capture(task, output_path)

    def analyze_task(self, task: str) -> Dict[str, Any]:
        try:
            capture = self.capture_frame(task)
            if not capture.get("success"):
                return capture
            return {
                "success": True,
                "task": task,
                "capture": capture,
                "analysis": (
                    f"Visual input captured for task '{task}' "
                    f"(mode={capture.get('mode', 'unknown')}). "
                    f"Path: {capture.get('path', 'n/a')}"
                ),
            }
        except Exception as exc:
            logger.error("analyze_task failed: %s", exc)
            self._ensure_simulation(f"analyze_task error: {exc}")
            return {
                "success": True,
                "task": task,
                "mode": "simulated",
                "analysis": f"Simulated analysis for task '{task}' after error: {exc}",
            }
