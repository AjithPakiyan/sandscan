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
MODEL_FILE = "sand_ai_model.h5"

DEFAULT_LAT = 13.0827     # fallback location (Chennai example)
DEFAULT_LON = 80.2707

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# ===============================
# LOAD AI MODEL
# ===============================
print("Loading AI model...")
model = load_model(MODEL_FILE)
print("AI model loaded")

# ===============================
# CREATE CSV IF NOT EXISTS
# ===============================
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=[
        "Image", "Latitude", "Longitude",
        "Prediction", "Confidence"
    ])
    df.to_csv(CSV_FILE, index=False)

# ===============================
# CREATE MAP
# ===============================
def create_map(df):
    if df.empty:
        return

    center_lat = df["Latitude"].astype(float).mean()
    center_lon = df["Longitude"].astype(float).mean()

    sand_map = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    for _, row in df.iterrows():

        if row["Prediction"] == "Fine":
            color = "blue"
        elif row["Prediction"] == "Medium":
            color = "green"
        else:
            color = "red"

        popup = (
            f"Image: {row['Image']}<br>"
            f"Class: {row['Prediction']}<br>"
            f"Confidence: {row['Confidence']}"
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
    print("Map updated")

# ===============================
# IMAGE UPLOAD ENDPOINT
# ===============================
@app.route("/upload", methods=["POST"])
def upload():

    # ---------- GPS (OPTIONAL) ----------
    lat = request.headers.get("Latitude")
    lon = request.headers.get("Longitude")

    if lat is None or lon is None:
        print("GPS not received → using default location")
        lat = DEFAULT_LAT
        lon = DEFAULT_LON

    # ---------- SAVE IMAGE ----------
    filename = f"sand_{int(time.time())}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)

    with open(filepath, "wb") as f:
        f.write(request.data)

    # ---------- AI PREDICTION ----------
    img = cv2.imread(filepath)
    img = cv2.resize(img, (224, 224))
    img = img / 255.0
    img = np.expand_dims(img, axis=0)

    pred = model.predict(img)[0]
    class_id = np.argmax(pred)
    confidence = round(float(np.max(pred)), 3)

    classes = ["Fine", "Medium", "Coarse"]
    result = classes[class_id]

    # ---------- SAVE DATA ----------
    df = pd.read_csv(CSV_FILE)
    df.loc[len(df)] = [filename, lat, lon, result, confidence]
    df.to_csv(CSV_FILE, index=False)

    # ---------- UPDATE MAP ----------
    create_map(df)

    print("Received:", filename, lat, lon, result, confidence)
    return "OK"

# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    print("Server running...")
    app.run(host="0.0.0.0", port=5000)
