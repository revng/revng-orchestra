FROM ubuntu:18.04

COPY install-dependencies.sh /orchestra/.orchestra/ci/install-dependencies.sh
COPY requirements.txt /orchestra/.orchestra/ci/requirements.txt

WORKDIR /orchestra/

RUN .orchestra/ci/install-dependencies.sh \
    && apt-get autoremove --yes --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
