FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (needed to exec into mcpjungle container)
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py .
COPY index.html .

# Expose port
EXPOSE 5000

# Run Flask app
CMD ["python", "app.py"]
