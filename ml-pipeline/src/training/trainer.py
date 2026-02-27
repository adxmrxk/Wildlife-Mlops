"""Wildlife model training pipeline with transfer learning support."""

import os
from pathlib import Path
from typing import Tuple, Dict, List
import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau
import numpy as np
from tqdm import tqdm
import mlflow
from datetime import datetime


class WildlifeModel(nn.Module):
    """Transfer learning model for wildlife species classification."""

    def __init__(self, num_classes: int, model_name: str = 'resnet50', pretrained: bool = True):
        """
        Initialize the wildlife classification model.

        Args:
            num_classes: Number of species classes to predict
            model_name: Name of pretrained model ('resnet50', 'resnet101', 'efficientnet_b0')
            pretrained: Whether to use pretrained ImageNet weights
        """
        super().__init__()
        self.num_classes = num_classes
        self.model_name = model_name

        if model_name == 'resnet50':
            from torchvision.models import resnet50
            self.backbone = resnet50(pretrained=pretrained)
            feature_dim = 2048
        elif model_name == 'resnet101':
            from torchvision.models import resnet101
            self.backbone = resnet101(pretrained=pretrained)
            feature_dim = 2048
        else:
            raise ValueError(f"Unsupported model: {model_name}")

        # Replace final classification layer
        self.backbone.fc = nn.Sequential(
            nn.Linear(feature_dim, 1024),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through the model."""
        return self.backbone(x)

    def freeze_backbone(self):
        """Freeze backbone weights for transfer learning."""
        for param in list(self.backbone.parameters())[:-1]:
            param.requires_grad = False

    def unfreeze_backbone(self):
        """Unfreeze all model weights."""
        for param in self.backbone.parameters():
            param.requires_grad = True


class Trainer:
    """Trainer for wildlife species classification model."""

    def __init__(
        self,
        model: nn.Module,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        learning_rate: float = 1e-3,
        weight_decay: float = 1e-4
    ):
        """
        Initialize the trainer.

        Args:
            model: PyTorch model to train
            device: Device to train on ('cuda' or 'cpu')
            learning_rate: Initial learning rate
            weight_decay: L2 regularization weight
        """
        self.model = model.to(device)
        self.device = device
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        self.scheduler = ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3
        )
        self.history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }

    def train_epoch(self, train_loader) -> Tuple[float, float]:
        """
        Train for one epoch.

        Args:
            train_loader: PyTorch DataLoader for training data

        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc='Training')
        for images, labels in pbar:
            images = images.to(self.device)
            labels = labels.to(self.device)

            self.optimizer.zero_grad()
            outputs = self.model(images)
            loss = self.criterion(outputs, labels)

            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()
            _, predicted = outputs.max(1)
            correct += predicted.eq(labels).sum().item()
            total += labels.size(0)

            pbar.set_postfix({'loss': total_loss / (total / len(labels))})

        avg_loss = total_loss / len(train_loader)
        accuracy = 100.0 * correct / total

        return avg_loss, accuracy

    def validate(self, val_loader) -> Tuple[float, float]:
        """
        Validate model on validation set.

        Args:
            val_loader: PyTorch DataLoader for validation data

        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0

        with torch.no_grad():
            pbar = tqdm(val_loader, desc='Validating')
            for images, labels in pbar:
                images = images.to(self.device)
                labels = labels.to(self.device)

                outputs = self.model(images)
                loss = self.criterion(outputs, labels)

                total_loss += loss.item()
                _, predicted = outputs.max(1)
                correct += predicted.eq(labels).sum().item()
                total += labels.size(0)

                pbar.set_postfix({'loss': total_loss / (total / len(labels))})

        avg_loss = total_loss / len(val_loader)
        accuracy = 100.0 * correct / total

        return avg_loss, accuracy

    def fit(
        self,
        train_loader,
        val_loader,
        epochs: int = 30,
        freeze_backbone: bool = True,
        unfreeze_at_epoch: int = 10
    ) -> Dict:
        """
        Train the model for multiple epochs.

        Args:
            train_loader: PyTorch DataLoader for training data
            val_loader: PyTorch DataLoader for validation data
            epochs: Number of epochs to train
            freeze_backbone: Whether to freeze backbone initially
            unfreeze_at_epoch: Epoch at which to unfreeze backbone

        Returns:
            Training history dictionary
        """
        if freeze_backbone:
            self.model.freeze_backbone()
            print("Backbone frozen - fine-tuning head layers only")

        best_val_loss = float('inf')
        patience_counter = 0
        max_patience = 5

        mlflow.start_run()
        mlflow.log_param('epochs', epochs)
        mlflow.log_param('model', self.model.model_name)
        mlflow.log_param('freeze_backbone', freeze_backbone)

        for epoch in range(1, epochs + 1):
            print(f"\n{'='*50}")
            print(f"Epoch {epoch}/{epochs}")
            print(f"{'='*50}")

            # Unfreeze backbone at specified epoch for full fine-tuning
            if epoch == unfreeze_at_epoch and freeze_backbone:
                self.model.unfreeze_backbone()
                print("Backbone unfrozen - fine-tuning all layers")

            train_loss, train_acc = self.train_epoch(train_loader)
            val_loss, val_acc = self.validate(val_loader)

            self.history['train_loss'].append(train_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_loss'].append(val_loss)
            self.history['val_acc'].append(val_acc)

            print(f"\nTrain Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
            print(f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%\n")

            mlflow.log_metric('train_loss', train_loss, step=epoch)
            mlflow.log_metric('train_acc', train_acc, step=epoch)
            mlflow.log_metric('val_loss', val_loss, step=epoch)
            mlflow.log_metric('val_acc', val_acc, step=epoch)

            self.scheduler.step(val_loss)

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self._save_checkpoint(epoch, val_acc)
            else:
                patience_counter += 1
                if patience_counter >= max_patience:
                    print(f"\nEarly stopping at epoch {epoch}")
                    break

        mlflow.end_run()
        return self.history

    def _save_checkpoint(self, epoch: int, val_acc: float):
        """Save model checkpoint."""
        checkpoint_dir = Path('models/checkpoints')
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = checkpoint_dir / f"wildlife_model_epoch{epoch}_acc{val_acc:.2f}.pt"
        torch.save({
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history
        }, checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")

    def save_model(self, save_path: str = 'models/wildlife_model.pt'):
        """Save the trained model."""
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), save_path)
        print(f"Model saved to {save_path}")

    def load_model(self, checkpoint_path: str):
        """Load model from checkpoint."""
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint['history']
        print(f"Checkpoint loaded from {checkpoint_path}")
