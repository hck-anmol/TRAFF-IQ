import cv2
import csv
import datetime
import numpy as np
from typing import Dict, List, Tuple, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from detect import Config
    from ultralytics import YOLO

class ViolationDetector:
    def __init__(self, cfg: 'Config', model: 'YOLO'):
        """
        Initializes the Violation Detector.
        Args:
            cfg (Config): The configuration object.
            model (YOLO): The pre-loaded YOLO model.
        """
        self.cfg = cfg
        self.model = model
        self.track_history: Dict[int, List] = {}
        self.violators: Set[int] = set()
        
        self.cfg.VIOLATION_LOG_PATH.mkdir(exist_ok=True)
        print("✅ ViolationDetector initialized.")

    def detect_violations(self, frame: np.ndarray, direction: str):
        """Analyzes a frame for red light violations using object tracking."""
        violation_line = self.cfg.VIOLATION_LINES[direction]
        cv2.line(frame, violation_line[0], violation_line[1], (0, 0, 255), 2)

        try:
            results = self.model.track(frame, persist=True, verbose=False, tracker="bytetrack.yaml")[0]
            if results.boxes.id is None: return

            tracked_boxes_xywh = results.boxes.xywh.cpu().numpy()
            tracked_boxes_xyxy = results.boxes.xyxy.cpu().numpy() 
            track_ids = results.boxes.id.int().cpu().tolist()

            for box_xywh, box_xyxy, track_id in zip(tracked_boxes_xywh, tracked_boxes_xyxy, track_ids):
                x, y, w, h = box_xywh
                current_position = (int(x), int(y + h / 2))

                if track_id not in self.track_history:
                    self.track_history[track_id] = []
                self.track_history[track_id].append(current_position)

                if len(self.track_history[track_id]) > 1:
                    previous_position = self.track_history[track_id][-2]
                    
                    if self.intersects(previous_position, current_position, violation_line[0], violation_line[1]):
                        if track_id not in self.violators:
                            self.violators.add(track_id)
                            
                            timestamp = datetime.datetime.now()
                            img_path = self.cfg.VIOLATION_LOG_PATH / f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{direction}_violation.jpg"
                            
                            x1, y1, x2, y2 = map(int, box_xyxy)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

                            cv2.imwrite(str(img_path), frame)
                            print(f"🚨 RED LIGHT VIOLATION DETECTED in {direction} lane! Evidence saved to {img_path}")

        except Exception as e:
            print(f"⚠️ Error during violation detection: {e}")
            
    def intersects(self, p1, p2, p3, p4):
        """Helper function to check if two line segments intersect."""
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)