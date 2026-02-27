"""Wildlife model inference pipeline for making predictions."""

import torch
import torch.nn.functional as F
from pathlib import Path
from typing import Dict, Tuple, List, Optional
import numpy as np
from PIL import Image
from torchvision import transforms
from datetime import datetime


class Predictor:
    """Inference predictor for wildlife species classification."""

    def __init__(
        self,
        model_path: str,
        species_mapping: Dict[int, str],
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        confidence_threshold: float = 0.5
    ):
        """
        Initialize the predictor.

        Args:
            model_path: Path to saved model weights
            species_mapping: Dictionary mapping class indices to species names
            device: Device to run inference on ('cuda' or 'cpu')
            confidence_threshold: Minimum confidence for predictions
        """
        self.device = device
        self.species_mapping = species_mapping
        self.confidence_threshold = confidence_threshold
        self.transforms = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

        # Model will be loaded lazily when needed
        self.model = None
        self.model_path = model_path
        self.is_loaded = False

    def load_model(self, model_class):
        """
        Load the model from saved weights.

        Args:
            model_class: The neural network model class
        """
        if self.is_loaded:
            return

        num_classes = len(self.species_mapping)
        self.model = model_class(num_classes=num_classes)
        self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        self.is_loaded = True
        print(f"Model loaded from {self.model_path}")

    def predict_single(
        self,
        image_path: str
    ) -> Dict:
        """
        Predict the species of a single image.

        Args:
            image_path: Path to the image file

        Returns:
            Dictionary with prediction results
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        image_tensor = self.transforms(image).unsqueeze(0).to(self.device)

        # Get predictions
        with torch.no_grad():
            outputs = self.model(image_tensor)
            probabilities = F.softmax(outputs, dim=1)
            confidence, predicted_idx = torch.max(probabilities, 1)

        predicted_idx = predicted_idx.item()
        confidence = confidence.item()
        predicted_species = self.species_mapping[predicted_idx]

        # Get top 3 predictions
        top_probs, top_indices = torch.topk(probabilities[0], k=min(3, len(self.species_mapping)))
        top_predictions = [
            {
                'species': self.species_mapping[idx.item()],
                'confidence': prob.item()
            }
            for prob, idx in zip(top_probs, top_indices)
        ]

        return {
            'image_path': image_path,
            'predicted_species': predicted_species,
            'confidence': confidence,
            'is_confident': confidence >= self.confidence_threshold,
            'top_predictions': top_predictions,
            'timestamp': datetime.now().isoformat()
        }

    def predict_batch(
        self,
        image_paths: List[str]
    ) -> List[Dict]:
        """
        Predict species for multiple images.

        Args:
            image_paths: List of paths to image files

        Returns:
            List of prediction results
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.predict_single(image_path)
                results.append(result)
            except Exception as e:
                results.append({
                    'image_path': image_path,
                    'error': str(e)
                })

        return results

    def predict_directory(
        self,
        directory_path: str,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Predict species for all images in a directory.

        Args:
            directory_path: Path to directory containing images
            recursive: Whether to search subdirectories

        Returns:
            List of prediction results
        """
        directory = Path(directory_path)
        valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}

        image_paths = []
        if recursive:
            for ext in valid_extensions:
                image_paths.extend(directory.rglob(f'*{ext}'))
        else:
            image_paths = [f for f in directory.glob('*')
                          if f.suffix.lower() in valid_extensions]

        return self.predict_batch([str(p) for p in image_paths])

    def get_prediction_statistics(self, predictions: List[Dict]) -> Dict:
        """
        Calculate statistics from batch predictions.

        Args:
            predictions: List of prediction results

        Returns:
            Dictionary containing prediction statistics
        """
        valid_predictions = [p for p in predictions if 'error' not in p]
        confident_predictions = [p for p in valid_predictions if p['is_confident']]

        species_counts = {}
        total_confidence = 0

        for pred in valid_predictions:
            species = pred['predicted_species']
            species_counts[species] = species_counts.get(species, 0) + 1
            total_confidence += pred['confidence']

        return {
            'total_predictions': len(valid_predictions),
            'confident_predictions': len(confident_predictions),
            'confidence_rate': len(confident_predictions) / len(valid_predictions) if valid_predictions else 0,
            'average_confidence': total_confidence / len(valid_predictions) if valid_predictions else 0,
            'species_distribution': species_counts,
            'errors': len(predictions) - len(valid_predictions)
        }
