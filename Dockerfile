FROM python:3.13-slim

WORKDIR /app

# Install dependencies first so source-code changes do not
# invalidate the dependency layer.
COPY api/requirements.txt api/requirements.txt

RUN pip install --no-cache-dir -r api/requirements.txt

# Copy application source after dependencies.
COPY . .

EXPOSE 8000

CMD ["flask", "--app", "api/app.py", "run", "--host", "0.0.0.0", "--port", "8000"]
