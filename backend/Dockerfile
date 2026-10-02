FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# sqlite db + uploaded avatars live here — mount a volume on /app/data
RUN mkdir -p /app/data

EXPOSE 8080
CMD ["python", "main.py"]
