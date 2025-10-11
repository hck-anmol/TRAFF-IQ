import cv2
import threading
from ultralytics import YOLO

density_model = YOLO('yolov8x.pt')
emergency_model = YOLO('../emergency/best.pt')

video_files = {
    "North": "data/ambulance_test.webm",
    "South": "data/south.mp4",
    "East": "data/east.mp4",
    "West": "data/west.mp4"
}

DENSITY_VEHICLE_IDS = [2, 3, 5, 7]
EMERGENCY_CLASSES = ['ambulance_on', 'ambulance_off', 'firetruck_on', 'firetruck_off']

FRAME_SKIP = 4
results_lock = threading.Lock()
final_results = {}

def process_video(direction, filename):
    try:
        cap = cv2.VideoCapture(filename)
        if not cap.isOpened():
            print(f"Error: Could not open video file {filename} for {direction}")
            return

        total_vehicles_on_processed_frames = 0
        processed_frame_count = 0
        frame_number = 0
        last_processed_frame = None
        final_emergency_detected = False
        window_name = f"Live Analysis - {direction}"

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_number += 1
            frame_emergency_alert = False

            if frame_number % FRAME_SKIP == 0:
                processed_frame_count += 1
                
                density_results = density_model(frame, conf=0.4, verbose=False)
                emergency_results = emergency_model(frame, conf=0.9, verbose=False)

                current_frame_vehicles = 0

                for box in density_results[0].boxes:
                    if int(box.cls[0]) in DENSITY_VEHICLE_IDS:
                        current_frame_vehicles += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                for box in emergency_results[0].boxes:
                    class_name = emergency_model.names[int(box.cls[0])]
                    if class_name in EMERGENCY_CLASSES:
                        frame_emergency_alert = True
                        final_emergency_detected = True
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)

                total_vehicles_on_processed_frames += current_frame_vehicles
                avg_density = (total_vehicles_on_processed_frames / processed_frame_count) if processed_frame_count > 0 else 0
                
                if frame_emergency_alert:
                    cv2.putText(frame, "!! EMERGENCY !!", (300, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                text_current = f"Live Count: {current_frame_vehicles}"
                text_avg = f"Avg Density: {avg_density:.2f}"
                cv2.rectangle(frame, (5, 5), (250, 70), (0,0,0), -1)
                cv2.putText(frame, text_current, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                cv2.putText(frame, text_avg, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                
                last_processed_frame = frame.copy()

            if last_processed_frame is not None:
                cv2.imshow(window_name, last_processed_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        final_avg_density = (total_vehicles_on_processed_frames / processed_frame_count) if processed_frame_count > 0 else 0
        with results_lock:
            final_results[direction] = {"density": final_avg_density, "emergency_detected": final_emergency_detected}

        cap.release()
        cv2.destroyWindow(window_name)
        print(f"✅ Finished processing for {direction}.")

    except Exception as e:
        print(f"An error occurred in thread for {direction}: {e}")

if __name__ == "__main__":
    print("🚀 Launching Dual-Model Tracking...")
    threads = []
    for direction, filename in video_files.items():
        thread = threading.Thread(target=process_video, args=(direction, filename))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    print("\n--- 🚦 Final Intersection Results ---")
    if final_results:
        for direction, data in sorted(final_results.items()):
            emergency_status = "Yes" if data["emergency_detected"] else "No"
            print(f"{direction:<6}: Avg Density={data['density']:.2f}, Emergency Vehicle Seen={emergency_status}")
    else:
        print("No results were calculated.")
    print("---------------------------------------\n")
    print("All processing is complete.")