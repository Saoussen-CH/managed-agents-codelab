"""Stage 4 solution — inline AGENTS.md + SKILL.md."""
from google import genai
from config import BASE_AGENT, AGENTS_MD, DIGEST_PROMPT, EDITORIAL_VOICE, PDF_SKILL_MD


def main():
    client = genai.Client()

    environment = {
        "type": "remote",
        "sources": [
            {
                "type": "inline",
                "target": ".agents/AGENTS.md",
                "content": AGENTS_MD,
            },
            {
                "type": "inline",
                "target": ".agents/skills/digest-pdf/SKILL.md",
                "content": PDF_SKILL_MD,
            },
        ],
    }

    stream = client.interactions.create(
        agent=BASE_AGENT,
        input=DIGEST_PROMPT,
        system_instruction=EDITORIAL_VOICE,
        environment=environment,
        stream=True,
    )

    env_id = None
    interaction_id = None
    for event in stream:
        print(event)
        if hasattr(event, "interaction") and event.interaction:
            if event.interaction.environment_id:
                env_id = event.interaction.environment_id
            if event.interaction.id:
                interaction_id = event.interaction.id

    print(f"\nEnvironment ID (save for Stage 5): {env_id}")
    print(f"Interaction ID (save for Stage 5): {interaction_id}")


if __name__ == "__main__":
    main()
