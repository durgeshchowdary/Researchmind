FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY backend/requirements.txt ./requirements.txt

# Install dependencies
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# Copy entire backend
COPY backend ./backend

# Set Python path so "app" works
ENV PYTHONPATH=/app/backend

# HuggingFace default port
EXPOSE 7860

# Start FastAPI
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]