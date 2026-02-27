"""Script to organize Animals-10 dataset into train/val split with English names."""

import os
import shutil
import random
from pathlib import Path

# Path to your extracted dataset (raw-img folder inside archive)
SOURCE_DIR = r"C:\Users\AdamR\Downloads\archive\raw-img"

# Output directories inside the project
TRAIN_DIR = Path("data/train")
VAL_DIR = Path("data/val")

# Train/val split ratio
TRAIN_RATIO = 0.8

VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

# Italian folder names → English
TRANSLATIONS = {
    "cane":       "dog",
    "cavallo":    "horse",
    "elefante":   "elephant",
    "farfalla":   "butterfly",
    "gallina":    "chicken",
    "gatto":      "cat",
    "mucca":      "cow",
    "pecora":     "sheep",
    "ragno":      "spider",
    "scoiattolo": "squirrel",
}


def organize_dataset():
    source = Path(SOURCE_DIR)

    if not source.exists():
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return

    species_folders = [f for f in source.iterdir() if f.is_dir()]

    if not species_folders:
        print(f"ERROR: No folders found in {SOURCE_DIR}")
        return

    print(f"Found {len(species_folders)} animal folders\n")

    total_train = 0
    total_val = 0

    for species_folder in species_folders:
        italian_name = species_folder.name
        english_name = TRANSLATIONS.get(italian_name, italian_name)

        # Get all images
        images = [
            f for f in species_folder.iterdir()
            if f.suffix.lower() in VALID_EXTENSIONS
        ]

        if not images:
            print(f"WARNING: No images found in {species_folder}")
            continue

        # Shuffle and split
        random.shuffle(images)
        split_idx = int(len(images) * TRAIN_RATIO)
        train_images = images[:split_idx]
        val_images = images[split_idx:]

        # Create output directories using English names
        train_species_dir = TRAIN_DIR / english_name
        val_species_dir = VAL_DIR / english_name
        train_species_dir.mkdir(parents=True, exist_ok=True)
        val_species_dir.mkdir(parents=True, exist_ok=True)

        # Copy images
        for img in train_images:
            shutil.copy2(img, train_species_dir / img.name)

        for img in val_images:
            shutil.copy2(img, val_species_dir / img.name)

        print(f"{italian_name} → {english_name}: {len(train_images)} train, {len(val_images)} val")
        total_train += len(train_images)
        total_val += len(val_images)

    print(f"\nDone! Total: {total_train} train, {total_val} val images")
    print(f"Train dir: {TRAIN_DIR.absolute()}")
    print(f"Val dir:   {VAL_DIR.absolute()}")


if __name__ == "__main__":
    random.seed(42)
    organize_dataset()
