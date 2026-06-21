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

# Add non-root user for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# bring in the built SPA (frontend/dist is .dockerignore'd from the context above)
COPY --from=frontend /fe/dist ./frontend/dist

# Ensure the user has write permissions for SQLite and Image data
RUN mkdir -p data/images && chown -R user:user $HOME/app

# Switch to the non-root user
USER user

EXPOSE 7860
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
