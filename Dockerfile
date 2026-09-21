FROM python:3.13-slim AS dependencies

WORKDIR /app

COPY api/requirements.txt ./api/requirements.txt
COPY ingest/requirements.txt ./ingest/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt -r ingest/requirements.txt

FROM python:3.13-slim

WORKDIR /app
COPY --from=dependencies /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY . .

EXPOSE 8000
CMD ["flask", "--app", "api/app.py", "run", "--host", "0.0.0.0", "--port", "8000"]
