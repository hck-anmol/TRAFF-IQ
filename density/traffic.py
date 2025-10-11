from ultralytics import YOLO
import cv2
import serial
import time
import requests
import json
import random
import numpy as np
import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Tuple, List

@dataclass
class Config:
    SIMULATION_MODE: bool = False
    ARDUINO_PORT: str = 'COM9'
    ARDUINO_BAUD: int = 9600

    GENERAL_MODEL_PATH: str = "models/yolov8n.pt"
    EMERGENCY_MODEL_PATH: str = "../emergency/best.pt"

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

    EMERGENCY_CLASS_ID: int = 0
    EMERGENCY_CONF_THRESHOLD: float = 0.60
    EMERGENCY_COOLDOWN: int = 5
    EMERGENCY_PREEMPT_TIME: int = 5
    EMERGENCY_POST_CLEAR_TIME: int = 3

    YELLOW_TIME: int = 3
    ALL_RED_TIME: int = 2
    DENSITY_WEIGHT: float = 1.0
    WAIT_TIME_WEIGHT: float = 0.5
    STARVATION_THRESHOLD: int = 120

    PEAK_HOURS: List[Tuple[int, int]] = field(default_factory=lambda: [(7, 10), (16, 19)])
    PEAK_TIMING: Tuple[int, int] = (15, 60)
    NORMAL_TIMING: Tuple[int, int] = (10, 45)
    NIGHT_TIMING: Tuple[int, int] = (8, 30)

    SERVER_ENDPOINT: str = "http://127.0.0.1:5000/log_traffic_data"
    INTERSECTION_ID: str = "GWL_CROSSING_01"

@dataclass
class LaneState:
    direction: str
    current_density: float = 0.0
    waiting_time: float = 0.0
    last_green_time: float = field(default_factory=time.time)
    has_emergency_vehicle: bool = False
    last_ev_seen_time: float = 0.0

class TrafficController:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        print("💡 Initializing Traffic Controller...")
        self.general_model = self.load_model(cfg.GENERAL_MODEL_PATH, "General Traffic")
        self.emergency_model = self.load_model(cfg.EMERGENCY_MODEL_PATH, "Emergency Vehicle")
        self.arduino = self.connect_arduino() if not cfg.SIMULATION_MODE else None

        self.caps = {direction: cv2.VideoCapture(path) for direction, path in cfg.VIDEO_SOURCES.items()}
        self.lanes: Dict[str, LaneState] = {direction: LaneState(direction) for direction in cfg.VIDEO_SOURCES.keys()}

        self.current_green_lane: str = random.choice(list(self.lanes.keys()))
        self.current_phase: str = 'GREEN'
        self.phase_end_time: float = 0

        self.emergency_mode_active: bool = False
        self.emergency_lane: str = ""

        self.should_quit: bool = False
        print("✅ Traffic Controller Initialized.")

    def load_model(self, path: str, name: str):
        try:
            model = YOLO(path)
            print(f"✅ {name} model loaded from {path}.")
            return model
        except Exception as e:
            print(f"❌ FATAL: Error loading {name} model: {e}")
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

    def analyze_frame_and_draw_boxes(self, frame: np.ndarray, lane: LaneState):
        density_score = 0.0
        if self.general_model:
            results_general = self.general_model(frame, conf=0.4, verbose=False)[0]
            for box in results_general.boxes:
                cls = int(box.cls[0])
                if cls in self.cfg.VEHICLE_WEIGHTS:
                    density_score += self.cfg.VEHICLE_WEIGHTS[cls]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        lane.current_density = density_score

        ev_detected_this_frame = False
        if self.emergency_model:
            results_emergency = self.emergency_model(frame, conf=0.5, verbose=False)[0]
            for box in results_emergency.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                if cls == self.cfg.EMERGENCY_CLASS_ID and conf > self.cfg.EMERGENCY_CONF_THRESHOLD:
                    ev_detected_this_frame = True
                    lane.last_ev_seen_time = time.time()
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 4)
                    cv2.putText(frame, f"EMERGENCY {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        if ev_detected_this_frame:
            if not lane.has_emergency_vehicle:
                print(f"🚨 New Emergency Vehicle detected in {lane.direction} lane!")
            lane.has_emergency_vehicle = True
        elif lane.has_emergency_vehicle:
            if time.time() - lane.last_ev_seen_time > self.cfg.EMERGENCY_COOLDOWN:
                print(f"✅ Emergency Vehicle cleared from {lane.direction} lane.")
                lane.has_emergency_vehicle = False

    def get_snapshot_data(self) -> Dict[str, np.ndarray]:
        snapshot_frames = {}
        for direction, cap in self.caps.items():
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret:
                snapshot_frames[direction] = frame
            else:
                snapshot_frames[direction] = np.zeros((480, 640, 3), dtype=np.uint8)
        return snapshot_frames

    def select_next_lane(self) -> str:
        waiting_lanes = [lane for lane in self.lanes.values() if lane.direction != self.current_green_lane]
        if not waiting_lanes: return random.choice(list(self.lanes.keys()))
        starving_lanes = [lane for lane in waiting_lanes if lane.waiting_time > self.cfg.STARVATION_THRESHOLD]
        if starving_lanes: return max(starving_lanes, key=lambda l: l.waiting_time).direction

        def calculate_score(lane: LaneState):
            return (lane.current_density * self.cfg.DENSITY_WEIGHT) + (lane.waiting_time * self.cfg.WAIT_TIME_WEIGHT)

        return max(waiting_lanes, key=calculate_score).direction

    def get_timing_profile(self) -> Tuple[int, int]:
        now = datetime.datetime.now()
        current_hour = now.hour
        if any(start <= current_hour < end for start, end in self.cfg.PEAK_HOURS): return self.cfg.PEAK_TIMING
        if 22 <= current_hour or current_hour < 6: return self.cfg.NIGHT_TIMING
        return self.cfg.NORMAL_TIMING

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

    def log_decision_to_server(self, green_lane: str, green_time: any):
        lane_states = {
            direction: { "density": round(lane.current_density, 2), "waiting_time": round(lane.waiting_time, 2), "has_ambulance": lane.has_emergency_vehicle }
            for direction, lane in self.lanes.items()
        }
        payload = { "timestamp": datetime.datetime.now().isoformat(), "intersection_id": self.cfg.INTERSECTION_ID, "decision": { "green_lane": green_lane, "green_time": green_time }, "lane_states": lane_states }
        try:
            headers = {'Content-Type': 'application/json'}
            requests.post(self.cfg.SERVER_ENDPOINT, data=json.dumps(payload), headers=headers, timeout=5)
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to the server: {e}")
            
    # --- NEW FEATURE: UNIFORM UI BOX ---
    def draw_ui_box(self, frame, direction, status_text, color, density):
        """Draws a consistent, semi-transparent box with all lane info."""
        box_x, box_y, box_w, box_h = 10, 10, 320, 80 
        
        # Ensure the box dimensions do not exceed the frame size
        if box_y + box_h > frame.shape[0] or box_x + box_w > frame.shape[1]:
            return # Skip drawing if the box is out of bounds

        # Create a semi-transparent overlay
        sub_img = frame[box_y:box_y+box_h, box_x:box_x+box_w]
        black_rect = np.ones(sub_img.shape, dtype=np.uint8) * 0
        res = cv2.addWeighted(sub_img, 0.4, black_rect, 0.6, 1.0) 
        frame[box_y:box_y+box_h, box_x:box_x+box_w] = res

        # Define text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # Line 1: Direction and Status
        cv2.putText(frame, f"{direction} | {status_text}", (box_x + 10, box_y + 30), font, 0.7, color, 2, cv2.LINE_AA)
        
        # Line 2: Density
        cv2.putText(frame, f"Density Score: {density:.1f}", (box_x + 10, box_y + 60), font, 0.7, (255, 255, 0), 2, cv2.LINE_AA)


    def run(self):
        print("\n🚀 Starting Integrated Traffic Control System"); print("=" * 50)
        snapshot_frames = self.get_snapshot_data()

        try:
            while not self.should_quit:
                current_time = time.time()

                if not self.emergency_mode_active:
                    for lane in self.lanes.values():
                        if lane.has_emergency_vehicle:
                            print(f"‼️ EMERGENCY OVERRIDE TRIGGERED for {lane.direction}! Interrupting normal cycle.")
                            self.emergency_lane = lane.direction
                            self.emergency_mode_active = True
                            self.current_phase = 'EMERGENCY_PREEMPT'
                            self.phase_end_time = current_time + self.cfg.EMERGENCY_PREEMPT_TIME

                            # --- MODIFICATION: Updated LCD text ---
                            self.send_to_arduino("LCD:CLEAR")
                            self.send_to_arduino("LCD1:Emergency") # UPDATED TEXT
                            self.send_to_arduino(f"LCD2:Lane {self.emergency_lane}")
                            # --- MODIFICATION END ---
                            
                            self.send_to_arduino("BUZZER:ON")
                            self.send_to_arduino(f"ALLRED,TIME:{self.cfg.EMERGENCY_PREEMPT_TIME}")
                            break

                if current_time >= self.phase_end_time:
                    if self.emergency_mode_active:
                        if self.current_phase == 'EMERGENCY_PREEMPT':
                            self.current_phase = 'EMERGENCY_GREEN'
                            self.current_green_lane = self.emergency_lane
                            self.phase_end_time = current_time + 999
                            self.send_to_arduino(f"GREEN:{self.emergency_lane},TIME:999")
                            self.log_decision_to_server(self.emergency_lane, "Emergency")

                        elif self.current_phase == 'POST_EMERGENCY':
                             self.current_phase = 'ALL_RED'
                             self.phase_end_time = current_time + self.cfg.ALL_RED_TIME

                    elif not self.emergency_mode_active:
                        if self.current_phase == 'GREEN':
                            self.lanes[self.current_green_lane].last_green_time = current_time
                            self.current_phase = 'YELLOW'
                            self.phase_end_time = current_time + self.cfg.YELLOW_TIME
                            self.send_to_arduino(f"YELLOW:{self.current_green_lane},TIME:{self.cfg.YELLOW_TIME}")

                        elif self.current_phase == 'YELLOW':
                            self.current_phase = 'ALL_RED'
                            self.phase_end_time = current_time + self.cfg.ALL_RED_TIME
                            self.send_to_arduino(f"ALLRED,TIME:{self.cfg.ALL_RED_TIME}")

                        elif self.current_phase == 'ALL_RED':
                            print("📸 Taking intersection snapshot for decision...")
                            next_lane = self.select_next_lane()
                            self.current_green_lane = next_lane
                            green_time = self.calculate_green_time(self.lanes[next_lane])
                            self.current_phase = 'GREEN'
                            self.phase_end_time = current_time + green_time
                            self.lanes[next_lane].waiting_time = 0
                            self.send_to_arduino(f"GREEN:{next_lane},TIME:{green_time}")
                            self.log_decision_to_server(next_lane, green_time)

                time_left = max(0, int(self.phase_end_time - current_time))

                for direction, cap in self.caps.items():
                    is_live_feed = False
                    if self.emergency_mode_active and direction == self.emergency_lane:
                        is_live_feed = True
                    elif not self.emergency_mode_active and direction == self.current_green_lane and self.current_phase in ['GREEN', 'YELLOW']:
                        is_live_feed = True

                    if is_live_feed:
                        ret, frame = cap.read()
                        if not ret:
                            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            ret, frame = cap.read()
                        if ret:
                            self.analyze_frame_and_draw_boxes(frame, self.lanes[direction])
                            display_frame = frame
                            snapshot_frames[direction] = frame
                    else:
                        display_frame = snapshot_frames[direction].copy()

                    if self.current_phase == 'EMERGENCY_GREEN' and direction == self.emergency_lane and not self.lanes[direction].has_emergency_vehicle:
                        print("🔚 EXITING EMERGENCY MODE. Vehicle has cleared.")
                        self.emergency_mode_active = False
                        self.current_phase = 'POST_EMERGENCY'
                        self.phase_end_time = current_time + self.cfg.EMERGENCY_POST_CLEAR_TIME
                        self.send_to_arduino("BUZZER:OFF")
                        self.send_to_arduino("LCD:CLEAR")
                        self.send_to_arduino(f"ALLRED,TIME:{self.cfg.EMERGENCY_POST_CLEAR_TIME}")

                    lane = self.lanes[direction]
                    status_text, color = "", (0,0,0)

                    if self.current_phase == 'EMERGENCY_GREEN' and direction == self.emergency_lane:
                         status_text, color = "🚨 EMERGENCY", (0, 0, 255)
                    elif self.current_phase == 'EMERGENCY_PREEMPT' or self.current_phase == 'POST_EMERGENCY':
                         status_text, color = f"🔴 RED ({time_left}s)", (0, 0, 255)
                    elif self.current_phase == 'GREEN' and direction == self.current_green_lane:
                        status_text, color = f"🟢 GREEN ({time_left}s)", (0, 255, 0)
                    elif self.current_phase == 'YELLOW' and direction == self.current_green_lane:
                         status_text, color = f"🟡 YELLOW ({time_left}s)", (0, 255, 255)
                    else:
                        if not self.emergency_mode_active:
                            lane.waiting_time = current_time - lane.last_green_time
                        status_text, color = f"🔴 RED ({int(lane.waiting_time)}s)", (0, 0, 255)

                    # --- MODIFICATION: Draw the new uniform UI box ---
                    self.draw_ui_box(display_frame, direction, status_text, color, lane.current_density)

                    cv2.imshow(f"Live Feed - {direction}", display_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'): self.should_quit = True

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