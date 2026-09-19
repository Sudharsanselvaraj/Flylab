# FlyLab simulation service
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONPATH=/app/services/sim-engine
COPY . /app/services/sim-engine
RUN pip install --no-cache-dir /app/services/sim-engine \
    && python -m playwright install --with-deps chromium
EXPOSE 8050
CMD ["python", "-m", "uvicorn", "hawking_fly.api.app:app", "--host", "0.0.0.0", "--port", "8050"]
