"""Wildlife image data loader and preprocessing module."""

import os
from pathlib import Path
from typing import Tuple, List
import numpy as np
from PIL import Image
import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader


class WildlifeDataset(Dataset):
    """Custom PyTorch dataset for wildlife images with species labels."""

    def __init__(
        self,
        image_dir: str,
        species_mapping: dict,
        transform=None,
        image_size: Tuple[int, int] = (224, 224)
    ):
        """
        Initialize the wildlife dataset.

        Args:
            image_dir: Path to directory containing species subdirectories with images
            species_mapping: Dictionary mapping species names to class indices
            transform: Optional torchvision transforms to apply to images
            image_size: Target image size (height, width)
        """
        self.image_dir = Path(image_dir)
        self.species_mapping = species_mapping
        self.image_size = image_size
        self.image_paths = []
        self.labels = []

        # Default transform if none provided
        if transform is None:
            self.transform = transforms.Compose([
                transforms.Resize(image_size),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
        else:
            self.transform = transform

        self._load_image_paths()

    def _load_image_paths(self):
        """Recursively load all image paths from species subdirectories."""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}

        for species_name, class_idx in self.species_mapping.items():
            species_dir = self.image_dir / species_name

            if not species_dir.exists():
                print(f"Warning: Species directory not found: {species_dir}")
                continue

            for image_file in species_dir.rglob('*'):
                if image_file.is_file() and image_file.suffix.lower() in valid_extensions:
                    self.image_paths.append(str(image_file))
                    self.labels.append(class_idx)

    def __len__(self) -> int:
        """Return total number of images in dataset."""
        return len(self.image_paths)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """Load and return a single image with its label."""
        image_path = self.image_paths[idx]
        label = self.labels[idx]

        try:
            image = Image.open(image_path).convert('RGB')
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            # Return a blank image and label 0 as fallback
            image = Image.new('RGB', self.image_size)

        if self.transform:
            image = self.transform(image)

        return image, label


class DataLoader:
    """Data loading utilities for the wildlife ML pipeline."""

    @staticmethod
    def get_data_loaders(
        train_dir: str,
        val_dir: str,
        species_mapping: dict,
        batch_size: int = 32,
        num_workers: int = 4,
        shuffle: bool = True
    ) -> Tuple:
        """
        Create PyTorch DataLoaders for training and validation.

        Args:
            train_dir: Path to training images directory
            val_dir: Path to validation images directory
            species_mapping: Dictionary mapping species names to class indices
            batch_size: Batch size for DataLoader
            num_workers: Number of worker processes
            shuffle: Whether to shuffle training data

        Returns:
            Tuple of (train_dataloader, val_dataloader)
        """
        # Training transforms with augmentation
        train_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.1),
            transforms.RandomRotation(degrees=15),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        # Validation transforms (no augmentation)
        val_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        train_dataset = WildlifeDataset(
            image_dir=train_dir,
            species_mapping=species_mapping,
            transform=train_transform
        )

        val_dataset = WildlifeDataset(
            image_dir=val_dir,
            species_mapping=species_mapping,
            transform=val_transform
        )

        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            pin_memory=True
        )

        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=True
        )

        return train_loader, val_loader

    @staticmethod
    def load_single_image(
        image_path: str,
        image_size: Tuple[int, int] = (224, 224)
    ) -> torch.Tensor:
        """
        Load and preprocess a single image for inference.

        Args:
            image_path: Path to the image file
            image_size: Target image size

        Returns:
            Preprocessed image tensor with batch dimension
        """
        transform = transforms.Compose([
            transforms.Resize(image_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        image = Image.open(image_path).convert('RGB')
        image = transform(image)

        # Add batch dimension
        return image.unsqueeze(0)

    @staticmethod
    def create_species_mapping(species_list: List[str]) -> dict:
        """
        Create a mapping from species names to class indices.

        Args:
            species_list: List of species names

        Returns:
            Dictionary mapping species names to indices
        """
        return {species: idx for idx, species in enumerate(sorted(species_list))}
