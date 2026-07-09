# TRAFF-IQ — Intelligent Traffic Management System
> 🏆 Finalist @ Hackatron, IIIT Gwalior
TRAFF-IQ is an AI-powered adaptive traffic management system built to work at
real intersections. Instead of fixed timers, it uses live computer vision to
actually *see* what's happening on the road — how many vehicles are in each lane,
whether an ambulance or fire truck is approaching, whether someone just ran a red
light — and makes decisions in real time based on that.
The system also streams everything to a live web dashboard so you can monitor
multiple intersections from one place. And it's not just software — it connects
to Arduino hardware to physically control the traffic signals on the ground.
We built this for Hackatron at IIIT Gwalior and made it to the finals.
---
## What It Does
**Emergency Vehicle Detection**
Detects ambulances, fire trucks, and police vehicles in the camera feed and
immediately clears the signal path for them. Achieved ~90% detection accuracy.
**Traffic Density Estimation**
Counts vehicles lane-by-lane and dynamically adjusts how long each signal stays
green. Busier lanes get more time. Achieved ~85% accuracy.
**Violation Detection**
Catches red-light jumpers and general traffic rule violations using computer
vision. Also ~85% accuracy. Logs every violation with a timestamp.
**Live Dashboard**
All intersection data is streamed in real time to a web dashboard via
Socket.io. You can see signal states, vehicle counts, and violation logs live.
**Hardware Integration**
The system talks to an Arduino board over serial to actually switch the physical
traffic lights. It's not just a simulation.

---
## Tech Stack
|
 Layer 
|
 Technology 
|
|
---
|
---
|
|
 Object Detection 
|
 Python, YOLOv8, OpenCV 
|
|
 Detection Server 
|
 Flask + Flask-SocketIO 
|
|
 Dashboard Backend 
|
 Node.js + Express + Socket.io 
|
|
 Dashboard Frontend 
|
 React.js 
|
|
 Hardware Control 
|
 Arduino (C++) 
|
---

## Setup
**Prerequisites:** Python 3.8+, Node.js 18+, Arduino IDE (only if using hardware)

### 1. Clone the repo
```bash
git clone https://github.com/hck-anmol/TRAFF-IQ.git
cd TRAFF-IQ

2. Set up Python environment
bash

pip install -r requirements.txt
Key packages: ultralytics, opencv-python, flask, flask-socketio, numpy, torch

3. Run the detection server
bash

python app.py
Flask server starts at http://localhost:5000. Point it to a camera feed or a video file — configure the source in config.py.

4. Run the Node.js dashboard backend
bash

cd dashboard
npm install
npm start

5. Run the React frontend
bash

cd client
npm install
npm run dev
Dashboard opens at http://localhost:5173.

6. Arduino (optional)
Open /arduino/signal_control.ino in Arduino IDE, upload it to your board, and update the COM port in config.py to match your setup.

Project Structure

TRAFF-IQ/
├── app.py                  # Main detection script
├── config.py               # Camera source, COM port, thresholds
├── requirements.txt
├── models/                 # YOLOv8 weights
├── detection/              # Vehicle, emergency, violation modules
├── dashboard/              # Node.js + Socket.io backend
├── client/                 # React frontend
└── arduino/                # Arduino signal control sketch

Demo
The system was demonstrated live at Hackatron, IIIT Gwalior with a physical Arduino-controlled signal board and a real video feed of traffic footage.