FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

COPY backend ./backend

WORKDIR /app/backend

CMD python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
