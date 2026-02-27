#!/usr/bin/env python3
"""Inference script for Wildlife MLOps Platform.

This script demonstrates how to:
1. Load a trained model
2. Make predictions on images
3. Log and analyze predictions
"""

import argparse
import torch
import json
from pathlib import Path
from src.inference import Predictor
from src.training import WildlifeModel
from src.monitoring import PredictionLogger


def main(args):
    """
    Main inference pipeline.

    Args:
        args: Command line arguments with inference configuration
    """
    print("=" * 60)
    print("Wildlife MLOps Platform - Inference")
    print("=" * 60)

    # Device setup
    device = 'cuda' if torch.cuda.is_available() and not args.cpu else 'cpu'
    print(f"\nUsing device: {device}")

    # Load species mapping
    with open(args.species_map, 'r') as f:
        species_mapping = json.load(f)

    # Convert string keys to integers
    species_mapping = {int(k): v for k, v in species_mapping.items()}
    print(f"\nSpecies mapping loaded: {len(species_mapping)} species")

    # Initialize predictor
    print(f"\nLoading model from: {args.model_path}")
    predictor = Predictor(
        model_path=args.model_path,
        species_mapping=species_mapping,
        device=device,
        confidence_threshold=args.confidence_threshold
    )

    # Load model
    predictor.load_model(WildlifeModel)

    # Initialize prediction logger
    logger = PredictionLogger(log_dir=args.log_dir)

    print("\n" + "=" * 60)
    print("Making Predictions")
    print("=" * 60)

    # Handle different input types
    if args.image:
        # Single image prediction
        print(f"\nPredicting single image: {args.image}")
        result = predictor.predict_single(args.image)
        print(f"\nResult:")
        print(f"  Predicted Species: {result['predicted_species']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Is Confident (>{args.confidence_threshold:.0%}): {result['is_confident']}")
        print(f"\nTop 3 Predictions:")
        for i, pred in enumerate(result['top_predictions'], 1):
            print(f"  {i}. {pred['species']}: {pred['confidence']:.2%}")

        logger.log_prediction(result)

    elif args.directory:
        # Directory prediction
        print(f"\nPredicting images in directory: {args.directory}")
        results = predictor.predict_directory(
            directory_path=args.directory,
            recursive=args.recursive
        )

        print(f"\nProcessed {len(results)} images")

        # Log all predictions
        logger.log_batch(results)

        # Calculate statistics
        stats = predictor.get_prediction_statistics(results)
        print(f"\nPrediction Statistics:")
        print(f"  Total Predictions: {stats['total_predictions']}")
        print(f"  Confident Predictions: {stats['confident_predictions']}")
        print(f"  Confidence Rate: {stats['confidence_rate']:.2%}")
        print(f"  Average Confidence: {stats['average_confidence']:.2%}")
        print(f"  Errors: {stats['errors']}")
        print(f"\nSpecies Distribution:")
        for species, count in sorted(
            stats['species_distribution'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            print(f"  {species}: {count}")

    else:
        print("Error: Either --image or --directory must be specified")
        return

    # Get session statistics
    session_stats = logger.get_session_statistics()
    print(f"\n✓ Predictions logged to: {logger.current_session_path}")
    print(f"  Session Statistics:")
    print(f"  - Total: {session_stats['total_predictions']}")
    print(f"  - Average Confidence: {session_stats['average_confidence']:.2%}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run inference with trained wildlife model'
    )

    # Model arguments
    parser.add_argument(
        '--model-path',
        type=str,
        required=True,
        help='Path to trained model weights'
    )
    parser.add_argument(
        '--species-map',
        type=str,
        required=True,
        help='Path to JSON file with species mapping'
    )

    # Input arguments (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--image',
        type=str,
        help='Path to single image for prediction'
    )
    input_group.add_argument(
        '--directory',
        type=str,
        help='Path to directory with images for batch prediction'
    )

    # Prediction arguments
    parser.add_argument(
        '--confidence-threshold',
        type=float,
        default=0.5,
        help='Minimum confidence threshold for predictions'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        default=True,
        help='Search subdirectories when using --directory'
    )

    # Logging arguments
    parser.add_argument(
        '--log-dir',
        type=str,
        default='data/predictions_log',
        help='Directory to store prediction logs'
    )
    parser.add_argument(
        '--cpu',
        action='store_true',
        help='Force CPU usage instead of GPU'
    )

    args = parser.parse_args()
    main(args)
