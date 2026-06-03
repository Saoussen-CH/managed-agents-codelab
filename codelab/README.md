# Build a Daily Tech Digest Agent — Codelab

## Hands-on workshop: Managed Agents on the Gemini API

In this codelab you will build a managed agent that fetches tech news, summarises it in a sharp editorial voice, and produces a polished PDF — using a single Gemini API call.

---

### What you will build

```
Stage 1 → First agent call (blocking)
Stage 2 → Stream the response live
Stage 3 → Add an editorial voice (system_instruction)
Stage 4 → Mount skills — AGENTS.md + SKILL.md inline
Stage 5 → Multi-turn refinement (same sandbox, new instruction)
Stage 6 → Save as a managed agent (agents.create)
Stage 7 → Invoke the saved agent + download files
```

---

### Duration

| Stage | Topic | Time |
|---|---|---|
| 1 | First call | 10 min |
| 2 | Streaming | 15 min |
| 3 | Editorial voice | 15 min |
| 4 | Skills (AGENTS.md + SKILL.md) | 25 min |
| 5 | Multi-turn refinement | 15 min |
| 6 | Save managed agent | 20 min |
| 7 | Invoke + file download | 15 min |
| | **Total** | **~2 hours** |

---

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- Gemini API key with billing enabled — [aistudio.google.com/api-keys](https://aistudio.google.com/api-keys)
- ~$5 of API credit (each run ≈ $0.50–$1.00)

---

### Setup

```bash
cd codelab/starter
cp .env.example .env
# Edit .env — paste your GEMINI_API_KEY
uv sync
```

---

### Directory structure

```
codelab/
├── README.md               # This file
├── starter/                # Your working directory — fill in the TODOs
│   ├── .env.example
│   ├── pyproject.toml
│   ├── config.py           # Shared constants (pre-filled)
│   ├── stage1_hello.py     # TODO 1-2
│   ├── stage2_stream.py    # TODO 3
│   ├── stage3_voice.py     # TODO 4
│   ├── stage4_skill.py     # TODO 5-6
│   ├── stage5_multiturn.py # TODO 7
│   ├── stage6_save.py      # TODO 8-9
│   └── stage7_invoke.py    # TODO 10-11
└── solution/               # Complete reference implementations
    └── (same files, fully implemented)
```

---

### How to work through the codelab

Each stage file has numbered `# TODO` comments. Read the comment, write the code, run the file, check the output. Each stage builds on the previous.

```bash
# Run a stage
uv run stage1_hello.py

# Peek at the solution if you're stuck
cat ../solution/stage1_hello.py
```

---

### Key concepts covered

| Concept | Stage |
|---|---|
| `client.interactions.create()` | 1 |
| Streaming with `stream=True` + event loop | 2 |
| `system_instruction` for voice/persona | 3 |
| Inline `environment.sources` — AGENTS.md + SKILL.md | 4 |
| `previous_interaction_id` + `environment` reuse | 5 |
| `client.agents.create()` with `base_environment` | 6 |
| Invoking a saved agent + file download API | 7 |
