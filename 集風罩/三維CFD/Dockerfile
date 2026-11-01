FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates
RUN sed -i 's|http://ports.ubuntu.com|https://ports.ubuntu.com|g' /etc/apt/sources.list.d/ubuntu.sources
RUN apt-get update && apt-get install -y --no-install-recommends openfoam python3-numpy python3-matplotlib python3-pil && rm -rf /var/lib/apt/lists/*
ENV OMP_NUM_THREADS=1
WORKDIR /analysis
