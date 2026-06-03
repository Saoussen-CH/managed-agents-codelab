# Daily Tech Digest Agent: Workshop

## Build a Managed Agent on the Gemini API — one call, one sandbox, a real PDF

This directory contains all the materials for the hands-on workshop codelab.

### Directory Structure

```
codelab/
├── diagrams/               # Screenshots used in the codelab
├── starter/                # Starter code given to participants
│   ├── backend/            # FastAPI backend — fill in the TODO sections
│   └── frontend/           # React frontend — pre-built, no changes needed
└── solution/               # Complete reference implementation
```

### What Participants Build

A full-stack web app that wraps the Gemini Managed Agents API:

| TODO | File | What you implement |
|---|---|---|
| 1 | `backend/services/agent_client.py` | Create the `genai.Client()` |
| 2 | `backend/services/agent_client.py` | First `interactions.create()` call with `stream=True` |
| 3 | `backend/services/agent_client.py` | Add `system_instruction` + inline `environment.sources` |
| 4 | `backend/services/agent_client.py` | Extract `environment_id` and `interaction_id` from the stream |
| 5 | `backend/services/agent_client.py` | Multi-turn refinement with `previous_interaction_id` |
| 6 | `backend/routes/agents.py` | Save and list managed agents with `agents.create()` |

### Workshop Details

| | |
|---|---|
| **Duration** | ~2 hours |
| **Level** | Intermediate |
| **Environment** | Local (Python + Node.js) |
| **Topics** | Managed Agents API, SSE streaming, inline skills, multi-turn, saved agents |

### Prerequisites for Participants

- Python 3.10+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- Gemini API key with billing — [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)

### Starter Code

The `starter/` directory contains the app participants start from:

- `agent_client.py` has numbered `# TODO` comments guiding through each API concept
- `agents.py` has TODOs for the agent management endpoints
- The frontend, FastAPI routing, SSE streaming, and PDF generation are pre-built
- Participants run the app immediately — it loads but **Run Digest** fails until the TODOs are complete

### Published Codelab

The official codelab guides participants step by step through each TODO with explanations of the underlying API concepts.

The `solution/` directory is the fully implemented reference. Check it if you get stuck.
