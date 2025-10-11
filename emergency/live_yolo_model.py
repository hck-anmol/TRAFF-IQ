import cv2
import json
from ultralytics import YOLO
import time
import sys
import argparse

# --- CONFIGURATION ---
MODEL_PATH = "../emergency/best.pt" 
# VIDEO_PATH has been removed from here
CONFIDENCE_THRESHOLD = 0.9 
# --------------------

# 2. The function now accepts video_path as a parameter
def analyze_video_with_preview(video_path):
    start_time = time.time()
    
    try:
        model = YOLO(MODEL_PATH)
    except Exception as e:
        print(f"Error loading model: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Error: Could not open video file at {video_path}", file=sys.stderr)
            sys.exit(1)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    except Exception as e:
        print(f"Error opening video: {e}", file=sys.stderr)
        sys.exit(1)

    final_emergency_detected = False
    emergency_classes = {name for idx, name in model.names.items() if 'ambulance' in name or 'firetruck' in name}

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model(frame, conf=CONFIDENCE_THRESHOLD)
        
        annotated_frame = results[0].plot()
        cv2.imshow("YOLOv8 Live Detection", annotated_frame)

        if not final_emergency_detected:
            detected_names = {model.names[int(cls)] for cls in results[0].boxes.cls}
            if not emergency_classes.isdisjoint(detected_names):
                final_emergency_detected = True
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
    end_time = time.time()
    processing_time = end_time - start_time
    fps = total_frames / processing_time if processing_time > 0 else 0

    final_report = {
        "model_path": MODEL_PATH,
        "video_path": video_path,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "processing_time_seconds": round(processing_time, 2),
        "avg_fps": round(fps, 2),
        "emergency_vehicle_detected_in_video": final_emergency_detected,
    }
    
    print(json.dumps(final_report, indent=4))

# 3. New main function to handle terminal arguments
def main():
    # Create a parser object
    parser = argparse.ArgumentParser(description="Live emergency vehicle detection in a video file.")
    
    # Add an argument for the video file path
    parser.add_argument("video_path", help="Path to the video file to be analyzed.")
    
    # Parse the arguments provided in the terminal
    args = parser.parse_args()
    
    # Call the analysis function with the video path from the terminal
    analyze_video_with_preview(args.video_path)

if __name__ == "__main__":
    main()
