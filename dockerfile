# Base image
FROM python:3.9-slim-buster

RUN apt-get update && apt-get install -y libpq-dev build-essential

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Set the environment variable for Flask
ENV FLASK_APP=app.py

# Expose the port that Flask runs on
EXPOSE 5000
