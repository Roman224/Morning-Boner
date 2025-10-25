FROM python:3.11-slim

# tzdata pt. fusurile IANA
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Default TZ (poți suprascrie din Railway Variables)
ENV TZ=Europe/Chisinau

# Pornește botul
CMD ["python", "main.py"]
