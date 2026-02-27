"""Wildlife model monitoring and performance tracking pipeline."""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import numpy as np
from collections import defaultdict


class PredictionLogger:
    """Log and store predictions for monitoring and analysis."""

    def __init__(self, log_dir: str = 'data/predictions_log'):
        """
        Initialize the prediction logger.

        Args:
            log_dir: Directory to store prediction logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_path = None
        self._create_new_session()

    def _create_new_session(self):
        """Create a new logging session."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_session_path = self.log_dir / f"session_{timestamp}.jsonl"

    def log_prediction(self, prediction: Dict):
        """
        Log a single prediction.

        Args:
            prediction: Prediction result dictionary
        """
        with open(self.current_session_path, 'a') as f:
            f.write(json.dumps(prediction) + '\n')

    def log_batch(self, predictions: List[Dict]):
        """
        Log multiple predictions.

        Args:
            predictions: List of prediction results
        """
        for pred in predictions:
            self.log_prediction(pred)

    def get_session_statistics(self, session_file: str = None) -> Dict:
        """
        Get statistics for a prediction session.

        Args:
            session_file: Path to session log file (uses current if None)

        Returns:
            Dictionary containing session statistics
        """
        log_file = Path(session_file) if session_file else self.current_session_path

        if not log_file.exists():
            return {}

        predictions = []
        with open(log_file, 'r') as f:
            for line in f:
                predictions.append(json.loads(line))

        species_counts = defaultdict(int)
        confidence_scores = []
        error_count = 0

        for pred in predictions:
            if 'error' in pred:
                error_count += 1
            else:
                species = pred['predicted_species']
                confidence = pred['confidence']
                species_counts[species] += 1
                confidence_scores.append(confidence)

        return {
            'total_predictions': len(predictions),
            'successful_predictions': len(predictions) - error_count,
            'errors': error_count,
            'average_confidence': np.mean(confidence_scores) if confidence_scores else 0,
            'min_confidence': np.min(confidence_scores) if confidence_scores else 0,
            'max_confidence': np.max(confidence_scores) if confidence_scores else 0,
            'std_confidence': np.std(confidence_scores) if confidence_scores else 0,
            'species_distribution': dict(species_counts)
        }


class ModelMonitor:
    """Monitor model performance and track metrics over time."""

    def __init__(self, metrics_dir: str = 'data/metrics'):
        """
        Initialize the model monitor.

        Args:
            metrics_dir: Directory to store metrics
        """
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_history = []

    def record_metrics(self, metrics: Dict, model_version: str = None):
        """
        Record model metrics.

        Args:
            metrics: Dictionary of metrics to record
            model_version: Optional model version identifier
        """
        metric_entry = {
            'timestamp': datetime.now().isoformat(),
            'model_version': model_version,
            **metrics
        }
        self.metrics_history.append(metric_entry)

        # Save to file
        metrics_file = self.metrics_dir / 'metrics_log.jsonl'
        with open(metrics_file, 'a') as f:
            f.write(json.dumps(metric_entry) + '\n')

    def get_performance_report(self) -> Dict:
        """
        Generate a performance report from recorded metrics.

        Returns:
            Dictionary containing performance statistics
        """
        if not self.metrics_history:
            return {}

        accuracies = [m.get('accuracy') for m in self.metrics_history if 'accuracy' in m]
        losses = [m.get('loss') for m in self.metrics_history if 'loss' in m]

        return {
            'total_evaluations': len(self.metrics_history),
            'average_accuracy': np.mean(accuracies) if accuracies else 0,
            'max_accuracy': np.max(accuracies) if accuracies else 0,
            'min_accuracy': np.min(accuracies) if accuracies else 0,
            'average_loss': np.mean(losses) if losses else 0,
            'min_loss': np.min(losses) if losses else 0,
            'max_loss': np.max(losses) if losses else 0,
            'last_evaluation': self.metrics_history[-1] if self.metrics_history else None
        }

    def detect_performance_drift(self, threshold: float = 0.05) -> Dict:
        """
        Detect performance drift in model metrics.

        Args:
            threshold: Acceptable performance variation threshold

        Returns:
            Dictionary with drift detection results
        """
        if len(self.metrics_history) < 2:
            return {'drift_detected': False, 'reason': 'Insufficient data'}

        recent = self.metrics_history[-10:]  # Last 10 evaluations
        oldest = self.metrics_history[0]

        recent_acc = np.mean([m.get('accuracy', 0) for m in recent])
        oldest_acc = oldest.get('accuracy', 0)

        accuracy_drop = oldest_acc - recent_acc

        return {
            'drift_detected': accuracy_drop > threshold,
            'accuracy_drop': accuracy_drop,
            'threshold': threshold,
            'oldest_accuracy': oldest_acc,
            'recent_accuracy': recent_acc,
            'recommendation': 'Retrain model' if accuracy_drop > threshold else 'Model performing well'
        }


class DataQualityChecker:
    """Check data quality and characteristics."""

    @staticmethod
    def check_dataset_balance(species_counts: Dict) -> Dict:
        """
        Check if dataset is balanced across species.

        Args:
            species_counts: Dictionary with species names as keys and counts as values

        Returns:
            Dictionary with balance analysis
        """
        counts = list(species_counts.values())
        total = sum(counts)
        mean_count = np.mean(counts)
        std_count = np.std(counts)
        imbalance_ratio = np.max(counts) / np.min(counts) if np.min(counts) > 0 else float('inf')

        return {
            'total_samples': total,
            'num_species': len(species_counts),
            'mean_samples_per_species': mean_count,
            'std_samples_per_species': std_count,
            'imbalance_ratio': imbalance_ratio,
            'is_balanced': imbalance_ratio < 3,  # Threshold for balance
            'species_distribution': species_counts
        }

    @staticmethod
    def check_image_statistics(image_paths: List[str]) -> Dict:
        """
        Check statistics of images in dataset.

        Args:
            image_paths: List of paths to image files

        Returns:
            Dictionary with image statistics
        """
        from PIL import Image

        sizes = []
        formats = defaultdict(int)
        corrupted = []

        for image_path in image_paths:
            try:
                img = Image.open(image_path)
                sizes.append(img.size)
                formats[img.format] += 1
            except Exception as e:
                corrupted.append({'path': image_path, 'error': str(e)})

        if sizes:
            sizes = np.array(sizes)
            width_stats = {
                'mean': float(np.mean(sizes[:, 0])),
                'std': float(np.std(sizes[:, 0])),
                'min': float(np.min(sizes[:, 0])),
                'max': float(np.max(sizes[:, 0]))
            }
            height_stats = {
                'mean': float(np.mean(sizes[:, 1])),
                'std': float(np.std(sizes[:, 1])),
                'min': float(np.min(sizes[:, 1])),
                'max': float(np.max(sizes[:, 1]))
            }
        else:
            width_stats = height_stats = {}

        return {
            'total_images': len(image_paths),
            'corrupted_images': len(corrupted),
            'image_formats': dict(formats),
            'width_statistics': width_stats,
            'height_statistics': height_stats,
            'corrupted_details': corrupted if corrupted else 'None'
        }
