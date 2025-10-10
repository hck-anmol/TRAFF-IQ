<<<<<<< HEAD
from ultralytics import YOLO
model = YOLO('yolov8n.pt')

source = 'sample.mp4' 

results = model.predict(source, show=True, save=True, conf=0.5)
print("Detection complete! The output video is saved in the 'runs' folder.")
=======
import cv2
import threading
from ultralytics import YOLO

model = YOLO('yolov8n.pt')

video_files = {
    "North": "data/north.mp4",
    "South": "data/south.mp4",
    "East": "data/east.mp4",
    "West": "data/west.mp4"
}

vehicle_class_ids = [2, 3, 5, 7]

density_results = {}
results_lock = threading.Lock()

def process_video(direction, filename):
    """
    Processes a single video file to detect vehicles and display live density.
    This function is the target for each thread.
    """
    try:
        cap = cv2.VideoCapture(filename)
        if not cap.isOpened():
            print(f"Error: Could not open video file {filename} for {direction}")
            return

        total_vehicles = 0
        frame_count = 0
        window_name = f"Live Density - {direction}"

        while True:
            success, frame = cap.read()
            if not success:
                break # End of video

            frame_count += 1
            
            # Perform YOLO detection
            results = model(frame, verbose=False)

            current_frame_vehicles = 0
            # Extract results and draw boxes
            for box in results[0].boxes:
                if int(box.cls[0]) in vehicle_class_ids:
                    current_frame_vehicles += 1
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2) # Blue box
            
            total_vehicles += current_frame_vehicles
            
            # --- Display Info on Frame ---
            avg_density = (total_vehicles / frame_count) if frame_count > 0 else 0
            text_current = f"Live Count: {current_frame_vehicles}"
            text_avg = f"Avg Density: {avg_density:.2f}"
            
            cv2.rectangle(frame, (5, 5), (250, 70), (0,0,0), -1)
            cv2.putText(frame, text_current, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            cv2.putText(frame, text_avg, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
            
            cv2.imshow(window_name, frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        final_avg_density = (total_vehicles / frame_count) if frame_count > 0 else 0
        with results_lock:
            density_results[direction] = final_avg_density

        cap.release()
        cv2.destroyWindow(window_name)
        print(f"✅ Finished processing for {direction}.")

    except Exception as e:
        print(f"An error occurred in thread for {direction}: {e}")

if __name__ == "__main__":
    print("🚀 Launching simultaneous vehicle density tracking for all directions...")
    print("Press 'q' in any window to close it individually.")
    
    threads = []
    for direction, filename in video_files.items():
        thread = threading.Thread(target=process_video, args=(direction, filename))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\n--- 🚦 Final Average Density Results ---")
    if density_results:
        for direction, density in sorted(density_results.items()):
            print(f"{direction:<6}: {density:.2f} vehicles/frame")
    else:
        print("No results were calculated.")
    print("---------------------------------------\n")
    print("All processing is complete.")
>>>>>>> anmol
