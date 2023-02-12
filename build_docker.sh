#!/usr/bin/env bash
set -euxo pipefail

export DOCKER_BUILDKIT=1

docker_image=ivanychev/otodom
docker_tag=0.13

# Install emulators for all CPU architectures.
docker run --privileged --rm tonistiigi/binfmt --install all

# Create a builder instance for multiple architectures.
docker buildx create --name multiplatform_builder || true
docker buildx use multiplatform_builder

docker buildx build \
     --platform linux/arm64/v8,linux/amd64 \
     -f Dockerfile \
     -t "${docker_image}:${docker_tag}" \
     --push \
     .
