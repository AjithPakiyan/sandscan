import os
import cv2
import pandas as pd

# ==============================
# CONFIGURATION
# ==============================
BASE_PATH = r"D:\PG_Ajith_Pakiyan_Project\Final codes\sand_dataset"
IMAGE_SIZE = 224

class_map = {
    "fine": 0,
    "medium": 1,
    "coarse": 2
}

# ==============================
# CREATE FOLDERS IF MISSING
# ==============================
print("📁 Checking dataset structure...")

os.makedirs(BASE_PATH, exist_ok=True)

for class_name in class_map.keys():
    path = os.path.join(BASE_PATH, "images", class_name)
    os.makedirs(path, exist_ok=True)
    print("✔", path)

print("✅ Folder structure ready")

# ==============================
# SCAN IMAGES
# ==============================
data = []

print("\n📂 Scanning dataset folders...")

for class_name, label in class_map.items():

    folder = os.path.join(BASE_PATH, "images", class_name)
    files = os.listdir(folder)

    for file in files:
        if file.lower().endswith((".jpg", ".png", ".jpeg")):

            path = os.path.join(folder, file)

            img = cv2.imread(path)
            if img is None:
                continue

            img = cv2.resize(img, (IMAGE_SIZE, IMAGE_SIZE))
            cv2.imwrite(path, img)

            data.append([path, class_name, label])

print("✅ Images processed:", len(data))

# ==============================
# SAVE CSV (only if images exist)
# ==============================
if len(data) > 0:
    df = pd.DataFrame(data, columns=["filepath", "class", "label"])
    csv_path = os.path.join(BASE_PATH, "labels.csv")
    df.to_csv(csv_path, index=False)
    print("✅ labels.csv created")
else:
    print("⚠ No images found — add images first")

# ==============================
# DATASET INFO
# ==============================
info_path = os.path.join(BASE_PATH, "dataset_info.txt")

with open(info_path, "w") as f:
    f.write("Sand AI Dataset\n")
    f.write("=================\n")
    f.write(f"Total images: {len(data)}\n")

print("✅ dataset_info.txt created")
print("\n🎯 Dataset ready!")
