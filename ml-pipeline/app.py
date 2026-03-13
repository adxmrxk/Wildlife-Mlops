"""FastAPI ML service for wildlife species prediction."""

import os
import json
import tempfile
import time
import threading
import subprocess
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
from src.inference.predictor import Predictor
from src.training.trainer import WildlifeModel

# Prometheus metrics
PREDICTIONS_TOTAL = Counter(
    'wildlife_predictions_total',
    'Total wildlife predictions made',
    ['species', 'is_confident']
)
PREDICTION_CONFIDENCE = Histogram(
    'wildlife_prediction_confidence_score',
    'Distribution of prediction confidence scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
MODEL_LOADED_GAUGE = Gauge(
    'wildlife_model_loaded',
    'Whether the ML model is loaded (1=yes, 0=no)'
)
LOW_CONFIDENCE_TOTAL = Counter(
    'wildlife_low_confidence_predictions_total',
    'Predictions below confidence threshold (model drift indicator)'
)


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
    heatmap_base64: Optional[str] = None


# ─── Training job tracker ──────────────────────────────────────────────────
training_jobs: dict = {}  # job_id -> { status, started_at, completed_at, error }


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

# Set up Prometheus instrumentation — exposes /metrics endpoint
Instrumentator().instrument(app).expose(app)

# Global predictor instance
predictor: Optional[Predictor] = None
start_time = time.time()


@app.on_event("startup")
async def load_model():
    """Load the model on application startup."""
    global predictor

    MODEL_LOADED_GAUGE.set(0)
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
        MODEL_LOADED_GAUGE.set(1)
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
async def predict(image: UploadFile = File(...), gradcam: bool = Query(default=False)):
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

        # Record Prometheus metrics
        PREDICTIONS_TOTAL.labels(
            species=result['predicted_species'],
            is_confident=str(result['is_confident'])
        ).inc()
        PREDICTION_CONFIDENCE.observe(result['confidence'])
        if not result['is_confident']:
            LOW_CONFIDENCE_TOTAL.inc()

        # Optionally generate GradCAM heatmap
        heatmap_b64 = None
        if gradcam:
            try:
                predicted_idx = list(predictor.species_mapping.keys())[
                    list(predictor.species_mapping.values()).index(result['predicted_species'])
                ]
                heatmap_b64 = predictor.generate_gradcam(temp_file_path, predicted_idx)
            except Exception as e:
                print(f"GradCAM failed (non-fatal): {e}")

        response = {
            "predicted_species": result['predicted_species'],
            "confidence": result['confidence'],
            "is_confident": result['is_confident'],
            "top_predictions": result['top_predictions'],
            "model_version": MODEL_VERSION,
            "timestamp": result['timestamp'],
            "heatmap_base64": heatmap_b64
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


@app.post("/reload")
async def reload_model_endpoint():
    """Hot-reload the ML model from disk without restarting the service."""
    global predictor

    try:
        MODEL_LOADED_GAUGE.set(0)

        with open(SPECIES_MAPPING_PATH, 'r') as f:
            species_mapping_raw = json.load(f)
        species_mapping = {int(k): v for k, v in species_mapping_raw.items()}

        new_predictor = Predictor(
            model_path=MODEL_PATH,
            species_mapping=species_mapping,
            device='cpu',
            confidence_threshold=CONFIDENCE_THRESHOLD
        )
        new_predictor.load_model(WildlifeModel)

        predictor = new_predictor
        MODEL_LOADED_GAUGE.set(1)
        print(f"✓ Model hot-reloaded successfully")

        return {"status": "reloaded", "model_version": MODEL_VERSION, "timestamp": time.time()}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model reload failed: {str(e)}")


@app.post("/train")
async def trigger_training(epochs: int = 10):
    """
    Kick off model retraining in a background thread.
    Returns a job_id — poll /train/status/{job_id} for completion.
    """
    job_id = str(uuid.uuid4())[:8]
    training_jobs[job_id] = {"status": "RUNNING", "started_at": time.time()}

    def run():
        try:
            result = subprocess.run(
                ["python", "train.py", "--epochs", str(epochs), "--cpu"],
                capture_output=True, text=True, timeout=7200,
                env={**os.environ, "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001")}
            )
            if result.returncode == 0:
                training_jobs[job_id]["status"] = "SUCCESS"
            else:
                training_jobs[job_id]["status"] = "FAILED"
                training_jobs[job_id]["error"] = result.stderr[-500:]
        except Exception as e:
            training_jobs[job_id]["status"] = "FAILED"
            training_jobs[job_id]["error"] = str(e)
        training_jobs[job_id]["completed_at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status": "RUNNING"}


@app.get("/train/status/{job_id}")
async def training_status(job_id: str):
    """Check the status of a training job."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return training_jobs[job_id]


@app.get("/evaluate")
async def evaluate_model():
    """
    Compare the latest trained model vs the previous one using MLflow metrics.
    Returns whether the new model should be promoted.
    """
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
        client = mlflow.tracking.MlflowClient()

        experiment = client.get_experiment_by_name("wildlife-classification")
        if not experiment:
            return {"can_promote": True, "reason": "no_previous_experiments"}

        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=2
        )

        if len(runs) < 2:
            return {"can_promote": True, "reason": "first_training_run", "latest_accuracy": runs[0].data.metrics.get("best_val_acc", 0) if runs else 0}

        latest_acc = runs[0].data.metrics.get("best_val_acc", 0)
        previous_acc = runs[1].data.metrics.get("best_val_acc", 0)
        improvement = latest_acc - previous_acc

        return {
            "can_promote": latest_acc > previous_acc,
            "latest_accuracy": round(latest_acc, 4),
            "previous_accuracy": round(previous_acc, 4),
            "improvement": round(improvement, 4),
            "reason": "accuracy_improved" if latest_acc > previous_acc else "accuracy_did_not_improve"
        }
    except Exception as e:
        return {"error": str(e), "can_promote": False}


@app.post("/promote")
async def promote_model():
    """Promote the latest trained model to production by hot-reloading it."""
    return await reload_model_endpoint()


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
