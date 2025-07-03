FROM ubuntu:24.04 AS base

RUN --mount=type=cache,target=/var/cache/apt,id=apt \
    --mount=type=cache,target=/var/lib/apt/lists,id=apt-list \
    export DEBIAN_FRONTEND="noninteractive" \
    && apt update \
    && apt install -y \
    # Basic utilities
    vim \
    git \
    curl \
    wget \
    build-essential

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /bin/uv
ENV UV_LINK_MODE='copy'

WORKDIR /workdir
