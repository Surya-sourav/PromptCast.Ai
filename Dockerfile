# Use Python slim image
FROM python:3.9-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Start Gunicorn server with gevent worker
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--workers", "1", "--timeout", "300"]
