FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8765 \
    JOBRADAR_HOST=0.0.0.0 \
    DOCKER_CONTAINER=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install --with-deps chromium

COPY . .

EXPOSE 8765

CMD ["python", "run.py", "--no-browser"]
