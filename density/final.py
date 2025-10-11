import cv2
import requests
import json
import time
import threading
import argparse
import sys
import os
from ultralytics import YOLO
from dataclasses import dataclass, field
from typing import Dict, List

# --- CONFIGURATION ---
@dataclass
class Config:
    DENSITY_MODEL_PATH: str = "yolov8x.pt"
    EMERGENCY_MODEL_PATH: str = "../emergency/best.pt"
    DENSITY_CONFIDENCE: float = 0.40
    EMERGENCY_CONFIDENCE: float = 0.85
    DENSITY_VEHICLE_IDS: List[int] = field(default_factory=lambda: [2, 3, 5, 7])
    EMERGENCY_CLASSES: List[str] = field(default_factory=lambda: ['ambulance_on', 'ambulance_off', 'firetruck_on', 'firetruck_off'])
    FRAME_SKIP: int = 4
    SERVER_URL: str = "http://localhost:5000/api/data"

# --- LANE STATE ---
@dataclass
class LaneState:
    direction: str
    current_density: int = 0
    has_emergency: bool = False

# --- INTERSECTION AI ENGINE ---
class IntersectionAI:
    def __init__(self, config: Config, intersection_id: str, video_sources: Dict[str, str]):
        self.cfg = config
        self.intersection_id = intersection_id
        self.video_sources = video_sources
        
        print(f"🔧 Initializing AI models for {intersection_id}...", file=sys.stderr)
        
        # Load YOLO models
        try:
            self.density_model = YOLO(config.DENSITY_MODEL_PATH)
            print(f"   ✅ Density model loaded: {config.DENSITY_MODEL_PATH}", file=sys.stderr)
        except Exception as e:
            print(f"   ❌ Error loading density model: {e}", file=sys.stderr)
            sys.exit(1)
        
        try:
            self.emergency_model = YOLO(config.EMERGENCY_MODEL_PATH)
            print(f"   ✅ Emergency model loaded: {config.EMERGENCY_MODEL_PATH}", file=sys.stderr)
        except Exception as e:
            print(f"   ⚠️  Warning: Emergency model not found. Continuing without it.", file=sys.stderr)
            self.emergency_model = None
        
        # Initialize lane states
        self.lanes: Dict[str, LaneState] = {
            direction: LaneState(direction) 
            for direction in video_sources.keys()
        }
        
        self.state_lock = threading.Lock()
        self.should_quit = False
        
        # Verify video files exist
        missing_videos = []
        for direction, path in video_sources.items():
            if not os.path.exists(path):
                missing_videos.append(f"{direction}: {path}")
        
        if missing_videos:
            print(f"   ❌ Missing video files:", file=sys.stderr)
            for mv in missing_videos:
                print(f"      - {mv}", file=sys.stderr)
            sys.exit(1)
        
        # Create processing threads
        self.threads = [
            threading.Thread(target=self._process_lane, args=(direction, path), daemon=True)
            for direction, path in self.video_sources.items()
        ]

    def _process_lane(self, direction: str, video_path: str):
        """Process video feed for a single lane"""
        cap = cv2.VideoCapture(video_path)
        frame_number = 0
        
        print(f"   🎥 Started processing {direction} lane", file=sys.stderr)
        
        while not self.should_quit:
            if not cap.isOpened():
                print(f"   ⚠️  Reopening video: {direction}", file=sys.stderr)
                time.sleep(1)
                cap.open(video_path)
                continue
            
            success, frame = cap.read()
            
            if not success:
                # Loop video
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            
            frame_number += 1
            
            # Skip frames for performance
            if frame_number % self.cfg.FRAME_SKIP != 0:
                continue

            try:
                # Run density detection
                density_results = self.density_model(
                    frame, 
                    conf=self.cfg.DENSITY_CONFIDENCE, 
                    verbose=False
                )[0]
                
                # Count vehicles
                live_density = sum(
                    1 for box in density_results.boxes 
                    if int(box.cls[0]) in self.cfg.DENSITY_VEHICLE_IDS
                )
                
                # Check for emergency vehicles
                has_emergency = False
                if self.emergency_model:
                    emergency_results = self.emergency_model(
                        frame, 
                        conf=self.cfg.EMERGENCY_CONFIDENCE, 
                        verbose=False
                    )[0]
                    
                    has_emergency = any(
                        self.emergency_model.names[int(box.cls[0])] in self.cfg.EMERGENCY_CLASSES 
                        for box in emergency_results.boxes
                    )
                
                # Update lane state
                with self.state_lock:
                    self.lanes[direction].current_density = live_density
                    self.lanes[direction].has_emergency = has_emergency
                    
            except Exception as e:
                print(f"   ❌ Error processing {direction}: {e}", file=sys.stderr)
                continue
        
        cap.release()
        print(f"   🛑 Stopped processing {direction} lane", file=sys.stderr)

    def _make_decision(self):
        """Determine optimal signal timing based on traffic density"""
        with self.state_lock:
            # Get densities for each direction
            north = self.lanes.get("NORTH", LaneState("NORTH")).current_density
            south = self.lanes.get("SOUTH", LaneState("SOUTH")).current_density
            east = self.lanes.get("EAST", LaneState("EAST")).current_density
            west = self.lanes.get("WEST", LaneState("WEST")).current_density
            
            # Calculate axis totals
            north_south = north + south
            east_west = east + west
            
            # Determine which signal should be active
            active_signal = "East-West" if east_west > north_south else "North-South"
            
            # Calculate timer based on max density
            max_density = max(north_south, east_west)
            timer = min(90, 20 + int(max_density * 1.5))
        
        return active_signal, timer

    def send_data_to_server(self):
        """Send current traffic state to the Node.js server"""
        with self.state_lock:
            densities = {
                direction: lane.current_density 
                for direction, lane in self.lanes.items()
            }
            is_emergency = any(lane.has_emergency for lane in self.lanes.values())
        
        # Get signal decision
        active_signal, timer = self._make_decision()
        
        # Override for emergency vehicles
        if is_emergency:
            for direction, lane in self.lanes.items():
                if lane.has_emergency:
                    # Give priority to emergency vehicle direction
                    if direction in ["NORTH", "SOUTH"]:
                        active_signal = "North-South"
                    else:
                        active_signal = "East-West"
                    timer = 60
                    break
        
        # Prepare payload
        payload = {
            "intersectionId": self.intersection_id,
            "densities": densities,
            "activeSignal": active_signal,
            "timer": timer,
            "isEmergency": is_emergency
        }
        
        # Send to server
        try:
            response = requests.post(
                self.cfg.SERVER_URL, 
                json=payload, 
                timeout=2
            )
            
            if response.status_code == 200:
                print(f"[{self.intersection_id}] ✅ Sent: {json.dumps(payload)}")
            else:
                print(f"[{self.intersection_id}] ⚠️  Server returned {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"[{self.intersection_id}] ❌ Network error: {e}", file=sys.stderr)

    def run(self):
        """Start the AI engine"""
        # Start all lane processing threads
        for thread in self.threads:
            thread.start()
        
        print(f"\n🚀 AI Engine LIVE for intersection: {self.intersection_id}", file=sys.stderr)
        print(f"   Monitoring lanes: {', '.join(self.lanes.keys())}", file=sys.stderr)
        print(f"   Update interval: 5 seconds\n", file=sys.stderr)
        
        try:
            while not self.should_quit:
                self.send_data_to_server()
                time.sleep(5)
                
        except KeyboardInterrupt:
            print(f"\n⚠️  Keyboard interrupt received", file=sys.stderr)
            self.should_quit = True
        
        # Wait for threads to finish
        print(f"   Waiting for threads to stop...", file=sys.stderr)
        for thread in self.threads:
            thread.join(timeout=2)
        
        print(f"✅ Shutdown complete for {self.intersection_id}\n", file=sys.stderr)

# --- MAIN FUNCTION ---
def main():
    parser = argparse.ArgumentParser(
        description="Traffic AI Engine - Live intersection monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python final.py live --intersection_id navrangpura_crossing
  python final.py live --intersection_id civil_hospital_area
        """
    )
    
    parser.add_argument(
        "mode", 
        type=str, 
        choices=['live'], 
        help="Operation mode: 'live' for continuous monitoring"
    )
    
    parser.add_argument(
        "--intersection_id", 
        type=str, 
        required=True,
        help="The unique ID for the intersection (e.g., navrangpura_crossing)"
    )
    
    args = parser.parse_args()
    
    if args.mode != 'live':
        print("❌ This script only supports 'live' mode.", file=sys.stderr)
        print("   Use snapshot.py for one-time traffic analysis.", file=sys.stderr)
        sys.exit(1)
    
    # Construct video paths
    video_folder = f"data/{args.intersection_id}"
    
    # Check if folder exists
    if not os.path.exists(video_folder):
        print(f"❌ Video folder not found: {video_folder}", file=sys.stderr)
        print(f"   Please ensure the data folder exists with videos for {args.intersection_id}", file=sys.stderr)
        sys.exit(1)
    
    video_sources = {
        "NORTH": f"{video_folder}/north.mp4",
        "SOUTH": f"{video_folder}/south.mp4",
        "EAST": f"{video_folder}/east.mp4",
        "WEST": f"{video_folder}/west.mp4"
    }
    
    # Initialize and run AI engine
    config = Config()
    ai_engine = IntersectionAI(config, args.intersection_id, video_sources)
    ai_engine.run()

if __name__ == "__main__":
    main()