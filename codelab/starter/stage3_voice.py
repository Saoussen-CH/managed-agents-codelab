"""
Stage 3 — Add an editorial voice with system_instruction.

system_instruction shapes the agent's personality and style for this call.
It is additive with AGENTS.md: both apply when present.

Run this twice with different voices and compare the output.
"""
from google import genai

from config import BASE_AGENT, DIGEST_PROMPT, EDITORIAL_VOICE


def main():
    client = genai.Client()

    # TODO 4: Add system_instruction=EDITORIAL_VOICE to your interactions.create() call.
    # Keep stream=True so you can watch it work.
    # Compare the tone to Stage 2's output.
    #
    # interaction = client.interactions.create(
    #     agent=BASE_AGENT,
    #     input=DIGEST_PROMPT,
    #     system_instruction=EDITORIAL_VOICE,   # <-- new
    #     environment="remote",
    #     stream=True,
    # )
    # for event in interaction:
    #     print(event)
    pass


if __name__ == "__main__":
    main()
