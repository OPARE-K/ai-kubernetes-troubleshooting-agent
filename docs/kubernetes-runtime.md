# Kubernetes Runtime (Windows Docker → remote cluster)

The backend container reads cluster credentials from a **mounted kubeconfig**. For the **Raspberry Pi kind** setup used in this fork, see the full guide:

**[raspberry-pi-kind-setup.md](raspberry-pi-kind-setup.md)**

## Quick reference

| Item | Value |
|---|---|
| Host kubeconfig path | `backend/.kube/config` |
| Container path | `/app/.kube/config` |
| Environment variable | `KUBECONFIG_PATH=/app/.kube/config` |
| Pi kind API (on Pi) | `https://127.0.0.1:6443` |
| From Docker backend | `https://host.docker.internal:<LOCAL_TUNNEL_PORT>` |
| TLS server name | `localhost` |
| Reachability | SSH tunnel required on Windows |

## Mount wiring

`docker-compose.yml` mounts the project kubeconfig into the backend container:

| Host (Windows) | Container |
|---|---|
| `./backend/.kube/config` | `/app/.kube/config` (read-only) |

Create `backend/.kube/config` as a **file** before the first `docker compose up`. If the file is missing, Docker may create a directory at that path.

## Verify from the backend container

```powershell
docker exec <backend-container> kubectl --kubeconfig=/app/.kube/config get nodes
```

## Troubleshooting

See [raspberry-pi-kind-setup.md — Common errors](raspberry-pi-kind-setup.md#common-errors-and-fixes).
