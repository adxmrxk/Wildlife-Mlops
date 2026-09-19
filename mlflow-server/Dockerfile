FROM python:3.11-slim
RUN pip install --no-cache-dir mlflow boto3
EXPOSE 5001
# --workers 1: the default of 4 gunicorn workers costs ~1.2GB and starves the
# ML service during training on this host. One worker is plenty for local use.
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5001", \
     "--backend-store-uri", "sqlite:////mlflow/mlflow.db", \
     "--default-artifact-root", "s3://wildlife-mlflow/artifacts", \
     "--serve-artifacts", \
     "--allowed-hosts", "mlflow:5001,mlflow,localhost:5001,localhost,127.0.0.1:5001", \
     "--workers", "1"]
