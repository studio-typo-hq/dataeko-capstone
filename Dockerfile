# Stage 1: build dependencies
FROM python:3.13-slim AS builder

WORKDIR /build

COPY api/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: runtime image
FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /install /usr/local

COPY api ./api
COPY ingest ./ingest
COPY data ./data

EXPOSE 8000

CMD ["flask", "--app", "api/app.py", "run", "--host", "0.0.0.0", "--port", "8000"]
