# Architecture

## Overview

The AI Kubernetes Agent is an on-demand troubleshooting system. Users trigger investigations manually; there is no continuous monitoring or Kubernetes operator.

## Flow

```text
User clicks "Investigate Cluster"
        ↓
API call (FastAPI)
        ↓
Kubernetes investigation layer
        ↓
AI reasoning (OpenRouter via InsForge)
        ↓
Root cause + suggested fix
        ↓
Diagnosis shown in frontend
```

## Components

| Layer | Responsibility |
|-------|----------------|
| **Frontend** | User interface, investigation trigger, diagnosis display |
| **FastAPI Backend** | API orchestration, request routing |
| **Kubernetes Layer** | Cluster inspection (pods, events, logs) |
| **AI Layer** | LLM reasoning over collected cluster data |
| **InsForge** | Backend platform for AI integration (future) |

## Current Status

Foundation only — health endpoint and placeholder modules. Kubernetes and AI logic are not yet implemented.
