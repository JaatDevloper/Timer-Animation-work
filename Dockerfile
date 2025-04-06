# Use the official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV HOST=0.0.0.0

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p data templates static

# Set up default data if not present
RUN if [ ! -f "data/questions.json" ]; then echo "[]" > data/questions.json; fi
RUN if [ ! -f "data/users.json" ]; then echo "{}" > data/users.json; fi

# Make directories writable for the app user
RUN chmod -R 777 data

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser
USER appuser

# Expose the application port
EXPOSE $PORT

# Healthcheck to ensure application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Start the application using the standalone script
CMD ["python", "standalone.py"]
