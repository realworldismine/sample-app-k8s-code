# Use an official Python runtime as a base image
FROM python:3.12-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create a virtual environment and activate it
RUN apt-get update && apt-get install -y tzdata python3-venv && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /app/venv

# Upgrade pip
RUN /app/venv/bin/pip install --upgrade pip

# Install any needed packages specified in requirements.txt using the virtual environment
RUN /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TC > /etc/timezone

# Ensure the cleanup runs before the main application
ENTRYPOINT ["sh", "-c", "/app/venv/bin/python -u post.py"]

