FROM python:3.13-slim AS builder

WORKDIR /build

COPY api/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.13-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

EXPOSE 8000

CMD ["flask", "--app", "api/app.py", "run", "--host", "0.0.0.0", "--port", "8000"]
