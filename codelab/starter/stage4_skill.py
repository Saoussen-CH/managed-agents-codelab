"""
Stage 4 — Mount skills using inline environment sources.

The Antigravity runtime auto-discovers files placed at:
  .agents/AGENTS.md          → persistent behavioural rules
  .agents/skills/<name>/SKILL.md → reusable skill packages

You mount them by passing inline sources in the environment config.
The agent reads them from the sandbox filesystem at runtime.

After this stage the agent will:
  1. Use AGENTS_MD rules (3 stories, Skip This, etc.)
  2. Follow PDF_SKILL_MD instructions to generate digest.pdf
"""
from google import genai

from config import BASE_AGENT, AGENTS_MD, DIGEST_PROMPT, EDITORIAL_VOICE, PDF_SKILL_MD


def main():
    client = genai.Client()

    # TODO 5: Build the environment dict with inline sources.
    # Mount AGENTS_MD at ".agents/AGENTS.md"
    # Mount PDF_SKILL_MD at ".agents/skills/digest-pdf/SKILL.md"
    #
    # environment = {
    #     "type": "remote",
    #     "sources": [
    #         {
    #             "type": "inline",
    #             "target": ".agents/AGENTS.md",
    #             "content": AGENTS_MD,
    #         },
    #         {
    #             "type": "inline",
    #             "target": ".agents/skills/digest-pdf/SKILL.md",
    #             "content": PDF_SKILL_MD,
    #         },
    #     ],
    # }

    # TODO 6: Create the interaction using your environment dict.
    # Save the environment_id for Stage 5.
    #
    # stream = client.interactions.create(
    #     agent=BASE_AGENT,
    #     input=DIGEST_PROMPT,
    #     system_instruction=EDITORIAL_VOICE,
    #     environment=environment,    # <-- new
    #     stream=True,
    # )
    #
    # env_id = None
    # interaction_id = None
    # for event in stream:
    #     print(event)
    #     if hasattr(event, "interaction") and event.interaction:
    #         if event.interaction.environment_id:
    #             env_id = event.interaction.environment_id
    #         if event.interaction.id:
    #             interaction_id = event.interaction.id
    #
    # print(f"\nEnvironment ID (save for Stage 5): {env_id}")
    # print(f"Interaction ID (save for Stage 5): {interaction_id}")
    pass


if __name__ == "__main__":
    main()
