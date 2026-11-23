import cv2, time
from ultralytics import YOLO
import database
import ocr

vehicle_model = YOLO("models/yolov8n.pt")
helmet_model = YOLO("models/helmet.pt")

VEHICLES = ["car", "motorcycle", "bus", "truck"]

last_count = 0
last_level = "Low"
last_capture = 0

def detect(frame):
    global last_count, last_level, last_capture

    results = vehicle_model(frame)
    count = 0

    for r in results:
        for box in r.boxes:
            if box.conf < 0.4:
                continue

            cls = int(box.cls)
            name = vehicle_model.names[cls]

            if name in VEHICLES:
                count += 1

                x1,y1,x2,y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)

                crop = frame[y1:y2, x1:x2]

                # Helmet check
                h_results = helmet_model(crop)

                for hr in h_results:
                    for hb in hr.boxes:
                        hcls = int(hb.cls)
                        hname = helmet_model.names[hcls]

                        if hname == "no_helmet":
                            cv2.putText(frame,"NO HELMET",(x1,y1-10),
                                        cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,255),2)

                            if time.time() - last_capture > 5:
                                plate = ocr.read_plate(crop)

                                filename = f"snapshots/{int(time.time())}.jpg"
                                cv2.imwrite(filename, frame)

                                database.add_violation(plate, "No Helmet", filename)

                                last_capture = time.time()

    last_count = count
    last_level = "Low" if count < 10 else "Medium" if count < 25 else "High"

    return frame