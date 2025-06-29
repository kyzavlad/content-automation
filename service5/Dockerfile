FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    flask==3.0.0 \
    requests==2.31.0 \
    google-api-python-client==2.108.0 \
    google-auth==2.23.4 \
    google-auth-httplib2==0.1.1 \
    google-auth-oauthlib==1.1.0

COPY service5.py .
COPY accounts-config.json .

CMD ["python", "service5.py"]
