FROM python:3.11-slim@sha256:a25f6aeb42924b56064742e12e8b563c7eb07f1ef18e49a806784680f32d8cfe

ENV DEBIAN_FRONTEND=noninteractive

# build tools: obspy has no arm64 wheel and compiles from source (needs gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# numpy first (obspy's build needs it), then the stack + pytest baked in
# (no-network task -> verifier cannot pip install pytest at runtime)
RUN pip install --no-cache-dir numpy==1.26.4 \
    && pip install --no-cache-dir \
    scipy==1.13.1 \
    obspy==1.4.1 \
    pytest==8.3.2 \
    pytest-json-ctrf==0.3.5

WORKDIR /root
COPY data /root/data
