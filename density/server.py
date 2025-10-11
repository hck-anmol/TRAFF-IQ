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
    'north_has_ambulance', 'south_has_ambulance', 'east_has_ambulance', 'west_has_ambulance'
]

def format_row_to_json(row):
    """Converts a CSV row (dict) into our desired JSON structure for historical data."""
    def to_float(value):
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    return {
        "timestamp": row.get("timestamp", ""),
        "intersection_id": row.get("intersection_id", ""),
        "decision": {"green_lane": row.get("green_lane", ""), "green_time": row.get("green_time", "")},
        "lanes": {
            "NORTH": {"density": to_float(row.get("north_density")), "has_ambulance": row.get("north_has_ambulance") == 'True'},
            "SOUTH": {"density": to_float(row.get("south_density")), "has_ambulance": row.get("south_has_ambulance") == 'True'},
            "EAST": {"density": to_float(row.get("east_density")), "has_ambulance": row.get("east_has_ambulance") == 'True'},
            "WEST": {"density": to_float(row.get("west_density")), "has_ambulance": row.get("west_has_ambulance") == 'True'},
        }
    }

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
        return jsonify(list(reversed(all_data)))
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/log_traffic_data', methods=['POST'])
def log_traffic_data():
    """Receives data from a traffic controller, logs it, and broadcasts it."""
    try:
        data = request.get_json()
        
        row_to_write = [
            data.get('timestamp'), data.get('intersection_id'),
            data.get('decision', {}).get('green_lane'), data.get('decision', {}).get('green_time'),
            data.get('lane_states', {}).get('NORTH', {}).get('density', 0),
            data.get('lane_states', {}).get('SOUTH', {}).get('density', 0),
            data.get('lane_states', {}).get('EAST', {}).get('density', 0),
            data.get('lane_states', {}).get('WEST', {}).get('density', 0),
            data.get('lane_states', {}).get('NORTH', {}).get('has_ambulance', False),
            data.get('lane_states', {}).get('SOUTH', {}).get('has_ambulance', False),
            data.get('lane_states', {}).get('EAST', {}).get('has_ambulance', False),
            data.get('lane_states', {}).get('WEST', {}).get('has_ambulance', False)
        ]
        with open(LOG_FILE, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row_to_write)
        
        frontend_data = {
            "timestamp": data.get('timestamp'),
            "intersection_id": data.get('intersection_id'),
            "decision": data.get('decision', {}),
            "lanes": {}
        }
        if 'lane_states' in data:
            for direction, lane_data in data['lane_states'].items():
                frontend_data['lanes'][direction] = {
                    "density": lane_data.get('density', 0),
                    "has_ambulance": lane_data.get('has_ambulance', False)
                }

        print(f"✅ Logged and Broadcasting: {data.get('intersection_id')} at {data.get('timestamp')}")
        
        socketio.emit('new_data', frontend_data)
        
        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"❌ Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    print("🚀 Starting Flask-SocketIO server...")
    socketio.run(app, host='0.0.0.0', port=5000)