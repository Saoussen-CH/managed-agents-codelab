"""
Stage 2 — Stream the response.

For long-running tasks, streaming lets you see the agent work in real time:
each tool call, code execution, and text chunk as it happens.

The stream is an iterable of event objects. Each event has an event_type
attribute (e.g. "step.start", "step.delta", "interaction.completed").

Docs: https://ai.google.dev/gemini-api/docs/managed-agents-quickstart#stream
"""
from google import genai

from config import BASE_AGENT, DIGEST_PROMPT


def main():
    client = genai.Client()

    # TODO 3: Call client.interactions.create() with stream=True.
    # Use BASE_AGENT, DIGEST_PROMPT, and environment="remote".
    # Iterate over the stream and print each event.
    #
    # stream = client.interactions.create(
    #     agent=BASE_AGENT,
    #     input=DIGEST_PROMPT,
    #     environment="remote",
    #     stream=True,
    # )
    # for event in stream:
    #     print(event)
    pass


if __name__ == "__main__":
    main()
