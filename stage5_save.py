from google import genai
from config import AGENTS_MD, EDITORIAL_VOICE, PDF_SKILL

AGENT_ID = "my-tech-digest"

client = genai.Client()

# Delete existing agent if present so this script is safely re-runnable
try:
    client.agents.delete(id=AGENT_ID)
    print(f"Deleted existing agent: {AGENT_ID}")
except Exception:
    pass

agent = client.agents.create(
    id=AGENT_ID,
    base_agent="antigravity-preview-05-2026",
    description="Daily tech news digest as a PDF.",
    system_instruction=EDITORIAL_VOICE,
    base_environment={
        "type": "remote",
        "sources": [
            {
                "type": "inline",
                "target": ".agents/skills/digest-pdf/SKILL.md",
                "content": PDF_SKILL,
            },
            {
                "type": "inline",
                "target": ".agents/AGENTS.md",
                "content": AGENTS_MD,
            },
        ],
    },
)

print(f"Saved agent: {agent.id}")

result = client.interactions.create(
    agent="my-tech-digest",
    input="Today's digest. Sources: HN, Verge, TechCrunch.",
    environment="remote",
)
print(result.output_text)
