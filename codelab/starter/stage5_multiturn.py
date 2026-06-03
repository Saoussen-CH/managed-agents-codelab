"""
Stage 5 — Multi-turn refinement in the same sandbox.

The Interactions API tracks two independent dimensions:
  - Conversation context  →  previous_interaction_id
  - Environment state     →  environment (files, packages, etc.)

Passing both lets you continue a conversation AND reuse the same sandbox.
The PDF from Stage 4 is still at /workspace/digest.pdf.

Replace ENV_ID and INTERACTION_ID below with the values printed by Stage 4.
"""
from google import genai

from config import BASE_AGENT

# Paste the values printed at the end of Stage 4
ENV_ID = "env_..."           # TODO: paste your environment_id here
INTERACTION_ID = "ChB..."    # TODO: paste your interaction_id here


def main():
    client = genai.Client()

    # TODO 7: Call client.interactions.create() using:
    #   agent=BASE_AGENT
    #   input="Make the Hacker News section twice as long. Add a one-sentence TL;DR at the very top."
    #   environment=ENV_ID          ← reuse the sandbox from Stage 4
    #   previous_interaction_id=INTERACTION_ID   ← continue the conversation
    #   stream=True
    #
    # stream = client.interactions.create(
    #     agent=BASE_AGENT,
    #     input="Make the Hacker News section twice as long. Add a one-sentence TL;DR at the very top.",
    #     environment=ENV_ID,
    #     previous_interaction_id=INTERACTION_ID,
    #     stream=True,
    # )
    # for event in stream:
    #     print(event)
    pass


if __name__ == "__main__":
    main()
