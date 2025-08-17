# Use a slim, recent version of Python
FROM python:3.11-slim as base

# Set environment variables to prevent writing .pyc files and to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment to isolate dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the entire application source code into the container first
COPY . .

# Install the project and its dependencies defined in pyproject.toml
# Now all source files (like 'domains/') are available for the build process.
RUN pip install --no-cache-dir .

# Expose the port that the application will run on
EXPOSE 8000

# The command to run the application using uvicorn
# --host 0.0.0.0 is required to make the application accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]