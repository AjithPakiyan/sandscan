from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import os
import time

app = Flask(__name__, static_folder="static")
CORS(app)

CSV_FILE = "sand_data.csv"
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

latest_gps = {"lat": 0.0, "lon": 0.0}

# Create CSV if not exists
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=[
        "Image", "Latitude", "Longitude",
        "Avg_Grain_Size_mm", "Grain_Class", "Timestamp"
    ])
    df.to_csv(CSV_FILE, index=False)

# ── Serve map at /
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# ── ESP1 GPS
@app.route("/gps", methods=["GET"])
def receive_gps():
    lat = request.args.get("lat", "0")
    lon = request.args.get("lon", "0")
    latest_gps["lat"] = float(lat)
    latest_gps["lon"] = float(lon)
    print(f"GPS → {lat}, {lon}")
    return "GPS OK"

# ── ESP2 Image (no AI — saves dummy grain size for now)
@app.route("/upload", methods=["POST"])
def upload():
    lat = latest_gps["lat"]
    lon = latest_gps["lon"]
    filename = f"sand_{int(time.time())}.jpg"
    filepath = os.path.join(IMAGE_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(request.data)

    # Dummy value until AI model is added
    avg_size = 1.5
    grain_class = "Medium"

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_csv(CSV_FILE)
    df.loc[len(df)] = [filename, lat, lon, avg_size, grain_class, timestamp]
    df.to_csv(CSV_FILE, index=False)
    print(f"Saved → {filename}")
    return "OK"

# ── Data API
@app.route("/data", methods=["GET"])
def get_data():
    if not os.path.exists(CSV_FILE):
        return jsonify([])
    df = pd.read_csv(CSV_FILE)
    return jsonify(df.to_dict(orient="records"))

# ── Stats API
@app.route("/stats", methods=["GET"])
def get_stats():
    if not os.path.exists(CSV_FILE):
        return jsonify({"total":0})
    df = pd.read_csv(CSV_FILE)
    return jsonify({"total": len(df)})

# ── Health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Server running → http://localhost:{port}")
    print(f"✅ Map → http://localhost:{port}/")
    app.run(host="0.0.0.0", port=port, debug=True)
