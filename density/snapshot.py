import cv2
import json
import sys
from ultralytics import YOLO

# --- CONFIGURATION ---
# This dictionary maps your intersection IDs to their video folders
ALL_INTERSECTIONS = {
    "navrangpura_crossing": "data/navrangpura_crossing",
    "usmanpura_garden": "data/usmanpura_garden",
    "subhash_bridge_east": "data/subhash_bridge_east",
    "civil_hospital_area": "data/civil_hospital_area"
}

DENSITY_MODEL_PATH = "yolov8x.pt"
DENSITY_VEHICLE_IDS = [2, 3, 5, 7]  # COCO IDs: car, motorcycle, bus, truck

def take_city_snapshot():
    """Analyzes the first frame from all 16 videos for an instant traffic snapshot."""
    print("📸 Taking city-wide traffic snapshot...", file=sys.stderr)
    model = YOLO(DENSITY_MODEL_PATH)
    city_snapshot_data = {}

    for intersection_id, video_folder in ALL_INTERSECTIONS.items():
        total_intersection_density = 0
        directions = ["north", "south", "east", "west"]

        for direction in directions:
            # Construct the full path to each of the 16 video files
            video_path = f"{video_folder}/{direction}.mp4"
            cap = cv2.VideoCapture(video_path)
            success, frame = cap.read()
            cap.release()

            if success:
                results = model(frame, conf=0.4, verbose=False)[0]
                density = sum(1 for box in results.boxes if int(box.cls[0]) in DENSITY_VEHICLE_IDS)
                total_intersection_density += density
        
        city_snapshot_data[intersection_id] = total_intersection_density

    # The script's only job is to print the final JSON object to the server
    print(json.dumps(city_snapshot_data))

if __name__ == "__main__":
    take_city_snapshot()