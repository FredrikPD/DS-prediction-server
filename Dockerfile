FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage cache
COPY backend/requirements.txt /app/backend/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend and frontend
COPY backend /app/backend
COPY frontend /app/frontend

# Copy run script
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

# Environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Start command
CMD ["./run.sh"]
