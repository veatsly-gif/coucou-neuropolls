FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data

COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt

COPY bot.py config.py parser.py ./

CMD ["python", "bot.py"]
