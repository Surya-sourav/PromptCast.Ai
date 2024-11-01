# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (including ffmpeg)
# '-o APT::Sandbox::User=root' helps avoid permission errors in some environments.
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && apt-get install -y ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app

# Expose the port on which the app will run
EXPOSE 5000

# Run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "--timeout", "120"]
