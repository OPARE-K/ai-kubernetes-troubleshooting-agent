# AI Kubernetes Agent

On-demand AI-powered Kubernetes troubleshooting.

This fork extends the original tutorial with **remote edge-cluster investigations** — the UI and FastAPI backend run in Docker Desktop on Windows, while the Kubernetes cluster runs on a **Raspberry Pi kind** cluster reached through an **SSH tunnel**.

## Architecture

```text
Frontend → FastAPI Backend → Kubernetes Investigation → AI Agent → LLM → Diagnosis
```

### Remote Raspberry Pi Cluster

```text
┌────────────── Windows (Docker Desktop) ──────────────┐
│  Browser → Frontend (:3000) → Backend (:8000)        │
│       Backend kubectl → host.docker.internal:<port>  │
│              │                                       │
│       SSH tunnel (localhost:<port> → Pi:6443)        │
└──────────────┼───────────────────────────────────────┘
               ▼
┌────────────── Raspberry Pi ──────────────────────────┐
│  kind API (127.0.0.1:6443) → demo / test workloads   │
└──────────────────────────────────────────────────────┘
```

**Setup guide:** [docs/raspberry-pi-kind-setup.md](docs/raspberry-pi-kind-setup.md)

Place your Pi kubeconfig at `backend/.kube/config`, run an SSH tunnel from Windows, and set `server: https://host.docker.internal:<LOCAL_TUNNEL_PORT>` with `tls-server-name: localhost`. Do not hardcode Pi IP addresses in the repository.

## Differences from the original tutorial

| Area | Original tutorial | This fork |
|---|---|---|
| Cluster location | Local kind or Docker Desktop Kubernetes | **kind on Raspberry Pi** (edge / ARM) |
| API access | Direct localhost kubeconfig | **SSH tunnel** from Windows to Pi localhost API |
| kubeconfig | Local `server` URL | **`host.docker.internal` + `tls-server-name: localhost`** for container access |
| AI availability | LLM required for every diagnosis | **OpenRouter fallback diagnosis** when the LLM is rate-limited or unavailable |
| Finding priority | All problematic pods treated equally | **Workload-priority ranking** — user app failures before kube-system noise |
| Suggested commands | Generic `kubectl describe` | **Failure-aware kubectl recommendations** (e.g. no `logs --previous` for ImagePullBackOff) |

## Quick Start

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

For Pi cluster access, complete [docs/raspberry-pi-kind-setup.md](docs/raspberry-pi-kind-setup.md) before investigating.

## Endpoints

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend homepage |
| http://localhost:8000/health | Backend health check |
| POST http://localhost:8000/investigate | Investigate cluster + AI diagnosis |

Set `OPENROUTER_API_KEY` in `backend/.env` (from InsForge dashboard) for AI reasoning. Investigations still return evidence-based fallback diagnoses when OpenRouter returns errors such as HTTP 429.

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
