# To build the image, run `docker build` command from the root of the
# repository:
#
#    docker build -f docker/Dockerfile .
#
# There is an optional PYTHON_VERSION build argument which sets the
# version of python to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg PYTHON_VERSION=3.8 .
#
# An optional LIBOLM_VERSION build argument which sets the
# version of libolm to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg LIBOLM_VERSION=3.1.4 .
#


##
## Creating a builder container
##

# We use an initial docker container to build all of the runtime dependencies,
# then transfer those dependencies to the container we're going to ship,
# before throwing this one away
ARG API_KEY
ARG PYTHON_VERSION=3.8
#FROM docker.io/python:${PYTHON_VERSION}-alpine3.11 as builder
FROM python:${PYTHON_VERSION}-buster as builder

RUN echo "${ANY_SCALE_API_KEY}"

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean

RUN pip install --upgrade pip
##
## Build libolm for matrix-nio e2e support
##

# Install libolm build dependencies
ARG LIBOLM_VERSION=3.1.4
RUN apt-get update && apt-get install -y \
    make \
    cmake \
    gcc \
    g++ \
    git \
    libffi-dev \
    libyaml-dev \
    python3-dev

# Build libolm
#
# Also build the libolm python bindings and place them at /python-libs
# We will later copy contents from both of these folders to the runtime
# container
COPY docker/build_and_install_libolm.sh /scripts/
RUN /scripts/build_and_install_libolm.sh ${LIBOLM_VERSION} /python-libs

# Install Postgres dependencies
#apt-get update && apt-get install -y \
#    musl-dev \
#    libpq \
#    postgresql-dev

# Install python runtime modules. We do this before copying the source code
# such that these dependencies can be cached
# This speeds up subsequent image builds when the source code is changed
RUN mkdir -p /src/amicus_bot
COPY amicus_bot/__init__.py /src/amicus_bot/
COPY README.md amicus-bot /src/

RUN apt-get update && apt-get install -y curl build-essential pkg-config
#RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
#ENV PATH="/root/.cargo/bin:${PATH}"
ENV PYTHONPATH="/src/amicus_bot:/src/plugins:${PYTHONPATH}"

# Build the dependencies
COPY setup.py /src/setup.py
RUN pip install --prefix="/python-libs" --no-warn-script-location "/src/.[postgres]"

# Now copy the source code
COPY *.py *.md /src/
COPY amicus_bot/*.py /src/amicus_bot/
COPY plugins/ /src/plugins/

#COPY interfaces/*.py /src/interfaces/

# And build the final module
RUN pip install --prefix="/python-libs" --no-warn-script-location "/src/.[postgres]"

##
## Creating the runtime container
##

# Create the container we'll actually ship. We need to copy libolm and any
# python dependencies that we built above to this container
FROM python:${PYTHON_VERSION}-buster

# Copy python dependencies from the "builder" container
COPY --from=builder /python-libs /usr/local

# Copy libolm from the "builder" container
COPY --from=builder /usr/local/lib/libolm* /usr/local/lib/

# Install any native runtime dependencies
RUN apt-get update && apt-get install -y libpq-dev
RUN apt-get install -y libstdc++6
#RUN pip install matrix-nio[e2e]
#RUN pip install amicus_interfaces
#RUN pip install watchdog

# Specify a volume that holds the config file, SQLite3 database,
# the matrix-nio store, and data's plugins
VOLUME ["/data"]

# Start the bot
ENTRYPOINT ["amicus-bot", "/data/config.yaml"]
