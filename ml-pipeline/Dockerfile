FROM python:3.11-slim

WORKDIR /app

# Install system dependency for PyTorch (OpenMP for CPU parallelism)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU-only first (large layer - cached separately for faster rebuilds)
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cpu

# Install inference service dependencies
RUN pip install --no-cache-dir \
    fastapi==0.110.0 \
    uvicorn==0.27.0 \
    python-multipart==0.0.9 \
    Pillow==10.2.0 \
    numpy==1.26.4 \
    tqdm \
    mlflow

# Copy application code
COPY app.py .
COPY src/ ./src/
COPY data/species_mapping.json ./data/species_mapping.json
COPY models/wildlife_model_resnet50.pt ./models/wildlife_model_resnet50.pt

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
