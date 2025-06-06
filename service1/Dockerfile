# service1/Dockerfile
FROM python:3.9-slim

# 1) системные зависимости
RUN apt-get update \
 && apt-get install -y yt-dlp ffmpeg git \
 && rm -rf /var/lib/apt/lists/*

# 2) CPU-only PyTorch ≈200 MB вместо CUDA-гигантов
RUN pip install --no-cache-dir \
      torch==2.0.1+cpu \
      torchvision==0.15.2+cpu \
      --index-url https://download.pytorch.org/whl/cpu

# 3) Whisper и Flask
RUN pip install --no-cache-dir openai-whisper flask

# 4) Копируем файл куки внутрь образа
COPY ../cookies.txt /cookies.txt

# 5) Рабочая директория
WORKDIR /app

# 6) Копируем код сервиса
COPY service1.py .

# 7) Открываем порт
EXPOSE 3001

# 8) Запуск
CMD ["python3", "service1.py"]
