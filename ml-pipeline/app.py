"""FastAPI ML service for wildlife species prediction."""

import os
import json
import tempfile
import time
import threading
import subprocess
import uuid
from datetime import datetime
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
CALIBRATION_PATH = os.getenv(
    'CALIBRATION_PATH', str(Path(MODEL_PATH).parent / 'calibration.json')
)


def load_temperature() -> float:
    """
    Read the temperature-scaling factor produced by calibrate.py.

    Falls back to 1.0 (raw, uncalibrated softmax) when no calibration file
    exists, so an uncalibrated model still serves normally.
    """
    try:
        with open(CALIBRATION_PATH) as f:
            t = float(json.load(f).get('temperature', 1.0))
        if t > 0:
            print(f"✓ Calibration loaded: T = {t:.4f} (from {CALIBRATION_PATH})")
            return t
        print(f"! Ignoring non-positive temperature in {CALIBRATION_PATH}")
    except FileNotFoundError:
        print(f"! No calibration file at {CALIBRATION_PATH} — using raw softmax "
              f"(run calibrate.py to fix over-confidence)")
    except Exception as e:
        print(f"! Could not read {CALIBRATION_PATH}: {e} — using raw softmax")
    return 1.0


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
# Persisted to disk: a training run lasts 25 minutes to several hours, and an
# in-memory dict loses every in-flight job on restart, crash or OOM kill. The
# Airflow DAG then polls a job id that no longer exists and fails with a 404
# even though nothing was wrong with the training itself.
JOBS_PATH = os.getenv('JOBS_PATH', str(Path(MODEL_PATH).parent / 'training_jobs.json'))
training_jobs: dict = {}  # job_id -> { status, started_at, completed_at, error }


def _load_jobs() -> dict:
    """Restore the job registry written by a previous process."""
    try:
        with open(JOBS_PATH) as f:
            jobs = json.load(f)
        # A job still marked RUNNING cannot survive its process: the training
        # subprocess died with it. Mark it INTERRUPTED so callers can tell the
        # difference between "training failed" and "the service restarted".
        for job_id, job in jobs.items():
            if job.get('status') == 'RUNNING':
                job['status'] = 'INTERRUPTED'
                job['error'] = 'ML service restarted while this job was running'
                job['completed_at'] = time.time()
        if jobs:
            print(f"✓ Restored {len(jobs)} training job(s) from {JOBS_PATH}")
        return jobs
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"! Could not read {JOBS_PATH}: {e}")
        return {}


def _save_jobs() -> None:
    """Write the job registry atomically so a crash can't truncate it."""
    try:
        Path(JOBS_PATH).parent.mkdir(parents=True, exist_ok=True)
        tmp = f"{JOBS_PATH}.tmp"
        with open(tmp, 'w') as f:
            json.dump(training_jobs, f, indent=2)
        os.replace(tmp, JOBS_PATH)
    except Exception as e:
        print(f"! Could not persist training jobs: {e}")


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str
    species_count: int
    uptime_seconds: float
    temperature: float = 1.0
    calibrated: bool = False


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
    global predictor, training_jobs

    training_jobs = _load_jobs()

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
            confidence_threshold=CONFIDENCE_THRESHOLD,
            temperature=load_temperature()
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
        "uptime_seconds": time.time() - start_time,
        "temperature": predictor.temperature if predictor else 1.0,
        "calibrated": bool(predictor and predictor.temperature != 1.0)
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
            confidence_threshold=CONFIDENCE_THRESHOLD,
            temperature=load_temperature()
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
    training_jobs[job_id] = {"status": "RUNNING", "started_at": time.time(), "epochs": epochs}
    _save_jobs()

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
        _save_jobs()

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
    """
    Promote the latest trained candidate to production, then hot-reload it.

    train.py writes new weights to a candidate file rather than overwriting the
    live model, so a failed or worse training run can never take production
    down. Promotion is the step that makes a candidate live. The outgoing model
    is kept as <MODEL_PATH>.previous so a bad promotion can be rolled back.
    """
    import shutil

    candidate = os.getenv(
        'CANDIDATE_MODEL_PATH',
        str(Path(MODEL_PATH).parent / f"candidate_{Path(MODEL_PATH).name}")
    )

    promoted_from = None
    if os.path.exists(candidate):
        try:
            if os.path.exists(MODEL_PATH):
                shutil.copyfile(MODEL_PATH, f"{MODEL_PATH}.previous")
            shutil.copyfile(candidate, MODEL_PATH)
            promoted_from = candidate
            print(f"✓ Promoted candidate {candidate} -> {MODEL_PATH}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Promotion failed: {str(e)}")
    else:
        print(f"No candidate at {candidate} — reloading current live model")

    result = await reload_model_endpoint()
    result["promoted_from"] = promoted_from
    return result


# ─── Model version management ──────────────────────────────────────────────
def _model_file_info(path: str) -> Optional[dict]:
    """Describe a model file on disk, or None if it isn't there."""
    p = Path(path)
    if not p.is_file():
        return None
    stat = p.stat()
    return {
        "path": str(p),
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
    }


@app.get("/models/versions")
async def list_model_versions():
    """
    Show every model file this service can serve — the live model, the
    rollback target, and any candidate waiting for promotion — alongside the
    versions recorded in the MLflow Model Registry.
    """
    candidate = os.getenv(
        'CANDIDATE_MODEL_PATH',
        str(Path(MODEL_PATH).parent / f"candidate_{Path(MODEL_PATH).name}")
    )

    local = {
        "live": _model_file_info(MODEL_PATH),
        "previous": _model_file_info(f"{MODEL_PATH}.previous"),
        "candidate": _model_file_info(candidate),
    }

    registry = []
    registry_error = None
    try:
        import mlflow
        mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5001"))
        client = mlflow.tracking.MlflowClient()
        for mv in client.search_model_versions("name='wildlife-classifier'"):
            registry.append({
                "version": mv.version,
                "run_id": mv.run_id,
                "status": mv.status,
                "created": datetime.fromtimestamp(mv.creation_timestamp / 1000).isoformat(),
            })
        registry.sort(key=lambda v: int(v["version"]), reverse=True)
    except Exception as e:
        registry_error = str(e)

    return {
        "model_version": MODEL_VERSION,
        "model_loaded": bool(predictor and predictor.is_loaded),
        "local_files": local,
        "can_rollback": local["previous"] is not None,
        "can_promote": local["candidate"] is not None,
        "registry": registry,
        "registry_error": registry_error,
    }


@app.post("/models/rollback")
async def rollback_model():
    """
    Roll back to the previously live model and hot-reload it.

    /promote saves the outgoing model as <MODEL_PATH>.previous; this swaps it
    back. The two files are exchanged, so a rollback can itself be undone.
    """
    import shutil

    previous = f"{MODEL_PATH}.previous"
    if not os.path.exists(previous):
        raise HTTPException(
            status_code=404,
            detail="No previous model to roll back to. Promote a model first."
        )

    try:
        # Swap live <-> previous so rollback is reversible.
        swap = f"{MODEL_PATH}.swap"
        shutil.copyfile(MODEL_PATH, swap)
        shutil.copyfile(previous, MODEL_PATH)
        shutil.move(swap, previous)
        print(f"✓ Rolled back {MODEL_PATH} to its previous weights")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {str(e)}")

    result = await reload_model_endpoint()
    result["rolled_back"] = True
    return result


# ─── Model evaluation report ───────────────────────────────────────────────
evaluation_jobs: dict = {}  # job_id -> { status, started_at, completed_at, report, error }

VAL_DIR = os.getenv('VAL_DIR', 'data/val')


def _score_validation_set(samples_per_class: int) -> dict:
    """
    Run the live model over the validation set and build a full
    classification report: confusion matrix plus per-class precision,
    recall and F1. Pure inference — no training, no weight changes.
    """
    valid_ext = {'.jpg', '.jpeg', '.png', '.bmp'}
    classes = [predictor.species_mapping[i] for i in sorted(predictor.species_mapping)]
    index_of = {name: i for i, name in enumerate(classes)}
    n = len(classes)

    # matrix[actual][predicted]
    matrix = [[0] * n for _ in range(n)]
    confidences: list[float] = []
    skipped = 0

    for actual in classes:
        class_dir = Path(VAL_DIR) / actual
        if not class_dir.is_dir():
            continue
        files = sorted(f for f in class_dir.iterdir()
                       if f.is_file() and f.suffix.lower() in valid_ext)
        if samples_per_class > 0:
            files = files[:samples_per_class]
        for f in files:
            try:
                r = predictor.predict_single(str(f))
            except Exception:
                skipped += 1
                continue
            matrix[index_of[actual]][index_of[r['predicted_species']]] += 1
            confidences.append(r['confidence'])

    # Per-class precision / recall / F1 from the matrix
    per_class = {}
    total = correct = 0
    for i, name in enumerate(classes):
        tp = matrix[i][i]
        actual_total = sum(matrix[i])          # row = true occurrences
        predicted_total = sum(row[i] for row in matrix)  # column = times predicted
        precision = tp / predicted_total if predicted_total else 0.0
        recall = tp / actual_total if actual_total else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[name] = {
            "support": actual_total,
            "correct": tp,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
        correct += tp
        total += actual_total

    # Macro averages weight every class equally — the honest number when the
    # dataset is imbalanced (dog has 973 val images, elephant 290).
    macro = {
        k: round(sum(c[k] for c in per_class.values()) / len(per_class), 4)
        for k in ("precision", "recall", "f1")
    } if per_class else {}

    sorted_by_f1 = sorted(per_class.items(), key=lambda kv: kv[1]["f1"])

    return {
        "model_version": MODEL_VERSION,
        "model_path": MODEL_PATH,
        "evaluated_at": datetime.now().isoformat(),
        "samples_per_class": samples_per_class if samples_per_class > 0 else "all",
        "images_scored": total,
        "images_skipped": skipped,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "macro_avg": macro,
        "mean_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
        "classes": classes,
        "confusion_matrix": matrix,
        "per_class": per_class,
        "weakest_classes": [name for name, _ in sorted_by_f1[:3]],
        "strongest_classes": [name for name, _ in reversed(sorted_by_f1[-3:])],
    }


@app.post("/evaluate/report")
async def start_evaluation_report(samples_per_class: int = Query(default=20, ge=0, le=1000)):
    """
    Score the live model against the validation set in the background.

    samples_per_class=0 scores every image (slow on CPU). Returns a job_id —
    poll /evaluate/report/{job_id} for the finished report.
    """
    if not predictor or not predictor.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if not Path(VAL_DIR).is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Validation directory '{VAL_DIR}' not found in the container."
        )

    job_id = str(uuid.uuid4())[:8]
    evaluation_jobs[job_id] = {"status": "RUNNING", "started_at": time.time()}

    def run():
        try:
            report = _score_validation_set(samples_per_class)
            evaluation_jobs[job_id].update(status="SUCCESS", report=report)
        except Exception as e:
            evaluation_jobs[job_id].update(status="FAILED", error=str(e))
        evaluation_jobs[job_id]["completed_at"] = time.time()

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "status": "RUNNING", "samples_per_class": samples_per_class}


@app.get("/evaluate/report/{job_id}")
async def get_evaluation_report(job_id: str):
    """Fetch an evaluation job's status and, once finished, its report."""
    if job_id not in evaluation_jobs:
        raise HTTPException(status_code=404, detail="Evaluation job not found")
    return evaluation_jobs[job_id]


@app.get("/evaluate/report")
async def latest_evaluation_report():
    """Return the most recent completed evaluation report."""
    done = [j for j in evaluation_jobs.values() if j.get("status") == "SUCCESS"]
    if not done:
        return {"status": "NO_REPORT", "detail": "Run POST /evaluate/report first."}
    return max(done, key=lambda j: j.get("completed_at", 0))


# ─── Batch prediction ──────────────────────────────────────────────────────
@app.post("/predict/batch")
async def predict_batch(images: list[UploadFile] = File(...)):
    """
    Classify several images in one request.

    Returns a per-image result plus aggregate statistics, so a caller can
    score a whole folder without issuing one request per file.
    """
    if not predictor or not predictor.is_loaded:
        raise HTTPException(status_code=503, detail="Model not loaded.")
    if not images:
        raise HTTPException(status_code=400, detail="No images supplied.")
    if len(images) > 100:
        raise HTTPException(status_code=413, detail="Maximum 100 images per batch.")

    results = []
    temp_paths = []
    try:
        for image in images:
            if not image.content_type or not image.content_type.startswith('image/'):
                results.append({"filename": image.filename, "error": "not an image"})
                continue
            suffix = Path(image.filename).suffix if image.filename else '.jpg'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await image.read())
                temp_paths.append(tmp.name)
            try:
                r = predictor.predict_single(temp_paths[-1])
                PREDICTIONS_TOTAL.labels(
                    species=r['predicted_species'],
                    is_confident=str(r['is_confident'])
                ).inc()
                PREDICTION_CONFIDENCE.observe(r['confidence'])
                if not r['is_confident']:
                    LOW_CONFIDENCE_TOTAL.inc()
                results.append({
                    "filename": image.filename,
                    "predicted_species": r['predicted_species'],
                    "confidence": r['confidence'],
                    "is_confident": r['is_confident'],
                    "top_predictions": r['top_predictions'],
                })
            except Exception as e:
                results.append({"filename": image.filename, "error": str(e)})

        ok = [r for r in results if "error" not in r]
        distribution: dict = {}
        for r in ok:
            distribution[r['predicted_species']] = distribution.get(r['predicted_species'], 0) + 1

        return {
            "count": len(results),
            "succeeded": len(ok),
            "failed": len(results) - len(ok),
            "mean_confidence": round(sum(r['confidence'] for r in ok) / len(ok), 4) if ok else 0.0,
            "low_confidence_count": sum(1 for r in ok if not r['is_confident']),
            "species_distribution": distribution,
            "model_version": MODEL_VERSION,
            "results": results,
        }
    finally:
        for p in temp_paths:
            try:
                os.unlink(p)
            except OSError:
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
            "predict": "POST /predict",
            "predict_batch": "POST /predict/batch",
            "evaluation_report": "POST /evaluate/report",
            "model_versions": "GET /models/versions",
            "rollback": "POST /models/rollback"
        }
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SERVER_PORT', '8000'))
    uvicorn.run(app, host="0.0.0.0", port=port)
