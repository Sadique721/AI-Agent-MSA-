# Use official Playwright-capable Python base image
FROM mcr.microsoft.com/playwright:v1.44.0-jammy

# Set work directory
WORKDIR /app

# Install system dependencies for audio and networking
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    portaudio19-dev \
    libasound2-dev \
    adb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose server port
EXPOSE 5000

# Set environment variables for production
ENV FLASK_ENV=production
ENV PORT=5000

# Start server using gevent-websocket for production Socket.IO performance
CMD ["python", "main.py"]
