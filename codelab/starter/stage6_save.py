"""
Stage 6 — Save as a managed agent.

Once you have iterated on your configuration, save it with agents.create().
This bakes in your voice, AGENTS.md, and SKILL.md permanently so future
calls need no inline configuration — just an agent ID.

Each invocation forks a fresh sandbox from base_environment, so every run
starts clean.

Docs: https://ai.google.dev/gemini-api/docs/custom-agents#save-agent
"""
from google import genai

from config import BASE_AGENT, AGENTS_MD, EDITORIAL_VOICE, PDF_SKILL_MD

AGENT_ID = "my-tech-digest"   # must be lowercase, hyphens only, max 63 chars


def main():
    client = genai.Client()

    # Clean up any previous version of this agent so the script is re-runnable.
    try:
        client.agents.delete(id=AGENT_ID)
        print(f"Deleted existing agent: {AGENT_ID}")
    except Exception:
        pass

    # TODO 8: Build base_environment with your inline sources (same as Stage 4).
    #
    # base_environment = {
    #     "type": "remote",
    #     "sources": [
    #         {"type": "inline", "target": ".agents/AGENTS.md", "content": AGENTS_MD},
    #         {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": PDF_SKILL_MD},
    #     ],
    # }

    # TODO 9: Call client.agents.create() with:
    #   id=AGENT_ID
    #   base_agent=BASE_AGENT
    #   description="Daily tech digest with editorial voice and PDF skill."
    #   system_instruction=EDITORIAL_VOICE
    #   base_environment=base_environment
    #
    # agent = client.agents.create(
    #     id=AGENT_ID,
    #     base_agent=BASE_AGENT,
    #     description="Daily tech digest with editorial voice and PDF skill.",
    #     system_instruction=EDITORIAL_VOICE,
    #     base_environment=base_environment,
    # )
    # print(f"Saved agent: {agent.id}")
    pass


if __name__ == "__main__":
    main()
