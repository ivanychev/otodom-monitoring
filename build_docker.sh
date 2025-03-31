#!/usr/bin/env bash
set -euxo pipefail

export DOCKER_BUILDKIT=1

docker_image=ivanychev/otodom
docker_tag=0.63-test3


docker build . --provenance=false -f Dockerfile --platform=linux/amd64 -t "${docker_image}:${docker_tag}-amd64"
docker build . --provenance=false -f Dockerfile --platform=linux/arm64/v8 -t "${docker_image}:${docker_tag}-aarch64"
docker push "${docker_image}:${docker_tag}-amd64"
docker push "${docker_image}:${docker_tag}-aarch64"
docker manifest create --amend "${docker_image}:${docker_tag}" "${docker_image}:${docker_tag}-amd64" "${docker_image}:${docker_tag}-aarch64"
docker manifest push "${docker_image}:${docker_tag}"
