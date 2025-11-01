FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install google-cloud-bigquery

COPY app ./app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV PROJECT_ID=buildtrace-demo

EXPOSE 8080

CMD ["uvicorn", "app.detect:app", "--host", "0.0.0.0", "--port", "8080"]
