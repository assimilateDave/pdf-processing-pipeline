FROM python:3.11-slim

# Install system dependencies for Tesseract and other required tools
RUN apt-get update && \
    apt-get install -y tesseract-ocr libtesseract-dev poppler-utils gcc && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY . /app

# Expose the default Flask port
EXPOSE 5000

# Run the main application (default to web server mode)
CMD ["python", "main.py", "--mode", "web", "--host", "0.0.0.0", "--port", "5000"]
