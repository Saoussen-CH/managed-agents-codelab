from google import genai
from config import BASE_AGENT, EDITORIAL_VOICE, PDF_SKILL

client = genai.Client()

interaction = client.interactions.create(
    agent=BASE_AGENT,
    input="Build today's digest as a PDF. Sources: HN, Verge, TechCrunch.",
    system_instruction=EDITORIAL_VOICE,
    environment={
        "type": "remote",
        "sources": [
            {
                "type": "inline",
                "target": ".agents/skills/digest-pdf/SKILL.md",
                "content": PDF_SKILL,
            }
        ],
    },
)

print(interaction.output_text)
print(f"\nEnvironment ID (pass to download_pdf.py): {interaction.environment_id}")
