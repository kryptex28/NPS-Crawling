
# Mistral AI Docker Server
The docker AI server runs Ollama as its backend. The server listens to the port `14000`.

## Important note
To utilize your Nvidia GPU, you have to install the Nvidia Container Toolkit, which allows you to passthrough your GPU to the docker container. This results in faster result generation.
- [Installing Docker and The Docker Utility Engine for NVIDIA GPUs](https://docs.nvidia.com/ai-enterprise/deployment/bare-metal/latest/docker.html)
- Utilization of different vendors like AMD or Apple is not tested and at the current state not foreseen.

## Build container
- Only CPU: `docker compose build`
- With GPU: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml build`

## Run container
- Only CPU: `docker compose up`
- With GPU: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`