"""
Stage 1 — Your first agent call (blocking).

The Managed Agents API provisions a Linux sandbox, runs the agent loop,
and returns the result synchronously.

Docs: https://ai.google.dev/gemini-api/docs/managed-agents-quickstart
"""
# TODO 1: Import genai from google
# from google import genai

from config import BASE_AGENT


def main():
    # TODO 2: Create a genai.Client()
    # client = genai.Client()

    # TODO 2: Call client.interactions.create() with:
    #   agent=BASE_AGENT
    #   input="Fetch news.ycombinator.com and list the top 3 story titles."
    #   environment="remote"
    # interaction = client.interactions.create(...)

    # TODO 2: Print interaction.output_text, interaction.id, interaction.environment_id
    # print(f"Output:\n{interaction.output_text}")
    # print(f"\nInteraction ID: {interaction.id}")
    # print(f"Environment ID: {interaction.environment_id}")
    pass


if __name__ == "__main__":
    main()
