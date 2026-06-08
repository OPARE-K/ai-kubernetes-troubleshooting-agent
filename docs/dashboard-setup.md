# Dashboard + InsForge Setup

## Environment variables

**Frontend** (`frontend/.env`):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_INSFORGE_BASE_URL=https://35dwg74a.eu-central.insforge.app
NEXT_PUBLIC_INSFORGE_ANON_KEY=<from InsForge dashboard or get-anon-key MCP tool>
```

**Backend** (`backend/.env`):

```env
INSFORGE_BASE_URL=https://35dwg74a.eu-central.insforge.app
INSFORGE_API_KEY=<your InsForge project API key>
```

The backend API key is required for:

- Persisting `investigations` and `investigation_progress` rows
- Publishing realtime progress on channel `investigation:{id}`

Do not expose `INSFORGE_API_KEY` in the frontend.

## Database

See [database-schema.md](database-schema.md) for table definitions and verification queries.

Migration SQL: `docs/migrations/002_investigation_progress.sql`

## User flow

1. Sign up / sign in at `/login`
2. Open `/dashboard`
3. Click **Investigate Cluster**
4. Backend creates DB rows and publishes realtime progress
5. View diagnosis and recent investigation history (read from InsForge)
