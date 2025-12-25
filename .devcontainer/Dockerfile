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
        build-essential \
        # locale support
        locales \
    # setup locales
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

FROM base as devcontainer

# venv setup
RUN mkdir /uv && chmod 777 /uv
ENV UV_PROJECT_ENVIRONMENT='/uv/venv' \
    UV_PYTHON_BIN_DIR="/uv/python" \
    UV_TOOL_BIN_DIR=/uv/tools/ \
    VIRTUAL_ENV='/uv/venv' \
    PATH="/uv/venv/bin:/uv/tools/:${PATH}:/uv/python" \
    # For the devcontainer, the cache can live inside the devcontainer for convenience
    UV_CACHE_DIR="/uv/cache"

USER ubuntu
WORKDIR /workdir

# Install a bunch of Python versions for convenience
RUN uv python install --no-cache 3.10 3.11 3.12 3.13 3.14
RUN uv tool install --no-cache prek

# Install current project dependencies
RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --all-groups --all-extras --no-install-project
