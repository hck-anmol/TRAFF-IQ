from ultralytics import YOLO
model = YOLO('yolov8n.pt')

source = 'sample.mp4' 

results = model.predict(source, show=True, save=True, conf=0.5)
print("Detection complete! The output video is saved in the 'runs' folder.")