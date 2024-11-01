FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . .

# Set the environment variable to production
ENV FLASK_ENV=production

# Run the application using Gunicorn
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--worker-class", "sync", "--timeout", "300"]
