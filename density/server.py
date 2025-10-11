import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO
import csv
import os
import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'kjahf78egrudfgrugfrw8hm' 
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
LOG_FILE = 'traffic_data_log.csv'
CSV_HEADER = [
    'timestamp', 'intersection_id', 'green_lane', 'green_time', 
    'north_density', 'south_density', 'east_density', 'west_density',
    'north_wait_time', 'south_wait_time', 'east_wait_time', 'west_wait_time'
]

def format_row_to_json(row):
    """Converts a CSV row (dict) into our desired JSON structure."""
    return {
        "timestamp": row["timestamp"],
        "intersection_id": row["intersection_id"],
        "current_green_lane": row["green_lane"],
        "lanes": {
            "NORTH": {"density": float(row["north_density"]), "wait_time": float(row["north_wait_time"])},
            "SOUTH": {"density": float(row["south_density"]), "wait_time": float(row["south_wait_time"])},
            "EAST": {"density": float(row["east_density"]), "wait_time": float(row["east_wait_time"])},
            "WEST": {"density": float(row["west_density"]), "wait_time": float(row["west_wait_time"])},
        }
    }

# Ensure the log file exists with a header
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)

@app.route('/')
def index():
    """Serves the main HTML page for the live dashboard."""
    return render_template('index.html')

@app.route('/get_all_data', methods=['GET'])
def get_all_data():
    """Reads the entire log file and returns it as a JSON array."""
    try:
        all_data = []
        with open(LOG_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_data.append(format_row_to_json(row))
        # Return data in reverse chronological order (newest first)
        return jsonify(list(reversed(all_data)))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/log_traffic_data', methods=['POST'])
def log_traffic_data():
    """Receives data from a traffic controller, logs it, and broadcasts it."""
    try:
        data = request.get_json()
        row_to_write = [
            data['timestamp'], data['intersection_id'], data['decision']['green_lane'],
            data['decision']['green_time'], data['lane_states']['NORTH']['density'],
            data['lane_states']['SOUTH']['density'], data['lane_states']['EAST']['density'],
            data['lane_states']['WEST']['density'], data['lane_states']['NORTH']['waiting_time'],
            data['lane_states']['SOUTH']['waiting_time'], data['lane_states']['EAST']['waiting_time'],
            data['lane_states']['WEST']['waiting_time']
        ]
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row_to_write)
        
        print(f"✅ Logged and Broadcasting: {data['intersection_id']} at {data['timestamp']}")
        
        # --- This is the MAGIC part ---
        # Format the data and emit it to all connected clients
        formatted_data = format_row_to_json(csv.DictReader([','.join(map(str, row_to_write))], fieldnames=CSV_HEADER).__next__())
        socketio.emit('new_data', formatted_data)
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# --- Main execution ---
if __name__ == '__main__':
    print("🚀 Starting Flask-SocketIO server...")
    # Use socketio.run() instead of app.run() and use eventlet
    socketio.run(app, host='0.0.0.0', port=5000)