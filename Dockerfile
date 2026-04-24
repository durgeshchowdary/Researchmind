FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY backend .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
