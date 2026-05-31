from google import genai
from config import BASE_AGENT

client = genai.Client()

interaction = client.interactions.create(
    agent=BASE_AGENT,
    input="Fetch news.ycombinator.com and list the top 3 story titles.",
    environment="remote",
)

print(interaction.output_text)
print(f"\nEnvironment ID: {interaction.environment_id}")
print(f"Interaction ID: {interaction.id}")
