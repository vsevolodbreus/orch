FROM python:3.10.2-slim-buster

# Install system dependencies
RUN \
  apt-get update && \
  apt-get -y install \
    apt-transport-https  \
    ca-certificates \
    git  \
    curl  \
    gnupg  \
    gnupg1  \
    gnupg2  \
    g++

RUN  apt-get -y install libpq-dev libffi-dev

# Install orch
WORKDIR /orch
RUN mkdir -p src/orch
COPY setup.py setup.py
RUN python -m pip install -e .
COPY . .

# Run
EXPOSE 8000
CMD \
  mkdir -p /var/log/orch && \
  alembic upgrade head && \
  uvicorn --workers "${UVICORN_WORKERS:-1}" --access-log --no-use-colors --host 0.0.0.0 orch:app 2>&1 | \
  tee -a /var/log/orch/orch.log
