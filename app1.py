from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import numpy as np
import pandas as pd
import os
import time

app = Flask(__name__, static_folder="static")
CORS(app)

# ===============================
# CONFIGURATION
# ===============================
IMAGE_FOLDER = "images"
CSV_FILE = "sand_data.csv"
PIXELS_PER_MM = 10
MIN_AREA = 30
MAX_AREA = 5000

os.makedirs(IMAGE_FOLDER, exist_ok=True)

latest_gps = {"lat": 0.0, "lon": 0.0}

# ===============================
# LOAD AI MODEL (TFLite)
# ===============================
interpreter = None

def load_model():
    global interpreter
    model_path = "sand_ai_model.tflite"
    h5_path = "sand_ai_model.h5"

    if os.path.exists(model_path):
        try:
            import tflite_runtime.interpreter as tflite
            interpreter = tflite.Interpreter(model_path=model_path)
            interpreter.allocate_tensors()
            print("TFLite model loaded")
        except Exception as e:
            print(f"TFLite load failed: {e}")

    elif os.path.exists(h5_path):
        try:
            import tensorflow as tf
            interpreter = tf.lite.Interpreter(model_path=h5_path)
            interpreter.allocate_tensors()
            print("TF model loaded")
        except Exception as e:
            print(f"TF load failed: {e}")
    else:
        print("No model found — using fallback grain size estimation")

load_model()

# ===============================
# CREATE CSV
# ===============================
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=[
        "Image", "Latitude", "Longitude",
        "Avg_Grain_Size_mm", "Grain_Class", "Timestamp"
    ])
    df.to_csv(CSV_FILE, index=False)

# ===============================
# AI ANALYSIS
# ===============================
def analyze_sand_ai(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 1.5

    # If model loaded — use it
    if interpreter is not None:
        try:
            original_h, original_w = img.shape[:2]
            img_resized = cv2.resize(img, (256, 256))
            img_norm = img_resized / 255.0
            img_input = np.expand_dims(img_norm, axis=0).astype(np.float32)

            input_details  = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            interpreter.set_tensor(input_details[0]['index'], img_input)
            interpreter.invoke()

            mask = interpreter.get_tensor(output_details[0]['index'])[0]
            mask = (mask > 0.5).astype("uint8") * 255
            mask = cv2.resize(mask, (original_w, original_h))

            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            sizes = []
            for c in contours:
                area = cv2.contourArea(c)
                if MIN_AREA < area < MAX_AREA:
                    x, y, w, h = cv2.boundingRect(c)
                    d_mm = ((w + h) / 2) / PIXELS_PER_MM
                    sizes.append(d_mm)

            return round(np.mean(sizes), 3) if sizes else 1.5
        except Exception as e:
            print(f"AI error: {e}")

    # Fallback — basic image analysis without model
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    sizes = []
    for c in contours:
        area = cv2.contourArea(c)
        if MIN_AREA < area < MAX_AREA:
            x, y, w, h = cv2.boundingRect(c)
            d_mm = ((w + h) / 2) / PIXELS_PER_MM
            sizes.append(d_mm)

    return round(np.mean(sizes), 3) if sizes else 1.5

# ===============================
# ROUTES
# ===============================
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/gps", methods=["GET"])
def receive_gps():
    lat = request.args.get("lat", "0")
    lon = request.args.get("lon", "0")
    latest_gps["lat"] = float(lat)
    latest_gps["lon"] = float(lon)
    print(f"GPS → {lat}, {lon}")
    return "GPS OK"

@app.route("/upload", methods=["POST"])
def upload():
    lat = latest_gps["lat"]
    lon = latest_gps["lon"]

    filename = f"sand_{int(time.time())}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(request.data)

    avg_size = analyze_sand_ai(filepath)

    if avg_size < 1.5:
        grain_class = "Fine"
    elif avg_size <= 2.5:
        grain_class = "Medium"
    else:
        grain_class = "Coarse"

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_csv(CSV_FILE)
    df.loc[len(df)] = [filename, lat, lon, avg_size, grain_class, timestamp]
    df.to_csv(CSV_FILE, index=False)

    print(f"Saved → {filename} | {grain_class} | {avg_size} mm")
    return "OK"

@app.route("/data", methods=["GET"])
def get_data():
    if not os.path.exists(CSV_FILE):
        return jsonify([])
    df = pd.read_csv(CSV_FILE)
    grain_class = request.args.get("class")
    if grain_class:
        df = df[df["Grain_Class"] == grain_class]
    limit = request.args.get("limit", type=int)
    if limit:
        df = df.tail(limit)
    return jsonify(df.to_dict(orient="records"))

@app.route("/stats", methods=["GET"])
def get_stats():
    if not os.path.exists(CSV_FILE):
        return jsonify({"total":0,"fine":0,"medium":0,"coarse":0,"avg_grain_size":0})
    df = pd.read_csv(CSV_FILE)
    if df.empty:
        return jsonify({"total":0,"fine":0,"medium":0,"coarse":0,"avg_grain_size":0})
    return jsonify({
        "total": len(df),
        "fine":   int((df["Grain_Class"]=="Fine").sum()),
        "medium": int((df["Grain_Class"]=="Medium").sum()),
        "coarse": int((df["Grain_Class"]=="Coarse").sum()),
        "avg_grain_size": round(float(df["Avg_Grain_Size_mm"].mean()), 3)
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server running on port {port}")
    app.run(host="0.0.0.0", port=port)
