# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
# gcc and python3-dev are often needed for libraries like Pandas and Shapely
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application (assuming you are using Gunicorn for production,
# or standard manage.py for local development. We'll use the dev server here.)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]