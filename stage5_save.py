from google import genai
from config import AGENTS_MD, EDITORIAL_VOICE, PDF_SKILL

client = genai.Client()

agent = client.agents.create(
    id="my-tech-digest",
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
