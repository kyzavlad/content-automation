FROM python:3.9-slim

RUN pip install --no-cache-dir flask

WORKDIR /app
COPY service4.py .

EXPOSE 3004
CMD ["python3", "service4.py"]
