# Use an official lightweight Python image.
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
WORKDIR /app
COPY . ./

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
# Cloud Run sets the PORT environment variable.
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1
