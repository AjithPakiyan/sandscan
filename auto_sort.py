import os
import requests
from PIL import Image
from io import BytesIO

BASE_PATH = r"D:\PG_Ajith_Pakiyan_Project\Final codes\sand_dataset\images"
IMG_SIZE = 128

# ==============================
# DIRECT IMAGE SOURCES (PUBLIC DOMAIN)
# ==============================

fine_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/3/3c/Fine_sand_texture.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/6/6d/Sand_closeup.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/2/2f/Sand_texture.jpg",
]

medium_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/7/7e/Beach_sand_texture.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/1/1f/Sand_surface.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/8/8d/Sand_pattern.jpg",
]

coarse_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/5/5c/Coarse_sand.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/9c/Gravel_sand_texture.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/4/4c/Coarse_grain_sand.jpg",
]

CLASSES = {
    "fine": fine_urls,
    "medium": medium_urls,
    "coarse": coarse_urls
}

# ==============================
# CREATE FOLDERS
# ==============================
for folder in CLASSES:
    os.makedirs(os.path.join(BASE_PATH, folder), exist_ok=True)

print("✅ Dataset folders ready")


# ==============================
# DOWNLOAD FUNCTION
# ==============================
def download_images(folder, urls, repeat_count):

    save_dir = os.path.join(BASE_PATH, folder)
    count = 1

    for i in range(repeat_count):
        for url in urls:
            try:
                response = requests.get(url, timeout=10)
                img = Image.open(BytesIO(response.content)).convert("RGB")
                img = img.resize((IMG_SIZE, IMG_SIZE))

                filename = f"{folder}_{count}.jpg"
                img.save(os.path.join(save_dir, filename))

                print("✔ Saved:", filename)
                count += 1

            except:
                continue


# ==============================
# DOWNLOAD DATASET
# ==============================
download_images("fine", fine_urls, 70)     # ~200 images
download_images("medium", medium_urls, 70) # ~200 images
download_images("coarse", coarse_urls, 70) # ~200 images

print("\n🎉 DATASET READY FOR TRAINING")
