"""
Wildlife MLOps - Model Training & Promotion Pipeline DAG

Orchestrates the full ML lifecycle:
  1. Verify the ML service is healthy
  2. Trigger model retraining
  3. Poll until training completes
  4. Evaluate: compare new model accuracy vs previous model
  5. Promote the new model if accuracy improved
  6. Reload the ML service to serve the new model

Trigger this DAG manually from the Airflow UI (http://localhost:8082)
or schedule it on a cron expression by setting `schedule`.
"""

import time
import requests
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator

ML_SERVICE = "http://ml-service:8000"
TRAINING_TIMEOUT = 7200   # 2 hours
POLL_INTERVAL   = 30      # seconds between status checks

default_args = {
    "owner": "wildlife-mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def check_ml_service_health(**ctx):
    """Fail fast if the ML service is not up."""
    resp = requests.get(f"{ML_SERVICE}/health", timeout=10)
    resp.raise_for_status()
    health = resp.json()
    if not health.get("model_loaded"):
        raise ValueError("ML service is up but model is not loaded — aborting pipeline")
    print(f"ML service healthy — model version: {health.get('model_version')}, "
          f"species: {health.get('species_count')}")


def trigger_training(**ctx):
    """Start async training and push the job_id to XCom."""
    resp = requests.post(f"{ML_SERVICE}/train", params={"epochs": 10}, timeout=15)
    resp.raise_for_status()
    job = resp.json()
    print(f"Training job started: {job['job_id']}")
    ctx["ti"].xcom_push(key="job_id", value=job["job_id"])


def wait_for_training(**ctx):
    """Poll /train/status until the job finishes or times out."""
    job_id = ctx["ti"].xcom_pull(key="job_id", task_ids="trigger_training")
    deadline = time.time() + TRAINING_TIMEOUT

    while time.time() < deadline:
        resp = requests.get(f"{ML_SERVICE}/train/status/{job_id}", timeout=10)
        resp.raise_for_status()
        status = resp.json()

        print(f"Training status: {status['status']}")

        if status["status"] == "SUCCESS":
            elapsed = time.time() - status.get("started_at", time.time())
            print(f"Training completed in {elapsed:.0f}s")
            return

        if status["status"] == "FAILED":
            raise RuntimeError(f"Training failed: {status.get('error', 'unknown error')}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Training did not complete within {TRAINING_TIMEOUT}s")


def evaluate_model(**ctx):
    """
    Compare new model accuracy vs previous model via MLflow metrics.
    Push the evaluation result to XCom for the branching decision.
    """
    resp = requests.get(f"{ML_SERVICE}/evaluate", timeout=15)
    resp.raise_for_status()
    evaluation = resp.json()

    print(f"Evaluation result: {evaluation}")
    ctx["ti"].xcom_push(key="evaluation", value=evaluation)

    if "error" in evaluation:
        print(f"Evaluation error: {evaluation['error']} — defaulting to promote")

    return evaluation


def branch_on_evaluation(**ctx):
    """Route to promote or skip based on evaluation."""
    evaluation = ctx["ti"].xcom_pull(key="evaluation", task_ids="evaluate_model")
    can_promote = evaluation.get("can_promote", True)

    print(f"Can promote: {can_promote} — reason: {evaluation.get('reason', 'unknown')}")
    return "promote_model" if can_promote else "skip_promotion"


def promote_model(**ctx):
    """Promote the new model by calling /promote (which hot-reloads the ML service)."""
    evaluation = ctx["ti"].xcom_pull(key="evaluation", task_ids="evaluate_model")
    improvement = evaluation.get("improvement", 0)

    resp = requests.post(f"{ML_SERVICE}/promote", timeout=60)
    resp.raise_for_status()

    print(f"Model promoted successfully!")
    if improvement:
        print(f"Accuracy improvement: +{improvement:.4f} ({improvement * 100:.2f}%)")


with DAG(
    dag_id="wildlife_ml_pipeline",
    default_args=default_args,
    description="Train, evaluate, and promote wildlife classification model",
    schedule=None,          # Manual trigger — set to e.g. '0 2 * * 0' for weekly
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["mlops", "wildlife", "training"],
) as dag:

    health_check = PythonOperator(
        task_id="check_ml_service",
        python_callable=check_ml_service_health,
    )

    start_training = PythonOperator(
        task_id="trigger_training",
        python_callable=trigger_training,
    )

    wait_training = PythonOperator(
        task_id="wait_for_training",
        python_callable=wait_for_training,
    )

    run_evaluation = PythonOperator(
        task_id="evaluate_model",
        python_callable=evaluate_model,
    )

    branch = BranchPythonOperator(
        task_id="branch_on_evaluation",
        python_callable=branch_on_evaluation,
    )

    promote = PythonOperator(
        task_id="promote_model",
        python_callable=promote_model,
    )

    skip = EmptyOperator(task_id="skip_promotion")

    done = EmptyOperator(
        task_id="pipeline_complete",
        trigger_rule="none_failed_min_one_success",
    )

    # DAG structure
    health_check >> start_training >> wait_training >> run_evaluation >> branch
    branch >> promote >> done
    branch >> skip >> done
