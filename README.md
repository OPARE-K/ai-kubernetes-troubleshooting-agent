# AI Kubernetes Agent

On-demand AI-powered Kubernetes troubleshooting.

## Project Origin

This project was built while following an **AI Kubernetes Agent** tutorial that walks through a FastAPI backend, a Next.js frontend, cluster investigation, and LLM-based diagnosis. After completing the tutorial flow, the project was **extended for a real development environment** where the application runs on a Windows laptop and the Kubernetes cluster runs on a separate Raspberry Pi.

The tutorial codebase remains the foundation. This repository adds remote-cluster access, more resilient diagnosis behavior, and operational documentation for that setup.

## What makes this version different

Compared with a typical local-only tutorial deployment, this version includes:

- **Remote kind cluster on a Raspberry Pi** — the workload cluster runs on ARM edge hardware, not on the same machine as Docker Desktop
- **Windows Docker Desktop backend** — the frontend and FastAPI backend run in containers on Windows
- **SSH tunneling to the Raspberry Pi Kubernetes API** — the Pi kind API listens on localhost; Windows reaches it through a forwarded port
- **Remote kubeconfig mounting** — `backend/.kube/config` is mounted into the backend container at `/app/.kube/config`
- **`tls-server-name` configuration** — the kubeconfig sets `tls-server-name: localhost` so TLS matches the kind API certificate while connecting through the tunnel
- **OpenRouter fallback diagnosis** — when the LLM is unavailable or rate-limited (for example HTTP 429), the app still returns an evidence-based diagnosis from cluster data
- **Workload-priority ranking** — user application failures are prioritized over noisy `kube-system` findings such as high restart counts
- **Failure-aware kubectl recommendations** — suggested commands depend on the failure type (for example, no `kubectl logs --previous` for `ImagePullBackOff` when the container never started)

For step-by-step setup, see [docs/raspberry-pi-kind-setup.md](docs/raspberry-pi-kind-setup.md).

## Architecture

```text
Browser
   │
   ▼
Frontend (Docker, :3000)
   │
   ▼
FastAPI Backend (Docker, :8000)
   │
   ├─► Kubernetes investigation (kubectl)
   │        │
   │        ▼
   │   host.docker.internal:<LOCAL_TUNNEL_PORT>
   │        │
   │        ▼
   │   SSH tunnel (Windows host → Pi localhost:6443)
   │        │
   │        ▼
   │   kind cluster on Raspberry Pi
   │
   └─► AI agent → OpenRouter LLM → diagnosis (+ fallback when LLM unavailable)
```

At a high level:

```text
Frontend → FastAPI Backend → Kubernetes Investigation → AI Agent → LLM → Diagnosis
```

Place your Pi kubeconfig at `backend/.kube/config`, start the SSH tunnel from Windows, and set `server: https://host.docker.internal:<LOCAL_TUNNEL_PORT>` with `tls-server-name: localhost`. Use placeholders in your own notes rather than hardcoding Pi IP addresses in the repository.

## Quick Start

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

For Raspberry Pi cluster access, complete [docs/raspberry-pi-kind-setup.md](docs/raspberry-pi-kind-setup.md) before running an investigation.

## Endpoints

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend homepage |
| http://localhost:8000/health | Backend health check |
| POST http://localhost:8000/investigate | Investigate cluster + AI diagnosis |

Set `OPENROUTER_API_KEY` in `backend/.env` for AI reasoning. Investigations still return evidence-based fallback diagnoses when OpenRouter returns errors such as HTTP 429.

## Dashboard

1. Configure InsForge env vars — see [docs/dashboard-setup.md](docs/dashboard-setup.md)
2. Open http://localhost:3000
3. Sign in, then use the dashboard to investigate and view history

## Project Structure

```text
ai-kubernetes-agent/
├── backend/     # FastAPI orchestrator
├── frontend/    # Next.js UI
├── docs/        # Documentation
└── prompts/     # Development prompts
```

## Local Development (without Docker)

**Backend:**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```
