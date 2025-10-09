# Docker Reference Guide

A compact guide to understand how Docker works in the MTG JudgeBot project — what it does, how it runs, and why it's useful.

## What Docker Is

Docker is a containerization platform that packages code, dependencies, environment variables, and runtime into a single image that can run identically on any machine.

Instead of "install Python, Redis, and all libraries manually," Docker creates isolated containers that include everything your app needs.

## Key Concepts

| Term | Description |
| --- | --- |
| Image | A static, read-only snapshot of your app (like a template or recipe) |
| Container | A live instance of an image (a running process using the recipe) |
| Dockerfile | Instructions to build an image (a step-by-step recipe) |
| Docker daemon | The background service that builds and runs containers |
| Docker client (CLI) | The command-line tool you use (`docker`, `docker compose`) |
| Docker Compose | A YAML tool to define and run multiple containers together |

## The Docker Daemon

The daemon (`dockerd`) is the always-running engine that handles the heavy lifting:
- Builds images from Dockerfiles
- Starts/stops containers
- Manages networking between containers
- Mounts volumes, ports, etc.

The CLI (`docker`) is just a front-end — it sends commands to the daemon through a local socket: `/var/run/docker.sock`.

If you see:

```text
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

It means the daemon isn't running (e.g., Docker Desktop isn't open).

## Build vs Run

Docker separates building and running:

| Phase | Command | Description |
| --- | --- | --- |
| Build | `docker build -t myapp .` | Reads your Dockerfile and creates an image with dependencies baked in. |
| Run | `docker run -p 8501:8501 myapp` | Starts a container (a running instance) from that image. |

Think of it as: _Bake once (build), serve many slices (run)._ You can build manually or let Compose do it automatically.

## Docker Compose Overview

`docker-compose.yml` defines what to build and how to run each part of your system.

Example from this project:

```yaml
services:
  proxy:
    build: ./proxy
    ports:
      - "8080:8080"
    env_file: .env
    depends_on:
      - redis

  redis:
    image: redis:7.2
    ports:
      - "6379:6379"

  streamlit:
    build: .
    ports:
      - "8501:8501"
    env_file: .env
    depends_on:
      - proxy
```

Each block (`proxy`, `redis`, `streamlit`) describes one service:
- If it has `build:` → Docker builds it from a Dockerfile.
- If it has `image:` → Docker pulls it from Docker Hub.
- `depends_on` ensures startup order.
- `ports` expose internal ports to your host machine.

## The Magic Command: `docker compose up --build`

This single command:
1. Reads `docker-compose.yml`
2. Builds any services with a `build:` key
3. Pulls images for any with an `image:` key
4. Starts (runs) all containers
5. Streams their logs together in your terminal

When you see:

```text
[+] Building 15.7s (12/12) FINISHED
[+] Running 3/3
```

It means:
- "Building" → created the images
- "Running" → launched them as live containers

### Common Commands

```bash
# Run without rebuilding
docker compose up

# Stop everything
docker compose down

# Run in background
docker compose up -d
```

## Running and Stopping Containers (TL;DR)

- **`docker compose up --build`**  
  Builds images and runs all containers in the foreground. Shows logs in your terminal.

- **`Ctrl + C`**  
  Gracefully stops all running containers started by `docker compose up`. Equivalent to `docker compose down`.

- **`docker compose up -d --build`**  
  Builds images and runs containers in detached (background) mode so you can continue using your terminal.

- **`docker compose down`**  
  Stops and removes all containers and networks created by `docker compose up -d`.

- **Stopping containers in Docker Desktop**  
  Clicking "Stop" in Docker Desktop performs the same action as `docker compose down`.

- **`docker compose logs -f`**  
  Streams logs from all containers while running in detached mode.

### In Short

- Use `docker compose up` for foreground runs (`Ctrl + C` to stop).
- Use `docker compose up -d` and `docker compose down` for background runs.
- Either method is functionally identical — only visibility and control differ.

## Sharing and Portability

Docker is the reason you can share this project and have it "just work" anywhere.

**Without Docker:**
- Others must install Python, Redis, dependencies, correct versions, etc.
- Platform inconsistencies cause errors.

**With Docker:**
- The environment is pre-packaged in images.
- Running one command sets up everything.

### Sharing Options

1. **Share the repo** — someone can clone and run:
   ```bash
   docker compose up --build
   ```

2. **Publish your image (optional):**
   ```bash
   docker build -t yourname/mtg-judgebot:latest .
   docker push yourname/mtg-judgebot:latest
   ```
   
   Then anyone can run:
   ```bash
   docker run -p 8501:8501 yourname/mtg-judgebot:latest
   ```

## Docker Commands Cheat Sheet

| Purpose | Command |
| --- | --- |
| Build all images | `docker compose build` |
| Run everything (build + start) | `docker compose up --build` |
| Stop everything | `docker compose down` |
| Run in background | `docker compose up -d` |
| List running containers | `docker ps` |
| View logs | `docker compose logs -f` |
| Clean up stopped containers & images | `docker system prune` |

## Typical Workflow for MTG JudgeBot

1. Make sure Docker Desktop is running (the whale icon).
2. In the repo root, run:
   ```bash
   docker compose up --build
   ```
3. Visit:
   - Streamlit app → [http://localhost:8501](http://localhost:8501)
   - Proxy health check → [http://localhost:8080/health](http://localhost:8080/health)
4. When done:
   ```bash
   docker compose down
   ```

## Visual Overview

```text
[ Streamlit App ]  →  [ LLM Proxy (FastAPI) ]  →  [ OpenAI API ]
│                        │
└──> (via Docker network) └──> [ Redis Cache ]
```

Each block is a container managed by Docker Compose. They all run on a shared internal network, exposing only the ports you map.

## In Summary

Docker gives you:
- **Reproducibility**
- **Portability**
- **Clean isolation**
- **Simple orchestration**