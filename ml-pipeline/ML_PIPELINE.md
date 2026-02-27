# ML Pipeline Documentation

## Overview

The Wildlife MLOps Platform includes a complete machine learning pipeline for training and deploying wildlife species classification models. The pipeline is organized into four main components:

- **Data Pipeline** - Loading and preprocessing wildlife images
- **Training Pipeline** - Training transfer learning models
- **Inference Pipeline** - Making predictions on new images
- **Monitoring Pipeline** - Tracking performance and model health

## Directory Structure

```
ml-pipeline/
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   └── loader.py           # WildlifeDataset and DataLoader classes
│   ├── training/
│   │   ├── __init__.py
│   │   └── trainer.py          # WildlifeModel and Trainer classes
│   ├── inference/
│   │   ├── __init__.py
│   │   └── predictor.py        # Predictor class for inference
│   └── monitoring/
│       ├── __init__.py
│       └── monitor.py          # PredictionLogger, ModelMonitor, DataQualityChecker
├── data/
│   ├── train/                  # Training images organized by species
│   ├── val/                    # Validation images organized by species
│   └── predictions_log/        # Prediction logs (auto-generated)
├── models/
│   ├── checkpoints/            # Model checkpoints during training
│   └── wildlife_model_*.pt     # Final trained models
├── notebooks/                  # Jupyter notebooks for exploration
├── train.py                    # Training script
├── predict.py                  # Inference script
└── requirements.txt            # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
cd ml-pipeline
pip install -r requirements.txt
```

### 2. Prepare Data

Organize your wildlife images by species in the following structure:

```
data/
├── train/
│   ├── lion/
│   │   ├── image1.jpg
│   │   ├── image2.jpg
│   │   └── ...
│   ├── elephant/
│   │   ├── image1.jpg
│   │   └── ...
│   └── zebra/
│       └── ...
└── val/
    ├── lion/
    ├── elephant/
    └── ...
```

Each species folder should contain at least a few representative images. For best results, use 20+ images per species.

## Training

### Basic Training

```bash
python train.py \
    --train-dir data/train \
    --val-dir data/val \
    --species lion,elephant,zebra,giraffe \
    --epochs 30 \
    --batch-size 32
```

### Training with Custom Parameters

```bash
python train.py \
    --train-dir data/train \
    --val-dir data/val \
    --species lion,elephant,zebra,giraffe,leopard \
    --model resnet50 \
    --epochs 40 \
    --batch-size 64 \
    --learning-rate 0.0005 \
    --freeze-backbone \
    --unfreeze-at 10
```

### Command Line Arguments

#### Data Arguments

- `--train-dir`: Path to training data (default: `data/train`)
- `--val-dir`: Path to validation data (default: `data/val`)
- `--species`: Comma-separated species names (default: `lion,elephant,zebra,giraffe`)

#### Model Arguments

- `--model`: Base architecture - `resnet50` or `resnet101` (default: `resnet50`)
- `--freeze-backbone`: Freeze pretrained weights initially (recommended for small datasets)
- `--unfreeze-at`: Epoch to start fine-tuning all layers (default: `10`)

#### Training Arguments

- `--epochs`: Number of training epochs (default: `30`)
- `--batch-size`: Batch size (default: `32`)
- `--learning-rate`: Learning rate (default: `0.001`)
- `--weight-decay`: L2 regularization (default: `0.0001`)
- `--num-workers`: Data loading workers (default: `4`)
- `--cpu`: Force CPU usage (GPU used by default if available)

### Understanding Training

The pipeline uses **transfer learning** with a two-phase approach:

1. **Phase 1 (Frozen Backbone)**: Train only the classification head layers
   - Preserves learned features from ImageNet
   - Faster convergence
   - Recommended for small datasets (< 1000 images per class)

2. **Phase 2 (Fine-tuning)**: Unfreeze and train all layers
   - Adapts pretrained features to wildlife domain
   - Improves accuracy
   - Starts at epoch specified by `--unfreeze-at`

With early stopping, training will stop if validation loss doesn't improve for 5 consecutive epochs.

## Inference

### Single Image Prediction

```bash
python predict.py \
    --model-path models/wildlife_model_resnet50.pt \
    --species-map data/species_mapping.json \
    --image /path/to/image.jpg
```

### Batch Prediction on Directory

```bash
python predict.py \
    --model-path models/wildlife_model_resnet50.pt \
    --species-map data/species_mapping.json \
    --directory /path/to/images/ \
    --confidence-threshold 0.5
```

### Prediction Output Example

```
Predicted Species: lion
Confidence: 92.45%
Is Confident (>50%): True

Top 3 Predictions:
1. lion: 92.45%
2. leopard: 6.22%
3. tiger: 1.33%
```

### Command Line Arguments

#### Model Arguments

- `--model-path`: Path to trained model (required)
- `--species-map`: Path to species mapping JSON file (required)

#### Input Arguments (choose one)

- `--image`: Path to single image
- `--directory`: Path to directory with images

#### Prediction Arguments

- `--confidence-threshold`: Minimum confidence (0-1, default: 0.5)
- `--recursive`: Search subdirectories (default: True)

#### Other

- `--cpu`: Force CPU usage
- `--log-dir`: Directory for prediction logs (default: `data/predictions_log`)

## Python API Usage

### Training

```python
from src.data import DataLoader
from src.training import WildlifeModel, Trainer
import torch

# Create species mapping
species_list = ['lion', 'elephant', 'zebra', 'giraffe']
species_mapping = DataLoader.create_species_mapping(species_list)

# Load data
train_loader, val_loader = DataLoader.get_data_loaders(
    train_dir='data/train',
    val_dir='data/val',
    species_mapping=species_mapping,
    batch_size=32
)

# Create model and trainer
model = WildlifeModel(num_classes=len(species_mapping), model_name='resnet50')
trainer = Trainer(model, device='cuda')

# Train
history = trainer.fit(
    train_loader=train_loader,
    val_loader=val_loader,
    epochs=30,
    freeze_backbone=True,
    unfreeze_at_epoch=10
)

# Save
trainer.save_model('models/wildlife_model.pt')
```

### Inference

```python
from src.inference import Predictor
from src.training import WildlifeModel
import json

# Load species mapping
with open('data/species_mapping.json', 'r') as f:
    species_mapping = json.load(f)
    species_mapping = {int(k): v for k, v in species_mapping.items()}

# Create predictor
predictor = Predictor(
    model_path='models/wildlife_model.pt',
    species_mapping=species_mapping,
    confidence_threshold=0.5
)
predictor.load_model(WildlifeModel)

# Single prediction
result = predictor.predict_single('path/to/image.jpg')
print(f"Predicted: {result['predicted_species']} ({result['confidence']:.2%})")

# Batch prediction
results = predictor.predict_batch(['image1.jpg', 'image2.jpg', 'image3.jpg'])
stats = predictor.get_prediction_statistics(results)
print(f"Average confidence: {stats['average_confidence']:.2%}")
```

### Monitoring

```python
from src.monitoring import PredictionLogger, ModelMonitor, DataQualityChecker
import json

# Log predictions
logger = PredictionLogger(log_dir='data/predictions_log')
logger.log_prediction(prediction_result)

# Get statistics
stats = logger.get_session_statistics()
print(f"Total predictions: {stats['total_predictions']}")
print(f"Average confidence: {stats['average_confidence']:.2%}")

# Monitor model performance
monitor = ModelMonitor()
monitor.record_metrics({'accuracy': 0.92, 'loss': 0.15})

# Check for drift
drift = monitor.detect_performance_drift(threshold=0.05)
if drift['drift_detected']:
    print("⚠️ Performance drift detected - consider retraining")

# Data quality check
quality = DataQualityChecker.check_dataset_balance(species_counts)
if not quality['is_balanced']:
    print(f"⚠️ Imbalanced dataset - ratio {quality['imbalance_ratio']:.1f}:1")
```

## Integration with Backend

The ML pipeline integrates with the Spring Boot backend through:

### API Endpoints

**Predictions Endpoint**: `POST /api/predictions`

- Receives image data
- Returns `prediction_id`, `predicted_species`, `confidence`
- Logged to database

**Predictions Stats**: `GET /api/predictions/stats`

- Returns `average_confidence` across all predictions

### Workflow

1. Frontend uploads image to backend
2. Backend stores image temporarily
3. Backend calls inference pipeline
4. Pipeline returns prediction
5. Backend stores in database
6. Frontend displays result

Example:

```python
# Backend calls inference
predictor = Predictor(model_path='wildlife_model.pt', ...)
result = predictor.predict_single(image_path)

# Store in database
prediction = Prediction(
    species_id=...,
    image_path=result['image_path'],
    predicted_species=result['predicted_species'],
    confidence=result['confidence']
)
```

## Best Practices

### Data Preparation

1. **Image Diversity**: Use varied angles, lighting, and backgrounds
2. **Data Balance**: Aim for similar number of images per species
3. **Image Quality**: Clear, focused wildlife images work best
4. **Minimum Data**: At least 20-30 images per species
5. **Validation Split**: Use 80/20 or 70/30 train/val split

### Training

1. **Start with Frozen Backbone**: Enables faster training with less data
2. **Monitor Validation Loss**: Use early stopping to prevent overfitting
3. **Adjust Learning Rate**: Lower rates (1e-4) for fine-tuning
4. **Batch Size**: 32 works for most cases, increase if GPU memory allows
5. **Check Metrics**: Review training history to ensure convergence

### Inference

1. **Confidence Thresholds**: Use 0.5-0.7 for reliable predictions
2. **Batch Processing**: Faster than single image predictions
3. **Logging**: Always log predictions for monitoring
4. **Error Handling**: Handle corrupted images gracefully

## Troubleshooting

### GPU Not Detected

```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# Force CPU mode
python train.py --cpu
```

### Out of Memory Errors

- Reduce batch size: `--batch-size 16`
- Use CPU mode: `--cpu`
- Use smaller model: `--model resnet50` (vs resnet101)

### Poor Training Accuracy

- More training data needed
- Longer training: `--epochs 50`
- Lower learning rate: `--learning-rate 0.0001`
- Check data quality and balance

### Slow Inference

- Use GPU: Remove `--cpu` flag
- Batch predictions: Use `--directory` instead of single `--image`
- Reduce image resolution in loader.py

## Performance Metrics

Typical performance with 500+ images per species:

- **Training Time**: 2-5 hours on GPU (ResNet50, 30 epochs)
- **Inference Time**: 20-50ms per image on GPU
- **Accuracy**: 85-95% with well-curated data
- **Model Size**: ~100 MB for ResNet50

## Next Steps

1. Prepare your wildlife image dataset
2. Run training: `python train.py --species lion,elephant,zebra`
3. Evaluate results in training output
4. Adjust parameters and retrain if needed
5. Deploy trained model with backend for live predictions
6. Monitor predictions and collect new data for periodic retraining
