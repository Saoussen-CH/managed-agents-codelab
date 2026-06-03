"""Stage 6 solution — save as a managed agent."""
from google import genai
from config import BASE_AGENT, AGENTS_MD, EDITORIAL_VOICE, PDF_SKILL_MD

AGENT_ID = "my-tech-digest"


def main():
    client = genai.Client()

    try:
        client.agents.delete(id=AGENT_ID)
        print(f"Deleted existing agent: {AGENT_ID}")
    except Exception:
        pass

    base_environment = {
        "type": "remote",
        "sources": [
            {"type": "inline", "target": ".agents/AGENTS.md", "content": AGENTS_MD},
            {"type": "inline", "target": ".agents/skills/digest-pdf/SKILL.md", "content": PDF_SKILL_MD},
        ],
    }

    agent = client.agents.create(
        id=AGENT_ID,
        base_agent=BASE_AGENT,
        description="Daily tech digest with editorial voice and PDF skill.",
        system_instruction=EDITORIAL_VOICE,
        base_environment=base_environment,
    )

    print(f"Saved agent: {agent.id}")


if __name__ == "__main__":
    main()
