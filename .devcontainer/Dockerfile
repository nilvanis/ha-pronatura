FROM mcr.microsoft.com/devcontainers/python:3-3.14-bookworm

# Native libraries used by Home Assistant and its Python dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libffi-dev \
        libjpeg-dev \
        libssl-dev \
        libturbojpeg0 \
        libudev-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Warsaw
