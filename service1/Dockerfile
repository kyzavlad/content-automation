FROM python:3.9-slim

# Install system dependencies including yt-dlp and ffmpeg
RUN apt-get update \
    && apt-get install -y wget curl ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

# Install latest yt-dlp from GitHub
RUN curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# Install Python dependencies
RUN pip install --no-cache-dir \
    torch==2.0.1+cpu \
    torchvision==0.15.2+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install additional Python packages
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gdown

# Copy cookies file for authenticated downloads
COPY cookies.txt /cookies.txt

# Copy application
COPY service1.py .

# Create data directory
RUN mkdir -p /data

# Run the application
CMD ["python3", "service1.py"]
