ARG BASE_REPO=artifactory.nextgenfed.com/ironbank-proxy
ARG BASE_IMAGE=ironbank/redhat/ubi/ubi10
ARG BASE_TAG=10.2

FROM $BASE_REPO/$BASE_IMAGE:$BASE_TAG AS builder

USER root

WORKDIR /opt/python-logging

# Use the latest Python 3 and pip available from the UBI 10 repositories.
RUN dnf update -y \
    && dnf install -y \
      python3 \
      python3-pip \
    && dnf clean all \
    && rm -rf /var/cache/dnf

COPY pyproject.toml README.md ./
COPY src ./src

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --upgrade pip setuptools wheel \
    && /opt/venv/bin/python -m pip install --no-cache-dir --no-deps . \
    && rm -rf /root/.cache/pip


FROM builder AS test

WORKDIR /opt/python-logging

COPY config ./config
COPY tests ./tests

RUN /opt/venv/bin/python -m pip install --no-cache-dir ".[test]" \
    && /opt/venv/bin/python -m pytest -q


FROM $BASE_REPO/$BASE_IMAGE:$BASE_TAG AS runtime

USER root

WORKDIR /opt/python-logging

# Install the runtime Python from UBI. The project currently has no external
# dependencies, but the virtual environment copied from the builder contains
# the installed project and its console entry point.
RUN dnf update -y \
    && dnf install -y python3 shadow-utils \
    && dnf clean all \
    && rm -rf /var/cache/dnf \
    && useradd --create-home --shell /sbin/nologin --uid 1000 logger

COPY --from=builder /opt/venv /opt/venv
COPY --chown=logger:logger config ./config
COPY --chown=logger:logger src ./src

RUN mkdir -p /tmp/logs/python-logging \
  && chown -R logger:logger /opt/venv /opt/python-logging /tmp/logs

ENV PATH="/opt/venv/bin:${PATH}"

USER logger

ENTRYPOINT ["python", "/opt/python-logging/src/example.py"]
