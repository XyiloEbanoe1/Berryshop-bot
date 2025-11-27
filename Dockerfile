FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости Linux (aiohttp без этого не работает)
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev

COPY requirements.txt /app/

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /app/

ENV PYTHONUNBUFFERED=1
ENV PORT=10000

CMD ["python", "main.py"]
