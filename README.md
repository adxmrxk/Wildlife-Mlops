# Wildlife MLOps Platform

**End-to-end machine learning platform for automated wildlife species classification.**

Upload an image, get a species prediction back in milliseconds. Behind that simple interaction sits a full MLOps lifecycle: a PyTorch model served by FastAPI, a Spring Boot backend that persists every prediction, an Airflow DAG that trains and promotes new models, an auto-retrain daemon that detects model drift via Prometheus metrics, and Terraform-managed AWS infrastructure to deploy it all.

---

## Table of Contents

- [Project Overview](#project-overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Configuration](#configuration)

---

## Project Overview

### What It Is

A production-grade MLOps platform built around a wildlife species image classifier. It includes everything a real ML system needs: a model serving API, a backend that persists predictions and metadata, a web dashboard for users, event streaming for downstream consumers, experiment tracking, automated retraining triggered by performance drift, and pipeline orchestration that handles training, evaluation, and promotion of new model versions.

### The Problem It Solves

Most ML projects ship a model and stop there. They have no way to know when the model degrades, no path to retrain on new data, no audit trail of which model produced which prediction, and no safe way to push a new model to production.

This platform is built around the lifecycle that those projects ignore:

- **The model degrades silently.** Confidence drops as the data distribution drifts away from what the model was trained on. Nobody notices until users start complaining.
- **Retraining is manual.** Engineers retrain on an ad-hoc cadence, often without comparing the new model to the previous one. Sometimes the new model is worse, but it ships anyway.
- **Deployments are risky.** Replacing a model in production usually means restarting the service. There is no hot-swap, no canary, and no rollback.
- **Predictions are not auditable.** Once a prediction is returned, it is gone. There is no record of which model version produced it or what the input was.

This project addresses each of these gaps with the right component: Prometheus measures drift, the auto-retrain daemon and Airflow DAG handle retraining and promotion based on MLflow-tracked accuracy comparisons, the ML service supports hot-reload of the model from disk without a restart, and every prediction is persisted to PostgreSQL with the model version that produced it.

### What It Does

- Classifies wildlife species from uploaded images using a fine-tuned ResNet50 model
- Generates GradCAM heatmaps showing which parts of the image drove the prediction
- Persists every prediction to PostgreSQL with model version and confidence score
- Caches species lookups in Redis to keep the dashboard snappy
- Publishes prediction events to Kafka for downstream consumers
- Tracks every training run in MLflow with metrics, parameters, and artifacts
- Detects model drift by watching average prediction confidence in Prometheus
- Automatically retrains when confidence drops below a configurable threshold
- Compares new and old model accuracy before promoting; only promotes if accuracy improved
- Hot-reloads the model in production without restarting the service
- Orchestrates the full training, evaluation, and promotion lifecycle through an Airflow DAG
- Provisions the entire AWS stack (VPC, ECS Fargate, RDS, S3, ECR) via Terraform

---

## How It Works

The platform runs as two interlocking loops: a real-time prediction loop that serves users, and a continuous training loop that keeps the model fresh.

### Prediction Loop (Real-Time)

```
        ┌─────────────────────────────┐
        │  React + Vite Frontend      │   User uploads image
        └──────────────┬──────────────┘
                       ▼
        ┌─────────────────────────────┐
        │  Spring Boot Backend        │   POST /api/predictions
        │  Validates, stores image    │
        │  in S3/MinIO, logs metadata │
        └──────────────┬──────────────┘
                       ▼
        ┌─────────────────────────────┐
        │  FastAPI ML Service         │   POST /predict
        │  ResNet50 inference         │
        │  Optional GradCAM heatmap   │
        │  Records Prometheus metrics │
        └──────────────┬──────────────┘
                       ▼
        ┌─────────────────────────────┐
        │  Result + heatmap returned  │
        │  Persisted to PostgreSQL    │
        │  Event published to Kafka   │
        └─────────────────────────────┘
```

### Training Loop (Continuous)

```
        ┌─────────────────────────────┐
        │  Prometheus                  │   Scrapes ML service every 15s
        │  Average confidence metric   │   wildlife_prediction_confidence_score
        └──────────────┬──────────────┘
                       ▼
        ┌─────────────────────────────┐
        │  Auto-Retrain Daemon         │   Polls Prometheus every 60 min
        │  retrain.py                  │   Threshold: confidence < 0.70
        └──────────────┬──────────────┘
                       ▼
                  Drift detected
                       │
                       ▼
        ┌─────────────────────────────┐
        │  Airflow DAG (optional)      │   Manual or scheduled trigger
        │  wildlife_ml_pipeline.py     │   Same lifecycle as daemon
        └──────────────┬──────────────┘
                       ▼
   1.  Trigger training via POST /train
       FastAPI spawns a background thread
       Runs train.py with transfer learning
       Logs run to MLflow tracking server
                       │
                       ▼
   2.  Poll /train/status/{job_id}
       until SUCCESS or FAILED
                       │
                       ▼
   3.  Evaluate via GET /evaluate
       Compare new accuracy vs previous (MLflow)
                       │
              ┌────────┴────────┐
              ▼                 ▼
          IMPROVED          NOT IMPROVED
              │                 │
              ▼                 ▼
   4.  POST /promote         Skip — keep current model
       Hot-reload weights
       No service restart
              │
              ▼
        ┌─────────────────────────────┐
        │  New model live, serving     │
        │  next prediction request     │
        └─────────────────────────────┘
```

---

## Architecture

```
                       ┌──────────────────────────────────────┐
                       │            CLIENT LAYER              │
                       │       React 19 + TypeScript SPA      │
                       └─────────────────┬────────────────────┘
                                         ▼
                       ┌──────────────────────────────────────┐
                       │             API LAYER                │
                       │     Spring Boot 3.3 (Java 17)        │
                       │     REST + Actuator + Validation     │
                       └─────────────────┬────────────────────┘
                                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                       ML LAYER                                │
        │  ┌──────────────────────┐   ┌─────────────────────────────┐  │
        │  │  FastAPI ML Service  │   │  Auto-Retrain Daemon         │  │
        │  │  PyTorch / ResNet50  │   │  retrain.py (Prometheus poll)│  │
        │  │  GradCAM heatmaps    │   │  Triggers training + reload  │  │
        │  │  Hot-reload endpoint │   │                              │  │
        │  └──────────────────────┘   └─────────────────────────────┘  │
        └──────────────────────────────────────────────────────────────┘
                                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                  ORCHESTRATION LAYER                          │
        │  Apache Airflow DAG: train → evaluate → branch → promote      │
        │  MLflow tracking server: experiments, runs, model registry    │
        └──────────────────────────────────────────────────────────────┘
                                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                    MESSAGING LAYER                            │
        │     Kafka (prediction events, feedback pipeline)              │
        └──────────────────────────────────────────────────────────────┘
                                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                      DATA LAYER                               │
        │   PostgreSQL (predictions, species, metadata, JPA-mapped)    │
        │   Redis (species lookup cache, prediction stats, LRU)         │
        │   MinIO / S3 (uploaded images, MLflow artifacts)              │
        └──────────────────────────────────────────────────────────────┘
                                         ▼
        ┌──────────────────────────────────────────────────────────────┐
        │                  OBSERVABILITY LAYER                          │
        │   Prometheus  ──▶  Grafana                                    │
        │   Spring Actuator + Micrometer (backend metrics)              │
        │   prometheus-fastapi-instrumentator (ML service metrics)      │
        └──────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────────────────────┐
        │                  INFRASTRUCTURE LAYER                         │
        │   Terraform: VPC, ECS Fargate, RDS, S3, ECR, CloudWatch       │
        └──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Application Runtime

| Component        | Technology                | Why It's Used |
|------------------|---------------------------|---------------|
| Backend API      | **Spring Boot 3.3 (Java 17)** | Enterprise-grade web framework with first-class JPA, validation, caching, and metrics support |
| ML Service       | **FastAPI + Uvicorn**     | Async-first Python web framework with automatic OpenAPI docs and Pydantic validation |
| ML Model         | **PyTorch + torchvision** | Industry-standard deep learning framework; ResNet50 pretrained on ImageNet provides strong baseline features |
| Frontend         | **React 19 + TypeScript + Vite** | Modern React with Vite for fast dev server and HMR; TypeScript for type safety across the API boundary |
| Auto-Retrain     | **Python daemon**         | Lightweight worker that polls Prometheus, triggers training, and promotes new models |

### Machine Learning

| Component             | Purpose |
|-----------------------|---------|
| **ResNet50 (transfer learning)** | Pretrained ImageNet backbone, fine-tuned on wildlife images with a two-phase frozen-then-unfrozen training strategy |
| **MLflow**            | Tracks every training run with parameters, metrics, and model artifacts; used to compare new models against the previous baseline |
| **GradCAM**           | Generates visual heatmaps showing which pixels drove a prediction; helps users trust the model and helps engineers debug it |
| **Evidently**         | Data drift and model monitoring framework |
| **scikit-learn**      | Classical metrics and preprocessing utilities |
| **DVC**               | Data versioning for reproducible training runs |

### Orchestration

| Tool             | Purpose |
|------------------|---------|
| **Apache Airflow** | Orchestrates the training-to-promotion lifecycle as a DAG. Branches on evaluation: only promotes if accuracy improved. |
| **Auto-Retrain Daemon** | Continuous loop watching Prometheus for drift; complements Airflow with metric-driven triggers |
| **MLflow Model Registry** | Stores model versions, accuracy history, and promotion lineage |

### Data and Storage

| Component       | Purpose |
|-----------------|---------|
| **PostgreSQL 15** | Primary relational store. JPA-mapped entities for predictions, species, model metadata, audit history. |
| **Redis 7**       | Caches species lookups and prediction stats; Spring Cache abstraction with `@Cacheable` annotations |
| **MinIO / S3**    | Object storage for uploaded images and MLflow artifacts. MinIO locally, AWS S3 in production. |

### Messaging

| Component       | Purpose |
|-----------------|---------|
| **Kafka (KRaft)** | Event streaming for prediction events and feedback pipeline. KRaft mode runs without Zookeeper. |
| **Spring Kafka**  | Backend producer for emitting events on every prediction |

### Resilience and Performance

| Component             | Purpose |
|-----------------------|---------|
| **Resilience4j**      | Circuit breakers around calls to the ML service; degrades gracefully if the ML service is down |
| **Spring Cache + Redis** | Server-side caching of repeated reads with `@Cacheable` and `@CacheEvict` |
| **Connection pooling** | HikariCP (Spring Boot default) for PostgreSQL connection management |

### Observability

| Component                              | Purpose |
|----------------------------------------|---------|
| **Prometheus**                         | Scrapes metrics from both the Spring Boot backend and the FastAPI ML service every 15 seconds |
| **Grafana**                            | Pre-provisioned dashboards for prediction volume, confidence distribution, and drift signals |
| **Spring Actuator + Micrometer**       | Exposes backend metrics, health checks, and JVM telemetry at `/actuator/prometheus` |
| **prometheus-fastapi-instrumentator**  | Auto-instruments the ML service with request, latency, and custom prediction metrics |

### Infrastructure as Code

| Tool             | Purpose |
|------------------|---------|
| **Terraform 1.6+** | Provisions the entire AWS stack: VPC with public and private subnets across two AZs, ECS Fargate cluster, RDS PostgreSQL, S3 buckets, ECR repositories, CloudWatch log groups, IAM roles |
| **Docker Compose** | One-command local stack with all 12+ services wired together |

### Tooling and Quality

| Tool                | Purpose |
|---------------------|---------|
| **Maven + JaCoCo**  | Java build and test coverage |
| **pytest**          | Python unit tests for the ML pipeline |
| **GitHub Actions**  | CI on every push, CD pipeline for image builds |
| **Lombok**          | Boilerplate reduction on Java DTOs and entities |

---

## Project Structure

```
wildlife-mlops-platform/
│
├── backend/                          Spring Boot 3.3 backend (Java 17)
│   ├── src/                          Controllers, services, repositories, JPA entities
│   ├── Dockerfile                    Multi-stage Maven build
│   ├── pom.xml                       Maven dependencies and JaCoCo coverage
│   └── mvnw                          Maven wrapper for reproducible builds
│
├── ml-pipeline/                      FastAPI ML service and training code
│   ├── app.py                        FastAPI service: /predict, /reload, /train, /evaluate, /promote
│   ├── train.py                      Training script with transfer learning
│   ├── predict.py                    Standalone inference script
│   ├── retrain.py                    Auto-retrain daemon watching Prometheus
│   ├── organize_data.py              Dataset organization helper
│   ├── create_dummy_model.py         Generates a placeholder model for cold-start dev
│   ├── requirements.txt              Python dependencies
│   ├── Dockerfile                    Container image for the ML service
│   ├── ML_PIPELINE.md                Detailed ML pipeline docs
│   ├── src/
│   │   ├── data/loader.py            WildlifeDataset and DataLoader
│   │   ├── training/trainer.py       WildlifeModel and Trainer classes
│   │   ├── inference/predictor.py    Predictor with GradCAM support
│   │   └── monitoring/monitor.py     PredictionLogger, ModelMonitor, DataQualityChecker
│   ├── tests/                        pytest unit tests
│   ├── data/
│   │   ├── species_mapping.json      Species ID to name lookup
│   │   └── metrics/metrics_log.jsonl Drift detection log
│   └── models/                       Trained model checkpoints (.pt files)
│
├── airflow/
│   └── dags/wildlife_ml_pipeline.py  Train → Evaluate → Branch → Promote DAG
│
├── mlflow-server/
│   └── Dockerfile                    MLflow tracking server image
│
├── frontend/                         React 19 + Vite SPA
│   ├── src/
│   │   ├── App.tsx                   Root component with routing
│   │   ├── main.tsx                  React entry point
│   │   ├── components/Navbar.tsx     Top navigation
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         Overview and stats
│   │   │   ├── Predict.tsx           Image upload and prediction UI
│   │   │   ├── Predictions.tsx       Prediction history table
│   │   │   ├── SpeciesPage.tsx       Per-species detail view
│   │   │   └── System.tsx            System health and metrics view
│   │   ├── services/api.ts           Typed axios client
│   │   └── types/index.ts            Shared TypeScript types
│   ├── nginx.conf                    Production NGINX config
│   ├── Dockerfile                    Multi-stage build (Vite → NGINX)
│   ├── vite.config.ts                Vite dev server config
│   └── package.json
│
├── terraform/                        AWS infrastructure as code
│   ├── main.tf                       VPC, subnets, ECS cluster, IAM roles, CloudWatch
│   ├── ecs.tf                        Fargate task definitions and services
│   ├── ecr.tf                        Container registries for backend, ml-service, frontend
│   ├── rds.tf                        PostgreSQL RDS instance
│   ├── s3.tf                         Buckets for uploads and MLflow artifacts
│   ├── variables.tf                  Inputs (region, environment, project name)
│   └── outputs.tf                    ARNs, endpoints, registry URLs
│
├── grafana/
│   ├── dashboards/wildlife.json      Pre-built wildlife platform dashboard
│   └── provisioning/                 Auto-provisioned datasources and dashboards
│
├── prometheus/
│   └── prometheus.yml                Scrape config for backend and ML service
│
├── .github/workflows/
│   ├── ci.yml                        Build and test on every push
│   └── cd.yml                        Image build and deploy pipeline
│
├── docker-compose.yml                Full local stack (12+ services)
├── BACKEND_DOCUMENTATION.md          Detailed backend API and architecture docs
└── README.md
```

---

## Getting Started

### Prerequisites

You only need Docker installed. Everything else runs in containers.

For frontend development, Node.js 20+ is helpful but not required.

### One-Command Startup

```bash
docker-compose up -d
```

This spins up the full stack: PostgreSQL, Redis, Kafka, MinIO, MLflow, Airflow, the Spring Boot backend, the FastAPI ML service, the React frontend, Prometheus, Grafana, and the auto-retrain daemon.

| Service             | URL                              | Notes |
|---------------------|----------------------------------|-------|
| Frontend            | http://localhost                 | React SPA served by NGINX |
| Backend API         | http://localhost:8080            | Spring Boot REST API |
| Backend actuator    | http://localhost:8080/actuator   | Health, metrics, info |
| ML Service          | http://localhost:8000            | FastAPI |
| ML Service docs     | http://localhost:8000/docs       | Interactive Swagger UI |
| MLflow              | http://localhost:5001            | Experiment tracking |
| Airflow             | http://localhost:8082            | DAG orchestration (admin / admin) |
| MinIO Console       | http://localhost:9001            | S3-compatible storage (minioadmin / minioadmin123) |
| Kafka external port | localhost:9094                   | Producer or consumer access |
| Prometheus          | http://localhost:9090            | Metrics queries |
| Grafana             | http://localhost:3000            | Dashboards (admin / admin) |

### First Prediction

If the model directory is empty, generate a dummy model so the ML service starts cleanly:

```bash
docker exec -it wildlife-ml-service python create_dummy_model.py
```

Then send an image:

```bash
curl -X POST http://localhost:8000/predict \
  -F "image=@/path/to/wildlife.jpg"
```

For an explainable prediction with a GradCAM heatmap overlay:

```bash
curl -X POST "http://localhost:8000/predict?gradcam=true" \
  -F "image=@/path/to/wildlife.jpg"
```

### Triggering Training Manually

```bash
# Kick off async training
curl -X POST http://localhost:8000/train?epochs=10

# Returns: { "job_id": "abc12345", "status": "RUNNING" }

# Poll for completion
curl http://localhost:8000/train/status/abc12345

# Compare the new model to the previous one
curl http://localhost:8000/evaluate

# Promote if accuracy improved (hot-reloads the live model)
curl -X POST http://localhost:8000/promote
```

The Airflow DAG `wildlife_ml_pipeline` automates this entire sequence.

### Tear Down

```bash
docker-compose down -v
```

The `-v` flag removes the persistent volumes (Postgres, Kafka, Redis, MLflow, MinIO, Airflow, Grafana).

---

## API Reference

### ML Service (FastAPI)

| Method | Path                          | Purpose |
|--------|-------------------------------|---------|
| GET    | `/`                           | Service info and endpoint list |
| GET    | `/health`                     | Liveness, model load state, species count, uptime |
| GET    | `/metrics`                    | Prometheus metrics |
| POST   | `/predict`                    | Classify an uploaded image. Optional `?gradcam=true` for heatmap |
| POST   | `/reload`                     | Hot-reload model weights from disk without restart |
| POST   | `/train?epochs=N`             | Spawn an async training job, returns `job_id` |
| GET    | `/train/status/{job_id}`      | Poll training job status (RUNNING / SUCCESS / FAILED) |
| GET    | `/evaluate`                   | Compare latest vs previous model accuracy via MLflow |
| POST   | `/promote`                    | Promote latest model to production (calls `/reload`) |

### Backend (Spring Boot)

| Method | Path                          | Purpose |
|--------|-------------------------------|---------|
| POST   | `/api/predictions`            | Submit image for prediction; persists result, emits Kafka event |
| GET    | `/api/predictions`            | List all predictions with pagination |
| GET    | `/api/predictions/{id}`       | Fetch a single prediction with metadata |
| GET    | `/api/predictions/stats`      | Aggregate stats including average confidence |
| GET    | `/api/species`                | List supported species (Redis-cached) |
| GET    | `/api/species/{id}`           | Species detail view |
| GET    | `/actuator/health`            | Spring Actuator health check |
| GET    | `/actuator/prometheus`        | Backend metrics in Prometheus format |

Full backend documentation in [BACKEND_DOCUMENTATION.md](BACKEND_DOCUMENTATION.md).

---

## Configuration

All configuration is environment-variable driven via `docker-compose.yml` for local development. Production values come from Terraform-managed environment configuration on ECS.

### Backend (Spring Boot)

| Variable                  | Description                       | Default |
|---------------------------|-----------------------------------|---------|
| `SPRING_PROFILES_ACTIVE`  | Active Spring profile             | `docker` |
| `ML_SERVICE_URL`          | FastAPI ML service base URL       | `http://ml-service:8000` |
| `STORAGE_S3_ENDPOINT`     | S3 / MinIO endpoint               | `http://minio:9000` |
| `STORAGE_S3_BUCKET`       | Uploads bucket name               | `wildlife-uploads` |
| `STORAGE_S3_ACCESS_KEY`   | Storage access key                | `minioadmin` |
| `STORAGE_S3_SECRET_KEY`   | Storage secret key                | `minioadmin123` |
| `STORAGE_S3_REGION`       | Storage region                    | `us-east-1` |
| `SPRING_DATA_REDIS_HOST`  | Redis host                        | `redis` |
| `SPRING_DATA_REDIS_PORT`  | Redis port                        | `6379` |

### ML Service (FastAPI)

| Variable                | Description                                  | Default |
|-------------------------|----------------------------------------------|---------|
| `MODEL_PATH`            | Path to PyTorch model weights                | `models/wildlife_model_resnet50.pt` |
| `SPECIES_MAPPING_PATH`  | Species ID-to-name mapping                   | `data/species_mapping.json` |
| `MODEL_VERSION`         | Version string returned in predictions        | `resnet50_v1` |
| `CONFIDENCE_THRESHOLD`  | Below this, predictions flagged low-confidence | `0.5` |
| `MLFLOW_TRACKING_URI`   | MLflow tracking server URL                   | `http://mlflow:5001` |
| `SERVER_PORT`           | Uvicorn port                                 | `8000` |

### Auto-Retrain Daemon

| Variable                       | Description                                | Default |
|--------------------------------|--------------------------------------------|---------|
| `PROMETHEUS_URL`               | Prometheus base URL                        | `http://prometheus:9090` |
| `ML_SERVICE_URL`               | Where to send retrain and reload calls     | `http://ml-service:8000` |
| `MLFLOW_TRACKING_URI`          | Where to log training runs                 | `http://mlflow:5001` |
| `CONFIDENCE_THRESHOLD`         | Retrain when avg confidence drops below    | `0.70` |
| `CHECK_INTERVAL_MINUTES`       | How often to poll Prometheus               | `60` |
| `MIN_PREDICTIONS_FOR_CHECK`    | Don't act until at least this many preds   | `10` |

### Airflow DAG

The `wildlife_ml_pipeline` DAG reads its config from constants at the top of `airflow/dags/wildlife_ml_pipeline.py`:

| Constant            | Description                              | Default |
|---------------------|------------------------------------------|---------|
| `ML_SERVICE`        | ML service base URL                      | `http://ml-service:8000` |
| `TRAINING_TIMEOUT`  | Max seconds before training is aborted   | `7200` (2h) |
| `POLL_INTERVAL`     | Seconds between status checks            | `30` |
| `schedule`          | Cron expression for auto-trigger         | `None` (manual) |
