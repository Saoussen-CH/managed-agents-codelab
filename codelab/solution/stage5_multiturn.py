"""Stage 5 solution — multi-turn refinement.
Replace ENV_ID and INTERACTION_ID with values from Stage 4.
"""
from google import genai
from config import BASE_AGENT

ENV_ID = "env_..."        # paste from Stage 4
INTERACTION_ID = "ChB..."  # paste from Stage 4


def main():
    client = genai.Client()

    stream = client.interactions.create(
        agent=BASE_AGENT,
        input="Make the Hacker News section twice as long. Add a one-sentence TL;DR at the very top.",
        environment=ENV_ID,
        previous_interaction_id=INTERACTION_ID,
        stream=True,
    )

    for event in stream:
        print(event)


if __name__ == "__main__":
    main()
