FROM python:3.9-slim

RUN apt-get update \
 && apt-get install -y ffmpeg \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY service2.py .

EXPOSE 3002
CMD ["python3", "service2.py"]
