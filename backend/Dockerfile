# Stage 1: Build Stage - Install dependencies
# Use an official Python image with build tools
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies required by psycopg2 (PostgreSQL driver)
# This keeps our final image clean from build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy and install Python requirements
# This is done before copying the app code to leverage Docker's layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---

# Stage 2: Final Stage - Create the production image
# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Set working directory
WORKDIR /code

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code
COPY ./app /code/app
COPY ./scripts /code/scripts
COPY alembic.ini /code/alembic.ini

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

RUN chmod +x /code/scripts/docker-entrypoint.sh
RUN chmod +x /code/scripts/prestart.sh

# Expose the port the app runs on (must match the Uvicorn command)
EXPOSE 8000

# Set the entrypoint
ENTRYPOINT ["/code/scripts/docker-entrypoint.sh"]

# The default command to be executed by the entrypoint
# This will be passed as "$@" to the entrypoint script
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
