from flask import Flask, Response, jsonify, send_from_directory, request
import cv2
from ultralytics import YOLO
import numpy as np
import os
import time
from roboflow import Roboflow
rf = Roboflow(api_key="iaaJHMcEjHDG0HcfIRXb")

project = rf.workspace("projects-uv0zk").project("helmet-detection-20241116-79jit")
helmet_model = project.version(1).model

app = Flask(__name__, static_folder="static")

vehicle_model = YOLO("yolov8n.pt")

VEHICLES = ["car", "motorcycle", "bus", "truck"]

# Vehicle type counting
vehicle_counts = {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0}
last_count = 0
last_level = "Low"

camera_on = False
cap = None
recording_cap = None
manual_snapshot_requested = False

os.makedirs("static/violations", exist_ok=True)
os.makedirs("snapshots", exist_ok=True)
os.makedirs("recordings", exist_ok=True)

# =========================
def detect_vehicle(frame):
    global vehicle_counts, last_count

    results = vehicle_model(frame)
    
    # Reset counts
    for v in VEHICLES:
        vehicle_counts[v] = 0
    
    # Count vehicles by type
    for r in results:
        for b in r.boxes:
            if b.conf < 0.4:  # Confidence threshold
                continue
            cls = int(b.cls)
            vehicle_name = vehicle_model.names[cls]
            if vehicle_name in VEHICLES:
                vehicle_counts[vehicle_name] += 1

    # Calculate total
    last_count = sum(vehicle_counts.values())
    return last_count, vehicle_counts

# =========================
def detect_helmet(frame):
    preds = helmet_model.predict(frame, confidence=40, overlap=30).json()
    violation = False

    for p in preds["predictions"]:
        if p["class"] == "no-helmet":
            violation = True
            x = int(p["x"])
            y = int(p["y"])

            cv2.putText(frame, "NO HELMET", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 1,
                        (0, 0, 255), 3)

    return frame, violation

# =========================
def level(c):
    global last_level
    last_level = "Low" if c < 10 else "Medium" if c < 25 else "High"
    return last_level

# =========================
def gen_frames():
    global cap, camera_on

    print("Video stream generator started")

    while True:
        if not camera_on or cap is None:
            print(f"Camera status - camera_on: {camera_on}, cap is None: {cap is None}")
            # Show "Camera Off" message
            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "Camera Off - Click START", (120, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            _, buffer = cv2.imencode('.jpg', blank)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            continue

        success, frame = cap.read()
        if not success:
            print("Failed to read frame from camera")
            # Show error message instead of breaking
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "Camera Read Error", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            _, buffer = cv2.imencode('.jpg', error_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            continue

        # Simple resize for display
        display_frame = cv2.resize(frame, (640, 480))
        
        # Add simple text overlay
        cv2.putText(display_frame, "LIVE CAMERA FEED", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 255, 0), 2)

        # Encode and send frame
        _, buffer = cv2.imencode('.jpg', display_frame)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    # Auto-start camera when page loads
    global camera_on, cap
    if not camera_on:
        print("Auto-starting camera...")
        cap = cv2.VideoCapture(0)
        
        if cap.isOpened():
            # Simple direct setup
            cap.set(3, 640)   # Width
            cap.set(4, 480)   # Height
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            camera_on = True
            print("Camera auto-started successfully")
        else:
            print("Error: Could not open camera")
    
    return app.send_static_file("index.html")

@app.route("/admin")
def admin():
    return app.send_static_file("admin.html")

@app.route("/video")
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/start")
def start():
    global camera_on, cap

    if not camera_on:
        print("Initializing camera...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("Error: Could not open camera")
            return "Camera Error"
        
        # Try maximum quality first, then fallback if not supported
        resolutions = [
            (4096, 2160),  # 4K
            (3840, 2160),  # Standard 4K
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (640, 480)     # SD
        ]
        
        camera_set = False
        for width, height in resolutions:
            cap.set(3, width)
            cap.set(4, height)
            # Test if resolution is supported
            actual_width = int(cap.get(3))
            actual_height = int(cap.get(4))
            if actual_width == width and actual_height == height:
                camera_set = True
                print(f"Camera set to {width}x{height}")
                break
            else:
                print(f"Resolution {width}x{height} not supported, trying next...")
        
        if not camera_set:
            print("Using default camera settings")
        
        cap.set(cv2.CAP_PROP_FPS, 30)  # 30 FPS for compatibility
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # Enable autofocus for quality
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure for quality
        cap.set(cv2.CAP_PROP_GAIN, 0)  # Fixed gain to reduce noise
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0)  # Neutral brightness
        cap.set(cv2.CAP_PROP_CONTRAST, 0)  # Neutral contrast
        cap.set(cv2.CAP_PROP_SATURATION, 0)  # Neutral saturation
        cap.set(cv2.CAP_PROP_HUE, 0)  # Neutral hue
        cap.set(cv2.CAP_PROP_GAMMA, 1.0)  # Standard gamma
        camera_on = True
        print("Camera started successfully")

    return "Started"

@app.route("/stop")
def stop():
    global camera_on, cap

    camera_on = False

    if cap:
        cap.release()
        cap = None

    return "Stopped"

@app.route("/stats")
def stats():
    return jsonify({
        "vehicles": last_count,
        "traffic": last_level,
        "vehicle_counts": vehicle_counts
    })

@app.route("/violations")
def violations():
    files = os.listdir("snapshots")
    return jsonify([f"/snapshots/{f}" for f in files])

@app.route("/snapshots/<path:filename>")
def serve_snapshot(filename):
    return send_from_directory("snapshots", filename)

@app.route("/capture", methods=["POST"])
def capture_snapshot():
    try:
        if 'snapshot' in request.files:
            file = request.files['snapshot']
            if file.filename:
                filename = f"manual_{int(time.time())}.jpg"
                file.save(f"snapshots/{filename}")
                return jsonify({"status": "success", "message": "Snapshot saved"})
        return jsonify({"status": "error", "message": "No snapshot file received"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/detect-helmet", methods=["POST"])
def detect_helmet_endpoint():
    try:
        if 'frame' in request.files:
            file = request.files['frame']
            
            # Read image from file
            import io
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Run helmet detection
                frame_with_detection, violation = detect_helmet(frame)
                
                return jsonify({
                    "status": "success", 
                    "violation": violation,
                    "message": "No helmet detected" if violation else "Helmet OK"
                })
            else:
                return jsonify({"status": "error", "message": "Invalid image"})
        return jsonify({"status": "error", "message": "No frame received"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/detect-vehicles", methods=["POST"])
def detect_vehicles_endpoint():
    try:
        if 'frame' in request.files:
            file = request.files['frame']
            
            # Read image from file
            import io
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Run vehicle detection
                count, vehicle_data = detect_vehicle(frame)
                
                return jsonify({
                    "status": "success", 
                    "vehicles": count,
                    "vehicle_counts": vehicle_data,
                    "message": f"Detected {count} vehicles"
                })
            else:
                return jsonify({"status": "error", "message": "Invalid image"})
        return jsonify({"status": "error", "message": "No frame received"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/save-violation", methods=["POST"])
def save_violation():
    try:
        if 'violation' in request.files:
            file = request.files['violation']
            if file.filename:
                filename = f"v_{int(time.time())}.jpg"
                file.save(f"snapshots/{filename}")
                return jsonify({"status": "success", "message": "Violation saved"})
        return jsonify({"status": "error", "message": "No violation file received"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/test-camera")
def test_camera():
    """Test camera functionality and return status"""
    global cap, camera_on
    
    try:
        test_cap = cv2.VideoCapture(0)
        if test_cap.isOpened():
            ret, frame = test_cap.read()
            if ret:
                test_cap.release()
                return jsonify({
                    "status": "success",
                    "message": f"Camera working! Frame shape: {frame.shape}",
                    "resolution": f"{int(test_cap.get(3))}x{int(test_cap.get(4))}",
                    "camera_on": camera_on,
                    "cap_is_none": cap is None
                })
            else:
                test_cap.release()
                return jsonify({
                    "status": "error",
                    "message": "Camera opened but failed to read frame"
                })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to open camera"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Exception: {str(e)}"
        })

# =========================
if __name__ == "__main__":
    app.run(debug=True)