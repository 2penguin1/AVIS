# --- stage 1: build the React dashboard ---
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build          # -> /fe/dist

# --- stage 2: python runtime (serves API + built dashboard) ---
FROM python:3.11-slim

# OpenCV / Pillow runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# bring in the built SPA (frontend/dist is .dockerignore'd from the context above)
COPY --from=frontend /fe/dist ./frontend/dist

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
