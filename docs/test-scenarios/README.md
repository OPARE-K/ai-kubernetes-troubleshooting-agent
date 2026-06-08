# Kubernetes Failure Test Scenarios

Use these manifests to validate end-to-end troubleshooting on a **non-production** cluster.

All scenarios deploy into namespace `ai-agent-test`.

## Prerequisites

```bash
kubectl config get-contexts
kubectl config use-context <your-test-context>
```

From the dashboard, select the same cluster context before clicking **Investigate**.

## Apply all scenarios

```bash
kubectl apply -f docs/test-scenarios/
```

## Teardown

```bash
kubectl delete namespace ai-agent-test --ignore-not-found
```

---

## Scenario 1 — CrashLoopBackOff

**File:** `01-crashloop.yaml`

**Cause:** Pod references missing environment variable `REQUIRED_API_KEY`.

**Expected diagnosis themes:**
- Root cause: missing env var / config
- Fix: add secret or configmap value and reference it in the deployment

**Verify:**

```bash
kubectl get pods -n ai-agent-test
kubectl logs -n ai-agent-test -l scenario=crashloop --tail=20
```

---

## Scenario 2 — ImagePullBackOff

**File:** `02-imagepull.yaml`

**Cause:** Deployment uses invalid image tag `nginx:does-not-exist-12345`.

**Expected diagnosis themes:**
- Root cause: invalid image tag
- Fix: update deployment image to a valid tag

**Verify:**

```bash
kubectl describe pod -n ai-agent-test -l scenario=imagepull
```

---

## Scenario 3 — OOMKilled

**File:** `03-oomkilled.yaml`

**Cause:** Memory limit too low (`16Mi`) for workload that allocates more memory.

**Expected diagnosis themes:**
- Root cause: container exceeded memory limit
- Fix: increase memory requests/limits

**Verify:**

```bash
kubectl describe pod -n ai-agent-test -l scenario=oomkilled
```

---

## Scenario 4 — Service Selector Mismatch

**File:** `04-service-selector.yaml`

**Cause:** Service selector `app=wrong-label` does not match pod labels `app=backend-api`.

**Expected diagnosis themes:**
- Root cause: service selector does not match pod labels
- Fix: update service selector or pod labels

**Verify:**

```bash
kubectl get endpoints -n ai-agent-test
kubectl get svc,pods -n ai-agent-test --show-labels
```

---

## End-to-end test checklist

1. Sign in at `/login` and verify email if required.
2. Open `/dashboard` and confirm all kubeconfig contexts are listed.
3. Select a reachable cluster.
4. Apply one scenario manifest.
5. Click **Investigate &lt;context&gt;**.
6. Confirm progress steps complete and diagnosis appears.
7. Confirm investigation appears in history.
8. Delete the test namespace and repeat for the next scenario.
