"""FastAPI ML service for wildlife species prediction."""

import os
import json
import tempfile
import time
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.inference.predictor import Predictor
from src.training.trainer import WildlifeModel


# Configuration from environment variables
MODEL_PATH = os.getenv('MODEL_PATH', 'models/wildlife_model_resnet50.pt')
SPECIES_MAPPING_PATH = os.getenv('SPECIES_MAPPING_PATH', 'data/species_mapping.json')
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.5'))
MODEL_VERSION = os.getenv('MODEL_VERSION', 'resnet50_v1')


# Response models
class TopPrediction(BaseModel):
    species: str
    confidence: float


class PredictionResponse(BaseModel):
    predicted_species: str
    confidence: float
    is_confident: bool
    top_predictions: list[TopPrediction]
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    species_count: int
    uptime_seconds: float


# Initialize FastAPI app
app = FastAPI(
    title="Wildlife MLOps - Prediction Service",
    description="ML service for wildlife species classification",
    version="1.0.0"
)

# Enable CORS for backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global predictor instance
predictor: Optional[Predictor] = None
start_time = time.time()


@app.on_event("startup")
async def load_model():
    """Load the model on application startup."""
    global predictor

    try:
        # Load species mapping
        print(f"Loading species mapping from: {SPECIES_MAPPING_PATH}")
        with open(SPECIES_MAPPING_PATH, 'r') as f:
            species_mapping_raw = json.load(f)

        # Convert string keys to integers
        species_mapping = {int(k): v for k, v in species_mapping_raw.items()}
        print(f"Loaded {len(species_mapping)} species: {list(species_mapping.values())}")

        # Initialize predictor
        print(f"Initializing predictor with model: {MODEL_PATH}")
        predictor = Predictor(
            model_path=MODEL_PATH,
            species_mapping=species_mapping,
            device='cpu',  # Use CPU for development (change to 'cuda' for GPU)
            confidence_threshold=CONFIDENCE_THRESHOLD
        )

        # Load model weights
        predictor.load_model(WildlifeModel)
        print(f"✓ Model loaded successfully")
        print(f"✓ Model version: {MODEL_VERSION}")
        print(f"✓ Confidence threshold: {CONFIDENCE_THRESHOLD}")

    except FileNotFoundError as e:
        print(f"ERROR: Required file not found: {e}")
        print("Please run 'python create_dummy_model.py' first to generate the dummy model")
        raise
    except Exception as e:
        print(f"ERROR: Failed to load model: {e}")
        raise


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify service is running."""
    return {
        "status": "healthy" if predictor and predictor.is_loaded else "unhealthy",
        "model_loaded": predictor is not None and predictor.is_loaded,
        "model_version": MODEL_VERSION,
        "species_count": len(predictor.species_mapping) if predictor else 0,
        "uptime_seconds": time.time() - start_time
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(image: UploadFile = File(...)):
    """
    Predict wildlife species from uploaded image.

    Args:
        image: Uploaded image file (jpg, jpeg, png)

    Returns:
        PredictionResponse with species, confidence, and top predictions
    """
    # Validate predictor is loaded
    if not predictor or not predictor.is_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service is starting up or failed to initialize."
        )

    # Validate file type
    if not image.content_type or not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {image.content_type}. Must be an image (jpg, jpeg, png)."
        )

    # Save uploaded file temporarily
    temp_file = None
    try:
        # Create temporary file with proper extension
        suffix = Path(image.filename).suffix if image.filename else '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await image.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Run prediction
        result = predictor.predict_single(temp_file_path)

        # Add model version to response
        response = {
            "predicted_species": result['predicted_species'],
            "confidence": result['confidence'],
            "is_confident": result['is_confident'],
            "top_predictions": result['top_predictions'],
            "model_version": MODEL_VERSION,
            "timestamp": result['timestamp']
        }

        return response

    except Exception as e:
        # Clean up temp file on error
        if temp_file and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        # Handle specific errors
        if "cannot identify image file" in str(e).lower() or "corrupted" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupted image file: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Model inference failed: {str(e)}"
            )

    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Wildlife MLOps - Prediction Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "GET /health",
            "predict": "POST /predict"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SERVER_PORT', '8000'))
    uvicorn.run(app, host="0.0.0.0", port=port)
