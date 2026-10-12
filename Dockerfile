FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY database database
COPY agents agents
COPY exchange_adapters exchange_adapters
COPY risk risk
COPY research research
RUN useradd --uid 10001 --create-home zen
USER zen
CMD ["sh","-c","python -m alembic -c database/alembic.ini upgrade head && python -m uvicorn backend.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
