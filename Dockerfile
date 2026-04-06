FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Install system dependencies including Rust toolchain and build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    pkg-config \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Rust toolchain
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir gunicorn
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Build the Rust extension
# Using pip to install the rust project, which will invoke maturin/setuptools-rust if properly configured in rust_predictor
# Alternatively, if maturin is used: RUN pip install maturin && cd rust_predictor && maturin develop --release
RUN cd rust_predictor && pip install -e .

# Expose port
EXPOSE $PORT

# Command to run gunicorn with uvicorn workers for production
CMD gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
