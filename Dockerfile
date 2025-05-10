from python:3.10-slim

# Install OS-level dependencies required by OpenCV
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk2.0-dev \
    libboost-all-dev \
    pkg-config \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

workdir /app
copy . /app

copy requirements.txt .
run pip install --upgrade pip setuptools wheel
run pip install -r requirements.txt

expose 5000

cmd python ./app.py