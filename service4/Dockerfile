FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ffmpeg \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install yt-dlp
RUN wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp && \
    chmod a+rx /usr/local/bin/yt-dlp

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    requests==2.31.0 \
    selenium==4.15.0 \
    instagrapi==2.0.0 \
    tweepy==4.14.0

COPY service4.py .
COPY accounts-config.json .

CMD ["python", "service4.py"]
