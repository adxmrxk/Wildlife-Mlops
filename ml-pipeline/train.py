#!/usr/bin/env python3
"""Main training script for the Wildlife MLOps Platform.

This script demonstrates the complete ML pipeline:
1. Load and prepare data
2. Train model with transfer learning
3. Log and monitor performance
4. Save trained model for inference
"""

import argparse
import torch
from pathlib import Path
from src.data import DataLoader
from src.training import WildlifeModel, Trainer
from src.monitoring import ModelMonitor, DataQualityChecker


def main(args):
    """
    Main training pipeline.

    Args:
        args: Command line arguments with training configuration
    """
    print("=" * 60)
    print("Wildlife MLOps Platform - Model Training")
    print("=" * 60)

    # Device setup
    device = 'cuda' if torch.cuda.is_available() and not args.cpu else 'cpu'
    print(f"\nUsing device: {device}")

    # Create species mapping
    species_list = args.species.split(',')
    species_mapping = DataLoader.create_species_mapping(species_list)
    print(f"\nSpecies mapping: {species_mapping}")

    # Create data loaders
    print(f"\nLoading training data from: {args.train_dir}")
    print(f"Loading validation data from: {args.val_dir}")

    train_loader, val_loader = DataLoader.get_data_loaders(
        train_dir=args.train_dir,
        val_dir=args.val_dir,
        species_mapping=species_mapping,
        batch_size=args.batch_size,
        num_workers=args.num_workers
    )

    print(f"Training batches: {len(train_loader)}")
    print(f"Validation batches: {len(val_loader)}")

    # Initialize model
    print(f"\nInitializing {args.model} model...")
    model = WildlifeModel(
        num_classes=len(species_mapping),
        model_name=args.model,
        pretrained=True
    )
    print(f"Model created with {sum(p.numel() for p in model.parameters())} parameters")

    # Initialize trainer
    trainer = Trainer(
        model=model,
        device=device,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay
    )

    # Monitor training
    monitor = ModelMonitor()

    # Train model
    print("\n" + "=" * 60)
    print("Starting Training...")
    print("=" * 60)

    history = trainer.fit(
        train_loader=train_loader,
        val_loader=val_loader,
        epochs=args.epochs,
        freeze_backbone=args.freeze_backbone,
        unfreeze_at_epoch=args.unfreeze_at
    )

    # Save trained model
    model_path = f'models/wildlife_model_{args.model}.pt'
    trainer.save_model(model_path)
    print(f"\n✓ Model saved to {model_path}")

    # Record final metrics
    final_metrics = {
        'model': args.model,
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'final_train_loss': history['train_loss'][-1],
        'final_train_acc': history['train_acc'][-1],
        'final_val_loss': history['val_loss'][-1],
        'final_val_acc': history['val_acc'][-1],
        'best_val_acc': max(history['val_acc'])
    }

    monitor.record_metrics(final_metrics, model_version=args.model)
    print(f"\n✓ Metrics recorded")

    # Print final summary
    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)
    print(f"Final Training Accuracy: {history['train_acc'][-1]:.2f}%")
    print(f"Final Validation Accuracy: {history['val_acc'][-1]:.2f}%")
    print(f"Best Validation Accuracy: {max(history['val_acc']):.2f}%")
    print(f"Final Training Loss: {history['train_loss'][-1]:.4f}")
    print(f"Final Validation Loss: {history['val_loss'][-1]:.4f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Train wildlife species classification model'
    )

    # Data arguments
    parser.add_argument(
        '--train-dir',
        type=str,
        default='data/train',
        help='Path to training data directory'
    )
    parser.add_argument(
        '--val-dir',
        type=str,
        default='data/val',
        help='Path to validation data directory'
    )
    parser.add_argument(
        '--species',
        type=str,
        default='lion,elephant,zebra,giraffe',
        help='Comma-separated list of species to classify'
    )

    # Model arguments
    parser.add_argument(
        '--model',
        type=str,
        default='resnet50',
        choices=['resnet50', 'resnet101'],
        help='Base model architecture'
    )
    parser.add_argument(
        '--freeze-backbone',
        action='store_true',
        default=True,
        help='Freeze backbone during first phase of training'
    )
    parser.add_argument(
        '--unfreeze-at',
        type=int,
        default=10,
        help='Epoch at which to unfreeze backbone'
    )

    # Training arguments
    parser.add_argument(
        '--epochs',
        type=int,
        default=30,
        help='Number of training epochs'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for training'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=1e-3,
        help='Learning rate'
    )
    parser.add_argument(
        '--weight-decay',
        type=float,
        default=1e-4,
        help='L2 regularization weight'
    )
    parser.add_argument(
        '--num-workers',
        type=int,
        default=4,
        help='Number of data loading workers'
    )
    parser.add_argument(
        '--cpu',
        action='store_true',
        help='Force CPU usage instead of GPU'
    )

    args = parser.parse_args()
    main(args)
