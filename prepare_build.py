import requests
import zipfile
import os
from tqdm import tqdm
import shutil

MODEL_SMALL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
BUNDLED_DIR = "bundled_model"

def prepare_model():
    if os.path.exists(BUNDLED_DIR):
        print(f"'{BUNDLED_DIR}' already exists. Skipping download.")
        return

    print("Downloading small model for bundling...")
    response = requests.get(MODEL_SMALL_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    zip_path = "temp_model.zip"

    with open(zip_path, "wb") as file, tqdm(total=total_size, unit='iB', unit_scale=True) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = file.write(data)
            bar.update(size)

    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(".")
        extracted_folder = zip_ref.namelist()[0].split('/')[0]
        os.rename(extracted_folder, BUNDLED_DIR)
    
    os.remove(zip_path)
    print("Done! Model is ready for packing.")

if __name__ == "__main__":
    prepare_model()
