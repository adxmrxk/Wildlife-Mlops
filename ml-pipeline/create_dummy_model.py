"""Script to create a dummy PyTorch model for testing the ML pipeline integration."""

import os
import json
import torch
from pathlib import Path
from src.training.trainer import WildlifeModel


def create_dummy_model():
    """
    Create a dummy PyTorch model and species mapping for testing.

    Creates:
    - models/wildlife_dummy_model.pt: Dummy model weights
    - data/species_mapping.json: Species class mapping
    """
    # Define sample species
    species_list = [
        "Lion",
        "Elephant",
        "Giraffe",
        "Zebra",
        "Leopard"
    ]

    num_classes = len(species_list)

    # Create species mapping (class index -> species name)
    species_mapping = {str(i): species for i, species in enumerate(species_list)}

    # Create directories
    models_dir = Path('models')
    data_dir = Path('data')
    models_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Save species mapping
    species_mapping_path = data_dir / 'species_mapping.json'
    with open(species_mapping_path, 'w') as f:
        json.dump(species_mapping, f, indent=2)
    print(f"✓ Species mapping saved to: {species_mapping_path}")
    print(f"  Species: {', '.join(species_list)}")

    # Create dummy model with ResNet50 architecture
    print(f"\nCreating dummy model with {num_classes} classes...")
    model = WildlifeModel(
        num_classes=num_classes,
        model_name='resnet50',
        pretrained=False  # Don't download pretrained weights for dummy model
    )

    # Initialize with random weights (for testing)
    # In production, this would be replaced with actual trained weights
    model.eval()

    # Save model weights
    model_path = models_dir / 'wildlife_dummy_model.pt'
    torch.save(model.state_dict(), model_path)
    print(f"✓ Dummy model saved to: {model_path}")

    # Calculate model size
    model_size_mb = os.path.getsize(model_path) / (1024 * 1024)
    print(f"  Model size: {model_size_mb:.2f} MB")
    print(f"  Architecture: ResNet50 with custom head")
    print(f"  Parameters: {sum(p.numel() for p in model.parameters()):,}")

    print("\n" + "="*60)
    print("Dummy model created successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. Start the ML service: uvicorn app:app --reload --port 8000")
    print("2. Test prediction with a sample image")
    print("\nNote: This is a DUMMY model with random weights.")
    print("Replace with a trained model (Priority 4) for real predictions.")


if __name__ == '__main__':
    create_dummy_model()
