# Raspberry Pi kind Cluster Setup

This guide documents how to run the AI Kubernetes Agent on **Windows (Docker Desktop)** while investigating a **kind** cluster that runs on a **Raspberry Pi**. It is the canonical setup for this fork.

The Pi kind API server listens on **localhost** on the Pi. Windows reaches it through an **SSH tunnel**. The backend container reads a **mounted kubeconfig** that points at `host.docker.internal`, not at a fixed Pi IP address.

> **Do not hardcode IP addresses.** Use environment variables or placeholders such as `<pi-host>` and `<LOCAL_TUNNEL_PORT>` in your own notes and scripts.

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Windows (Docker Desktop)                                                │
│                                                                         │
│  Browser ──► Frontend container (:3000)                                 │
│                  │                                                      │
│                  ▼                                                      │
│            Backend container (:8000)                                    │
│                  │                                                      │
│                  │  kubectl --kubeconfig=/app/.kube/config              │
│                  │  server: https://host.docker.internal:<TUNNEL_PORT>    │
│                  │  tls-server-name: localhost                          │
│                  ▼                                                      │
│            host.docker.internal (Windows host)                          │
│                  │                                                      │
│                  │  SSH tunnel: localhost:<TUNNEL_PORT>                 │
│                  ▼                                                      │
└──────────────────┼──────────────────────────────────────────────────────┘
                   │  SSH (encrypted)
                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Raspberry Pi                                                            │
│                                                                         │
│  SSH tunnel endpoint ──► 127.0.0.1:6443 (kind API server)              │
│                                                                         │
│  kind cluster (e.g. kind-kubernetes-demo-cluster)                       │
│    └── Pods, Deployments, test scenarios                                │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why `host.docker.internal`?** The backend runs inside Docker Desktop. The SSH tunnel listens on the **Windows host**. `host.docker.internal` lets the container reach that host port.

**Why `tls-server-name: localhost`?** kind issues a certificate for `localhost`. You connect through the tunnel, but TLS must validate against the name on the certificate.

---

## Prerequisites

### Windows

- [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) with WSL 2 backend (recommended)
- [OpenSSH client](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse) (for `ssh` and `scp`)
- SSH key access to the Pi (password auth works for lab use, keys are preferred)
- This repository cloned locally
- PowerShell 5.1+ or PowerShell 7+

### Raspberry Pi

- 64-bit Raspberry Pi OS (or another Linux ARM64 distro)
- Enough RAM and disk for kind (4 GB+ RAM recommended)
- Network reachability from Windows over SSH (LAN or VPN)
- A non-root user with `sudo` (examples use `<pi-user>`)
- Internet access to pull container images

---

## Part 1 — Prepare the Raspberry Pi

All commands in this section run **on the Pi** (Linux shell), unless noted otherwise.

### 1. Install standalone kubectl

```bash
# Download the ARM64 kubectl binary (check https://kubernetes.io/releases/ for the latest version)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/arm64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/kubectl

kubectl version --client
```

### 2. Install kind

```bash
# Download kind for ARM64 (check https://github.com/kubernetes-sigs/kind/releases for the latest version)
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.27.0/kind-linux-arm64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind

kind version
```

### 3. Create a named kind cluster

Use a descriptive cluster name so it is easy to pick in the UI and kubeconfig.

```bash
# Example cluster name — choose your own
export KIND_CLUSTER_NAME="kind-kubernetes-demo-cluster"

cat <<EOF | kind create cluster --name "${KIND_CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  apiServerAddress: "127.0.0.1"
  apiServerPort: 6443
EOF
```

Binding the API server to `127.0.0.1` on the Pi is intentional: only local processes (and SSH tunnels) can reach it directly.

Verify on the Pi:

```bash
kubectl cluster-info --context "kind-${KIND_CLUSTER_NAME}"
kubectl get nodes
```

### 4. Export kubeconfig on the Pi

kind writes kubeconfig automatically. Confirm context and server:

```bash
kubectl config get-contexts
kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}{"\n"}'
```

You should see something like:

```text
https://127.0.0.1:6443
```

That address is correct **on the Pi only**. You will change it after copying the file to Windows.

---

## Part 2 — Copy kubeconfig to Windows

Run these commands **on Windows** (PowerShell).

### 1. Create the project kubeconfig directory

```powershell
New-Item -ItemType Directory -Force -Path "C:\path\to\ai-kubernetes-agent\backend\.kube"
```

Replace `C:\path\to\ai-kubernetes-agent` with your actual clone path.

> **Important:** Create `backend\.kube\config` as a **file** before `docker compose up`. If the file is missing, Docker may create `config` as a **directory**, which breaks kubectl.

### 2. Copy kubeconfig with scp

```powershell
$PiHost = "<pi-host>"      # e.g. raspberrypi.local or a LAN hostname — not committed to git
$PiUser = "<pi-user>"
$ProjectRoot = "C:\path\to\ai-kubernetes-agent"

scp "${PiUser}@${PiHost}:/home/${PiUser}/.kube/config" "$ProjectRoot\backend\.kube\config"
```

Linux/macOS equivalent:

```bash
scp <pi-user>@<pi-host>:~/.kube/config ./backend/.kube/config
```

---

## Part 3 — Edit the kubeconfig on Windows

Open `backend\.kube\config` in a text editor. Make these changes for **each** cluster block you intend to use from Docker:

### 1. Set the API server URL

Replace the Pi-local server with the Docker Desktop host and your **local tunnel port**:

```yaml
clusters:
  - cluster:
      server: https://host.docker.internal:<LOCAL_TUNNEL_PORT>
      # certificate-authority-data: <leave unchanged — do not paste keys into docs>
    name: kind-<your-cluster-name>
```

Example using the default API port as the local tunnel port:

```yaml
server: https://host.docker.internal:6443
```

### 2. Set TLS server name

Add `tls-server-name` under the same cluster entry:

```yaml
clusters:
  - cluster:
      server: https://host.docker.internal:<LOCAL_TUNNEL_PORT>
      tls-server-name: localhost
      certificate-authority-data: ...
    name: kind-<your-cluster-name>
```

### 3. Confirm the active context

```yaml
contexts:
  - context:
      cluster: kind-<your-cluster-name>
      user: kind-<your-cluster-name>
    name: kind-<your-cluster-name>
current-context: kind-<your-cluster-name>
```

**Do not commit** `backend/.kube/config` to git. It contains cluster credentials.

---

## Part 4 — SSH tunnel (Windows)

The tunnel must be running **before** you investigate the cluster. It forwards a port on Windows to the kind API on the Pi.

### PowerShell — foreground tunnel

```powershell
$PiHost = "<pi-host>"
$PiUser = "<pi-user>"
$LocalPort = 6443   # must match <LOCAL_TUNNEL_PORT> in kubeconfig

ssh -N -L "${LocalPort}:127.0.0.1:6443" "${PiUser}@${PiHost}"
```

- `-N` — no remote shell, forwarding only
- `-L local:remote` — forward `localhost:<LocalPort>` on Windows to `127.0.0.1:6443` on the Pi

Leave this window open while you work. Use a second terminal for Docker and testing.

### PowerShell — background tunnel (optional)

```powershell
Start-Process ssh -ArgumentList "-N","-L","6443:127.0.0.1:6443","<pi-user>@<pi-host>" -WindowStyle Hidden
```

### Linux/macOS — foreground tunnel

```bash
ssh -N -L 6443:127.0.0.1:6443 <pi-user>@<pi-host>
```

### Verify the tunnel (Windows)

With the tunnel running:

```powershell
Test-NetConnection -ComputerName localhost -Port 6443
```

---

## Part 5 — Docker Compose and backend kubeconfig

`docker-compose.yml` already mounts the kubeconfig and sets `KUBECONFIG_PATH`:

| Host (Windows) | Container |
|---|---|
| `./backend/.kube/config` | `/app/.kube/config` (read-only) |

| Variable | Value |
|---|---|
| `KUBECONFIG_PATH` | `/app/.kube/config` |

Start the stack:

```powershell
cd C:\path\to\ai-kubernetes-agent
docker compose up --build
```

---

## Part 6 — Verify cluster access from the backend container

Replace `<backend-container>` with your running container name (often `ai-kubernetes-agent-backend-1`):

```powershell
docker exec <backend-container> kubectl --kubeconfig=/app/.kube/config get nodes
```

List contexts:

```powershell
docker exec <backend-container> kubectl --kubeconfig=/app/.kube/config config get-contexts
```

Test a specific context (match the name shown in your kubeconfig):

```powershell
docker exec <backend-container> kubectl --kubeconfig=/app/.kube/config --context kind-<your-cluster-name> get pods -A
```

Trigger an investigation:

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/investigate" `
  -Body (@{ cluster_context = "kind-<your-cluster-name>" } | ConvertTo-Json) `
  -ContentType "application/json"
```

---

## Common errors and fixes

| Symptom | Likely cause | What to check |
|---|---|---|
| `connection refused` to API server | SSH tunnel not running, or wrong local port | Start `ssh -N -L ...`; ensure kubeconfig `server` port matches tunnel |
| TLS / hostname mismatch | Missing or wrong `tls-server-name` | Set `tls-server-name: localhost` in kubeconfig cluster block |
| Wrong cluster / empty results | Wrong `current-context` or UI context | `kubectl config get-contexts`; pass `cluster_context` in `/investigate` |
| Pods appear on Docker Desktop, not Pi | kubeconfig points at local Docker Desktop Kubernetes | Confirm `server` is `host.docker.internal:<tunnel-port>`, not `kubernetes.docker.internal` |
| `backend\.kube\config` is a directory | File missing before first `docker compose up` | Delete the directory; copy a real kubeconfig file |
| `Unable to connect to the server` from container | `host.docker.internal` unreachable | Docker Desktop running; tunnel on Windows host; port not blocked by firewall |
| Investigation succeeds on Pi but fails in UI | Tunnel dropped after sleep/reboot | Re-open SSH tunnel; re-run `get nodes` from container |
| `scp` / `ssh` fails | Pi offline, wrong host, or SSH not enabled | Ping or `ssh <pi-user>@<pi-host>` from Windows; enable SSH on Pi |

---

## Daily workflow checklist

1. Power on the Raspberry Pi and confirm kind is running (`kubectl get nodes` on the Pi).
2. Open the SSH tunnel from Windows.
3. Start Docker Compose (`docker compose up`).
4. Verify `kubectl get nodes` from the backend container.
5. Open http://localhost:3000, select the **kind** context, and run **Investigate**.
6. Stop the tunnel when finished (Ctrl+C in the SSH window).

---

## Related documentation

- [kubernetes-runtime.md](kubernetes-runtime.md) — short kubeconfig mount reference
- [test-scenarios/README.md](test-scenarios/README.md) — sample failing workloads to deploy on the Pi cluster
- [integration-testing.md](integration-testing.md) — end-to-end investigation checks
