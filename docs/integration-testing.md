# Integration Testing & Deployment

## End-to-end flow

```text
Login (/login)
    ↓
Dashboard — select cluster from kubeconfig
    ↓
Click Investigate <context>
    ↓
POST /investigate { investigation_id, user_id, cluster_context }
    ↓
Backend persists investigations + investigation_progress
    ↓
kubectl evidence collection (pods, logs, events, deployments, network)
    ↓
AI diagnosis (or healthy-cluster / fallback diagnosis)
    ↓
Realtime progress on investigation:{id}
    ↓
Diagnosis card + history table
```

## API endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Backend health |
| `GET /clusters` | List kubeconfig contexts + reachability |
| `GET /clusters/{context}/health` | Probe one cluster |
| `POST /investigate` | Run full investigation |

## Error handling

| Failure | User-facing behavior |
|---|---|
| Missing kubeconfig | Cluster list shows configuration error |
| Cluster unreachable | Cluster marked unreachable; investigate disabled |
| kubectl failure during run | HTTP 503 with checklist message |
| OpenRouter failure | Warning + fallback diagnosis (investigation still completes) |
| API timeout | Friendly timeout message (10 min client timeout) |
| Healthy cluster | Green diagnosis banner, skips LLM call |

## Local run

```bash
docker compose up --build
```

1. Frontend: http://localhost:3000
2. Backend: http://localhost:8000
3. Place kubeconfig at `backend/.kube/config`
4. Set `KUBECONFIG_PATH=/app/.kube/config` in `backend/.env`

## Verify clusters API

```powershell
Invoke-RestMethod http://localhost:8000/clusters
```

## Verify investigation

```powershell
$id = [guid]::NewGuid().ToString()
$body = @{
  investigation_id = $id
  user_id = "your-user-id"
  cluster_context = "your-context-name"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri http://localhost:8000/investigate -Body $body -ContentType "application/json" -TimeoutSec 600
```

## Failure scenario testing

See [test-scenarios/README.md](test-scenarios/README.md).

Apply manifests on a test cluster, select that context in the dashboard, and run investigate.

## UX states

- **Loading clusters:** "Loading clusters from kubeconfig..."
- **Investigating:** button + progress header show "Investigating Kubernetes Cluster..."
- **Progress steps:** Checking Pods → Reading Logs → Analyzing Events → Inspecting Deployments → Checking Networking → AI Reasoning
- **Healthy cluster:** "No critical Kubernetes issues detected. Cluster appears healthy."
- **Errors:** multi-line beginner-friendly messages (no stack traces in UI)
