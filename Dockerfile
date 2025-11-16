# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for headless Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# We use --no-cache-dir to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend and telegram_bot directories into the container at /app
COPY backend/ ./backend/
COPY telegram_bot/ ./telegram_bot/

# Copy the startup script into the container at /app
COPY start.sh .

# Make the startup script executable
RUN chmod +x ./start.sh

# Expose ports
EXPOSE 8001
EXPOSE 8080

# Run the startup script when the container launches
CMD ["./start.sh"]
