"""
Auto-retrain daemon for Wildlife MLOps Platform.

Watches Prometheus metrics and automatically retrains the model
when average prediction confidence drops below the threshold.
"""

import os
import time
import subprocess
import requests
from datetime import datetime

# Configuration from environment variables
PROMETHEUS_URL      = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
ML_SERVICE_URL      = os.getenv('ML_SERVICE_URL', 'http://localhost:8000')
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5001')
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.70'))
CHECK_INTERVAL      = int(os.getenv('CHECK_INTERVAL_MINUTES', '60')) * 60
MIN_PREDICTIONS     = int(os.getenv('MIN_PREDICTIONS_FOR_CHECK', '10'))


def get_average_confidence():
    """Query Prometheus for average prediction confidence over the last hour."""
    query = (
        'sum(rate(wildlife_prediction_confidence_score_sum[1h])) / '
        'sum(rate(wildlife_prediction_confidence_score_count[1h]))'
    )
    try:
        response = requests.get(
            f'{PROMETHEUS_URL}/api/v1/query',
            params={'query': query},
            timeout=10
        )
        data = response.json()
        if data['status'] == 'success' and data['data']['result']:
            return float(data['data']['result'][0]['value'][1])
        return None
    except Exception as e:
        print(f"  Failed to query Prometheus: {e}")
        return None


def get_total_predictions():
    """Get total prediction count from Prometheus."""
    try:
        response = requests.get(
            f'{PROMETHEUS_URL}/api/v1/query',
            params={'query': 'sum(wildlife_predictions_total)'},
            timeout=10
        )
        data = response.json()
        if data['status'] == 'success' and data['data']['result']:
            return int(float(data['data']['result'][0]['value'][1]))
        return 0
    except Exception as e:
        print(f"  Failed to query Prometheus: {e}")
        return 0


def trigger_retrain():
    """Run train.py as a subprocess."""
    print(f"  Starting training...")
    try:
        result = subprocess.run(
            ['python', 'train.py', '--epochs', '10', '--cpu'],
            capture_output=True,
            text=True,
            timeout=3600,
            env={**os.environ, 'MLFLOW_TRACKING_URI': MLFLOW_TRACKING_URI}
        )
        if result.returncode == 0:
            print(f"  Training completed successfully")
            return True
        else:
            print(f"  Training failed:\n{result.stderr[-1000:]}")
            return False
    except subprocess.TimeoutExpired:
        print("  Training timed out after 1 hour")
        return False
    except Exception as e:
        print(f"  Training error: {e}")
        return False


def evaluate_new_model():
    """
    Compare the latest trained model vs the previous one in MLflow.
    Returns True if the new model is better and should be promoted.
    """
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        client = mlflow.tracking.MlflowClient()

        experiment = client.get_experiment_by_name('wildlife-classification')
        if not experiment:
            print("  No MLflow experiments found — promoting by default")
            return True

        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=['start_time DESC'],
            max_results=2
        )

        if len(runs) < 2:
            print("  First training run — promoting by default")
            return True

        latest_acc   = runs[0].data.metrics.get('best_val_acc', 0)
        previous_acc = runs[1].data.metrics.get('best_val_acc', 0)

        print(f"  New model accuracy:      {latest_acc:.4f}")
        print(f"  Previous model accuracy: {previous_acc:.4f}")

        if latest_acc > previous_acc:
            print(f"  ✓ New model is better (+{latest_acc - previous_acc:.4f}) — promoting")
            return True
        else:
            print(f"  ✗ New model did not improve — keeping current model")
            return False

    except Exception as e:
        print(f"  Evaluation error: {e} — promoting by default")
        return True


def reload_ml_service():
    """Tell the ML service to hot-reload the new model."""
    try:
        response = requests.post(f'{ML_SERVICE_URL}/reload', timeout=60)
        if response.status_code == 200:
            print(f"  ML service reloaded successfully")
            return True
        else:
            print(f"  Reload failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  Reload error: {e}")
        return False


def main():
    print("=" * 60)
    print("Wildlife MLOps - Auto-Retrain Daemon")
    print("=" * 60)
    print(f"Prometheus:           {PROMETHEUS_URL}")
    print(f"ML Service:           {ML_SERVICE_URL}")
    print(f"MLflow:               {MLFLOW_TRACKING_URI}")
    print(f"Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"Check interval:       {CHECK_INTERVAL // 60} minutes")
    print(f"Min predictions:      {MIN_PREDICTIONS}")
    print("=" * 60)

    last_retrain = None

    while True:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n[{now}] Checking model performance...")

        avg_confidence   = get_average_confidence()
        total_predictions = get_total_predictions()

        print(f"  Total predictions:  {total_predictions}")
        if avg_confidence is not None:
            print(f"  Avg confidence:     {avg_confidence:.3f}")
        else:
            print(f"  Avg confidence:     N/A (no data yet)")

        # Only act if we have enough predictions to make a judgement
        if total_predictions >= MIN_PREDICTIONS and avg_confidence is not None:
            if avg_confidence < CONFIDENCE_THRESHOLD:
                print(f"  ⚠ Confidence {avg_confidence:.3f} below threshold {CONFIDENCE_THRESHOLD} — retraining!")
                success = trigger_retrain()
                if success:
                    last_retrain = datetime.now()
                    print(f"  Evaluating new model vs current...")
                    should_promote = evaluate_new_model()
                    if should_promote:
                        reload_ml_service()
                        print(f"  ✓ New model promoted and live")
                    else:
                        print(f"  ✓ Training done — kept current model (new model wasn't better)")
                else:
                    print(f"  ✗ Retrain failed — will retry next cycle")
            else:
                print(f"  ✓ Confidence OK ({avg_confidence:.3f} >= {CONFIDENCE_THRESHOLD})")
        else:
            if total_predictions < MIN_PREDICTIONS:
                print(f"  Waiting for more predictions ({total_predictions}/{MIN_PREDICTIONS} required)")

        if last_retrain:
            print(f"  Last retrain: {last_retrain.strftime('%Y-%m-%d %H:%M:%S')}")

        print(f"  Next check in {CHECK_INTERVAL // 60} minutes...")
        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
