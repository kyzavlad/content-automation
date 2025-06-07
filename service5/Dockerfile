FROM python:3.9-slim

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY service5.py .

EXPOSE 3005
CMD ["python3", "service5.py"]
