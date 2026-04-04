from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import pandas as pd
import os
import time
from tensorflow.keras.models import load_model

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the cloud map dashboard

# ===============================
# CONFIGURATION
# ===============================
IMAGE_FOLDER = "images"
CSV_FILE = "sand_data.csv"

PIXELS_PER_MM = 10
MIN_AREA = 30
MAX_AREA = 5000

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ===============================
# TEMP STORAGE (holds latest GPS until image arrives)
# ===============================
latest_gps = {"lat": 0.0, "lon": 0.0}

# ===============================
# LOAD AI MODEL
# ===============================
print("Loading AI model...")
model = load_model("sand_ai_model.h5")
print("AI model loaded")

# ===============================
# CREATE CSV IF NOT EXISTS
# ===============================
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=[
        "Image", "Latitude", "Longitude",
        "Avg_Grain_Size_mm", "Grain_Class", "Timestamp"
    ])
    df.to_csv(CSV_FILE, index=False)

# ===============================
# AI IMAGE ANALYSIS FUNCTION
# ===============================
def analyze_sand_ai(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return 0

    original_h, original_w = img.shape[:2]

    img_resized = cv2.resize(img, (256, 256))
    img_norm = img_resized / 255.0
    img_input = np.expand_dims(img_norm, axis=0)

    mask = model.predict(img_input)[0]
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

    avg_size = round(np.mean(sizes), 3) if sizes else 0
    return avg_size

# ===============================
# ESP 1 — GPS ENDPOINT
# ===============================
@app.route("/gps", methods=["GET"])
def receive_gps():
    lat = request.args.get("lat", "0")
    lon = request.args.get("lon", "0")

    latest_gps["lat"] = float(lat)
    latest_gps["lon"] = float(lon)

    print(f"GPS received → Lat: {lat}, Lon: {lon}")
    return "GPS OK"

# ===============================
# ESP 2 — IMAGE ENDPOINT
# ===============================
@app.route("/upload", methods=["POST"])
def upload():
    lat = latest_gps["lat"]
    lon = latest_gps["lon"]

    filename = f"sand_{int(time.time())}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(request.data)

    print(f"Image received: {filename} | GPS → Lat: {lat}, Lon: {lon}")

    # AI PROCESSING
    avg_size = analyze_sand_ai(filepath)

    # CLASSIFICATION
    if avg_size < 1.5:
        grain_class = "Fine"
    elif avg_size <= 2.5:
        grain_class = "Medium"
    else:
        grain_class = "Coarse"

    # SAVE DATA
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_csv(CSV_FILE)
    df.loc[len(df)] = [filename, lat, lon, avg_size, grain_class, timestamp]
    df.to_csv(CSV_FILE, index=False)

    print("Saved:", filename, lat, lon, avg_size, grain_class)
    return "OK"

# ===============================
# CLOUD MAP — DATA API ENDPOINT
# ===============================
@app.route("/data", methods=["GET"])
def get_data():
    """Returns all sand grain records as JSON for the cloud map dashboard."""
    if not os.path.exists(CSV_FILE):
        return jsonify([])

    df = pd.read_csv(CSV_FILE)

    # Optional filter by class: /data?class=Fine
    grain_class = request.args.get("class")
    if grain_class:
        df = df[df["Grain_Class"] == grain_class]

    # Optional limit: /data?limit=100
    limit = request.args.get("limit", type=int)
    if limit:
        df = df.tail(limit)

    records = df.to_dict(orient="records")
    return jsonify(records)

# ===============================
# CLOUD MAP — STATS ENDPOINT
# ===============================
@app.route("/stats", methods=["GET"])
def get_stats():
    """Returns summary statistics for the dashboard."""
    if not os.path.exists(CSV_FILE):
        return jsonify({
            "total": 0, "fine": 0, "medium": 0, "coarse": 0,
            "avg_grain_size": 0, "last_updated": None
        })

    df = pd.read_csv(CSV_FILE)
    if df.empty:
        return jsonify({
            "total": 0, "fine": 0, "medium": 0, "coarse": 0,
            "avg_grain_size": 0, "last_updated": None
        })

    stats = {
        "total": len(df),
        "fine": int((df["Grain_Class"] == "Fine").sum()),
        "medium": int((df["Grain_Class"] == "Medium").sum()),
        "coarse": int((df["Grain_Class"] == "Coarse").sum()),
        "avg_grain_size": round(float(df["Avg_Grain_Size_mm"].mean()), 3),
        "last_updated": df["Timestamp"].iloc[-1] if "Timestamp" in df.columns else None
    }
    return jsonify(stats)

# ===============================
# HEALTH CHECK
# ===============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})

# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    print("Server running on http://192.168.0.6:5000")
    print("Cloud map endpoints:")
    print("  GET /data        → all records as JSON")
    print("  GET /stats       → summary statistics")
    print("  GET /health      → server health check")
    app.run(host="192.168.0.6", port=5000)
