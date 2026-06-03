"""Stage 3 solution — editorial voice via system_instruction."""
from google import genai
from config import BASE_AGENT, DIGEST_PROMPT, EDITORIAL_VOICE


def main():
    client = genai.Client()

    stream = client.interactions.create(
        agent=BASE_AGENT,
        input=DIGEST_PROMPT,
        system_instruction=EDITORIAL_VOICE,
        environment="remote",
        stream=True,
    )

    for event in stream:
        print(event)


if __name__ == "__main__":
    main()
