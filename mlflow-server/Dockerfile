FROM python:3.11-slim
RUN pip install --no-cache-dir mlflow boto3
EXPOSE 5001
CMD ["mlflow", "server", \
     "--host", "0.0.0.0", \
     "--port", "5001", \
     "--backend-store-uri", "sqlite:////mlflow/mlflow.db", \
     "--default-artifact-root", "s3://wildlife-mlflow/artifacts", \
     "--serve-artifacts"]
