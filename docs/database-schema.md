# InsForge Database Schema

## Tables

### `investigations`

Parent record for each cluster investigation run.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Investigation ID (matches frontend `investigation_id`) |
| `user_id` | TEXT | InsForge authenticated user ID |
| `root_cause` | TEXT | Final root cause (set on completion) |
| `namespace` | TEXT | Primary namespace from evidence |
| `confidence` | INTEGER | AI confidence score (0–100) |
| `status` | TEXT | `running`, `completed`, or `failed` |
| `diagnosis` | JSONB | Full AI diagnosis payload |
| `investigation` | JSONB | Full Kubernetes evidence payload |
| `created_at` | TIMESTAMPTZ | Start timestamp |
| `completed_at` | TIMESTAMPTZ | Finish timestamp |

### `investigation_progress`

Child rows linked to `investigations.id` via `investigation_id` foreign key.

| Column | Type | Description |
|---|---|---|
| `id` | UUID (PK) | Progress row ID |
| `investigation_id` | UUID (FK) | Parent investigation |
| `step` | TEXT | `pods`, `logs`, `events`, `deployments`, `networking`, `ai_diagnosis` |
| `status` | TEXT | `pending`, `running`, `completed`, or `failed` |
| `message` | TEXT | Human-readable step message |
| `details` | JSONB | Optional metadata |
| `created_at` | TIMESTAMPTZ | First seen |
| `updated_at` | TIMESTAMPTZ | Last update |

Unique constraint: `(investigation_id, step)`.

## Relationship

```text
investigations (1) ──< investigation_progress (many)
```

## Write flow

All writes happen in the **backend** using `INSFORGE_API_KEY` (never exposed to the frontend).

1. `POST /investigate` starts → INSERT `investigations` (`status=running`) + pending progress rows
2. Each investigation step → PATCH `investigation_progress` (`running` → `completed`)
3. Realtime channel `investigation:{id}` still publishes live updates (complements DB)
4. On finish → PATCH `investigations` with diagnosis, evidence, `status=completed`, `completed_at`

The frontend only **reads** history via the InsForge SDK.

## Migration

SQL lives in `docs/migrations/002_investigation_progress.sql`.

## Verification

After setting `INSFORGE_API_KEY` in `backend/.env`:

```powershell
$investigationId = [guid]::NewGuid().ToString()
$body = @{
  investigation_id = $investigationId
  user_id = "your-insforge-user-id"
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri http://localhost:8000/investigate -Body $body -ContentType "application/json" -TimeoutSec 600
```

Then in the InsForge dashboard SQL editor:

```sql
SELECT id, status, root_cause, confidence, completed_at
FROM investigations
ORDER BY created_at DESC
LIMIT 5;

SELECT investigation_id, step, status, message, updated_at
FROM investigation_progress
WHERE investigation_id = '<your-investigation-id>'
ORDER BY updated_at;
```

You should see one `investigations` row and six `investigation_progress` rows.
