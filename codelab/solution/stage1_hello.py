"""Stage 1 solution — first blocking call."""
from google import genai
from config import BASE_AGENT


def main():
    client = genai.Client()

    interaction = client.interactions.create(
        agent=BASE_AGENT,
        input="Fetch news.ycombinator.com and list the top 3 story titles.",
        environment="remote",
    )

    print(f"Output:\n{interaction.output_text}")
    print(f"\nInteraction ID: {interaction.id}")
    print(f"Environment ID: {interaction.environment_id}")


if __name__ == "__main__":
    main()
