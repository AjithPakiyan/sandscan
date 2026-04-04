import os
import cv2
import numpy as np

DATASET_PATH = "sand_dataset/images"
IMG_SIZE = 128

classes = ["fine", "medium", "coarse"]

X = []
y = []

print("📂 Loading dataset...")

for label, class_name in enumerate(classes):

    class_path = os.path.join(DATASET_PATH, class_name)

    if not os.path.exists(class_path):
        print("❌ Missing folder:", class_path)
        continue

    for file in os.listdir(class_path):

        img_path = os.path.join(class_path, file)

        # skip non-image files
        if not file.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        img = cv2.imread(img_path)

        if img is None:
            print("⚠ Skipped unreadable:", img_path)
            continue

        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        X.append(img)
        y.append(label)

print("✅ Images loaded:", len(X))

X = np.array(X) / 255.0
y = np.array(y)
