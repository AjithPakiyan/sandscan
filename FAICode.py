from flask import Flask, request
import cv2
import numpy as np
import pandas as pd
import os
import time
import folium
from tensorflow.keras.models import load_model

app = Flask(__name__)

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
        "Avg_Grain_Size_mm", "Grain_Class"
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
# MAP CREATION
# ===============================
def create_map(df):
    if df.empty:
        return

    center_lat = df["Latitude"].astype(float).mean()
    center_lon = df["Longitude"].astype(float).mean()

    sand_map = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    for _, row in df.iterrows():
        if row["Grain_Class"] == "Fine":
            color = "blue"
        elif row["Grain_Class"] == "Medium":
            color = "green"
        elif row["Grain_Class"] == "Coarse":
            color = "red"
        else:
            color = "gray"  # GPS-only entries

        popup = (
            f"Image: {row['Image']}<br>"
            f"Lat: {row['Latitude']}<br>"
            f"Lon: {row['Longitude']}<br>"
            f"Grain Size: {row['Avg_Grain_Size_mm']} mm<br>"
            f"Class: {row['Grain_Class']}"
        )

        folium.CircleMarker(
            location=[float(row["Latitude"]), float(row["Longitude"])],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            popup=popup
        ).add_to(sand_map)

    sand_map.save("sand_map.html")
    print("Map updated → sand_map.html")

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

    # Use latest GPS from ESP 1
    lat = latest_gps["lat"]
    lon = latest_gps["lon"]

    filename = f"sand_{int(time.time())}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(request.data)

    print(f"Image received: {filename} | Using GPS → Lat: {lat}, Lon: {lon}")

    # ===== AI PROCESSING =====
    avg_size = analyze_sand_ai(filepath)

    # ===== CLASSIFICATION =====
    if avg_size < 1.5:
        grain_class = "Fine"
    elif avg_size <= 2.5:
        grain_class = "Medium"
    else:
        grain_class = "Coarse"

    # ===== SAVE DATA =====
    df = pd.read_csv(CSV_FILE)
    df.loc[len(df)] = [filename, lat, lon, avg_size, grain_class]
    df.to_csv(CSV_FILE, index=False)

    # ===== UPDATE MAP =====
    create_map(df)

    print("Saved:", filename, lat, lon, avg_size, grain_class)
    return "OK"

# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    print("Server running...")
    app.run(host="0.0.0.0", port=5000)