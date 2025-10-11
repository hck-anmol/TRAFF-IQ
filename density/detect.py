from ultralytics import YOLO
import cv2
import serial
import time
import random
import numpy as np
import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Tuple, List


@dataclass
class Config:
    SIMULATION_MODE: bool = True
    ARDUINO_PORT: str = 'COM9'
    ARDUINO_BAUD: int = 9600
    MODEL_PATH: str = "models/yolov8x.pt"

    VIDEO_SOURCES: Dict[str, str] = field(default_factory=lambda: {
        "NORTH": "data/north.mp4",
        "SOUTH": "data/south.mp4",
        "EAST": "data/east.mp4",
        "WEST": "data/west.mp4"
    })
    
    VEHICLE_WEIGHTS: Dict[int, float] = field(default_factory=lambda: {
        2: 1.0,
        3: 0.6,
        5: 2.5,
        7: 2.2,
    })

    YELLOW_TIME: int = 3
    ALL_RED_TIME: int = 2
    PEDESTRIAN_CROSS_TIME: int = 15
    
    DENSITY_WEIGHT: float = 1.0
    WAIT_TIME_WEIGHT: float = 0.5
    STARVATION_THRESHOLD: int = 120
    
    PEAK_HOURS: List[Tuple[int, int]] = field(default_factory=lambda: [(7, 10), (16, 19)])
    PEAK_TIMING: Tuple[int, int] = (15, 60)
    NORMAL_TIMING: Tuple[int, int] = (10, 45)
    NIGHT_TIMING: Tuple[int, int] = (8, 30)

@dataclass
class LaneState:
    direction: str
    current_density: float = 0.0
    waiting_time: float = 0.0
    last_green_time: float = field(default_factory=time.time)
    has_ambulance: bool = False

class TrafficController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.model = self.load_model()
        self.arduino = self.connect_arduino() if not cfg.SIMULATION_MODE else None
        
        self.caps = {direction: cv2.VideoCapture(path) for direction, path in cfg.VIDEO_SOURCES.items()}
        self.lanes: Dict[str, LaneState] = {direction: LaneState(direction) for direction in cfg.VIDEO_SOURCES.keys()}
        
        self.current_green_lane: str = random.choice(list(self.lanes.keys()))
        self.current_phase: str = 'GREEN'
        self.phase_end_time: float = 0
        
        self.pedestrian_request: bool = False
        self.should_quit: bool = False
        print("✅ Traffic Controller Initialized.")
        print(f"💡 Current Mode: {'SIMULATION' if cfg.SIMULATION_MODE else 'LIVE'}")

    def load_model(self):
        try:
            model = YOLO(self.cfg.MODEL_PATH)
            print(f"✅ YOLOv8 model loaded from {self.cfg.MODEL_PATH}.")
            return model
        except Exception as e:
            print(f"❌ FATAL: Error loading YOLO model: {e}")
            return None

    def connect_arduino(self):
        try:
            arduino = serial.Serial(self.cfg.ARDUINO_PORT, self.cfg.ARDUINO_BAUD, timeout=1)
            time.sleep(2)
            print(f"✅ Arduino connected on {self.cfg.ARDUINO_PORT}.")
            return arduino
        except serial.SerialException as e:
            print(f"❌ WARNING: Could not connect to Arduino: {e}")
            return None

    def get_timing_profile(self) -> Tuple[int, int]:
        now = datetime.datetime.now()
        current_hour = now.hour
        if any(start <= current_hour < end for start, end in self.cfg.PEAK_HOURS): return self.cfg.PEAK_TIMING
        if 22 <= current_hour or current_hour < 6: return self.cfg.NIGHT_TIMING
        return self.cfg.NORMAL_TIMING

    def analyze_frame_and_draw_boxes(self, frame) -> Tuple[float, bool]:
        score = 0.0
        ambulance_detected = False
        if not self.model: return 0.0, False
        
        try:
            results = self.model(frame, conf=0.4, verbose=False)[0]
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls = int(box.cls[0])
                if cls in self.cfg.VEHICLE_WEIGHTS.keys():
                    score += self.cfg.VEHICLE_WEIGHTS[cls]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        except Exception as e:
            print(f"⚠️ YOLO error: {e}")
            
        return score, ambulance_detected

    def get_snapshot_data(self) -> Dict[str, np.ndarray]:
        snapshot_frames = {}
        current_time = time.time()
        for direction, cap in self.caps.items():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret: 
                    snapshot_frames[direction] = np.zeros((480, 640, 3), dtype=np.uint8)
                    continue
            
            snapshot_frames[direction] = frame
            score, has_ambulance = self.analyze_frame_and_draw_boxes(frame)
            
            self.lanes[direction].current_density = score
            self.lanes[direction].has_ambulance = has_ambulance
            
            if direction != self.current_green_lane:
                self.lanes[direction].waiting_time = current_time - self.lanes[direction].last_green_time
                
        return snapshot_frames

    def select_next_lane(self) -> str:
        waiting_lanes = [lane for lane in self.lanes.values() if lane.direction != self.current_green_lane]
        
        if self.pedestrian_request: 
            self.pedestrian_request = False
            return "PEDESTRIAN"
        
        starving_lanes = [lane for lane in waiting_lanes if lane.waiting_time > self.cfg.STARVATION_THRESHOLD]
        if starving_lanes: 
            return max(starving_lanes, key=lambda l: l.waiting_time).direction
        
        if not waiting_lanes: 
            return random.choice(list(self.lanes.keys()))

        def calculate_score(lane: LaneState):
            return (lane.current_density * self.cfg.DENSITY_WEIGHT) + (lane.waiting_time * self.cfg.WAIT_TIME_WEIGHT)
        
        best_lane = max(waiting_lanes, key=calculate_score)
        return best_lane.direction

    def calculate_green_time(self, lane: LaneState) -> int:
        min_green, max_green = self.get_timing_profile()
        density_factor = min(lane.current_density / 25.0, 1.0) 
        green_time = min_green + int((max_green - min_green) * density_factor)
        return max(min_green, min(green_time, max_green))

    def send_to_arduino(self, command: str):
        if self.arduino and self.arduino.is_open:
            try:
                self.arduino.write((command + '\n').encode())
                print(f"🚀 Arduino CMD: {command}")
            except Exception as e:
                print(f"❌ Arduino write error: {e}")
        else:
            print(f"🔩 SIMULATED Arduino CMD: {command}")
            
    def run(self):
        print("\n🚀 Starting Traffic Control System"); print("=" * 50)
        snapshot_frames = self.get_snapshot_data()

        try:
            while not self.should_quit:
                current_time = time.time()

                if current_time >= self.phase_end_time:
                    if self.current_phase == 'GREEN':
                        self.current_phase = 'YELLOW'
                        self.phase_end_time = current_time + self.cfg.YELLOW_TIME
                        self.send_to_arduino(f"YELLOW:{self.current_green_lane},TIME:{self.cfg.YELLOW_TIME}")
                        print(f"🟡 Switching {self.current_green_lane} -> YELLOW ({self.cfg.YELLOW_TIME}s)")

                    elif self.current_phase == 'YELLOW':
                        self.current_phase = 'ALL_RED'
                        self.phase_end_time = current_time + self.cfg.ALL_RED_TIME
                        self.send_to_arduino(f"ALLRED,TIME:{self.cfg.ALL_RED_TIME}")
                        print(f"🔴 ALL RED for {self.cfg.ALL_RED_TIME}s")

                    elif self.current_phase in ['ALL_RED', 'PEDESTRIAN']:
                        print("\n" + "=" * 40)
                        print("📸 Taking intersection snapshot for decision...")
                        snapshot_frames = self.get_snapshot_data()
                        next_lane_dir = self.select_next_lane()
                        
                        if next_lane_dir == "PEDESTRIAN":
                            self.current_phase = 'PEDESTRIAN'
                            self.phase_end_time = current_time + self.cfg.PEDESTRIAN_CROSS_TIME
                            self.send_to_arduino(f"PEDESTRIAN,TIME:{self.cfg.PEDESTRIAN_CROSS_TIME}")
                            print(f"🚶 Pedestrian crossing for {self.cfg.PEDESTRIAN_CROSS_TIME}s")
                        else:
                            self.current_green_lane = next_lane_dir
                            lane_obj = self.lanes[next_lane_dir]
                            green_time = self.calculate_green_time(lane_obj)
                            
                            self.current_phase = 'GREEN'
                            self.phase_end_time = current_time + green_time
                            lane_obj.last_green_time = time.time()
                            lane_obj.waiting_time = 0
                            
                            self.send_to_arduino(f"GREEN:{next_lane_dir},TIME:{green_time}")
                            print(f"🟢 GREEN: {next_lane_dir} for {green_time}s")

                time_left = max(0, int(self.phase_end_time - current_time))

                if self.current_phase == 'GREEN':
                    green_cap = self.caps[self.current_green_lane]
                    ret, green_frame = green_cap.read()
                    if not ret:
                        green_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, green_frame = green_cap.read()
                    if ret:
                        self.analyze_frame_and_draw_boxes(green_frame)
                        cv2.putText(green_frame, f"{self.current_green_lane} 🟢 GREEN ({time_left}s)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        cv2.imshow(f"Live Feed - {self.current_green_lane}", green_frame)
                
                for direction, frame in snapshot_frames.items():
                    lane = self.lanes[direction]
                    if direction != self.current_green_lane:
                         lane.waiting_time = current_time - lane.last_green_time

                    if self.current_phase == 'GREEN' and direction == self.current_green_lane:
                        continue

                    display_frame = frame.copy()
                    status_text, color = "", (0,0,0)
                    if self.current_phase == 'YELLOW' and direction == self.current_green_lane:
                        status_text = f"🟡 YELLOW ({time_left}s)"
                        color = (0, 255, 255)
                    else:
                        status_text = f"🔴 RED ({int(lane.waiting_time)}s)"
                        color = (0, 0, 255)
                    
                    cv2.putText(display_frame, f"{direction} {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    cv2.imshow(f"Live Feed - {direction}", display_frame)

                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.should_quit = True
                if key == ord('p'):
                    self.pedestrian_request = True
                    print("\n🚶 Pedestrian button pressed!\n")

        except KeyboardInterrupt:
            print("\n\n🛑 System stopped by user")
        finally:
            self.cleanup()

    def cleanup(self):
        print("🧹 Cleaning up...")
        if not self.cfg.SIMULATION_MODE:
             self.send_to_arduino("RESET")
             if self.arduino: self.arduino.close()
        for cap in self.caps.values():
            cap.release()
        cv2.destroyAllWindows()
        print("✅ Shutdown complete.")

if __name__ == "__main__":
    config = Config()
    controller = TrafficController(config)
    controller.run()
