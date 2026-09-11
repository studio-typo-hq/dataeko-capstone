# Stage 1: Builder stage to install wheels and dependencies
FROM python:3.13-slim AS builder

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r api/requirements.txt
COPY . .

# Stage 2: Final lightweight runtime container
FROM python:3.13-slim

WORKDIR /app

# Copy installed Python dependencies from the builder stage
COPY --from=builder /install /usr/local

# Copy application code into the runtime container
COPY . .

EXPOSE 8000
CMD ["flask", "--app", "api/app.py", "run", "--host", "0.0.0.0", "--port", "8000"]
