import os
import shutil
from pathlib import Path

# The folder where create_ocr_dataset_final.py saved everything
DATA_ROOT = Path("ocr_finetune_dataset")

print("Reorganizing data for the new EasyOCR trainer...")

# --- Create new structure ---
train_dir = DATA_ROOT / "train"
val_dir = DATA_ROOT / "val"
train_dir.mkdir(exist_ok=True)
val_dir.mkdir(exist_ok=True)

# --- Move training data ---
try:
    shutil.move(str(DATA_ROOT / "train_images"), str(train_dir / "train_images"))
    shutil.move(str(DATA_ROOT / "train_gt.txt"), str(train_dir / "gt.txt"))
    print("Successfully organized training data.")
except FileNotFoundError:
    print("Training data already organized or not found.")

# --- Move validation data ---
try:
    shutil.move(str(DATA_ROOT / "val_images"), str(val_dir / "val_images"))
    shutil.move(str(DATA_ROOT / "val_gt.txt"), str(val_dir / "gt.txt"))
    print("Successfully organized validation data.")
except FileNotFoundError:
    print("Validation data already organized or not found.")

print("\nReorganization complete!")